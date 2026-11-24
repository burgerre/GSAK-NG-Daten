# Katalogabschnitt «karten» (Format 1)

Entwurf für #1332, erweitert mit #1386. Aufbau wie der Abschnitt `hoehen`, nur ohne Kachelliste: **eine Datei je Gebiet**.
Kleine Länder sind ein Gebiet; grosse Länder bestehen aus **Regionen** (`us-california`, `ca-quebec`), weil die USA als eine
Datei rund 10 GB wären und Kanada ähnlich – auf einem Handy unbrauchbar.
Die Dateien liegen nicht auf GitHub-Releases, sondern auf **Cloudflare R2** (Entscheid Reto 16.11.2026) – der
Katalog nennt die vollständige Adresse, die App unterscheidet die Ablage nicht.

```json
"karten": {
  "format": 1,
  "schema": "openmaptiles",
  "stand": "2026-11-17",
  "quelle": "OpenStreetMap (Auszüge von Geofabrik), planetiler",
  "attribution": "Karte: © OpenStreetMap contributors, ODbL 1.0",
  "attribution_en": "Map: © OpenStreetMap contributors, ODbL 1.0",
  "lizenz": "ODbL-1.0",
  "minzoom": 0,
  "maxzoom": 14,
  "laender": [
    { "id": "ch", "name": { "de": "Schweiz", "en": "Switzerland" }, "regionen": [] },
    { "id": "us", "name": { "de": "Vereinigte Staaten", "en": "United States" }, "regionen": ["us-california", "us-texas"] }
  ],
  "dateien": [
    {
      "id": "ch",
      "land": "ch",
      "name": { "de": "Schweiz", "en": "Switzerland" },
      "datei": "schweiz.pmtiles",
      "url": "https://<r2-domain>/karten/2026-11-17/schweiz.pmtiles",
      "groesse": 350239471,
      "sha256": "…",
      "stand": "2026-11-17"
    },
    {
      "id": "us-california",
      "land": "us",
      "name": { "de": "Kalifornien", "en": "California" },
      "datei": "us-california.pmtiles",
      "url": "https://<r2-domain>/karten/2026-11-20/us-california.pmtiles",
      "groesse": 1103244912,
      "sha256": "…",
      "stand": "2026-11-20"
    }
  ]
}
```

| Feld | Bedeutung |
|---|---|
| `format` | 1. Die App liest den Abschnitt nur bei genau diesem Wert, wie bei `hoehen` und `routing`. |
| `schema` | `openmaptiles`. Der Stil der App erwartet diese Ebenen; ein anderes Schema wäre eine andere Karte. |
| `minzoom` / `maxzoom` | 0–14. Höhere Massstäbe entstehen durch Überzoomen der Vektordaten, die Geometrie bleibt vollständig. |
| `laender` | Liste für die Auswahl, mit deutschem und englischem Namen. `regionen` nennt bei grossen Ländern die Gebiets-Ids der Teile (#1386); leer bzw. fehlend heisst: eine Datei für das ganze Land. |
| `dateien` | Je Gebiet eine Datei mit Adresse, Grösse, Prüfsumme und Stand. `id` ist das Gebiet (Land oder Region), `land` immer das Land; `name` der Name des Gebiets. Fehlt `id`, gilt `land` – so bleiben ältere Kataloge lesbar. |
| `stand` | Datum des OSM-Auszugs. Die App zeigt es je Land an, wie Cachly. |

**Prüfsumme:** SHA-256 über die ganze Datei, wie bei den Höhenkacheln. Bei Dateien von mehreren Gigabyte prüft
die App beim Laden fortlaufend und verwirft die Datei bei Abweichung.

**Was die App damit macht:** Auf der Seite «Offline-Karten» erscheint neben Routingdaten und Höhendaten ein
Abschnitt «Karten» mit Land, Grösse und Stand. Geladene Dateien landen im Kartenordner und erscheinen von selbst
im Blatt «Karte wählen» (#715), wo mehrere Länder gleichzeitig angehakt werden können.

## Mehrere Kontinente (#1386)

Ein Lauf von [`hochladen.py`](hochladen.py) **ergänzt** den Abschnitt: Einträge mit gleicher `id` und gleichem Dateinamen
werden ersetzt, fremde bleiben stehen. Ein Lauf mit dem Nordamerika-Ordner lässt Europa also im Katalog – früher hätte
`katalog["karten"] = abschnitt` Europa verdrängt, die Dateien lägen weiter auf R2 und die App zeigte sie nicht mehr.
Der `stand` des Abschnitts ist der neueste; je Datei steht der eigene Stand daneben.

Die Gebietstabelle kommt aus [`verbund/gebiete.py`](../verbund/gebiete.py) über `gebiete()`, also mit Regionen; die
Umgebungsvariable `VERBUND` wählt den Kontinent (Standard `europa`), wie beim Verbundbau:

```sh
VERBUND=nordamerika python3 -I karten/hochladen.py ~/karten-nordamerika/out 2026-11-20 --trockenlauf
```

Als Schlüssel für die Zuordnung Datei → Gebiet gelten beide Schreibweisen, die vorkommen: die Gebiets-Id
(`us-california.pmtiles`) und der letzte Teil des Geofabrik-Pfads (`switzerland.pmtiles`).

**Leere Karten** werden übersprungen (unter 64 KB, `MIN_KARTE`): Puerto Rico und die Amerikanischen Jungferninseln
fehlen im Geofabrik-Kontinentauszug `north-america-latest.osm.pbf` und ergaben 0 B (siehe #1385). Ein Land mit einer
Karte, die nichts zeigt, gehört nicht in den Katalog.

Prüfungen ohne Netz: `python3 -I -m unittest discover -s karten -p "test_*.py"`.
