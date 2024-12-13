#!/usr/bin/bash

set -e

SRC="$1"

if [ -z "$SRC" ]; then
  echo "Provide filename with source DEM"
  exit 1
fi

gdal_calc.py \
  -A "$SRC" \
  --outfile dem_nodata_512_cropped.tif \
  --NoDataValue=-512 \
  --projwin -180 85.06 180 -85.06 \
  --co TILED=YES --co COMPRESS=ZSTD --co BIGTIFF=YES \
  --calc "(A+512) * (A >= -430) - 512"

gdalwarp \
  -t_srs EPSG:3857 \
  -r bilinear \
  -te -20037508.3427892 -20037508.3427892 20037508.3427892 20037508.3427892 \
  -ts 524288 524288 \
  -co TILED=YES -co COMPRESS=ZSTD -co BIGTIFF=YES \
  -multi -wo NUM_THREADS=ALL_CPUS -wm 2000 \
  dem_nodata_512_cropped.tif \
  gmerc_11.tif

gdalwarp \
  -t_srs EPSG:3857 \
  -r bilinear \
  -te -20037508.3427892 -20037508.3427892 20037508.3427892 20037508.3427892 \
  -ts 524288 524288 \
  -co TILED=YES -co COMPRESS=ZSTD -co BIGTIFF=YES \
  -multi  -wo NUM_THREADS=ALL_CPUS -wm 2000 \
  3arcsec_nodata_512.tif \
  gmerc11.tif

gdaladdo \
  -r gauss \
  -ro gmerc_11.tif \
  --config COMPRESS_OVERVIEW ZSTD \
  --config GDAL_TIFF_OVR_BLOCKSIZE 256 \
  --config BIGTIFF_OVERVIEW YES \
  --config GDAL_NUM_THREADS ALL_CPUS \
  --config GDAL_CACHEMAX 2GB