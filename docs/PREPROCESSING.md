# PREPROCESSING — Cleaning and Preparation

> Decisions and results of M3 (cleaning and preprocessing). Each section states
> what was checked, what was decided and why, and how to reproduce it.

## Contents

- [Missing values and duplicates](#missing-values-and-duplicates)
- [Train/validation/test split](#trainvalidationtest-split)

## Missing values and duplicates

Issue #12. Reproduce with: `python src/data_cleaning.py`

### What was checked

| Check | Result |
|---|---|
| Explicit nulls (`NaN`) in any of the 55 columns | 0 |
| Rows without exactly one active `Wilderness_Area` indicator | 0 |
| Rows without exactly one active `Soil_Type` indicator | 0 |
| Exact duplicate rows (all 55 columns equal) | 0 |
| Rows with equal features but a different `Cover_Type` | 0 |

The one-hot checks look for *disguised* missing values: a row whose four
`Wilderness_Area` columns (or forty `Soil_Type` columns) are all 0 would have
an unknown category even though no cell is null. Every row has exactly one of
each.

The official documentation (`covtype.info`, section 9) also states
"Missing Attribute Values: None", and all columns load as `int64`, which would
not be possible if the file contained empty cells.

### Zero values in numeric features

Zeros were counted because a 0 is a common placeholder for a missing measurement.

| Feature | Rows equal to 0 |
|---|---|
| Elevation | 0 |
| Aspect | 4,914 |
| Slope | 656 |
| Horizontal_Distance_To_Hydrology | 24,603 |
| Vertical_Distance_To_Hydrology | 38,665 |
| Horizontal_Distance_To_Roadways | 124 |
| Hillshade_9am | 13 |
| Hillshade_Noon | 5 |
| Hillshade_3pm | 1,338 |
| Horizontal_Distance_To_Fire_Points | 51 |

They are **not treated as missing**: 0 is inside the documented range of every
one of these features (an aspect of 0 degrees is north, a distance of 0 is a
cell on the water/road, a hillshade of 0 is full shade) and the documentation
declares no missing-value code. Whether some of the 1,338 zeros in
`Hillshade_3pm` are placeholders was not investigated.

### Decision

| Topic | Strategy | Reason |
|---|---|---|
| Missing values | No imputation and no row removal. | There are none, explicit or disguised. |
| Duplicates | Nothing to remove. | There are no duplicate rows and no conflicting labels. |
| Future data | `clean()` raises an error if nulls appear and drops exact duplicate rows (keeping the first). | New data collected by the app (M6) may not be as clean as the original file; failing loudly is safer than imputing with a strategy nobody chose. |

Rows with equal features but different targets would be kept by `clean()`:
they are legitimate label noise, not duplicates.

### Verification

`clean()` applied to the raw dataset returns 581,012 rows (0 removed), with
0 nulls and 0 duplicates remaining.

### Usage

```python
from data_audit import load_raw
from data_cleaning import clean

df = clean(load_raw())
```

## Train/validation/test split

Issue #16. Reproduce with: `python src/data_split.py`

### Ratios

| Partition | Share |
|---|---|
| Train | 70% |
| Validation | 15% |
| Test | 15% |

### Decision

| Topic | Strategy | Reason |
|---|---|---|
| Ratios | 70 / 15 / 15 | Standard split. 15% test ≈ 87k rows is enough to reliably measure the rarest class (Cottonwood/Willow, 0.47% ≈ 410 rows in test); 70% train ≈ 406k rows is ample for training. |
| Stratification | On `Cover_Type` | Preserves the class proportions in every partition. |
| Seed | `random_state=42` | Reproducible partitions. |
| Order | Test first, then validation from the remainder | The three partitions never overlap. |

The split happens **before** any fitted step, so it does not leak; `data_split.py`
fits nothing.

### Verification

`split_train_val_test()` on the cleaned dataset returns 406,708 train /
87,152 validation / 87,152 test rows (70% / 15% / 15%), and
`check_stratification()` passes: every partition matches the full class shares
to within 0.001 percentage points.

### Usage

```python
from data_audit import load_raw
from data_cleaning import clean, FEATURES, TARGET
from data_split import split_train_val_test

df = clean(load_raw())
X_train, X_val, X_test, y_train, y_val, y_test = split_train_val_test(df[FEATURES], df[TARGET])
```
