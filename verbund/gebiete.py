"""Gebiete des Routing-Verbunds (#442): Länder und – bei grossen Ländern – Regionen nach dem Zuschnitt der Geofabrik-Auszüge.

Jedes Gebiet ist ein Download-Teil. Ein ganzes grosses Land besteht aus seinen Regionen (die App lädt dann alle), es gibt dafür
keinen eigenen, doppelten Teil.
"""
import sys

# id, Geofabrik-Pfad des Polygons, Name deutsch, Name englisch, typ, teilVon
LAENDER_EUROPA = [
    ("al", "europe/albania", "Albanien", "Albania"),
    ("ad", "europe/andorra", "Andorra", "Andorra"),
    ("at", "europe/austria", "Österreich", "Austria"),
    ("azoren", "europe/azores", "Azoren", "Azores"),
    ("by", "europe/belarus", "Belarus", "Belarus"),
    ("be", "europe/belgium", "Belgien", "Belgium"),
    ("ba", "europe/bosnia-herzegovina", "Bosnien und Herzegowina", "Bosnia-Herzegovina"),
    ("bg", "europe/bulgaria", "Bulgarien", "Bulgaria"),
    ("hr", "europe/croatia", "Kroatien", "Croatia"),
    ("cy", "europe/cyprus", "Zypern", "Cyprus"),
    ("cz", "europe/czech-republic", "Tschechien", "Czech Republic"),
    ("dk", "europe/denmark", "Dänemark", "Denmark"),
    ("ee", "europe/estonia", "Estland", "Estonia"),
    ("fo", "europe/faroe-islands", "Färöer", "Faroe Islands"),
    ("fi", "europe/finland", "Finnland", "Finland"),
    ("fr", "europe/france", "Frankreich", "France"),
    ("ge", "europe/georgia", "Georgien", "Georgia"),
    ("de", "europe/germany", "Deutschland", "Germany"),
    ("gb", "europe/great-britain", "Grossbritannien", "Great Britain"),
    ("gr", "europe/greece", "Griechenland", "Greece"),
    ("gg", "europe/guernsey-jersey", "Guernsey und Jersey", "Guernsey and Jersey"),
    ("hu", "europe/hungary", "Ungarn", "Hungary"),
    ("is", "europe/iceland", "Island", "Iceland"),
    ("ie", "europe/ireland-and-northern-ireland", "Irland und Nordirland", "Ireland and Northern Ireland"),
    ("im", "europe/isle-of-man", "Isle of Man", "Isle of Man"),
    ("it", "europe/italy", "Italien", "Italy"),
    ("xk", "europe/kosovo", "Kosovo", "Kosovo"),
    ("lv", "europe/latvia", "Lettland", "Latvia"),
    ("li", "europe/liechtenstein", "Liechtenstein", "Liechtenstein"),
    ("lt", "europe/lithuania", "Litauen", "Lithuania"),
    ("lu", "europe/luxembourg", "Luxemburg", "Luxembourg"),
    ("mk", "europe/macedonia", "Nordmazedonien", "Macedonia"),
    ("mt", "europe/malta", "Malta", "Malta"),
    ("md", "europe/moldova", "Moldau", "Moldova"),
    ("mc", "europe/monaco", "Monaco", "Monaco"),
    ("me", "europe/montenegro", "Montenegro", "Montenegro"),
    ("nl", "europe/netherlands", "Niederlande", "Netherlands"),
    ("no", "europe/norway", "Norwegen", "Norway"),
    ("pl", "europe/poland", "Polen", "Poland"),
    ("pt", "europe/portugal", "Portugal", "Portugal"),
    ("ro", "europe/romania", "Rumänien", "Romania"),
    ("rs", "europe/serbia", "Serbien", "Serbia"),
    ("sk", "europe/slovakia", "Slowakei", "Slovakia"),
    ("si", "europe/slovenia", "Slowenien", "Slovenia"),
    ("es", "europe/spain", "Spanien", "Spain"),
    ("se", "europe/sweden", "Schweden", "Sweden"),
    ("ch", "europe/switzerland", "Schweiz", "Switzerland"),
    ("tr", "europe/turkey", "Türkei", "Turkey"),
    ("ua", "europe/ukraine", "Ukraine", "Ukraine (with Crimea)"),
]

