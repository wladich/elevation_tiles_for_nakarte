# coding: utf-8
import argparse
import gzip
import os
import sqlite3
import time

import numpy as np
from osgeo import gdal

ZOOM = 11
TILESIZE = 256
NO_DATA = -512


def get_rasterband(filename):
    dataset = gdal.Open(filename)
    assert dataset
    assert dataset.RasterCount == 1

    band = dataset.GetRasterBand(1)
    assert band.XSize == 2**ZOOM * TILESIZE
    assert band.YSize == 2**ZOOM * TILESIZE
    assert band.DataType == gdal.GDT_Int16
    assert band.GetBlockSize() == [TILESIZE, TILESIZE]
    assert band.GetOverviewCount() == ZOOM
    return dataset, band


def get_overview(rasterband, zoom):
    overview_n = ZOOM - zoom - 1
    overview = rasterband.GetOverview(overview_n)
    assert overview.XSize == 2**zoom * TILESIZE
    assert overview.YSize == 2**zoom * TILESIZE
    assert overview.DataType == gdal.GDT_Int16
    assert overview.GetBlockSize() == [TILESIZE, TILESIZE]
    return overview


def create_mbtiles_file(filepath: str):
    """
    Создаёт файл в формате MBTiles и возвращает подключение к базе данных.

    :param filepath: Путь к создаваемому файлу MBTiles.
    :return: Подключение к базе данных SQLite.
    """
    if os.path.exists(filepath):
        os.unlink(filepath)

    connection = sqlite3.connect(filepath)
    connection.executescript(
        """
    PRAGMA journal_mode = OFF;
    PRAGMA synchronous = OFF;
    
    CREATE TABLE tiles (
        zoom_level INTEGER,
        tile_column INTEGER,
        tile_row INTEGER,
        tile_data BLOB
    );
    """
    )
    return connection


def create_mbtiles_index(mbtiles):
    mbtiles.execute(
        """
        CREATE UNIQUE INDEX tile_index 
        ON tiles (zoom_level, tile_column, tile_row);
        """
    )


def insert_tile(
    connection, zoom_level: int, tile_column: int, tile_row: int, tile_data: bytes
):
    """
    Вставляет тайл в базу данных MBTiles.

    :param connection: Подключение к базе данных SQLite (MBTiles).
    :param zoom_level: Уровень масштабирования (зум).
    :param tile_column: Колонка тайла.
    :param tile_row: Строка тайла.
    :param tile_data: Данные тайла в формате bytes.
    """
    cursor = connection.cursor()
    cursor.execute(
        """
    INSERT INTO tiles (zoom_level, tile_column, tile_row, tile_data)
    VALUES (?, ?, ?, ?);
    """,
        (zoom_level, tile_column, tile_row, tile_data),
    )


def decode_raw_tile(b: bytearray):
    assert len(b) == TILESIZE * TILESIZE * 2
    return np.frombuffer(b, dtype=np.int16)


def is_tile_empty(tile: np.ndarray) -> bool:
    return np.all(tile == NO_DATA)


def apply_predictor(tile):
    return tile - np.concatenate(
        (
            np.array([0], dtype=np.int16),
            tile[:-1],
        )
    )


def write_zoom_level_tiles_from_geotiff_to_mbtiles(zoom_level, band, mbtiles):
    size = 0
    tiles_count = 2**zoom_level
    for y in range(tiles_count):
        for x in range(tiles_count):
            tile = decode_raw_tile(band.ReadBlock(x, y))
            if is_tile_empty(tile):
                continue
            tile = apply_predictor(tile)
            encoded = gzip.compress(tile.tobytes(), compresslevel=6)
            size += len(encoded)
            insert_tile(mbtiles, zoom_level, x, y, encoded)
        print(f"\r{(y+1) / tiles_count * 100:.2f}%", end="", flush=True)
    print()
    print('Size', size)

def write_tiles_from_geotiff_to_mbtiles(band, mbtiles):
    # print(f"Zoom level: {ZOOM}".center(50, "="))
    # write_zoom_level_tiles_from_geotiff_to_mbtiles(ZOOM, band, mbtiles)
    # for zoom in range(ZOOM):
    for zoom in [0]:
        print(f"Zoom level: {zoom}".center(50, "="))
        overview = get_overview(band, zoom)
        write_zoom_level_tiles_from_geotiff_to_mbtiles(zoom, overview, mbtiles)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("src", help="GeoTIFF file with world DEM")
    parser.add_argument("dest", help="MBTiles file")
    conf = parser.parse_args()
    _unused_dataset, rasterband = get_rasterband(conf.src)
    mbtiles = create_mbtiles_file(conf.dest)
    write_tiles_from_geotiff_to_mbtiles(rasterband, mbtiles)
    mbtiles.commit()
    create_mbtiles_index(mbtiles)
    mbtiles.close()


if __name__ == "__main__":
    start = time.time()
    main()
    print("Elapsed:", round(time.time() - start, 2))
