"""Zerlegt einen Valhalla-Kachelbaum (tile_dir) in Download-Teile für GSAK-NG (#442, Paketformat 2).

basis.zip:     Ebenen 0 und 1 des ganzen Verbunds + valhalla.json + tzdata.tar
<gebiet>.zip:  Ebene 2 aller Kacheln, die das Gebietspolygon berühren (Kacheln an Grenzen liegen in beiden Teilen, sie sind identisch)

Jeder Teil enthält gsakng-routing.json (Beschreibung) und die Kacheln unter tiles/<ebene>/<ddd>/<ddd>/<ddd>.gph.
Schreibt out/verbund.json für den Katalog.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import zipfile
from datetime import date

from shapely.geometry import Polygon, box
from shapely.ops import unary_union
from shapely.prepared import prep

sys.path.insert(0, os.path.dirname(__file__))
from gebiete import gebiete, laender  # noqa: E402

# Valhalla-Ebenen: Kantenlänge der Kacheln in Grad
GROESSE = {0: 4.0, 1: 1.0, 2: 0.25}
TILE = re.compile(r"^(\d)/(\d{3})/(\d{3})/(\d{3})\.gph$")


def lese_poly(path):
    """Geofabrik-.poly (Osmosis-Format) → shapely-Fläche; Ringe mit «!» sind Löcher."""
    aussen, loecher, ring, name = [], [], None, None
    with open(path, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    for l in lines[1:]:
        if ring is None:
            name, ring = l, []
        elif l == "END":
            (loecher if name.startswith("!") else aussen).append(ring)
            ring = None
        else:
            lon, lat = map(float, l.split()[:2])
            ring.append((lon, lat))
    flaeche = unary_union([Polygon(r) for r in aussen if len(r) >= 3])
    for r in loecher:
        if len(r) >= 3:
            flaeche = flaeche.difference(Polygon(r))
    return flaeche


def kachel_box(level, tid):
    s = GROESSE[level]
    cols = int(round(360 / s))
    row, col = divmod(tid, cols)
    return box(-180 + col * s, -90 + row * s, -180 + (col + 1) * s, -90 + (row + 1) * s)


def kacheln(tiles):
    """(Ebene, Kachel-ID, relativer Pfad) aller .gph-Dateien."""
    for root, _, files in os.walk(tiles):
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), tiles).replace(os.sep, "/")
            m = TILE.match(rel)
            if m:
                yield int(m.group(1)), int(m.group(2) + m.group(3) + m.group(4)), rel


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def schreibe(out, datei, beschreibung, eintraege, tiles):
    """ZIP mit Beschreibung und Kacheln (Deflate: Kacheln werden etwa auf die Hälfte kleiner)."""
    path = os.path.join(out, datei)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.writestr("gsakng-routing.json", json.dumps(beschreibung, ensure_ascii=False, indent=2))
        for quelle, ziel in eintraege:
            z.write(quelle, ziel)
        for rel in tiles["dateien"]:
            z.write(os.path.join(tiles["root"], rel), "tiles/" + rel)
    return os.path.getsize(path), sha256(path)


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--tiles", required=True)
    a.add_argument("--poly", required=True)
    a.add_argument("--config", required=True)
    a.add_argument("--tzdata", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--verbund", required=True)
    a.add_argument("--osm-date", required=True)
    a.add_argument("--bbox", required=True)
    a.add_argument("--base-url", required=True)
    args = a.parse_args()
    os.makedirs(args.out, exist_ok=True)

    alle = list(kacheln(args.tiles))
    print(f"{len(alle)} Kacheln: " + ", ".join(f"Ebene {l}: {sum(1 for k in alle if k[0] == l)}" for l in sorted({k[0] for k in alle})))
    w, s, e, n = map(float, args.bbox.split(","))
    kopf = {"format": 2, "engine": "valhalla", "engineVersion": "3.9.0", "verbund": args.verbund, "osmDate": args.osm_date,
            "created": date.today().isoformat(), "attribution": "© OpenStreetMap-Mitwirkende (ODbL)"}
    teile = []

    basis = [rel for level, _, rel in alle if level in (0, 1)]
    groesse, sha = schreibe(args.out, "basis.zip", {**kopf, "teil": "basis", "typ": "basis", "bbox": [w, s, e, n]},
                            [(args.config, "valhalla.json"), (args.tzdata, "tzdata.tar")], {"root": args.tiles, "dateien": basis})
    teile.append({"id": "basis", "typ": "basis", "name": {"de": "Grundnetz", "en": "Base network"}, "bbox": [w, s, e, n],
                  "datei": "basis.zip", "url": f"{args.base_url}/basis.zip", "groesse": groesse, "sha256": sha, "kacheln": len(basis), "ebenen": [0, 1]})
    print(f"basis: {len(basis)} Kacheln, {groesse // 1048576} MB")

    ebene2 = [(tid, rel) for level, tid, rel in alle if level == 2]
    for g in gebiete():
        flaeche = lese_poly(os.path.join(args.poly, g["id"] + ".poly"))
        p = prep(flaeche)
        dateien = [rel for tid, rel in ebene2 if p.intersects(kachel_box(2, tid))]
        ids = sorted(tid for tid, rel in ebene2 if p.intersects(kachel_box(2, tid)))
        if not dateien:
            print(f"{g['id']}: keine Kacheln – übersprungen")
            continue
        gw, gs, ge, gn = (round(v, 5) for v in flaeche.bounds)
        datei = f"{g['id']}.zip"
        groesse, sha = schreibe(args.out, datei, {**kopf, "teil": g["id"], "typ": g["typ"], "land": g["land"], "name": g["name"],
                                                  "bbox": [gw, gs, ge, gn]}, [], {"root": args.tiles, "dateien": dateien})
        teile.append({"id": g["id"], "typ": g["typ"], "land": g["land"], "name": g["name"], "bbox": [gw, gs, ge, gn],
                      "datei": datei, "url": f"{args.base_url}/{datei}", "groesse": groesse, "sha256": sha,
                      # Ebene-2-Kacheln des Gebiets: die App prüft damit genau, ob ein Punkt abgedeckt ist (Bounding Boxen überlappen an Grenzen)
                      "kacheln": ids})
        print(f"{g['id']}: {len(dateien)} Kacheln, {groesse // 1048576} MB")
        if groesse > 1900 * 1048576:
            sys.exit(f"{datei} grösser als 1,9 GB – Gebiet aufteilen")

    verbund = {**kopf, "bbox": [w, s, e, n], "laender": laender(), "teile": teile}
    with open(os.path.join(args.out, "verbund.json"), "w", encoding="utf-8") as f:
        json.dump(verbund, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