# Grosse Länder: Regionen statt eines einzigen Teils (Auszug grösser als rund 1 GB)
REGIONEN_EUROPA = {
    "fr": [   # Polygone unter europe/france
        ("alsace", "Alsace", "Alsace"),
        ("aquitaine", "Aquitaine", "Aquitaine"),
        ("auvergne", "Auvergne", "Auvergne"),
        ("basse-normandie", "Basse-Normandie", "Basse-Normandie"),
        ("bourgogne", "Bourgogne", "Bourgogne"),
        ("bretagne", "Bretagne", "Bretagne"),
        ("centre", "Centre", "Centre"),
        ("champagne-ardenne", "Champagne Ardenne", "Champagne Ardenne"),
        ("corse", "Corse", "Corse"),
        ("franche-comte", "Franche Comte", "Franche Comte"),
        ("haute-normandie", "Haute-Normandie", "Haute-Normandie"),
        ("ile-de-france", "Ile-de-France", "Ile-de-France"),
        ("languedoc-roussillon", "Languedoc-Roussillon", "Languedoc-Roussillon"),
        ("limousin", "Limousin", "Limousin"),
        ("lorraine", "Lorraine", "Lorraine"),
        ("midi-pyrenees", "Midi-Pyrenees", "Midi-Pyrenees"),
        ("nord-pas-de-calais", "Nord-Pas-de-Calais", "Nord-Pas-de-Calais"),
        ("pays-de-la-loire", "Pays de la Loire", "Pays de la Loire"),
        ("picardie", "Picardie", "Picardie"),
        ("poitou-charentes", "Poitou-Charentes", "Poitou-Charentes"),
        ("provence-alpes-cote-d-azur", "Provence Alpes-Cote-d'Azur", "Provence Alpes-Cote-d'Azur"),
        ("rhone-alpes", "Rhone-Alpes", "Rhone-Alpes"),
    ],
    "de": [   # Polygone unter europe/germany
        ("baden-wuerttemberg", "Baden-Württemberg", "Baden-Württemberg"),
        ("bayern", "Bayern", "Bayern"),
        ("berlin", "Berlin", "Berlin"),
        ("brandenburg", "Brandenburg (mit Berlin)", "Brandenburg (mit Berlin)"),
        ("bremen", "Bremen", "Bremen"),
        ("hamburg", "Hamburg", "Hamburg"),
        ("hessen", "Hessen", "Hessen"),
        ("mecklenburg-vorpommern", "Mecklenburg-Vorpommern", "Mecklenburg-Vorpommern"),
        ("niedersachsen", "Niedersachsen", "Niedersachsen (mit Bremen)"),
        ("nordrhein-westfalen", "Nordrhein-Westfalen", "Nordrhein-Westfalen"),
        ("rheinland-pfalz", "Rheinland-Pfalz", "Rheinland-Pfalz"),
        ("saarland", "Saarland", "Saarland"),
        ("sachsen", "Sachsen", "Sachsen"),
        ("sachsen-anhalt", "Sachsen-Anhalt", "Sachsen-Anhalt"),
        ("schleswig-holstein", "Schleswig-Holstein", "Schleswig-Holstein"),
        ("thueringen", "Thüringen", "Thüringen"),
    ],
    "gb": [   # Polygone unter europe/united-kingdom
        ("england", "England", "England"),
        ("scotland", "Schottland", "Scotland"),
        ("wales", "Wales", "Wales"),
    ],
    "it": [   # Polygone unter europe/italy
        ("centro", "Mitte", "Centro"),
        ("isole", "Inseln", "Isole"),
        ("nord-est", "Nordosten", "Nord-Est"),
        ("nord-ovest", "Nordwesten", "Nord-Ovest"),
        ("sud", "Süden", "Sud"),
    ],
    "nl": [   # Polygone unter europe/netherlands
        ("drenthe", "Drenthe", "Drenthe"),
        ("flevoland", "Flevoland", "Flevoland"),
        ("friesland", "Friesland", "Friesland"),
        ("gelderland", "Gelderland", "Gelderland"),
        ("groningen", "Groningen", "Groningen"),
        ("limburg", "Limburg", "Limburg"),
        ("noord-brabant", "Noord-Brabant", "Noord-Brabant"),
        ("noord-holland", "Noord-Holland", "Noord-Holland"),
        ("overijssel", "Overijssel", "Overijssel"),
        ("utrecht", "Utrecht", "Utrecht"),
        ("zeeland", "Zeeland", "Zeeland"),
        ("zuid-holland", "Zuid-Holland", "Zuid-Holland"),
    ],
    "no": [   # Polygone unter europe/norway
        ("nord-norge", "Nordnorwegen", "Nord-Norge<br />(Northern Norway)"),
        ("ostlandet", "Ostnorwegen", "Østlandet<br />(Eastern Norway)"),
        ("sorlandet", "Südnorwegen", "Sørlandet<br />(Southern Norway)"),
        ("svalbard-janmayen", "Spitzbergen und Jan Mayen", "Svalbard and Jan Mayen"),
        ("trondelag", "Trøndelag", "Trøndelag<br />(Central Norway)"),
        ("vestlandet", "Westnorwegen", "Vestlandet<br />(Western Norway)"),
    ],
    "pl": [   # Polygone unter europe/poland
        ("dolnoslaskie", "Województwo dolnośląskie<br />(Lower Silesian Voivodeship)", "Województwo dolnośląskie<br />(Lower Silesian Voivodeship)"),
        ("kujawsko-pomorskie", "Województwo kujawsko-pomorskie<br />(Kuyavian-Pomeranian Voivodeship)", "Województwo kujawsko-pomorskie<br />(Kuyavian-Pomeranian Voivodeship)"),
        ("lodzkie", "Województwo łódzkie<br />(Łódź Voivodeship)", "Województwo łódzkie<br />(Łódź Voivodeship)"),
        ("lubelskie", "Województwo lubelskie<br />(Lublin Voivodeship)", "Województwo lubelskie<br />(Lublin Voivodeship)"),
        ("lubuskie", "Województwo lubuskie<br />(Lubusz Voivodeship)", "Województwo lubuskie<br />(Lubusz Voivodeship)"),
        ("malopolskie", "Województwo małopolskie<br />(Lesser Poland Voivodeship)", "Województwo małopolskie<br />(Lesser Poland Voivodeship)"),
        ("mazowieckie", "Województwo mazowieckie<br />(Mazovian Voivodeship)", "Województwo mazowieckie<br />(Mazovian Voivodeship)"),
        ("opolskie", "Województwo opolskie<br />(Opole Voivodeship)", "Województwo opolskie<br />(Opole Voivodeship)"),
        ("podkarpackie", "Województwo podkarpackie<br />(Subcarpathian Voivodeship)", "Województwo podkarpackie<br />(Subcarpathian Voivodeship)"),
        ("podlaskie", "Województwo podlaskie<br />(Podlaskie Voivodeship)", "Województwo podlaskie<br />(Podlaskie Voivodeship)"),
        ("pomorskie", "Województwo pomorskie<br />(Pomeranian Voivodeship)", "Województwo pomorskie<br />(Pomeranian Voivodeship)"),
        ("slaskie", "Województwo śląskie<br />(Silesian Voivodeship)", "Województwo śląskie<br />(Silesian Voivodeship)"),
        ("swietokrzyskie", "Województwo świętokrzyskie<br />(Świętokrzyskie Voivodeship)", "Województwo świętokrzyskie<br />(Świętokrzyskie Voivodeship)"),
        ("warminsko-mazurskie", "Województwo warmińsko-mazurskie<br />(Warmian-Masurian Voivodeship)", "Województwo warmińsko-mazurskie<br />(Warmian-Masurian Voivodeship)"),
        ("wielkopolskie", "Województwo wielkopolskie<br />(Greater Poland Voivodeship)", "Województwo wielkopolskie<br />(Greater Poland Voivodeship)"),
        ("zachodniopomorskie", "Województwo zachodniopomorskie<br />(West Pomeranian Voivodeship)", "Województwo zachodniopomorskie<br />(West Pomeranian Voivodeship)"),
    ],
    "es": [   # Polygone unter europe/spain
        ("andalucia", "Andalucía", "Andalucía"),
        ("aragon", "Aragón", "Aragón"),
        ("asturias", "Asturias", "Asturias"),
        ("cantabria", "Cantabria", "Cantabria"),
        ("castilla-la-mancha", "Castilla-La Mancha", "Castilla-La Mancha"),
        ("castilla-y-leon", "Castilla y León", "Castilla y León"),
        ("cataluna", "Cataluña", "Cataluña"),
        ("ceuta", "Ceuta", "Ceuta"),
        ("extremadura", "Extremadura", "Extremadura"),
        ("galicia", "Galicia", "Galicia"),
        ("islas-baleares", "Islas Baleares", "Islas Baleares"),
        ("la-rioja", "La Rioja", "La Rioja"),
        ("madrid", "Madrid", "Madrid"),
        ("melilla", "Melilla", "Melilla"),
        ("murcia", "Murcia", "Murcia"),
        ("navarra", "Navarra", "Navarra"),
        ("pais-vasco", "País Vasco", "País Vasco"),
        ("valencia", "Valencia", "Valencia"),
    ],
}


