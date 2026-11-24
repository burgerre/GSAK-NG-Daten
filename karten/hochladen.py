"""#1332 Kartenkacheln nach Cloudflare R2 hochladen und den Katalogabschnitt «karten» schreiben.

#1386 Mehrere Kontinente: Die Zuordnung läuft über `gebiete.gebiete()` (mit Regionen), und der Abschnitt «karten» wird **ergänzt**
statt ersetzt – ein Lauf mit dem Nordamerika-Ordner lässt Europa im Katalog stehen.

Aufruf:
    VERBUND=nordamerika python3 -I karten/hochladen.py <ordner-mit-pmtiles> <stand-jjjj-mm-tt> [--trockenlauf]

`VERBUND` wählt die Gebietstabelle (Standard `europa`), wie beim Verbundbau.

Umgebung (aus GitHub-Secrets des Repositorys burgerre/GSAK-NG-Daten):
    R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT, R2_PUBLIC_BASE
    R2_BUCKET   (optional, Standard «gsak-ng-karten»)

Bewusst ohne Fremdpakete: S3-Signatur (AWS SigV4) und mehrteiliger Upload sind hier knapp zwei Bildschirmseiten
Standardbibliothek. Ein Paket wie boto3 oder rclone müsste auf dem Build-PC installiert und gepflegt werden, und
die Läufe sollen überall gleich funktionieren.

Eigenschaften, die bei Dateien von mehreren Gigabyte zählen:
- mehrteilig mit 64 MB je Teil, jeder Teil einzeln wiederholbar (drei Versuche mit wachsender Wartezeit),
- schon vorhandene Dateien mit gleicher Grösse und gleichem ETag werden übersprungen, ein Lauf lässt sich also
  nach einem Abbruch einfach wiederholen,
- ein abgebrochener mehrteiliger Upload wird abgebrochen gemeldet, nicht stillschweigend liegen gelassen.
"""

import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

TEIL = 64 * 1024 * 1024          # Teilgrösse beim mehrteiligen Upload
VERSUCHE = 3
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"


def jetzt():
    return datetime.now(timezone.utc)


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


