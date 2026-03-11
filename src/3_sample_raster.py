import argparse
import glob
import os

import geopandas as gpd
import numpy as np
import rasterio
import tqdm

def sample_raster(raster_path, gdf, band_prefix="band"):
    """Sample multi-band raster values for points in a GeoDataFrame."""

    if gdf.sindex is None:
        _ = gdf.sindex  # triggers index build
    
    with rasterio.open(raster_path) as src:
        raster_bounds = src.bounds
        candidate_idx = list(gdf.sindex.intersection(raster_bounds))

        subset = gdf.loc[candidate_idx]
        if len(subset) == 0:
            return gdf

        coords = [(geom.x, geom.y) for geom in subset.geometry]

        sampled = np.array(list(src.sample(coords)))
        n_bands = sampled.shape[1]

        for b in range(n_bands):
            col = f"{band_prefix}_{b+1}"
            gdf.loc[subset.index, col] = sampled[:, b]

    return gdf

def main(geojson_path, tif_dir, type):
    "Sample rasters to point GeoJSON."
    gdf = gpd.read_file(args.geojson_path)
    tif_paths = sorted(glob.glob(os.path.join(args.tif_dir, "*.tif")))

    for tif_path in tqdm.tqdm(tif_paths):
        gdf = sample_raster(tif_path, gdf, band_prefix="band")

    outpath = args.geojson_path.split('.geojson')[0] + f"_{args.type}.parquet"
    gdf.to_parquet(outpath, index=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sample rasters to point GeoJSON.")
    parser.add_argument("geojson_path", help="Path to input points GeoJSON")
    parser.add_argument("tif_dir", help="Directory containing raster files")
    parser.add_argument("type", help="Type of sample to generate")

    args = parser.parse_args()
    main(*vars(args))