POLY_ELTERN_EUROPA = {"gb": "europe/united-kingdom"}

# ---------------------------------------------------------------------------
# Nordamerika (#1216). Zuschnitt nach den Geofabrik-Auszügen unter north-america: die USA und Kanada kommen als Regionen,
# weil die Gesamtauszüge weit über einem GB liegen; Mexiko und Grönland bleiben je ein Teil.
LAENDER_NORDAMERIKA = [
    ("ca", "north-america/canada", "Kanada", "Canada"),
    ("gl", "north-america/greenland", "Grönland", "Greenland"),
    ("mx", "north-america/mexico", "Mexiko", "Mexico"),
    ("us", "north-america/us", "Vereinigte Staaten", "United States"),
]

REGIONEN_NORDAMERIKA = {
    "ca": [   # Polygone unter north-america/canada
        ("alberta", "Alberta", "Alberta"),
        ("british-columbia", "Britisch-Kolumbien", "British Columbia"),
        ("manitoba", "Manitoba", "Manitoba"),
        ("new-brunswick", "New Brunswick", "New Brunswick"),
        ("newfoundland-and-labrador", "Neufundland und Labrador", "Newfoundland and Labrador"),
        ("northwest-territories", "Nordwest-Territorien", "Northwest Territories"),
        ("nova-scotia", "Nova Scotia", "Nova Scotia"),
        ("nunavut", "Nunavut", "Nunavut"),
        ("ontario", "Ontario", "Ontario"),
        ("prince-edward-island", "Prince Edward Island", "Prince Edward Island"),
        ("quebec", "Québec", "Quebec"),
        ("saskatchewan", "Saskatchewan", "Saskatchewan"),
        ("yukon", "Yukon", "Yukon"),
    ],
    "us": [   # Polygone unter north-america/us
        ("alabama", "Alabama", "Alabama"),
        ("alaska", "Alaska", "Alaska"),
        ("arizona", "Arizona", "Arizona"),
        ("arkansas", "Arkansas", "Arkansas"),
        ("california", "Kalifornien", "California"),
        ("colorado", "Colorado", "Colorado"),
        ("connecticut", "Connecticut", "Connecticut"),
        ("delaware", "Delaware", "Delaware"),
        ("district-of-columbia", "Washington, D.C.", "District of Columbia"),
        ("florida", "Florida", "Florida"),
        ("georgia", "Georgia", "Georgia"),
        ("hawaii", "Hawaii", "Hawaii"),
        ("idaho", "Idaho", "Idaho"),
        ("illinois", "Illinois", "Illinois"),
        ("indiana", "Indiana", "Indiana"),
        ("iowa", "Iowa", "Iowa"),
        ("kansas", "Kansas", "Kansas"),
        ("kentucky", "Kentucky", "Kentucky"),
        ("louisiana", "Louisiana", "Louisiana"),
        ("maine", "Maine", "Maine"),
        ("maryland", "Maryland", "Maryland"),
        ("massachusetts", "Massachusetts", "Massachusetts"),
        ("michigan", "Michigan", "Michigan"),
        ("minnesota", "Minnesota", "Minnesota"),
        ("mississippi", "Mississippi", "Mississippi"),
        ("missouri", "Missouri", "Missouri"),
        ("montana", "Montana", "Montana"),
        ("nebraska", "Nebraska", "Nebraska"),
        ("nevada", "Nevada", "Nevada"),
        ("new-hampshire", "New Hampshire", "New Hampshire"),
        ("new-jersey", "New Jersey", "New Jersey"),
        ("new-mexico", "New Mexico", "New Mexico"),
        ("new-york", "New York", "New York"),
        ("north-carolina", "North Carolina", "North Carolina"),
        ("north-dakota", "North Dakota", "North Dakota"),
        ("ohio", "Ohio", "Ohio"),
        ("oklahoma", "Oklahoma", "Oklahoma"),
        ("oregon", "Oregon", "Oregon"),
        ("pennsylvania", "Pennsylvania", "Pennsylvania"),
        ("puerto-rico", "Puerto Rico", "Puerto Rico"),
        ("rhode-island", "Rhode Island", "Rhode Island"),
        ("south-carolina", "South Carolina", "South Carolina"),
        ("south-dakota", "South Dakota", "South Dakota"),
        ("tennessee", "Tennessee", "Tennessee"),
        ("texas", "Texas", "Texas"),
        ("us-virgin-islands", "Amerikanische Jungferninseln", "US Virgin Islands"),
        ("utah", "Utah", "Utah"),
        ("vermont", "Vermont", "Vermont"),
        ("virginia", "Virginia", "Virginia"),
        ("washington", "Washington", "Washington"),
        ("west-virginia", "West Virginia", "West Virginia"),
        ("wisconsin", "Wisconsin", "Wisconsin"),
        ("wyoming", "Wyoming", "Wyoming"),
    ],
}

