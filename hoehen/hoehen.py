"""Höhendaten je Land/Region für GSAK-NG (#213 Stufe 2): Copernicus DEM → 1°-Kacheln im SRTM-HGT-Format (gepackt, .hgt.gz).

Valhalla 3.9.0 («skadi», valhalla-mobile 0.6.4) liest nur Kacheln mit 3601 × 3601 Werten (1″, Ränder doppelt wie SRTM). GLO-90 (3″) wird
darum auf das 1″-Raster bilinear interpoliert; GLO-30 (1″) wird nur vom Flächen- auf das Punktraster verschoben. Die App liest dieselben
Kacheln für «Höhen aktualisieren» (Desktop und Handy).

  hoehen.py kacheln  <poly-dir> <out.json>                     Gebiete (wie Routing-Verbund) → berührte 1°-Kacheln, Liste der DEM-Kacheln
  hoehen.py dem      <kacheln.json> <glo90|glo30>              druckt «url<TAB>datei» aller nötigen Copernicus-Kacheln (inkl. Nachbarn)
  hoehen.py bauen    <kacheln.json> <glo90|glo30> <dem-dir> <out-dir> [--roh3]
                                                               je 1°-Kachel N47E008.hgt.gz (3601²); --roh3 zusätzlich 1201² zum Vergleich
  hoehen.py katalog  <kacheln.json> <glo90|glo30> <out-dir> <stand> <base-url>
                                                               schreibt <out-dir>/hoehen.json (Katalogabschnitt «hoehen»)
  hoehen.py bericht  <kacheln.json> <mess-dir>...              Grössenbericht (Markdown) je Gebiet und Variante
"""
import glob
import gzip
import hashlib
import json
import math
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verbund"))
from gebiete import gebiete, laender  # noqa: E402

FORMAT = 1
DIM = 3601          # Valhalla skadi: HGT_DIM 3601 (1″)
DIM3 = 1201         # SRTM 3″ (nur Messung)
PUFFER = 0.01       # Grad um das Gebietspolygon

QUELLEN = {
    "glo90": {
        "name": "Copernicus DEM GLO-90",
        "bucket": "https://copernicus-dem-90m.s3.amazonaws.com",
        "prefix": "Copernicus_DSM_COG_30",
        "aufloesung": "3″ (≈ 90 m), auf 1″-Raster interpoliert",
        "attribution": "Höhendaten: Copernicus DEM GLO-90, © DLR e.V. 2010-2014 und © Airbus Defence and Space GmbH 2014-2018, "
                       "bereitgestellt unter COPERNICUS durch die Europäische Union und ESA; alle Rechte vorbehalten. Verändert (HGT-Kacheln).",
        "attributionEn": "produced using Copernicus WorldDEM-90 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 "
                         "provided under COPERNICUS by the European Union and ESA; all rights reserved. Modified (HGT tiles).",
    },
    "glo30": {
        "name": "Copernicus DEM GLO-30",
        "bucket": "https://copernicus-dem-30m.s3.amazonaws.com",
        "prefix": "Copernicus_DSM_COG_10",
        "aufloesung": "1″ (≈ 30 m)",
        "attribution": "Höhendaten: Copernicus DEM GLO-30, © DLR e.V. 2010-2014 und © Airbus Defence and Space GmbH 2014-2018, "
                       "bereitgestellt unter COPERNICUS durch die Europäische Union und ESA; alle Rechte vorbehalten. Verändert (HGT-Kacheln).",
        "attributionEn": "produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 "
                         "provided under COPERNICUS by the European Union and ESA; all rights reserved. Modified (HGT tiles).",
    },
}
LIZENZ = "Licence for the use of the Copernicus DEM (frei, auch kommerziell, mit Quellenangabe)"
LIZENZ_URL = "https://registry.opendata.aws/copernicus-dem/"


def hgt_name(lat, lon):
    return f"{'N' if lat >= 0 else 'S'}{abs(lat):02d}{'E' if lon >= 0 else 'W'}{abs(lon):03d}"


def dem_name(quelle, lat, lon):
    q = QUELLEN[quelle]
    ns = f"N{lat:02d}" if lat >= 0 else f"S{-lat:02d}"
    ew = f"E{lon:03d}" if lon >= 0 else f"W{-lon:03d}"
    return f"{q['prefix']}_{ns}_00_{ew}_00_DEM"


def parse_hgt(name):
    lat = int(name[1:3]) * (1 if name[0] == "N" else -1)
    lon = int(name[4:7]) * (1 if name[3] == "E" else -1)
    return lat, lon