class R2:
    """Das Nötigste vom S3-Protokoll: Kopf lesen, einteilig und mehrteilig schreiben."""

    def __init__(self, endpoint, bucket, key_id, secret):
        self.endpoint = endpoint.rstrip("/")
        self.host = urllib.parse.urlparse(self.endpoint).netloc
        self.bucket = bucket
        self.key_id = key_id
        self.secret = secret
        self.region = "auto"

    # ---------- Signatur ----------

    def _sign(self, method, key, query, payload_hash, laenge, extra=None):
        pfad = "/" + self.bucket + "/" + urllib.parse.quote(key)
        t = jetzt()
        amz = t.strftime("%Y%m%dT%H%M%SZ")
        tag = t.strftime("%Y%m%d")
        kopf = {
            "host": self.host,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz,
        }
        if extra:
            kopf.update({k.lower(): v for k, v in extra.items()})
        namen = sorted(kopf)
        can_kopf = "".join(f"{n}:{kopf[n].strip()}\n" for n in namen)
        signed = ";".join(namen)
        can_query = "&".join(
            f"{urllib.parse.quote(k, safe='-_.~')}={urllib.parse.quote(str(v), safe='-_.~')}"
            for k, v in sorted((query or {}).items()))
        canonical = f"{method}\n{pfad}\n{can_query}\n{can_kopf}\n{signed}\n{payload_hash}"
        scope = f"{tag}/{self.region}/s3/aws4_request"
        to_sign = f"AWS4-HMAC-SHA256\n{amz}\n{scope}\n{sha256_hex(canonical.encode())}"

        def h(k, m):
            return hmac.new(k, m.encode(), hashlib.sha256).digest()

        k = h(("AWS4" + self.secret).encode(), tag)
        k = h(k, self.region)
        k = h(k, "s3")
        k = h(k, "aws4_request")
        sig = hmac.new(k, to_sign.encode(), hashlib.sha256).hexdigest()
        kopf["Authorization"] = (f"AWS4-HMAC-SHA256 Credential={self.key_id}/{scope}, "
                                 f"SignedHeaders={signed}, Signature={sig}")
        if laenge is not None:
            kopf["content-length"] = str(laenge)
        url = f"{self.endpoint}{pfad}" + (f"?{can_query}" if can_query else "")
        return url, kopf

    def _ruf(self, method, key, query=None, body=b"", extra=None, erwartet=(200, 204)):
        payload_hash = sha256_hex(body if body else b"")
        url, kopf = self._sign(method, key, query, payload_hash, len(body) if body is not None else None, extra)
        req = urllib.request.Request(url, data=body if body else None, method=method)
        for n, v in kopf.items():
            req.add_header(n, v)
        with urllib.request.urlopen(req, timeout=600) as antwort:
            if antwort.status not in erwartet:
                raise RuntimeError(f"{method} {key}: HTTP {antwort.status}")
            return antwort.status, dict(antwort.headers), antwort.read()

    # ---------- Vorgänge ----------

    def kopf(self, key):
        """Grösse und ETag einer vorhandenen Datei, sonst None."""
        try:
            _, kopf, _ = self._ruf("HEAD", key, erwartet=(200,))
        except urllib.error.HTTPError as e:
            if e.code in (404, 403):
                return None
            raise
        return int(kopf.get("Content-Length", 0)), kopf.get("ETag", "").strip('"')

    def klein_hochladen(self, key, daten, content_type):
        self._ruf("PUT", key, body=daten, extra={"content-type": content_type}, erwartet=(200,))

    def mehrteilig(self, key, pfad, groesse, content_type, melden):
        _, _, body = self._ruf("POST", key, query={"uploads": ""}, extra={"content-type": content_type}, erwartet=(200,))
        upload_id = ET.fromstring(body).findtext(f"{NS}UploadId")
        if not upload_id:
            raise RuntimeError(f"{key}: keine UploadId")
        teile = []
        try:
            with open(pfad, "rb") as f:
                nummer = 0
                geschrieben = 0
                while True:
                    block = f.read(TEIL)
                    if not block:
                        break
                    nummer += 1
                    etag = self._teil(key, upload_id, nummer, block)
                    teile.append((nummer, etag))
                    geschrieben += len(block)
                    melden(geschrieben, groesse)
            xml = "<CompleteMultipartUpload>" + "".join(
                f"<Part><PartNumber>{n}</PartNumber><ETag>\"{e}\"</ETag></Part>" for n, e in teile
            ) + "</CompleteMultipartUpload>"
            self._ruf("POST", key, query={"uploadId": upload_id}, body=xml.encode(),
                      extra={"content-type": "application/xml"}, erwartet=(200,))
        except BaseException:
            # Nie halbe Uploads liegen lassen: sie kosten Speicher und sind unsichtbar
            try:
                self._ruf("DELETE", key, query={"uploadId": upload_id}, erwartet=(204, 200))
                print(f"    abgebrochener Upload aufgeräumt ({key})", flush=True)
            except Exception as ex:          # noqa: BLE001 – Aufräumen darf den eigentlichen Fehler nicht verdecken
                print(f"    Warnung: abgebrochener Upload blieb liegen ({ex})", flush=True)
            raise

    def _teil(self, key, upload_id, nummer, block):
        for versuch in range(1, VERSUCHE + 1):
            try:
                _, kopf, _ = self._ruf("PUT", key, query={"partNumber": nummer, "uploadId": upload_id},
                                       body=block, erwartet=(200,))
                return kopf.get("ETag", "").strip('"')
            except (urllib.error.URLError, RuntimeError, TimeoutError) as ex:
                if versuch == VERSUCHE:
                    raise
                warten = 5 * versuch
                print(f"    Teil {nummer} fehlgeschlagen ({ex}), neuer Versuch in {warten} s", flush=True)
                time.sleep(warten)
        raise RuntimeError("unerreichbar")


def etag_erwartet(pfad, groesse):
    """ETag, das R2 nach unserem Upload führt: einteilig der MD5, mehrteilig «md5-anzahl»."""
    if groesse <= TEIL:
        with open(pfad, "rb") as f:
            return hashlib.md5(f.read(), usedforsecurity=False).hexdigest()
    teile = []
    with open(pfad, "rb") as f:
        while True:
            block = f.read(TEIL)
            if not block:
                break
            teile.append(hashlib.md5(block, usedforsecurity=False).digest())
    return hashlib.md5(b"".join(teile), usedforsecurity=False).hexdigest() + f"-{len(teile)}"


