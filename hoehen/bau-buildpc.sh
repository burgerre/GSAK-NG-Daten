#!/usr/bin/env bash
# #1323 Hoehendaten auf dem Build-PC (Alternative zum Workflow hoehen.yml, wenn die Menge fuer CI zu gross ist).
# #1216 Je Kontinent aufrufbar, weil «europa» hier fest verdrahtet war:
#
#   hoehen/bau-buildpc.sh                # Europa (wie bisher)
#   hoehen/bau-buildpc.sh nordamerika    # Nordamerika (Tabelle in verbund/gebiete.py)
#
# Das Skript laedt NICHTS hoch. Ergebnis: <ZIEL> mit den HGT-Kacheln und hoehen.json fuer den Katalog.
set -euo pipefail
REPO=$(cd "$(dirname "$0")/.." && pwd)
VERBUND=${1:-${VERBUND:-europa}}
export VERBUND            # gebiete.py waehlt damit die Tabelle des Kontinents
ZIEL=${ZIEL:-$HOME/hoehen-$VERBUND-release}
WORK=${ARBEIT:-$HOME/hoehen-$VERBUND}
GDAL=ghcr.io/osgeo/gdal:ubuntu-small-3.9.2
STAND=$(date -u +%F)
TAG="hoehen-glo90-3s-$STAND"
unset VERBUND_GEBIETE   # leer = alle Gebiete des Kontinents
echo "$(date -Is) Hoehendaten fuer $VERBUND, Arbeitsordner $WORK, Ziel $ZIEL"

mkdir -p "$WORK/poly" "$WORK/dem" "$WORK/out"
cd "$REPO"

echo "$(date -Is) == Umrisse holen =="
python3 verbund/gebiete.py --list | while IFS=$'\t' read -r id poly; do
  [ -s "$WORK/poly/$id.poly" ] || curl -fsSL --retry 5 --retry-delay 3 --retry-all-errors \
      -o "$WORK/poly/$id.poly" "https://download.geofabrik.de/${poly}.poly" || echo "FEHLT: $id"
done
echo "Polygone: $(ls "$WORK/poly" | wc -l)"

echo "$(date -Is) == Noetige Kacheln bestimmen =="
python3 hoehen/hoehen.py kacheln "$WORK/poly" "$WORK/kacheln.json"
python3 - "$WORK/kacheln.json" <<'PY'
import json, sys
k = json.load(open(sys.argv[1], encoding="utf-8"))
print("Gebiete:", len(k["gebiete"]), "| Kacheln:", len(k["kacheln"]))
PY

echo "$(date -Is) == DEM-Liste =="
python3 hoehen/hoehen.py dem "$WORK/kacheln.json" glo90 > "$WORK/dem.txt"
echo "DEM-Dateien: $(wc -l < "$WORK/dem.txt")"

echo "$(date -Is) == DEM laden (10 parallel, fehlende = Meer) =="
cd "$WORK"
cut -f1,2 dem.txt | xargs -P 10 -L 1 sh -c 'test -s "dem/$1" || curl -fsS --retry 3 --retry-delay 2 -o "dem/$1" "$0" 2>/dev/null || true'
echo "geladen: $(ls dem | wc -l) Dateien, $(du -sh dem | cut -f1)"

echo "$(date -Is) == HGT bauen =="
sudo -n docker run --rm -v "$WORK:/work" -v "$REPO:/repo" -w /repo "$GDAL" \
  python3 hoehen/hoehen.py bauen /work/kacheln.json glo90 /work/dem /work/out 3s
sudo -n chown -R "$USER" "$WORK/out"
echo "fertig: $(ls "$WORK/out"/*.hgt.gz | wc -l) Kacheln, $(du -sh "$WORK/out" | cut -f1)"

echo "$(date -Is) == Katalog =="
cd "$REPO"
python3 hoehen/hoehen.py katalog "$WORK/kacheln.json" glo90 "$WORK/out" "$STAND" \
  "https://github.com/burgerre/GSAK-NG-Daten/releases/download/$TAG" 3s
python3 - "$WORK/out/hoehen.json" <<'PY'
import json, sys
h = json.load(open(sys.argv[1], encoding="utf-8"))
print("Stand:", h["stand"], "| Raster:", h["raster"], "| Kacheln:", len(h["kacheln"]), "| gesamt: %.0f MB" % (h["groesse"] / 1e6))
for l in h["laender"]:
    gs = [g for g in h["gebiete"] if g["land"] == l["id"]]
    print("  %-6s %-22s %3d Gebiete, %7.1f MB" % (l["id"], l["name"]["de"], len(gs), sum(g["groesse"] for g in gs) / 1e6))
PY

mkdir -p "$ZIEL"
rm -f "$ZIEL"/*.hgt.gz "$ZIEL"/hoehen.json
cp "$WORK/out"/*.hgt.gz "$WORK/out/hoehen.json" "$ZIEL/"
echo "$(date -Is) bereit in $ZIEL: $(ls "$ZIEL" | wc -l) Dateien, $(du -sh "$ZIEL" | cut -f1)"
echo "TAG=$TAG"