def kacheln(poly_dir, out):
    from shapely.geometry import box
    from shapely.prepared import prep
    from teile import lese_poly
    result = {"gebiete": [], "laender": laender()}
    alle = set()
    for g in gebiete():
        flaeche = lese_poly(os.path.join(poly_dir, g["id"] + ".poly"))
        gepuffert = prep(flaeche.buffer(PUFFER))
        x0, y0, x1, y1 = flaeche.bounds
        ks = []
        for lat in range(math.floor(y0 - PUFFER), math.ceil(y1 + PUFFER)):
            for lon in range(math.floor(x0 - PUFFER), math.ceil(x1 + PUFFER)):
                if gepuffert.intersects(box(lon, lat, lon + 1, lat + 1)):
                    ks.append(hgt_name(lat, lon))
        alle.update(ks)
        result["gebiete"].append({**{k: g[k] for k in ("id", "typ", "land", "name")},
                                  "bbox": [round(v, 5) for v in (x0, y0, x1, y1)], "kacheln": sorted(ks)})
        print(f"{g['id']}: {len(ks)} Kacheln", file=sys.stderr)
    result["kacheln"] = sorted(alle)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"zusammen {len(alle)} Kacheln", file=sys.stderr)


def dem(kacheln_json, quelle):
    """Copernicus-Kacheln aller Zielkacheln und ihrer Nachbarn (Randzeilen der HGT-Kachel liegen eine halbe Zelle daneben)."""
    with open(kacheln_json, encoding="utf-8") as f:
        k = json.load(f)
    need = set()
    for name in k["kacheln"]:
        lat, lon = parse_hgt(name)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                need.add((lat + dy, lon + dx))
    q = QUELLEN[quelle]
    for lat, lon in sorted(need):
        n = dem_name(quelle, lat, lon)
        print(f"{q['bucket']}/{n}/{n}.tif\t{n}.tif")


def run(*args):
    subprocess.run(args, check=True)