def sha256_datei(pfad):
    h = hashlib.sha256()
    with open(pfad, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


# #1386 Eine Karte unter dieser Grösse ist leer: planetiler schreibt auch ohne Daten einen Kopf. Puerto Rico und die Amerikanischen
# Jungferninseln fehlen im Geofabrik-Kontinentauszug «north-america» und ergaben 0 MB (siehe #1385) – solche Dateien gehören nicht in den
# Katalog, sonst steht da ein Land, dessen Karte nichts zeigt.
MIN_KARTE = 64 * 1024


def gebiete_tabelle():
    """
    #1386 Dateiname → Gebiet (id, land, Name de/en, typ) aus derselben Quelle wie Routing und Höhen.

    Die Zuordnung läuft über `gebiete.gebiete()` statt über die Ländertabelle, damit **Regionen** mitkommen: Die USA und Kanada werden je
    Region geschnitten (`us-california`, `ca-quebec`), weil eine Datei je Land rund 10 GB wäre. Als Schlüssel gelten beide Schreibweisen,
    die vorkommen: die Gebiets-Id (`us-california.pmtiles`, Nordamerika) und der letzte Teil des Geofabrik-Pfads
    (`switzerland.pmtiles`, Europa).
    """
    hier = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(os.path.dirname(hier), "verbund"))
    import gebiete                                     # noqa: PLC0415 – erst hier, der Pfad steht vorher nicht
    tabelle = {}
    for g in gebiete.gebiete():
        eintrag = (g["id"], g["land"], g["name"]["de"], g["name"]["en"], g["typ"])
        tabelle.setdefault(g["id"], eintrag)
        tabelle.setdefault(g["poly"].split("/")[-1], eintrag)
    return tabelle, {l["id"]: l for l in gebiete.laender()}


