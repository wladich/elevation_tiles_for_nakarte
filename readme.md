Purpose
=======
Create elevation tiles for https://nakarte.me.
Tiles are used to display elevation at mouse cursor.

Requirements
============
`apt install gdal-bin python3-gdal`

Running
=======
1. `prepare_raster.sh <DEM.tif>`
   
   Creates intermediate geotff file with DEM in Google Mercator projection

   **DEM.tif** - File with global DEM, e.g. merged from hgt files from https://viewfinderpanoramas.org/Coverage%20map%20viewfinderpanoramas_org3.htm
2. `python3 geotiff2mbtiles.py gmerc_11.tif elevation.mbtiles`