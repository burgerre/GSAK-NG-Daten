#!/usr/bin/env bash
# #1332 Vektorkacheln (PMTiles, OpenMapTiles-Schema) je Land auf dem Build-PC: planetiler im Docker-Abbild, kein Systemeingriff.
# Nacheinander, weil planetiler alle Kerne braucht. Kleine Laender zuerst, damit frueh Ergebnisse vorliegen.
set -u
PBF=$HOME/verbund-europa/pbf
WORK=$HOME/karten-europa
IMG=ghcr.io/onthegomap/planetiler:latest
mkdir -p "$WORK/out"
MASS=$WORK/groessen.tsv
[ -s "$MASS" ] || printf 'land\tpbf_mb\tpmtiles_mb\tminuten\n' > "$MASS"

ls -S -r "$PBF"/*.osm.pbf | while read -r q; do
  name=$(basename "$q" .osm.pbf); name=${name#europe_}
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
