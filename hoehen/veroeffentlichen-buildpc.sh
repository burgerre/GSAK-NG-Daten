#!/usr/bin/env bash
# #1323 Hoehenkacheln vom Build-PC veroeffentlichen und in katalog.json eintragen.
#
# Zwei Grenzen von GitHub bestimmen den Ablauf:
#   - hoechstens 1000 Anhaenge je Release. Europa hat 1396 Kacheln, darum mehrere Releases
#     «<tag>», «<tag>-teil2», «<tag>-teil3» …  Der Katalog nennt je Kachel die genaue Adresse,
#     fuer die App macht die Aufteilung keinen Unterschied.
#   - die Kommandozeile fasst nicht 1000 Pfade, darum Bloecke von 60 Dateien.
#
# Aufruf: hoehen/veroeffentlichen-buildpc.sh <ordner-mit-kacheln> [<arbeitskopie-daten>]
# gh muss angemeldet sein (laeuft unter Windows/Git Bash, nicht in WSL).
set -euo pipefail
OUT=${1:?Ordner mit den .hgt.gz und hoehen.json}
D=${2:-$(cd "$(dirname "$0")/.." && pwd)}
REPO=burgerre/GSAK-NG-Daten
JE_RELEASE=1000
JE_BLOCK=60

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
  gh release view "$tag" --repo "$REPO" >/dev/null 2>&1 || \
    gh release create "$tag" --repo "$REPO" --title "Höhendaten Copernicus DEM GLO-90 Europa ($STAND)${nr:+, Teil $nr}" \
       --notes "Höhendaten für GSAK-NG, 1°-Kacheln im SRTM-HGT-Format (gzip). Die App lädt sie über \`katalog.json\`, Abschnitt \`hoehen\`."
  # hoehen.json gehoert ins letzte Release, darum ein Platz Reserve
  grenze=$JE_RELEASE
  rest=$(( ${#ALLE[@]} - i ))
  [ $rest -le $JE_RELEASE ] && grenze=$((JE_RELEASE - 1))
  teil=("${ALLE[@]:$i:$grenze}")
  j=0
  while [ $j -lt ${#teil[@]} ]; do
    gh release upload "$tag" --repo "$REPO" --clobber "${teil[@]:$j:$JE_BLOCK}" >/dev/null
    j=$((j+JE_BLOCK))
    printf '\r  %s: %d/%d' "$tag" "$(( j < ${#teil[@]} ? j : ${#teil[@]} ))" "${#teil[@]}"
  done
  echo
  i=$((i+grenze))
done
letztes=${teile[-1]}
gh release upload "$letztes" --repo "$REPO" --clobber hoehen.json >/dev/null
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
k["hoehen"] = h
json.dump(k, io.open(katalog, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2)
io.open(katalog, "a", encoding="utf-8", newline="\n").write("\n")
print("Katalog: %d Länder, %d Gebiete, %d Kacheln, %.0f MB, Releases: %s"
      % (len(h["laender"]), len(h["gebiete"]), len(h["kacheln"]), h["groesse"] / 1e6, ", ".join(teile)))
PY
echo "== Katalog geschrieben. Noch zu tun: katalog.json committen und pushen =="
