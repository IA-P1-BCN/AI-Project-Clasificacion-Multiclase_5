# EDA — Exploratory Data Analysis

> Plan and results of the exploratory data analysis.

## Plan

- [x] Audit the dataset (rows, columns, dtypes, nulls, duplicates)
- [x] Analyze class distribution (frequencies, imbalance)
- [ ] Analyze numeric features (histograms, boxplots)
- [ ] Analyze feature correlations (correlation matrix)
- [ ] Classification-specific visualizations (histograms per class)

## Dataset audit

Source: UCI Covertype (`data/raw/covtype.data`, no header; column names taken from `covtype.info`).
Dataset: download from https://archive.ics.uci.edu/dataset/31/covertype and place `covtype.data` in `data/raw/` (not tracked by Git).
Reproduce with: `python src/data_audit.py`

| Metric | Value |
|---|---|
| Rows | 581,012 |
| Columns | 55 (54 features + target `Cover_Type`) |
| Dtypes | 55 x int64 |
| Nulls | 0 |
| Duplicates | 0 |

### Data types

| Columns | Count | dtype |
|---|---|---|
| Elevation, Aspect, Slope, Horizontal_Distance_To_Hydrology, Vertical_Distance_To_Hydrology, Horizontal_Distance_To_Roadways, Hillshade_9am, Hillshade_Noon, Hillshade_3pm, Horizontal_Distance_To_Fire_Points | 10 | int64 |
| Wilderness_Area1 - Wilderness_Area4 | 4 | int64 |
| Soil_Type1 - Soil_Type40 | 40 | int64 |
| Cover_Type (target) | 1 | int64 |

### Findings

- Row and column counts match the official metadata (581,012 x 55).
- No null values and no fully duplicated rows were found. Nothing was removed or imputed (audit only).
- The raw file has no header; column names were assigned from the official documentation.
- The 44 binary indicator columns (Wilderness_Area, Soil_Type) and the categorical target `Cover_Type` (7 classes) are stored as int64, not as categorical/boolean types.

## Class distribution

Target: `Cover_Type` (7 classes). Reproduce with: `python src/class_distribution.py`

| Class | Count | Percentage |
|---|---|---|
| 1 | 211,840 | 36.46% |
| 2 | 283,301 | 48.76% |
| 3 | 35,754 | 6.15% |
| 4 | 2,747 | 0.47% |
| 5 | 9,493 | 1.63% |
| 6 | 17,367 | 2.99% |
| 7 | 20,510 | 3.53% |

![Class distribution](figures/class_distribution.png)

**Imbalance:** the least frequent class (4, 2,747 samples) versus the most frequent (2, 283,301 samples) gives a min/max ratio of 0.0097, about 1:103. Classes 1 and 2 together account for about 85% of the samples.

**Is imbalance handling needed?** Yes. The imbalance is strong, so plain accuracy would be misleading (always predicting class 2 already gives about 49%). For M3 this suggests a stratified train/test split, evaluating with per-class metrics (e.g. macro F1) and considering techniques such as class weights or resampling. No balancing was applied here (analysis only).

## Feature analysis

_To be filled in M2._

## Findings

_To be filled in M2._
