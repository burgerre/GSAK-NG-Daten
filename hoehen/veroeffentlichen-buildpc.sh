#!/usr/bin/env bash
# #1323 Hoehenkacheln vom Build-PC veroeffentlichen und in katalog.json eintragen.
#
# Zwei Grenzen von GitHub bestimmen den Ablauf:
#   - hoechstens 1000 Anhaenge je Release. Europa hat 1396 Kacheln, darum mehrere Releases
#     «<tag>», «<tag>-teil2», «<tag>-teil3» …  Der Katalog nennt je Kachel die genaue Adresse,
#     fuer die App macht die Aufteilung keinen Unterschied.
#   - die Kommandozeile fasst nicht 1000 Pfade, darum Bloecke von 60 Dateien.
#
# Aufruf: hoehen/veroeffentlichen-buildpc.sh <ordner-mit-kacheln> [<arbeitskopie-daten>] [<Gebietsname fuer den Titel>]
# gh muss angemeldet sein (laeuft unter Windows/Git Bash, nicht in WSL).
#
# #1216: Der Gebietsname steht im Releasetitel (vorher immer «Europa»), schon vorhandene Anhaenge gleicher Groesse
# werden uebersprungen (ein abgebrochener Lauf laesst sich wiederholen), und bei der Ratenbegrenzung von GitHub wartet
# das Skript statt abzubrechen. Der Katalog wird ERGAENZT, nicht ersetzt: ein zweiter Kontinent kommt dazu.
set -euo pipefail
OUT=${1:?Ordner mit den .hgt.gz und hoehen.json}
D=${2:-$(cd "$(dirname "$0")/.." && pwd)}
GEBIET=${3:-Europa}
REPO=burgerre/GSAK-NG-Daten
JE_RELEASE=1000
JE_BLOCK=60
WARTE=${WARTE:-90}        # Sekunden Pause, wenn GitHub die Schreibrate begrenzt
VERSUCHE=${VERSUCHE:-4}

# Ein Aufruf mit Wiederholung: GitHub antwortet bei vielen Uploads kurzzeitig mit 403 («rate limit exceeded»).
mit_geduld() {
  local versuch=1
  until "$@"; do
    if [ $versuch -ge $VERSUCHE ]; then echo "  fehlgeschlagen nach $versuch Versuchen: $*" >&2; return 1; fi
    echo "  Versuch $versuch misslungen, warte ${WARTE}s" >&2
    sleep "$WARTE"
    versuch=$((versuch + 1))
  done
}

STAND=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1],encoding='utf-8'))['stand'])" "$OUT/hoehen.json")
TAG="hoehen-glo90-3s-$STAND"
cd "$OUT"
mapfile -t ALLE < <(ls *.hgt.gz | sort)
echo "== $TAG: ${#ALLE[@]} Kacheln =="

