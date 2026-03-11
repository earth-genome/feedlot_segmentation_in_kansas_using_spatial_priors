# Feedlot Segmentation in Kansas Using Spatial Priors

This repository develops a segmentation workflow for identifying **feedlot lots**, **waste ponds**, and **other land cover** in Kansas using **AlphaEarth embeddings** and **spatial priors**. The current implementation focuses on a first workflow (`W1`) that uses spatial priors as a constrained search space and trains a **Random Forest** classifier for pixel-level classification.

## Overview

The goal of this project is to segment three classes:

- **0 — Other**
- **1 — Pond**
- **2 — Lot**

The pipeline combines:

1. **Spatial priors** that roughly localize candidate feedlot footprints.
2. **AlphaEarth annual embedding tiles** as the input raster features.
3. **Sampled point labels** drawn from polygons / priors.
4. A **Random Forest classifier** trained to predict class labels at the pixel level.
5. A post-training **inference and IoU evaluation** workflow.

## Current workflow: W1

### Main idea

Workflow 1 uses the **intersection of spatial priors and labels** to construct training data. For now, the approach trains a **Random Forest classifier** to segment:

- **lot (2)**
- **pond (1)**
- **other (0)**

A key assumption in this workflow is that the sampled training points are taken **within the labels / priors**, which makes the training data dependent on the quality and completeness of those priors. In future versions, these sampled points could be replaced with **manually marked points inside the spatial priors**.

### Sampling design

The current training sample uses:

- **5,000 lot points**
- **5,000 pond points**
- **7,000 other points**

### How spatial priors are used

The spatial priors act as a **hard-ish boundary**:

- The **bounding box** of each prior is taken.
- That box is **expanded outward by a fixed positive buffer**.
- Pixels outside the expanded prior region are treated as **other**.

Only the **AlphaEarth 256 × 256 tiles** intersecting the processed spatial priors are used.

### Important limitation

This boundary assumption is useful for constraining the search area, but it introduces a known failure mode:

- Some true lots or ponds can fall **outside** the buffered priors.
- Those pixels are then incorrectly treated as **other**.

This likely depresses performance near prior boundaries and contributes to false negatives for foreground classes.

## Results (W1)

The following results are computed **only on pixels that were not sampled for training**:

| Class | Label | IoU |
|---|---:|---:|
| Other | 0 | 0.9992 |
| Pond | 1 | 0.4984 |
| Lot | 2 | 0.6879 |

**Aggregate metrics**

- **mIoU:** `0.7285`
- **Foreground IoU (pond + lot):** `0.6618`

### Interpretation

The model performs well overall and achieves usable segmentation quality, especially given the noisy supervision setup. As expected:

- **Other** has extremely high IoU.
- **Lot** performs reasonably well.
- **Pond** is the weakest class.

The relatively lower pond IoU is likely driven by two factors:

1. the **hard-ish spatial boundary assumption**, and
2. **false positives near pond areas**.

## Repository structure

The repository currently contains a lightweight pipeline organized around scripts, notebooks, utilities, and saved outputs:

```text
feedlot_segmentation_in_kansas_using_spatial_priors/
├── src/
│   ├── 1_gee_data_pull.py
│   ├── 2_sample_points_from_poly.ipynb
│   ├── 3_sample_raster.py
│   ├── 4_merge_to_final_data.ipynb
│   ├── 5_model.ipynb
│   ├── 6_inference.ipynb
│   ├── 7_calculate_pixel_iou.ipynb
│   └── utils/
│       ├── gee.py
│       └── tile_utils.py
├── model/
│   └── 20260309_150216/
├── inference/
│   └── 20260309_150216/
└── README.md
```

## Pipeline

### 1. Pull AlphaEarth / GEE data

`src/1_gee_data_pull.py` reads a GeoJSON of polygons, converts it to **EPSG:4326**, creates tiles, and downloads raster data from Google Earth Engine. The default collection is **AlphaEarth**, defined in `src/utils/gee.py`, which maps this collection to **64 embedding bands** (`A00` to `A63`).

### 2. Sample labeled points

`src/2_sample_points_from_poly.ipynb` is used to sample point labels from polygons / priors.

### 3. Extract raster values

`src/3_sample_raster.py` samples raster values for the training points.

### 4. Merge features and labels

`src/4_merge_to_final_data.ipynb` combines the sampled raster features and labels into the final modeling table.

### 5. Train the model

`src/5_model.ipynb` fits a **RandomForestClassifier**.

### 6. Run inference

`src/6_inference.ipynb` applies the trained model to tiles / pixels in the inference workflow.

### 7. Evaluate performance

`src/7_calculate_pixel_iou.ipynb` computes pixel-level IoU metrics.

## Data notes

This workflow currently relies on:

- **Spatial priors** for candidate feedlot regions.
- **Label polygons / points** for supervision.
- **AlphaEarth annual embeddings** downloaded from GEE.

Because the labels are partly induced by the prior geometry, the training data are not purely independent of the prior assumptions. This should be kept in mind when interpreting performance.

## Environment and dependencies

The repository is not yet packaged with a pinned environment file, but the existing code indicates dependencies such as:

- `python>=3.10`
- `geopandas`
- `numpy`
- `pandas`
- `rasterio`
- `rasterstats`
- `tqdm`
- `scikit-learn`
- `earthengine-api`
- `google-api-core`
- `descarteslabs`
- `affine`
- `torch`
- `tensorflow`

A minimal setup might look like:

```bash
git clone https://github.com/earth-genome/feedlot_segmentation_in_kansas_using_spatial_priors.git
cd feedlot_segmentation_in_kansas_using_spatial_priors

python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install geopandas numpy pandas rasterio rasterstats tqdm scikit-learn \
    earthengine-api google-api-core descarteslabs affine torch tensorflow
```

You will also need to authenticate Google Earth Engine separately.

## Example workflow

A typical run follows this order:

```bash
# 1. Pull AlphaEarth tiles for a GeoJSON region
python src/1_gee_data_pull.py \
  --geojson-path path/to/priors.geojson \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --collection AlphaEarth
```

Then proceed through the notebooks in order:

1. `2_sample_points_from_poly.ipynb`
2. `3_sample_raster.py`
3. `4_merge_to_final_data.ipynb`
4. `5_model.ipynb`
5. `6_inference.ipynb`
6. `7_calculate_pixel_iou.ipynb`

## Known limitations

- **Spatial-prior leakage / dependence:** labels are sampled within prior-defined regions.
- **Boundary bias:** true foreground pixels outside buffered priors can be mislabeled as other.
- **Class difficulty imbalance:** ponds are harder to segment than lots.
- **Packaging:** the project would benefit from a `requirements.txt` or `environment.yml`.

## Next steps

Potential improvements include:

- replacing sampled prior-based labels with **manually curated point labels**;
- softening the prior constraint instead of using a hard boundary;
- trying models beyond Random Forest;
- calibrating the prior buffer size;
- adding clearer experiment tracking and environment reproducibility.

## Acknowledgment

This repository is part of an Earth Genome workflow exploring whether **spatial priors can improve feedlot segmentation** using embedding-based remote sensing features.
