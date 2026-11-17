# Katalogabschnitt «karten» (Format 1)

Entwurf für #1332. Aufbau wie der Abschnitt `hoehen`, nur einfacher: **eine Datei je Land**, keine Kachelliste.
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
    { "id": "ch", "name": { "de": "Schweiz", "en": "Switzerland" } }
  ],
  "dateien": [
    {
      "land": "ch",
      "datei": "schweiz.pmtiles",
      "url": "https://<r2-domain>/karten/2026-11-17/schweiz.pmtiles",
      "groesse": 350239471,
      "sha256": "…",
      "stand": "2026-11-17"
    }
  ]
}
```

| Feld | Bedeutung |
|---|---|
| `format` | 1. Die App liest den Abschnitt nur bei genau diesem Wert, wie bei `hoehen` und `routing`. |
| `schema` | `openmaptiles`. Der Stil der App erwartet diese Ebenen; ein anderes Schema wäre eine andere Karte. |
| `minzoom` / `maxzoom` | 0–14. Höhere Massstäbe entstehen durch Überzoomen der Vektordaten, die Geometrie bleibt vollständig. |
| `laender` | Liste für die Auswahl, mit deutschem und englischem Namen. Keine Regionen: eine Datei je Land genügt, auch für Deutschland und Frankreich. |
| `dateien` | Je Land eine Datei mit Adresse, Grösse, Prüfsumme und Stand. Mehrere Einträge je Land sind erlaubt, falls ein Land später geteilt wird. |
| `stand` | Datum des OSM-Auszugs. Die App zeigt es je Land an, wie Cachly. |

**Prüfsumme:** SHA-256 über die ganze Datei, wie bei den Höhenkacheln. Bei Dateien von mehreren Gigabyte prüft
die App beim Laden fortlaufend und verwirft die Datei bei Abweichung.

**Was die App damit macht:** Auf der Seite «Offline-Karten» erscheint neben Routingdaten und Höhendaten ein
Abschnitt «Karten» mit Land, Grösse und Stand. Geladene Dateien landen im Kartenordner und erscheinen von selbst
im Blatt «Karte wählen» (#715), wo mehrere Länder gleichzeitig angehakt werden können.