POLY_ELTERN_NORDAMERIKA = {}

# Verbund -> (Länder, Regionen, Polygon-Eltern). Ein Verbund ist ein einziger Valhalla-Bau; Kacheln verschiedener Bauten
# passen nicht zusammen, darum wird je Kontinent gebaut und veröffentlicht.
KONTINENTE = {
    "europa": (LAENDER_EUROPA, REGIONEN_EUROPA, POLY_ELTERN_EUROPA),
    "nordamerika": (LAENDER_NORDAMERIKA, REGIONEN_NORDAMERIKA, POLY_ELTERN_NORDAMERIKA),
}


def tabellen():
    """Tabellen des Verbunds aus der Umgebungsvariablen VERBUND (Standard europa)."""
    import os
    name = os.environ.get("VERBUND", "europa").strip() or "europa"
    if name not in KONTINENTE:
        raise SystemExit("Unbekannter Verbund: %s (bekannt: %s)" % (name, ", ".join(sorted(KONTINENTE))))
    return KONTINENTE[name]


def auswahl():
    """Länder dieses Baus: alle, oder die in der Umgebungsvariablen VERBUND_GEBIETE genannten (z. B. «ch,li,at,de,fr»).

    Ein Verbund ist ein einziger Valhalla-Bau; nur Teile desselben Baus passen zusammen. Darum lässt sich hier einschränken,
    welche Länder ein Bau umfasst – ein kleiner Bau ist schneller fertig als ein ganzer Kontinent."""
    import os
    gewaehlt = [x.strip() for x in os.environ.get("VERBUND_GEBIETE", "").split(",") if x.strip()]
    laender_tab = tabellen()[0]
    if not gewaehlt:
        return laender_tab
    bekannt = {l[0]: l for l in laender_tab}
    fehlt = [x for x in gewaehlt if x not in bekannt]
    if fehlt:
        raise SystemExit("Unbekannte Länder in VERBUND_GEBIETE: " + ", ".join(fehlt))
    return [bekannt[x] for x in gewaehlt]


