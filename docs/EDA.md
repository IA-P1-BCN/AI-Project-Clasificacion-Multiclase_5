# EDA — Exploratory Data Analysis

> Plan and results of the exploratory data analysis.

## Plan

- [x] Audit the dataset (rows, columns, dtypes, nulls, duplicates)
- [x] Analyze class distribution (frequencies, imbalance)
- [ ] Analyze numeric features (histograms, boxplots)
- [x] Analyze feature correlations (correlation matrix)
- [x] Classification-specific visualizations (histograms per class)

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

Scope: the 10 quantitative features (the 44 binary `Wilderness_Area` / `Soil_Type` indicators are not included). Reproduce with: `python src/class_eda.py`

### Distributions per class

![Histograms per class](figures/class_histograms.png)

![Boxplots per class](figures/class_boxplots.png)

### Correlation matrix

![Correlation matrix](figures/correlation_matrix.png)

Strongest correlations between numeric features (Pearson):

| Feature pair | r |
|---|---|
| Hillshade_9am / Hillshade_3pm | -0.780 |
| Aspect / Hillshade_3pm | 0.647 |
| Horizontal_Distance_To_Hydrology / Vertical_Distance_To_Hydrology | 0.606 |
| Hillshade_Noon / Hillshade_3pm | 0.594 |
| Aspect / Hillshade_9am | -0.579 |
| Slope / Hillshade_Noon | -0.527 |

No pair exceeds |r| = 0.8, so there is moderate (not extreme) redundancy. The hillshade features correlate with each other and with Aspect and Slope, which is consistent with hillshade being derived from terrain orientation and slope.

### Features that separate the classes

Eta squared (share of each feature's variance explained by `Cover_Type`; higher means the class means differ more):

| Feature | Eta squared |
|---|---|
| Elevation | 0.6160 |
| Horizontal_Distance_To_Roadways | 0.0959 |
| Slope | 0.0742 |
| Horizontal_Distance_To_Fire_Points | 0.0698 |
| Hillshade_9am | 0.0323 |
| Hillshade_Noon | 0.0293 |
| Horizontal_Distance_To_Hydrology | 0.0238 |
| Vertical_Distance_To_Hydrology | 0.0123 |
| Hillshade_3pm | 0.0106 |
| Aspect | 0.0046 |

- `Elevation` is by far the most discriminative numeric feature (61.6% of its variance is explained by the class).
- `Horizontal_Distance_To_Roadways`, `Slope` and `Horizontal_Distance_To_Fire_Points` show some separation (about 7-10%); the remaining features separate the classes weakly on their own.
- Limitation: eta squared only captures differences between class means. A feature with a low score may still help to tell some classes apart through the shape of its distribution, and the binary soil/wilderness indicators were not evaluated here.

## Findings

_To be filled in M2._
