"""Gebiete des Routing-Verbunds (#442): Länder und – bei grossen Ländern – Regionen nach dem Zuschnitt der Geofabrik-Auszüge.

Jedes Gebiet ist ein Download-Teil. Ein ganzes grosses Land besteht aus seinen Regionen (die App lädt dann alle), es gibt dafür
keinen eigenen, doppelten Teil.
"""
import sys

# id, Geofabrik-Pfad des Polygons, Name deutsch, Name englisch, typ, teilVon
LAENDER = [
    ("ch", "europe/switzerland", "Schweiz", "Switzerland"),
    ("li", "europe/liechtenstein", "Liechtenstein", "Liechtenstein"),
    ("at", "europe/austria", "Österreich", "Austria"),
    ("de", "europe/germany", "Deutschland", "Germany"),
]

# Grosse Länder: Regionen statt eines einzigen Teils
REGIONEN = {
    "de": [
        ("baden-wuerttemberg", "Baden-Württemberg", "Baden-Württemberg"),
        ("bayern", "Bayern", "Bavaria"),
        ("berlin", "Berlin", "Berlin"),
        ("brandenburg", "Brandenburg", "Brandenburg"),
        ("bremen", "Bremen", "Bremen"),
        ("hamburg", "Hamburg", "Hamburg"),
        ("hessen", "Hessen", "Hesse"),
        ("mecklenburg-vorpommern", "Mecklenburg-Vorpommern", "Mecklenburg-Western Pomerania"),
        ("niedersachsen", "Niedersachsen", "Lower Saxony"),
        ("nordrhein-westfalen", "Nordrhein-Westfalen", "North Rhine-Westphalia"),
        ("rheinland-pfalz", "Rheinland-Pfalz", "Rhineland-Palatinate"),
        ("saarland", "Saarland", "Saarland"),
        ("sachsen", "Sachsen", "Saxony"),
        ("sachsen-anhalt", "Sachsen-Anhalt", "Saxony-Anhalt"),
        ("schleswig-holstein", "Schleswig-Holstein", "Schleswig-Holstein"),
        ("thueringen", "Thüringen", "Thuringia"),
    ],
}


def gebiete():
    """Alle Download-Gebiete: dict mit id, poly, name, typ, land."""
    result = []
    for land, poly, de, en in LAENDER:
        if land in REGIONEN:
            for rid, rde, ren in REGIONEN[land]:
                result.append({"id": f"{land}-{rid}", "poly": f"{poly}/{rid}", "name": {"de": rde, "en": ren}, "typ": "region", "land": land})
        else:
            result.append({"id": land, "poly": poly, "name": {"de": de, "en": en}, "typ": "land", "land": land})
    return result


def laender():
    return [{"id": land, "name": {"de": de, "en": en}, "regionen": [f"{land}-{r[0]}" for r in REGIONEN.get(land, [])]}
            for land, _, de, en in LAENDER]


def bbox(poly_dir):
    """Umriss aller Gebietspolygone (lonMin,latMin,lonMax,latMax). Der Bounding-Box-Kopf der zusammengeführten OSM-Datei taugt nicht:
    Relationen (Fähren, Inseln) reichen weit hinaus (beim ersten Lauf -20..28° Länge)."""
    import glob
    xs, ys = [], []
    for path in glob.glob(f"{poly_dir}/*.poly"):
        with open(path, encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        xs.append(float(parts[0])); ys.append(float(parts[1]))
                    except ValueError:
                        pass
    return f"{min(xs):.5f},{min(ys):.5f},{max(xs):.5f},{max(ys):.5f}"


if __name__ == "__main__":
    if "--bbox" in sys.argv:
        print(bbox(sys.argv[sys.argv.index("--bbox") + 1]))
    if "--list" in sys.argv:
        for g in gebiete():
            print(f"{g['id']}\t{g['poly']}")