def gebiete():
    """Alle Download-Gebiete: dict mit id, poly, name, typ, land."""
    result = []
    _, regionen_tab, poly_eltern = tabellen()
    for land, poly, de, en in auswahl():
        if land in regionen_tab:
            for rid, rde, ren in regionen_tab[land]:
                result.append({"id": f"{land}-{rid}", "poly": poly_eltern.get(land, poly) + "/" + rid, "name": {"de": rde, "en": ren}, "typ": "region", "land": land})
        else:
            result.append({"id": land, "poly": poly, "name": {"de": de, "en": en}, "typ": "land", "land": land})
    return result


def laender():
    regionen_tab = tabellen()[1]
    return [{"id": land, "name": {"de": de, "en": en}, "regionen": [f"{land}-{r[0]}" for r in regionen_tab.get(land, [])]}
            for land, _, de, en in auswahl()]


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
    # Datumsgrenze: Alaska reicht mit fünf Polygonpunkten über 180° hinaus. Ohne Korrektur spannt der Umriss die ganze Erde
    # auf (-180..180) und valhalla_build_elevation lädt Höhendaten für Europa, Afrika und Asien mit. Eine so kleine
    # Minderheit auf der anderen Seite wird darum weggelassen; die paar Inseln bekommen dann keine Höhendaten.
    west = [x for x in xs if x <= 0]
    ost = [x for x in xs if x > 0]
    if west and ost:
        klein = west if len(west) < len(ost) else ost
        if len(klein) < 0.02 * len(xs):
            xs = ost if klein is west else west
    return f"{min(xs):.5f},{min(ys):.5f},{max(xs):.5f},{max(ys):.5f}"


if __name__ == "__main__":
    if "--bbox" in sys.argv:
        print(bbox(sys.argv[sys.argv.index("--bbox") + 1]))
    if "--list" in sys.argv:
        for g in gebiete():
            print(f"{g['id']}\t{g['poly']}")
    if "--laender-poly" in sys.argv:
        # Geofabrik-Pfade der Auszüge, die gebaut werden (ein Auszug je Land dieses Baus)
        for land, poly, _de, _en in auswahl():
            print(poly)
