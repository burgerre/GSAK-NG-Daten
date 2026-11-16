#!/bin/bash
# Routing-Verbund auf dem Build-PC bauen (#1216). Gleiche Schritte wie der Workflow routing-verbund.yml, aber lokal:
# Der GitHub-Läufer reicht für einen ganzen Kontinent nicht (16 GB Arbeitsspeicher, rund 70 GB Platz – gemessen wurden
# 45 GB Arbeitsspeicher und rund 80 GB Platz für Europa).
#
#   verbund/verbund-lokal.sh europa europe               # ganz Europa (ein Auszug je Land aus gebiete.py)
#   verbund/verbund-lokal.sh nordamerika north-america   # Kontinentauszug am Stück
#
# Das Skript lädt NICHTS hoch und veröffentlicht nichts. Ergebnis: <Arbeitsordner>/out mit basis.zip, je Gebiet einer
# ZIP-Datei und verbund.json für den Katalog. Das Hochladen ist ein eigener, ausdrücklich freizugebender Schritt.
set -u
VERBUND=${1:?Name des Verbunds, z. B. europa}
QUELLE=${2:?Geofabrik-Pfad des Kontinents, z. B. europe}
D=${ARBEIT:-$HOME/verbund-$VERBUND}
REPO=$(cd "$(dirname "$0")/.." && pwd)
IMG=ghcr.io/valhalla/valhalla:3.9.0
MOBILE=0.6.4
# Grenzen wie bei der Messung (Build-PC: 62 GB, 32 Kerne); Valhalla füllt den Speicher als Zwischenspeicher
SPEICHER=${SPEICHER:-46g}
KERNE=${KERNE:-28}

mkdir -p "$D/pbf" "$D/poly" "$D/out"
cd "$D" || exit 1
LOG=$D/bau.log
log() { echo "$(date -Is) $*" | tee -a "$LOG"; }

log "Verbund $VERBUND aus $QUELLE, Arbeitsordner $D"
command -v osmium >/dev/null || { log "osmium-tool fehlt (sudo apt-get install osmium-tool)"; exit 1; }
command -v zip >/dev/null || { log "zip fehlt"; exit 1; }
python3 -c "import shapely" 2>/dev/null || { log "python3-shapely fehlt"; exit 1; }

# 1. Auszüge je Land (so bleibt der Bau auf die Gebiete beschränkt, die auch ladbar sind)
log "Auszüge laden"
python3 "$REPO/verbund/gebiete.py" --laender-poly 2>/dev/null | sort -u > laender.txt || true
if [ ! -s laender.txt ]; then
    # Fallback: ein Auszug für den ganzen Kontinent
    echo "$QUELLE" > laender.txt
