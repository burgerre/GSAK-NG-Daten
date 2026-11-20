# -*- coding: utf-8 -*-
"""Schneidet die Gebietsauszüge in wenigen osmium-Durchgängen statt einem pro Gebiet (#1216).

Ein Durchgang liest die 19-GB-Gesamtdatei einmal; 68 einzelne Aufrufe lesen sie 68-mal. osmium extract nimmt mehrere
Gebiete in einer Konfigurationsdatei und schreibt sie in einem Lauf – darum Blöcke statt Einzelaufrufe.
"""
import io, json, os, subprocess, sys, urllib.request

repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
gesamt = sys.argv[1]
poly_dir = sys.argv[2]
ziel_dir = sys.argv[3]
je_block = int(os.environ.get("JE_BLOCK", "20"))

sys.path.insert(0, os.path.join(repo, "verbund"))
import gebiete as g   # noqa: E402  (nutzt VERBUND aus der Umgebung)

os.makedirs(poly_dir, exist_ok=True)
os.makedirs(ziel_dir, exist_ok=True)

offen = []
for gebiet in g.gebiete():
    ziel = os.path.join(ziel_dir, gebiet["id"] + ".osm.pbf")
    if os.path.exists(ziel) and os.path.getsize(ziel) > 0:
        continue
    poly = os.path.join(poly_dir, gebiet["id"] + ".poly")
    if not (os.path.exists(poly) and os.path.getsize(poly) > 0):
        url = "https://download.geofabrik.de/%s.poly" % gebiet["poly"]
        try:
            with urllib.request.urlopen(url, timeout=60) as r, io.open(poly, "wb") as f:
                f.write(r.read())
        except Exception as e:                      # noqa: BLE001 – ein fehlendes Polygon darf den Lauf nicht beenden
            print("Polygon fehlt (%s): %s" % (gebiet["id"], e))
            continue
    offen.append((gebiet["id"], poly))

print("Zu schneiden: %d Gebiete, Blöcke von %d" % (len(offen), je_block))
if not offen:
    raise SystemExit(0)

for nr in range(0, len(offen), je_block):
    block = offen[nr:nr + je_block]
    cfg = {"extracts": [{"output": gid + ".osm.pbf", "polygon": {"file_name": poly, "file_type": "poly"}}
                        for gid, poly in block]}
    cfg_pfad = os.path.join(ziel_dir, "extract-block.json")
    with io.open(cfg_pfad, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print("== Block %d: %s" % (nr // je_block + 1, ", ".join(gid for gid, _ in block)), flush=True)
    # --set-bounds ist nicht Kosmetik: ohne Bounding Box im Kopf der Datei nimmt planetiler die ganze Welt an und packt die
    # globalen Zusatzdaten (Natural Earth, Wasserflächen) in jede Karte. Gemessen: 681 MB für die Amerikanischen
    # Jungferninseln statt weniger MB. Die Geofabrik-Auszüge bringen die Box mit, selbst geschnittene nicht.
    rc = subprocess.call(["osmium", "extract", "-c", cfg_pfad, "-d", ziel_dir, "-s", "simple",
                          "--set-bounds", "--overwrite", "--no-progress", gesamt])
    if rc != 0:
        print("osmium rc=%d – Block abgebrochen" % rc)
        raise SystemExit(rc)

fehlend = [gid for gid, _ in offen if not os.path.exists(os.path.join(ziel_dir, gid + ".osm.pbf"))]
print("Fertig. Fehlend: %s" % (", ".join(fehlend) if fehlend else "keine"))