teile=()
i=0; nr=0
while [ $i -lt ${#ALLE[@]} ]; do
  nr=$((nr+1))
  tag=$TAG; [ $nr -gt 1 ] && tag="$TAG-teil$nr"
  teile+=("$tag")
  titel="Höhendaten Copernicus DEM GLO-90 $GEBIET ($STAND)"
  [ "$nr" -gt 1 ] && titel="$titel, Teil $nr"
  gh release view "$tag" --repo "$REPO" >/dev/null 2>&1 || \
    mit_geduld gh release create "$tag" --repo "$REPO" --title "$titel" \
       --notes "Höhendaten für GSAK-NG, 1°-Kacheln im SRTM-HGT-Format (gzip). Die App lädt sie über \`katalog.json\`, Abschnitt \`hoehen\`."
  # hoehen.json gehoert ins letzte Release, darum ein Platz Reserve
  grenze=$JE_RELEASE
  rest=$(( ${#ALLE[@]} - i ))
  [ $rest -le $JE_RELEASE ] && grenze=$((JE_RELEASE - 1))
  teil=("${ALLE[@]:$i:$grenze}")
  # Was schon mit gleicher Groesse oben liegt, wird nicht erneut geschickt
  vorhanden=$(gh release view "$tag" --repo "$REPO" --json assets --jq '.assets[] | .name + ":" + (.size|tostring)' 2>/dev/null || true)
  offen=()
  for f in "${teil[@]}"; do
    groesse=$(stat -c%s "$f" 2>/dev/null || stat -f%z "$f")
    case "$vorhanden" in *"$f:$groesse"*) ;; *) offen+=("$f") ;; esac
  done
  echo "  $tag: ${#offen[@]} von ${#teil[@]} noch zu laden"
  j=0
  while [ $j -lt ${#offen[@]} ]; do
    mit_geduld gh release upload "$tag" --repo "$REPO" --clobber "${offen[@]:$j:$JE_BLOCK}" >/dev/null || exit 1
    j=$((j+JE_BLOCK))
    printf '\r  %s: %d/%d\n' "$tag" "$(( j < ${#offen[@]} ? j : ${#offen[@]} ))" "${#offen[@]}"
    sleep 2
  done
  i=$((i+grenze))
done
letztes=${teile[-1]}
mit_geduld gh release upload "$letztes" --repo "$REPO" --clobber hoehen.json >/dev/null
echo "hoehen.json in $letztes"

python3 - "$OUT/hoehen.json" "$D/katalog.json" "${teile[@]}" <<'PY'
import io, json, os, sys, datetime
quelle, katalog = sys.argv[1], sys.argv[2]
teile = sys.argv[3:]
basis = "https://github.com/burgerre/GSAK-NG-Daten/releases/download/"
h = json.load(io.open(quelle, encoding="utf-8"))
# Jede Kachel bekommt die Adresse des Releases, in dem sie wirklich liegt: Reihenfolge wie beim Hochladen.
namen = sorted(k["name"] for k in h["kacheln"])
wo = {}
i = 0
for nr, tag in enumerate(teile, 1):
    grenze = 1000 if nr < len(teile) else 999
    for name in namen[i:i + grenze]:
        wo[name] = tag
    i += grenze
for k in h["kacheln"]:
    k["url"] = basis + wo[k["name"]] + "/" + k["name"] + ".hgt.gz"
h["release"] = teile[0]
h["release_teile"] = teile
for ziel in (quelle, None):
    if ziel:
        json.dump(h, io.open(ziel, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2)
        io.open(ziel, "a", encoding="utf-8", newline="\n").write("\n")
k = json.load(io.open(katalog, encoding="utf-8"))
k["aktualisiert"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
# #1216 Ergaenzen statt ersetzen: ein zweiter Kontinent kommt dazu, der erste bleibt. Gleiche Kennung ersetzt den
# alten Eintrag. «stand» bleibt der des Katalogs: Quelle und Raster sind gleich, und ein neuer Stand wuerde jedes
# Geraet seine schon geladenen Kacheln fuer veraltet halten lassen (Kennung = Quelle + Raster + Stand).
vorher = k.get("hoehen")
if vorher and vorher.get("kacheln"):
    for feld in ("format", "quelleId", "raster", "kachelformat"):
        if vorher.get(feld) != h.get(feld):
            raise SystemExit("Unterschiedliche %s (%r gegen %r) - die Kacheln passen nicht zusammen"
                             % (feld, vorher.get(feld), h.get(feld)))
    def zusammen(name, schluessel):
        alt_map = {schluessel(x): x for x in vorher.get(name, [])}
        dazu = sum(1 for x in h.get(name, []) if schluessel(x) not in alt_map)
        for x in h.get(name, []):
            alt_map[schluessel(x)] = x
        return list(alt_map.values()), dazu
    laender, laender_dazu = zusammen("laender", lambda x: x["id"])
    gebiete, gebiete_dazu = zusammen("gebiete", lambda x: x["id"])
    kacheln, kacheln_dazu = zusammen("kacheln", lambda x: x["name"])
    stand_alt = vorher.get("stand")
    h = dict(h)
    h["laender"], h["gebiete"], h["kacheln"] = laender, gebiete, kacheln
    h["groesse"] = sum(int(x.get("groesse", 0)) for x in kacheln)
    h["stand"] = stand_alt or h["stand"]
    h["release_teile"] = sorted(set(vorher.get("release_teile", [])) | set(h.get("release_teile", [])))
    h["release"] = h["release_teile"][0] if h["release_teile"] else h.get("release")
    print("Ergaenzt: Laender +%d, Gebiete +%d, Kacheln +%d; Stand bleibt %s"
          % (laender_dazu, gebiete_dazu, kacheln_dazu, h["stand"]))
k["hoehen"] = h
json.dump(k, io.open(katalog, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2)
io.open(katalog, "a", encoding="utf-8", newline="\n").write("\n")
print("Katalog: %d Länder, %d Gebiete, %d Kacheln, %.0f MB, Releases: %s"
      % (len(h["laender"]), len(h["gebiete"]), len(h["kacheln"]), h["groesse"] / 1e6, ", ".join(teile)))
PY
echo "== Katalog geschrieben. Noch zu tun: katalog.json committen und pushen =="