def abschnitt_zusammenfuehren(alt, neu):
    """
    #1386 Den Abschnitt «karten» **ergänzen** statt ersetzen: Einträge gleicher id (bzw. gleichen Dateinamens) werden ersetzt, fremde
    bleiben. Sonst verschwände mit dem Nordamerika-Ordner Europa aus dem Katalog – die Dateien lägen weiter auf R2, die App zeigte sie
    nicht mehr.
    """
    if not isinstance(alt, dict) or alt.get("format") != neu["format"] or alt.get("schema") != neu["schema"]:
        return neu                                     # anderes Format: lieber neu schreiben als mischen

    def schluessel(e):
        return (e.get("id") or e.get("land") or "") + "|" + (e.get("datei") or "")

    ergebnis = dict(alt)
    neue_dateien = {schluessel(e): e for e in neu["dateien"]}
    dateien = [e for e in alt.get("dateien", []) if schluessel(e) not in neue_dateien]
    dateien += neu["dateien"]
    neue_laender = {l["id"] for l in neu["laender"]}
    laender = [l for l in alt.get("laender", []) if l.get("id") not in neue_laender] + neu["laender"]
    ergebnis.update({k: v for k, v in neu.items() if k not in ("laender", "dateien", "stand")})
    ergebnis["laender"] = laender
    ergebnis["dateien"] = dateien
    # Der Stand des Abschnitts ist der neueste; je Datei steht der eigene Stand ohnehin daneben.
    ergebnis["stand"] = max(alt.get("stand", ""), neu["stand"])
    return ergebnis


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    if len(args) < 2:
        raise SystemExit(__doc__)
    ordner, stand = args[0], args[1]
    katalog_pfad = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "katalog.json")
    trockenlauf = "--trockenlauf" in flags

    endpoint = os.environ["R2_ENDPOINT"]
    basis = os.environ["R2_PUBLIC_BASE"].rstrip("/")
    bucket = os.environ.get("R2_BUCKET", "gsak-ng-karten")
    r2 = R2(endpoint, bucket, os.environ["R2_ACCESS_KEY_ID"], os.environ["R2_SECRET_ACCESS_KEY"])

    tabelle, laender_tabelle = gebiete_tabelle()
    dateien = sorted(f for f in os.listdir(ordner) if f.endswith(".pmtiles"))
    if not dateien:
        raise SystemExit(f"Keine .pmtiles in {ordner}")

    laender, eintraege = [], []
    gesamt = sum(os.path.getsize(os.path.join(ordner, f)) for f in dateien)
    print(f"{len(dateien)} Dateien, {gesamt / 1e9:.1f} GB, Stand {stand}", flush=True)
    begonnen = time.time()
    hochgeladen = 0

    for i, datei in enumerate(dateien, 1):
        pfad = os.path.join(ordner, datei)
        groesse = os.path.getsize(pfad)
        name = datei[:-len(".pmtiles")]
        gebiet = tabelle.get(name)
        if gebiet is None:
            print(f"[{i}/{len(dateien)}] {datei}: kein Gebiet bekannt – übersprungen", flush=True)
            continue
        if groesse < MIN_KARTE:
            # #1386 Leere Karte (kein Auszug im Kontinent-PBF): nicht hochladen und nicht in den Katalog
            print(f"[{i}/{len(dateien)}] {datei}: leer ({groesse} B) – übersprungen", flush=True)
            continue
        key = f"karten/{stand}/{datei}"
        url = f"{basis}/{key}"

        if not trockenlauf:
            vorhanden = r2.kopf(key)
            erwartet = etag_erwartet(pfad, groesse)
            if vorhanden and vorhanden[0] == groesse and vorhanden[1] == erwartet:
                print(f"[{i}/{len(dateien)}] {datei}: schon oben ({groesse / 1e6:.0f} MB)", flush=True)
            else:
                def melden(fertig, ganz, datei=datei, i=i):
                    print(f"\r[{i}/{len(dateien)}] {datei}: {fertig / 1e6:.0f} / {ganz / 1e6:.0f} MB", end="", flush=True)

                t0 = time.time()
                if groesse <= TEIL:
                    with open(pfad, "rb") as f:
                        r2.klein_hochladen(key, f.read(), "application/octet-stream")
                else:
                    r2.mehrteilig(key, pfad, groesse, "application/octet-stream", melden)
                dauer = max(1.0, time.time() - t0)
                print(f"\r[{i}/{len(dateien)}] {datei}: {groesse / 1e6:.0f} MB in {dauer / 60:.1f} min "
                      f"({groesse * 8 / dauer / 1e6:.0f} Mbit/s)   ", flush=True)
                hochgeladen += groesse

        gid, kennung, de, en, typ = gebiet
        if kennung not in {l["id"] for l in laender}:
            aus_tabelle = laender_tabelle.get(kennung, {})
            laender.append({
                "id": kennung,
                "name": aus_tabelle.get("name", {"de": de, "en": en}),
                # #1386 Regionen wie beim Routing; bei kleinen Ländern bleibt die Liste leer
                "regionen": list(aus_tabelle.get("regionen", [])),
            })
        eintraege.append({
            "id": gid, "land": kennung, "name": {"de": de, "en": en}, "datei": datei, "url": url,
            "groesse": groesse, "sha256": sha256_datei(pfad), "stand": stand,
        })

    abschnitt = {
        "format": 1,
        "schema": "openmaptiles",
        "stand": stand,
        "quelle": "OpenStreetMap (Auszüge von Geofabrik), planetiler",
        "attribution": "Karte: © OpenStreetMap contributors, ODbL 1.0",
        "attributionEn": "Map: © OpenStreetMap contributors, ODbL 1.0",
        "lizenz": "ODbL-1.0",
        "minzoom": 0,
        "maxzoom": 14,
        "laender": laender,
        "dateien": eintraege,
    }
    if trockenlauf:
        print(json.dumps(abschnitt, ensure_ascii=False, indent=2)[:2000])
        return

    with open(katalog_pfad, encoding="utf-8") as f:
        katalog = json.load(f)
    katalog["aktualisiert"] = jetzt().strftime("%Y-%m-%dT%H:%M:%SZ")
    # #1386 ergänzen, nicht ersetzen
    katalog["karten"] = abschnitt_zusammenfuehren(katalog.get("karten"), abschnitt)
    with open(katalog_pfad, "w", encoding="utf-8", newline="\n") as f:
        json.dump(katalog, f, ensure_ascii=False, indent=2)
        f.write("\n")

    dauer = time.time() - begonnen
    print(f"Fertig: {len(eintraege)} Gebiete in {len(laender)} Ländern im Katalog, {hochgeladen / 1e9:.1f} GB neu hochgeladen, "
          f"{dauer / 60:.0f} min", flush=True)


if __name__ == "__main__":
    main()