fi
# Mehrere Dateien gleichzeitig: Geofabrik begrenzt die einzelne Verbindung (gemessen rund 2.5 MB/s), nicht den Rechner.
# Erst in eine Teildatei laden und dann umbenennen, damit ein Abbruch keine halbe Datei als fertig zurücklässt.
export LADE_LOG=$LOG
lade_einen() {
    pfad=$1
    ziel="pbf/$(echo "$pfad" | tr '/' '_').osm.pbf"
    [ -s "$ziel" ] && return 0
    curl -fsSL -o "$ziel.teil" "https://download.geofabrik.de/${pfad}-latest.osm.pbf" || { echo "$(date -Is) Auszug $pfad fehlgeschlagen" >> "$LADE_LOG"; return 1; }
    mv "$ziel.teil" "$ziel"
}
export -f lade_einen
rm -f pbf/*.teil
xargs -a laender.txt -I{} -P 5 bash -c 'lade_einen "$@"' _ {} || { log "Auszüge unvollständig"; exit 1; }
log "Auszüge: $(du -sh pbf | cut -f1)"

# 2. Polygone der Download-Gebiete
log "Polygone laden"
python3 "$REPO/verbund/gebiete.py" --list | while IFS=$'\t' read -r id poly; do
    [ -s "poly/$id.poly" ] || curl -fsSL -o "poly/$id.poly" "https://download.geofabrik.de/${poly}.poly" || log "Polygon $id fehlt"
done

OSM_DATE=$(for f in pbf/*.osm.pbf; do osmium fileinfo -g header.option.osmosis_replication_timestamp "$f" | cut -c1-10; done | sort | head -1)
BBOX=$(python3 "$REPO/verbund/gebiete.py" --bbox poly)
log "OSM-Stand $OSM_DATE, Umriss $BBOX"

# 3. Zusammenführen
if [ ! -s verbund.osm.pbf ]; then
    log "Auszüge zusammenführen"
    osmium merge -o verbund.osm.pbf pbf/*.osm.pbf || exit 1
fi
log "Gesamtdatei $(du -h verbund.osm.pbf | cut -f1)"

# 4. Kacheln bauen (Höhendaten wie im Workflow, damit Steigungen stimmen)
rm -rf tiles; mkdir tiles
: > speicher.log
( while true; do m=$(sudo docker stats --no-stream --format '{{.MemUsage}}' "verbund-$VERBUND" 2>/dev/null | awk '{print $1}'); \
    [ -n "$m" ] && echo "$(date -Is) $m $(free -g | awk '/Mem:/{print "frei="$7"G"}')" >> speicher.log; sleep 60; done ) &
WACHE=$!
t0=$(date +%s)
log "Kacheln bauen ($SPEICHER, $KERNE Kerne) – bei Europa rund vier Stunden"
sudo docker run --rm --name "verbund-$VERBUND" --cpus="$KERNE" --memory="$SPEICHER" -v "$D:/data" -w /data "$IMG" bash -c "
  set -e
  valhalla_build_config --mjolnir-tile-dir /data/tiles --mjolnir-tile-extract '' --additional-data-elevation /data/elevation > /data/valhalla.json
  sed -i 's/\"concurrency\": [0-9]*/\"concurrency\": $KERNE/' /data/valhalla.json
  valhalla_build_elevation -b '$BBOX' -c /data/valhalla.json -v
  valhalla_build_tiles -c /data/valhalla.json /data/verbund.osm.pbf
" > kacheln.log 2>&1
rc=$?
kill $WACHE 2>/dev/null
log "Kacheln rc=$rc, Dauer $(( ($(date +%s)-t0)/60 )) min"
[ $rc -eq 0 ] || { log "ABBRUCH"; tail -20 kacheln.log | tee -a "$LOG"; exit $rc; }
sudo chown -R "$USER" tiles elevation 2>/dev/null
log "Kacheln $(du -sh tiles | cut -f1)"

# 5. In Download-Teile zerlegen
[ -s tzdata.tar ] || curl -fsSL -o tzdata.tar "https://raw.githubusercontent.com/Rallista/valhalla-mobile/${MOBILE}/apple/Sources/Valhalla/SupportData/tzdata.tar"
log "Teile schneiden"
python3 "$REPO/verbund/teile.py" --tiles tiles --poly poly --config valhalla.json --tzdata tzdata.tar \
    --out out --verbund "$VERBUND" --osm-date "$OSM_DATE" --bbox="$BBOX" \
    --base-url "https://github.com/burgerre/GSAK-NG-Daten/releases/download/routing-${VERBUND}-${OSM_DATE}" || exit 1

log "Fertig. Teile in $D/out:"
du -h out/*.zip | sort -h | tee -a "$LOG"
log "Speicher-Höchstwert: $(sort -k2 -h speicher.log | tail -1)"
log "Zum Veröffentlichen (erst nach Freigabe von Reto):"
log "  gh release create routing-${VERBUND}-${OSM_DATE} $D/out/*.zip --repo burgerre/GSAK-NG-Daten --title \"Routing-Verbund ${VERBUND} (${OSM_DATE})\""
log "  danach katalog.json mit out/verbund.json nachführen (wie der Workflow routing-verbund.yml)"