def bauen(kacheln_json, quelle, dem_dir, out_dir, roh3=False):
    with open(kacheln_json, encoding="utf-8") as f:
        k = json.load(f)
    os.makedirs(out_dir, exist_ok=True)
    tifs = sorted(glob.glob(os.path.join(dem_dir, "*.tif")))
    if not tifs:
        sys.exit("keine DEM-Kacheln")
    vrt = os.path.join(dem_dir, "dem.vrt")
    run("gdalbuildvrt", "-q", "-overwrite", vrt, *tifs)
    vorhanden = {os.path.basename(t)[:-4] for t in tifs}
    leer = []
    for name in k["kacheln"]:
        lat, lon = parse_hgt(name)
        if dem_name(quelle, lat, lon) not in vorhanden:
            leer.append(name)       # Meer: Copernicus hat keine Kachel
            continue
        for dim, suffix in ((DIM, ""), (DIM3, ".3s")) if roh3 else ((DIM, ""),):
            h = 0.5 / (dim - 1)     # halbe Zelle: Mittelpunkte der Randzellen liegen genau auf den Kachelgrenzen
            tmp = os.path.join(out_dir, f"{name}{suffix}.tif")
            hgt = os.path.join(out_dir, f"{name}.hgt") if not suffix else os.path.join(out_dir, "3s", f"{name}.hgt")
            os.makedirs(os.path.dirname(hgt), exist_ok=True)
            run("gdalwarp", "-q", "-overwrite", "-te", str(lon - h), str(lat - h), str(lon + 1 + h), str(lat + 1 + h),
                "-ts", str(dim), str(dim), "-r", "bilinear", "-ot", "Int16", "-dstnodata", "-32768", "-wo", "NUM_THREADS=ALL_CPUS", vrt, tmp)
            run("gdal_translate", "-q", "-of", "SRTMHGT", tmp, hgt)
            os.remove(tmp)
            for aux in glob.glob(hgt + ".aux.xml"):
                os.remove(aux)
            size = os.path.getsize(hgt)
            if size != dim * dim * 2:
                sys.exit(f"{hgt}: {size} Bytes statt {dim * dim * 2}")
            with open(hgt, "rb") as src, gzip.GzipFile(hgt + ".gz", "wb", compresslevel=9, mtime=0) as dst:
                dst.write(src.read())
            os.remove(hgt)
    with open(os.path.join(out_dir, "leer.json"), "w", encoding="utf-8") as f:
        json.dump(leer, f)
    print(f"{len(k['kacheln']) - len(leer)} Kacheln gebaut, {len(leer)} ohne Daten (Meer): {', '.join(leer)}", file=sys.stderr)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def katalog(kacheln_json, quelle, out_dir, stand, base_url):
    with open(kacheln_json, encoding="utf-8") as f:
        k = json.load(f)
    q = QUELLEN[quelle]
    tiles = {}
    for path in sorted(glob.glob(os.path.join(out_dir, "*.hgt.gz"))):
        name = os.path.basename(path)[:-7]
        tiles[name] = {"name": name, "url": f"{base_url}/{name}.hgt.gz", "groesse": os.path.getsize(path), "sha256": sha256(path)}
    gebiete_out = []
    for g in k["gebiete"]:
        ks = [n for n in g["kacheln"] if n in tiles]
        gebiete_out.append({**g, "kacheln": ks, "groesse": sum(tiles[n]["groesse"] for n in ks)})
    result = {
        "format": FORMAT, "quelle": q["name"], "quelleId": quelle, "aufloesung": q["aufloesung"], "raster": DIM,
        "kachelformat": "SRTM-HGT, 1° × 1°, Int16 big-endian, Meter über Geoid (EGM2008), -32768 = keine Daten, gzip",
        "stand": stand, "attribution": q["attribution"], "attributionEn": q["attributionEn"], "lizenz": LIZENZ, "lizenzUrl": LIZENZ_URL,
        "laender": k["laender"], "gebiete": gebiete_out, "kacheln": [tiles[n] for n in sorted(tiles)],
        "groesse": sum(t["groesse"] for t in tiles.values()),
    }
    with open(os.path.join(out_dir, "hoehen.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)


def mb(b):
    return f"{b / 1048576:.1f}"


def bericht(kacheln_json, mess_dirs):
    """Markdown: Grösse je Gebiet und Variante (Verzeichnisname = Variante, darin *.hgt.gz und optional 3s/*.hgt.gz)."""
    with open(kacheln_json, encoding="utf-8") as f:
        k = json.load(f)
    varianten = []
    for d in mess_dirs:
        name = os.path.basename(os.path.normpath(d))
        varianten.append((f"{name} 1″ (3601²)", {os.path.basename(p)[:-7]: os.path.getsize(p) for p in glob.glob(os.path.join(d, "*.hgt.gz"))}))
        drei = {os.path.basename(p)[:-7]: os.path.getsize(p) for p in glob.glob(os.path.join(d, "3s", "*.hgt.gz"))}
        if drei:
            varianten.append((f"{name} 3″ (1201², nur Vergleich)", drei))
    lines = ["| Gebiet | Kacheln | " + " | ".join(f"{v} MB" for v, _ in varianten) + " |", "|---|---:|" + "---:|" * len(varianten)]
    for g in k["gebiete"]:
        ks = g["kacheln"]
        lines.append(f"| {g['id']} | {len(ks)} | " + " | ".join(mb(sum(s.get(n, 0) for n in ks)) for _, s in varianten) + " |")
    # Länder (alle Regionen zusammen, gemeinsame Kacheln einmal)
    for land in k["laender"]:
        if not land["regionen"]:
            continue
        ks = sorted({n for g in k["gebiete"] if g["land"] == land["id"] for n in g["kacheln"]})
        lines.append(f"| **{land['id']} gesamt** | {len(ks)} | " + " | ".join(mb(sum(s.get(n, 0) for n in ks)) for _, s in varianten) + " |")
    ks = k["kacheln"]
    lines.append(f"| **alle** | {len(ks)} | " + " | ".join(mb(sum(s.values())) for _, s in varianten) + " |")
    roh = len([n for n in ks if any(n in s for _, s in varianten)]) * DIM * DIM * 2
    lines.append("")
    lines.append(f"Ungepackt (3601², alle Kacheln mit Daten): {mb(roh)} MB. Mittel je Kachel: "
                 + ", ".join(f"{v}: {mb(sum(s.values()) / max(1, len(s)))} MB" for v, s in varianten))
    print("\n".join(lines))


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "kacheln":
        kacheln(*args)
    elif cmd == "dem":
        dem(*args)
    elif cmd == "bauen":
        bauen(args[0], args[1], args[2], args[3], roh3="--roh3" in args)
    elif cmd == "katalog":
        katalog(*args)
    elif cmd == "bericht":
        bericht(args[0], args[1:])
    else:
        sys.exit(__doc__)
