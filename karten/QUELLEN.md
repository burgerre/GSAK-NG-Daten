# Kartenkacheln: Quellen und Lizenz

| | |
|---|---|
| Daten | [OpenStreetMap](https://www.openstreetmap.org), Länderauszüge von [Geofabrik](https://download.geofabrik.de) |
| Lizenz | [ODbL 1.0](https://opendatacommons.org/licenses/odbl/) – Quellenangabe Pflicht: «© OpenStreetMap contributors» |
| Werkzeug | [planetiler](https://github.com/onthegomap/planetiler) (Apache 2.0), Schema [OpenMapTiles](https://openmaptiles.org) |
| Format | [PMTiles v3](https://docs.protomaps.com/pmtiles/) – eine Datei je Land, die App liest daraus einzelne Kacheln |
| Zoomstufen | z0–14. Vektorkacheln werden darüber hinaus überzoomt: die Geometrie bleibt vollständig, die Karte ist auch im Massstab 20 m scharf. |

Die App zeigt die Quellenangabe bei jeder Karte an. Eigene Dateien gehören in denselben Ordner und erscheinen von selbst
im Blatt «Karte wählen» (#715).
