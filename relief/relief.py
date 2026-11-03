"""Relief-Messung für GSAK-NG (#681): Terrain-RGB-Kacheln und Höhenlinien aus Copernicus DEM GLO-30 für ein Gebiet.

Nur Messung: erzeugt MBTiles (danach mit go-pmtiles in PMTiles umgewandelt) und einen Grössenbericht je Ebene und Zoom.

  relief.py gebiet   <poly> <out.geojson> <puffer°>      Geofabrik-Polygon → GeoJSON (gepuffert), druckt die GLO-30-Kachelnamen
  relief.py terrain  <gebiet.geojson> <dem-dir> <zmin> <zmax> <out-dir>
                                                         je Zoom gdalwarp nach EPSG:3857, Kodierung Mapbox (0,1 m) und Terrarium (1 m)
  relief.py hoehen   <in.geojsons> <out.geojsons>        Höhenlinien: Minzoom je Äquidistanz (100 m z9, 20 m z11, 10 m z13)
  relief.py bericht  <out-dir> <zeiten.txt>              Grössenbericht (Markdown) aus den MBTiles und PMTiles
"""
import glob
import io
import json
import math
import os
import sqlite3
import sys

ORIGIN = 20037508.342789244
TILE = 256


def lese_poly(path):
    """Geofabrik-.poly: Ringe; Ringe mit «!» sind Löcher."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    aussen, loecher, ring, name = [], [], None, None
    with open(path, encoding="utf-8") as f:
        lines = [l.strip() for l in f][1:]
    for line in lines:
        if not line:
            continue
        if ring is None:
            if line == "END":
                break
            name, ring = line, []
        elif line == "END":
            (loecher if name.startswith("!") else aussen).append(Polygon(ring))
            ring = None
        else:
            x, y = line.split()[:2]
            ring.append((float(x), float(y)))
    geom = unary_union(aussen)
    if loecher:
        geom = geom.difference(unary_union(loecher))
    return geom


def gebiet(poly, out, puffer):
    from shapely.geometry import mapping
    geom = lese_poly(poly).buffer(float(puffer))
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": mapping(geom)}]}, f)
    x0, y0, x1, y1 = geom.bounds
    for lat in range(math.floor(y0), math.ceil(y1)):
        for lon in range(math.floor(x0), math.ceil(x1)):
            ns = f"N{lat:02d}" if lat >= 0 else f"S{-lat:02d}"
            ew = f"E{lon:03d}" if lon >= 0 else f"W{-lon:03d}"
            print(f"Copernicus_DSM_COG_10_{ns}_00_{ew}_00_DEM")


def tile_bounds_lonlat(z, x, y):
    n = 2 ** z
    lon0, lon1 = x / n * 360 - 180, (x + 1) / n * 360 - 180
    lat = lambda t: math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * t / n))))
    return lon0, lat(y + 1), lon1, lat(y)


def mbtiles_neu(path, name, zmin, zmax, bounds, fmt="png"):
    if os.path.exists(path):
        os.remove(path)
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE metadata (name TEXT, value TEXT)")
    db.execute("CREATE TABLE tiles (zoom_level INTEGER, tile_column INTEGER, tile_row INTEGER, tile_data BLOB)")
    db.execute("CREATE UNIQUE INDEX tile_index ON tiles (zoom_level, tile_column, tile_row)")
    meta = {"name": name, "format": fmt, "type": "baselayer", "minzoom": str(zmin), "maxzoom": str(zmax),
            "bounds": ",".join(f"{b:.5f}" for b in bounds),
            "attribution": "Copernicus DEM GLO-30 © DLR e.V. 2010-2014 und © Airbus Defence and Space GmbH 2014-2018, bereitgestellt unter COPERNICUS durch die Europäische Union und ESA"}
    db.executemany("INSERT INTO metadata VALUES (?, ?)", meta.items())
    return db


def kodiere(h, art):
    import numpy as np
    if art == "mapbox":
        v = np.round((h.astype(np.float64) + 10000.0) * 10.0).astype(np.int64)
        v = np.clip(v, 0, 2 ** 24 - 1)
        return np.dstack([(v >> 16) & 255, (v >> 8) & 255, v & 255]).astype(np.uint8)
    v = np.clip(np.round(h.astype(np.float64)), -32768, 32767).astype(np.int64) + 32768  # Terrarium, ganze Meter: Blau = 0
    return np.dstack([(v >> 8) & 255, v & 255, np.zeros_like(v)]).astype(np.uint8)


def terrain(gebiet_geojson, dem_dir, zmin, zmax, out_dir):
    import numpy as np
    from osgeo import gdal
    from PIL import Image
    from shapely.geometry import box, shape
    gdal.UseExceptions()
    zmin, zmax = int(zmin), int(zmax)
    with open(gebiet_geojson, encoding="utf-8") as f:
        geom = shape(json.load(f)["features"][0]["geometry"])
    vrt = os.path.join(out_dir, "dem.vrt")
    gdal.BuildVRT(vrt, sorted(glob.glob(os.path.join(dem_dir, "*.tif"))))
    arten = ("mapbox", "terrarium")
    dbs = {a: mbtiles_neu(os.path.join(out_dir, f"terrain-{a}.mbtiles"), f"Terrain-RGB {a}", zmin, zmax, geom.bounds) for a in arten}
    webp = {a: {} for a in arten}
    for z in range(zmin, zmax + 1):
        res = 2 * ORIGIN / (TILE * 2 ** z)
        # Kacheln, die das gepufferte Gebiet berühren
        n = 2 ** z
        lx = lambda lon: int((lon + 180) / 360 * n)
        ly = lambda lat: int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
        x0, y0, x1, y1 = geom.bounds
        kacheln = [(x, y) for x in range(lx(x0), lx(x1) + 1) for y in range(ly(y1), ly(y0) + 1)
                   if geom.intersects(box(*tile_bounds_lonlat(z, x, y)))]
        txs = [k[0] for k in kacheln]; tys = [k[1] for k in kacheln]
        ex = (min(txs) * TILE * res - ORIGIN, ORIGIN - (max(tys) + 1) * TILE * res,
              (max(txs) + 1) * TILE * res - ORIGIN, ORIGIN - min(tys) * TILE * res)
        tif = os.path.join(out_dir, f"z{z}.tif")
        # Genau auf das Kachelraster; «average» mittelt die Höhen (nicht die kodierten Farben) für kleine Zooms
        gdal.Warp(tif, vrt, dstSRS="EPSG:3857", outputBounds=ex, xRes=res, yRes=res,
                  resampleAlg="average" if res > 40 else "bilinear", outputType=gdal.GDT_Float32,
                  dstNodata=-32768, multithread=True, warpOptions=["NUM_THREADS=ALL_CPUS"], creationOptions=["TILED=YES", "COMPRESS=DEFLATE"])
        ds = gdal.Open(tif)
        band = ds.GetRasterBand(1)
        gx0, gy0 = min(txs), min(tys)
        anzahl = 0
        for x, y in kacheln:
            h = band.ReadAsArray((x - gx0) * TILE, (y - gy0) * TILE, TILE, TILE)
            h = np.where(h <= -1000, 0, h)  # Lücken/Meer → 0 m
            for a in arten:
                img = Image.fromarray(kodiere(h, a), "RGB")
                buf = io.BytesIO(); img.save(buf, "PNG", compress_level=9)
                dbs[a].execute("INSERT INTO tiles VALUES (?, ?, ?, ?)", (z, x, n - 1 - y, buf.getvalue()))
                buf = io.BytesIO(); img.save(buf, "WEBP", lossless=True, quality=100, method=4)
                webp[a][z] = webp[a].get(z, 0) + len(buf.getvalue())
            anzahl += 1
        ds = None
        os.remove(tif)
        for db in dbs.values():
            db.commit()
        print(f"z{z}: {anzahl} Kacheln, Auflösung {res:.1f} m (Äquator)", flush=True)
    for db in dbs.values():
        db.close()
    with open(os.path.join(out_dir, "terrain-webp.json"), "w") as f:
        json.dump(webp, f)


def hoehen(src, dst):
    n = 0
    with open(src, encoding="utf-8") as fi, open(dst, "w", encoding="utf-8") as fo:
        for line in fi:
            line = line.strip().lstrip("\x1e")
            if not line:
                continue
            f = json.loads(line)
            ele = int(round(f["properties"]["ele"]))
            mz = 9 if ele % 100 == 0 else 11 if ele % 20 == 0 else 13
            f["properties"] = {"ele": ele, "idx": 1 if ele % 100 == 0 else 0}
            f["tippecanoe"] = {"minzoom": mz}
            fo.write(json.dumps(f, separators=(",", ":")) + "\n")
            n += 1
    print(f"{n} Höhenlinien")


def mb(b):
    return f"{b / 1048576:.1f}"


def zoomtabelle(path, webp=None):
    db = sqlite3.connect(path)
    rows = db.execute("SELECT zoom_level, COUNT(*), SUM(LENGTH(tile_data)), MAX(LENGTH(tile_data)) FROM tiles GROUP BY zoom_level ORDER BY zoom_level").fetchall()
    db.close()
    kopf = "| Zoom | Kacheln | MB | grösste Kachel KB | MB kumuliert |" + (" WebP verlustfrei MB | WebP kumuliert |" if webp else "")
    out = [kopf, "|" + "---|" * (kopf.count("|") - 1)]
    summe = wsumme = 0
    for z, cnt, size, mx in rows:
        summe += size
        line = f"| {z} | {cnt} | {mb(size)} | {mx / 1024:.0f} | {mb(summe)} |"
        if webp:
            w = webp.get(str(z), 0); wsumme += w
            line += f" {mb(w)} | {mb(wsumme)} |"
        out.append(line)
    return out


def bericht(out_dir, zeiten):
    webp = {}
    p = os.path.join(out_dir, "terrain-webp.json")
    if os.path.exists(p):
        with open(p) as f:
            webp = json.load(f)
    lines = ["# Relief-Messung (#681)", ""]
    if os.path.exists(zeiten):
        with open(zeiten, encoding="utf-8") as f:
            lines += ["## Laufzeit", "", "| Schritt | Minuten |", "|---|---|"]
            for l in f:
                schritt, sek = l.rstrip("\n").split("\t")
                lines.append(f"| {schritt} | {int(sek) / 60:.1f} |")
            lines.append("")
    lines += ["## Dateien", "", "| Datei | MB |", "|---|---|"]
    for f in sorted(glob.glob(os.path.join(out_dir, "*.pmtiles")) + glob.glob(os.path.join(out_dir, "*.mbtiles"))):
        lines.append(f"| {os.path.basename(f)} | {mb(os.path.getsize(f))} |")
    lines.append("")
    for f in sorted(glob.glob(os.path.join(out_dir, "*.mbtiles"))):
        name = os.path.basename(f)
        art = name.removeprefix("terrain-").removesuffix(".mbtiles")
        lines += [f"## {name} je Zoom", ""] + zoomtabelle(f, webp.get(art)) + [""]
    text = "\n".join(lines)
    with open(os.path.join(out_dir, "bericht.md"), "w", encoding="utf-8") as fo:
        fo.write(text)
    print(text)


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    {"gebiet": gebiet, "terrain": terrain, "hoehen": hoehen, "bericht": bericht}[cmd](*args)
