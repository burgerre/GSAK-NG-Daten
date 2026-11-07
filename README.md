# GSAK-NG-Daten

Offline-Daten für die App [GSAK-NG](https://gsak-ng.com): **Routing-Pakete je Land** für «Route hierher» ohne Netz und
**Höhendaten je Land** (Höhenprofil offline, «Höhen aktualisieren»).
Die App lädt die Pakete direkt von hier, ohne Anmeldung. Der App-Code liegt nicht in diesem Repository.

*Offline data for the GSAK-NG app: routing packages per country, downloaded by the app without sign-in. App code is not part of this repository.*

## Inhalt

| Ort | Inhalt |
|---|---|
| [`katalog.json`](katalog.json) | Verzeichnis aller Pakete (Land, Stand, Grösse, Prüfsumme, Download-Adressen). Die App liest nur diese Datei; ziehen die Pakete einmal um, ändern sich nur die Adressen hier. |
| [Releases](../../releases) | Die Pakete selbst, ein Release je Land und Stand, z. B. `routing-ch-2026-11-02`. Pakete über 1,9 GB sind in Teile `…zip.001`, `…zip.002` aufgeteilt. |
| [`.github/workflows/hoehen.yml`](.github/workflows/hoehen.yml) | Höhendaten (#213): Copernicus DEM GLO-90 (Standard) bzw. GLO-30 → 1°-Kacheln SRTM-HGT 3601 × 3601 (`.hgt.gz`) je Land bzw. Region (gleiche Gebiete wie der Routing-Verbund) → Release `hoehen-<quelle>-<stand>` (eine Datei je Kachel) → Katalog, Abschnitt `hoehen`. Pull Requests messen nur (Grösse, Laufzeit). |
| [`.github/workflows/routing-land.yml`](.github/workflows/routing-land.yml) | Erzeugung: Geofabrik-Auszug des Landes → Valhalla 3.9.0 → Paket im GSAK-NG-Paketformat 1 → Release → Katalog. Nur von Hand gestartet. |

Aktualisierung etwa alle drei Monate. Ältere Stände bleiben als Releases erhalten, der Katalog zeigt je Land den neusten.

## Paketformat 1

Ein ZIP (ungepackt gespeichert) mit `gsakng-routing.json` (Beschreibung: Land, Bounding Box, Stand, Quellenangabe),
`valhalla.json`, `valhalla_tiles.tar` (Valhalla 3.9.0, valhalla-mobile 0.6.4) und `tzdata.tar` (Zeitzonen für iOS).

## Höhendaten (Format 1)

Eine Datei je 1°-Kachel, z. B. `N47E008.hgt.gz`: SRTM-HGT 3601 × 3601, Int16 big-endian, Meter, -32768 = keine Daten, gzip. Der Katalog
nennt je Gebiet die Kacheln und die Summe der Grössen, je Kachel Adresse, Grösse und SHA-256. Kacheln an Grenzen gehören zu mehreren Gebieten;
die App lädt jede nur einmal.

## Lizenz und Quellen

- **Daten:** © OpenStreetMap-Mitwirkende, verfügbar unter der [Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1-0/).
  Die Pakete sind eine aus OpenStreetMap abgeleitete Datenbank und stehen ebenfalls unter der ODbL.
  Quelle der Auszüge: [Geofabrik](https://download.geofabrik.de/).
- **Höhendaten** für die Steigungsberechnung: öffentliche Terrain-Kacheln (Mapzen/AWS Terrain Tiles,
  [Quellenangaben](https://github.com/tilezen/joerd/blob/master/docs/attribution.md)).
- **Höhendaten** (Abschnitt `hoehen` im Katalog, Releases `hoehen-…`): Copernicus DEM GLO-90 bzw. GLO-30,
  © DLR e.V. 2010-2014 und © Airbus Defence and Space GmbH 2014-2018, bereitgestellt unter COPERNICUS durch die Europäische Union und ESA;
  alle Rechte vorbehalten. Verändert (HGT-Kacheln). Details und englischer Wortlaut: [`hoehen/QUELLEN.md`](hoehen/QUELLEN.md).
- **Routing-Engine:** [Valhalla](https://github.com/valhalla/valhalla) (MIT); Zeitzonen-Daten aus
  [valhalla-mobile](https://github.com/Rallista/valhalla-mobile).
- Fragen und Rückmeldungen: [GSAK-NG-Community](https://github.com/burgerre/GSAK-NG-Community).
