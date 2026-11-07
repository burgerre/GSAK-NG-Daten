# Höhendaten: Quelle, Lizenz und Quellenangabe (#213)

## Quelle

**Copernicus DEM** (Europäische Union / ESA), Bezug über AWS Open Data ([registry.opendata.aws/copernicus-dem](https://registry.opendata.aws/copernicus-dem/)):

- **GLO-90** (Standard): 3″ ≈ 90 m, Bucket `copernicus-dem-90m`
- **GLO-30** (Alternative, nur wenn die Grösse vertretbar ist): 1″ ≈ 30 m, Bucket `copernicus-dem-30m`

Oberflächenmodell (DSM, mit Wald und Gebäuden), Aufnahmen 2011–2015, Höhen in Metern über dem Geoid EGM2008
(Unterschied zu EGM96/SRTM in Mitteleuropa unter 1 m).

## Lizenz

«Licence for the use of the Copernicus DEM» (GLO-30 Public und GLO-90): weltweit, kostenlos, nicht ausschliesslich, auch kommerziell;
Vervielfältigung, Bearbeitung und Weitergabe erlaubt. Pflicht: Quellenangabe; bei veränderten Daten der Hinweis, dass sie verändert sind.
Keine Gewähr der EU/ESA. Siehe auch [relief/LIZENZEN.md](../relief/LIZENZEN.md).

## Quellenangabe (in App, Release und Katalog)

> Höhendaten: Copernicus DEM GLO-90, © DLR e.V. 2010-2014 und © Airbus Defence and Space GmbH 2014-2018, bereitgestellt unter
> COPERNICUS durch die Europäische Union und ESA; alle Rechte vorbehalten. Verändert (HGT-Kacheln).

Englisch (Wortlaut der Lizenz):

> produced using Copernicus WorldDEM-90 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS
> by the European Union and ESA; all rights reserved. Modified (HGT tiles).

Bei GLO-30 steht «GLO-30» bzw. «WorldDEM-30». Der Katalog führt den passenden Text in `hoehen.attribution` / `hoehen.attributionEn`.

## Verarbeitung

`hoehen/hoehen.py`: je 1°-Kachel mit GDAL (`gdalwarp -r bilinear`, `gdal_translate -of SRTMHGT`) auf das SRTM-Punktraster 3601 × 3601
(Randzeilen doppelt, wie SRTM 1″), Int16, -32768 = keine Daten, gzip -9. Valhalla 3.9.0 liest nur dieses Raster (`HGT_DIM = 3601`);
GLO-90 wird darum auf 1″ interpoliert (keine zusätzliche Genauigkeit). Kacheln ganz im Meer (keine Copernicus-Kachel) fehlen.
