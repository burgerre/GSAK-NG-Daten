#!/usr/bin/env bash
# #1332 Vektorkacheln (PMTiles, OpenMapTiles-Schema) je Land auf dem Build-PC: planetiler im Docker-Abbild, kein Systemeingriff.
# Nacheinander, weil planetiler alle Kerne braucht. Kleine Laender zuerst, damit frueh Ergebnisse vorliegen.
#
# #1216 Je Kontinent aufrufbar, weil «europa» hier fest verdrahtet war:
#
#   karten/bau-buildpc.sh                # Europa (wie bisher)
#   karten/bau-buildpc.sh nordamerika    # Nordamerika
#
# Quelle sind die Gebietsauszuege in $PBF. Gibt es sie nicht (ein Kontinent kann am Stueck gebaut worden sein, dann liegt
# dort nur verbund.osm.pbf), schneidet das Skript sie zuerst mit osmium an den Geofabrik-Polygonen aus - dieselben Gebiete
# wie im Routing-Verbund, damit Karte und Routing dieselben Namen und Grenzen haben.
set -u
VERBUND=${1:-${VERBUND:-europa}}
export VERBUND
REPO=$(cd "$(dirname "$0")/.." && pwd)
PBF=${PBF:-$HOME/verbund-$VERBUND/pbf}
GESAMT=${GESAMT:-$HOME/verbund-$VERBUND/verbund.osm.pbf}
POLY=${POLY:-$HOME/verbund-$VERBUND/poly}
WORK=${ARBEIT:-$HOME/karten-$VERBUND}
IMG=ghcr.io/onthegomap/planetiler:latest
mkdir -p "$WORK/out" "$PBF"

# Fehlen die Gebietsauszuege, aus dem Gesamtauszug schneiden (osmium, ein Durchgang je Block von Gebieten)
if [ "$(ls "$PBF"/*.osm.pbf 2>/dev/null | wc -l)" -eq 0 ]; then
  if [ ! -s "$GESAMT" ]; then
    echo "Weder Gebietsauszuege in $PBF noch Gesamtauszug $GESAMT - erst den Routing-Verbund bauen."; exit 1
  fi
  echo "$(date -Is) == Gebietsauszuege aus $(du -h "$GESAMT" | cut -f1) schneiden =="
  # Ein osmium-Durchgang je Block (Standard 20 Gebiete): die Gesamtdatei wird so vier- statt 68-mal gelesen.
  python3 -I "$REPO/karten/gebietsauszuege.py" "$GESAMT" "$POLY" "$PBF" || { echo "Schneiden fehlgeschlagen"; exit 1; }
  echo "$(date -Is) Auszuege: $(ls "$PBF"/*.osm.pbf 2>/dev/null | wc -l)"
fi
MASS=$WORK/groessen.tsv
[ -s "$MASS" ] || printf 'land\tpbf_mb\tpmtiles_mb\tminuten\n' > "$MASS"

ls -S -r "$PBF"/*.osm.pbf | while read -r q; do
  name=$(basename "$q" .osm.pbf); name=${name#europe_}; name=${name#north-america_}
  ziel="$WORK/out/$name.pmtiles"
  if [ -s "$ziel" ]; then echo "$(date -Is) $name schon da, uebersprungen"; continue; fi
  pbfmb=$(( $(stat -c%s "$q") / 1048576 ))
  echo "$(date -Is) == $name ($pbfmb MB Auszug) =="
  t0=$(date +%s)
  sudo -n docker run --rm -v "$q:/data/in.osm.pbf:ro" -v "$WORK/out:/out" "$IMG" \
      --osm-path=/data/in.osm.pbf --output="/out/$name.pmtiles" --force \
      --download --nodemap-type=sparsearray --storage=mmap --threads=20 > "$WORK/$name.log" 2>&1
  rc=$?
  min=$(( ($(date +%s)-t0)/60 ))
  if [ $rc -eq 0 ] && [ -s "$ziel" ]; then
    sudo -n chown "$USER" "$ziel" 2>/dev/null
    mb=$(( $(stat -c%s "$ziel") / 1048576 ))
    printf '%s\t%d\t%d\t%d\n' "$name" "$pbfmb" "$mb" "$min" >> "$MASS"
    echo "$(date -Is) $name fertig: $mb MB in $min min"
  else
    printf '%s\t%d\tFEHLER(rc=%d)\t%d\n' "$name" "$pbfmb" "$rc" "$min" >> "$MASS"
    echo "$(date -Is) $name FEHLER rc=$rc nach $min min"; tail -5 "$WORK/$name.log"
  fi
done
echo "$(date -Is) == alles durch =="
cat "$MASS"
du -sh "$WORK/out"
