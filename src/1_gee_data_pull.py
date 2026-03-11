
import argparse
from dataclasses import fields
from pathlib import Path
import re
import sys

import geopandas as gpd
from tqdm import tqdm

sys.path.append('/Users/muhammadabdul/Desktop/penn/earth_genome_internship/climate_trace/sub_facility_discrimination/code/utils/')
import gee
from tile_utils import create_tiles

def valid_date(s: str) -> str:
    """Validate date string in YYYY-MM-DD format and return it unchanged."""
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s
    raise argparse.ArgumentTypeError(f"Not a valid date: '{s}'.")

def main(args):
    """Pull raster data from Earth Engine."""
    tiles_written = []
    
    extractor = gee.GEE_Data_Extractor(
        args.start_date, 
        args.end_date,
        args.config
    )

    gdf = gpd.read_file(args.geojson_path).to_crs("EPSG:4326")
    tiles = create_tiles(
        gdf.unary_union,
        extractor.config.tilesize,
        extractor.config.pad
    )
    print(f'{len(tiles)} tiles created.')

    outdir = Path(args.geojson_path.split('.geojson')[0] + args.collection)
    outdir.mkdir(parents=True, exist_ok=True)

    for tile in tqdm(tiles, desc="Pulling tiles from GEE"): 
        tif_name = (f"{extractor.config.collection}_{tile.key}_"
                    f"{extractor.start_date}_{extractor.end_date}.tif")
        outpath = outdir / tif_name

        if outpath.exists():
            print(f"Tile {tif_name} already exists at {outdir}, skipping.")
            continue

        pixels = extractor.get_tile_data(tile)
        extractor.save_tile(pixels, tile, outdir)
        tiles_written.append(tile)

    return tiles_written

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=("Pull raster data from GEE."))

    # Required args
    parser.add_argument(
        "--geojson-path", type=str,
        help="GeoJSON polygons for which to pull raster data.",
    )
    parser.add_argument(
        "--start-date", type=valid_date, required=True,
        help="Start date in YYYY-MM-DD format")
    parser.add_argument(
        "--end-date", type=valid_date, required=True,
        help="End date in YYYY-MM-DD format")

    # DataConfig args
    data_defaults = gee.DataConfig()

    parser.add_argument("--tilesize", type=int,
                        default=data_defaults.tilesize,
                        help="Tile width in pixels for requests to GEE")
    parser.add_argument("--pad", type=int,
                        default=data_defaults.pad,
                        help="Number of pixels to pad each tile")
    parser.add_argument("--collection", type=str,
                        default=data_defaults.collection,
                        choices=gee.DataConfig.available_collections(),
                        help="Satellite image collection")
    parser.add_argument("--clear_threshold", type=float,
                        default=data_defaults.clear_threshold,
                        help="Clear sky (cloud absence) threshold")
    parser.add_argument("--max_workers", type=int,
                        default=data_defaults.max_workers,
                        help="Maximum concurrent GEE requests")

    args = parser.parse_args()

    config_dict = {
        f.name: getattr(args, f.name, None) for f in fields(gee.DataConfig)
    }

    args.config = gee.DataConfig(**config_dict)
    main(args)
