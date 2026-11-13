# PREPROCESSING — Cleaning and Preparation

> Decisions and results of M3 (cleaning and preprocessing). Each section states
> what was checked, what was decided and why, and how to reproduce it.

## Contents

- [Missing values and duplicates](#missing-values-and-duplicates)
- [Train/validation/test split](#trainvalidationtest-split)
- [Feature scaling](#feature-scaling)
- [Outliers](#outliers)

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

## Feature scaling

Issue #14. Reproduce with: `python src/feature_scaling.py` (about 1.5 minutes)

### What is scaled

| Group | Columns | Treatment |
|---|---|---|
| Numeric features | 10 (`Elevation`, `Aspect`, `Slope`, the 4 distances, the 3 hillshades) | `StandardScaler` |
| Binary features | 44 (`Wilderness_Area1-4`, `Soil_Type1-40`) | Passed through unchanged |
| Target | `Cover_Type` | Never scaled |

The binary indicators are already on a 0/1 scale. Standardizing them would
turn each rare soil type into a column with very large values for the few
rows that have it and would remove their meaning as indicators.

### Why scaling is needed

The numeric features live on very different scales (training partition):

| Feature | Mean | Standard deviation |
|---|---|---|
| Elevation | 2959.51 | 280.02 |
| Aspect | 155.83 | 111.98 |
| Slope | 14.10 | 7.49 |
| Horizontal_Distance_To_Hydrology | 269.35 | 212.39 |
| Vertical_Distance_To_Hydrology | 46.42 | 58.23 |
| Horizontal_Distance_To_Roadways | 2351.82 | 1559.33 |
| Hillshade_9am | 212.13 | 26.76 |
| Hillshade_Noon | 223.32 | 19.77 |
| Hillshade_3pm | 142.55 | 38.27 |
| Horizontal_Distance_To_Fire_Points | 1979.97 | 1323.56 |

Linear and distance-based models (Logistic Regression, neural networks) are
sensitive to this. Tree-based models (Random Forest, XGBoost, LightGBM) are
not; they can use the same pipeline or skip the preprocessor.

### Scaler choice: StandardScaler

Logistic regression (default hyperparameters, `max_iter=1000`) on a stratified
60,000-row sample, 75% train / 25% validation, one run per scaler:

| Scaler | Accuracy | Macro F1 | Iterations | Converged |
|---|---|---|---|---|
| none | 0.6789 | 0.3296 | 1000 | No |
| standard | 0.7219 | 0.5257 | 233 | Yes |
| robust | 0.7212 | 0.5253 | 182 | Yes |
| minmax | 0.7212 | 0.4987 | 233 | Yes |

- Without scaling the solver does not converge and macro F1 drops to 0.33.
- `StandardScaler` and `RobustScaler` are tied (macro F1 0.5257 vs 0.5253, a
  difference too small to mean anything on a single split). `MinMaxScaler` is
  lower on macro F1 (0.4987), that is, on the minority classes.
- `StandardScaler` is chosen: it is the conventional choice for regularized
  linear models, and the numeric features are bounded physical measurements
  with long tails (at most 5.4% of rows outside the IQR fences, see
  [EDA.md](EDA.md)), not the extreme outliers that `RobustScaler` is meant for.
- `build_preprocessor("robust")` and `build_preprocessor("minmax")` remain
  available if the decision on outliers (#13) changes this.

This comparison only supports the scaler choice. It uses a sample, a single
split and untuned hyperparameters, so the scores are not model results.

### No data leakage

The scaler learns the mean and standard deviation from the **training rows
only** and applies them to validation and test rows. `build_preprocessor()`
returns an unfitted transformer meant to be the first step of a scikit-learn
`Pipeline`, so cross-validation refits it on each training fold.

Checked on a stratified 80/20 split (464,809 / 116,203 rows; demonstration
only, the project split is defined in #16):

| Check | Result |
|---|---|
| Fitted mean and scale equal the training partition statistics | Yes |
| Training numeric features after scaling | Mean 0, standard deviation 1 |
| Test numeric features after scaling | Means between -0.0077 and 0.0030, standard deviations between 0.9970 and 1.0054 (close to 0 and 1 but not exact, as expected when the test rows are not used to fit) |
| 44 binary features identical before and after, in train and test | Yes |
| Column names and order preserved (54 columns) | Yes |

`main()` runs these checks through `check_scaling()` and fails if any does not hold.

### Usage

```python
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from feature_scaling import build_preprocessor

pipeline = Pipeline([
    ("preprocessor", build_preprocessor()),      # fitted on training data only
    ("model", LogisticRegression(max_iter=1000)),
])
pipeline.fit(X_train, y_train)
pipeline.predict(X_test)
```

Do not call `fit` or `fit_transform` on the full dataset before splitting.
Exporting the fitted pipeline for the app is covered by #32.

## Outliers

Issue #13. Reproduce with: `python src/outlier_treatment.py`

### What was checked

Outliers were counted on the 10 numeric features of the **training partition**
only (the 44 binary indicators cannot have outliers in this sense), with two
rules: the IQR rule (value beyond Q1 - 1.5*IQR or Q3 + 1.5*IQR) and the z-score
rule (|z| > 3).

| Feature | IQR count | IQR % | z-score count | z-score % |
|---|---|---|---|---|
| Elevation | 10,997 | 2.70 | 4,103 | 1.01 |
| Aspect | 0 | 0.00 | 0 | 0.00 |
| Slope | 10,705 | 2.63 | 2,831 | 0.70 |
| Horizontal_Distance_To_Hydrology | 9,254 | 2.28 | 5,010 | 1.23 |
| Vertical_Distance_To_Hydrology | 21,982 | 5.41 | 7,101 | 1.75 |
| Horizontal_Distance_To_Roadways | 460 | 0.11 | 22 | 0.01 |
| Hillshade_9am | 12,204 | 3.00 | 5,231 | 1.29 |
| Hillshade_Noon | 11,046 | 2.72 | 4,634 | 1.14 |
| Hillshade_3pm | 5,475 | 1.35 | 2,131 | 0.52 |
| Horizontal_Distance_To_Fire_Points | 21,724 | 5.34 | 7,654 | 1.88 |

The IQR rule flags more points than the z-score rule because the features are
skewed (see `docs/EDA.md`). The heaviest are `Vertical_Distance_To_Hydrology`
and `Horizontal_Distance_To_Fire_Points` (about 5.4% each); `Aspect` has none.

### Decision

**Clip (winsorize) the numeric features to the training IQR fences. No row is
removed.** Reasons:

1. **They are legitimate tails, not errors.** The EDA shows these are long tails
   of skewed distributions; the documentation declares no missing-value code and
   nothing confirmed them as measurement errors.
2. **The main models do not need it.** The project's models are tree-based
   (Random Forest, XGBoost, LightGBM), insensitive to monotonic outliers.
   Clipping still caps extremes for the linear and distance-based baselines.
3. **Removal would distort the classes.** Dropping every training row flagged by
   the IQR rule in any feature would remove **75,308 of 406,708 rows (18.5%)**
   and shift the per-class shares by up to **2.375 percentage points** (class 1
   up, class 3 down about 1.8 pp), worsening the already strong imbalance.
   Clipping removes no row, so the class distribution is preserved exactly.

### Applied and verified

The treatment is a scikit-learn transformer, `OutlierClipper`, wrapped in a
`ColumnTransformer` (`build_outlier_preprocessor`) that clips the numeric
features and passes the binary ones through. It learns the clip bounds in `fit`
from the **training partition only**, so it is leakage-safe and runs before the
scaler inside a `Pipeline`.

| Check | Result |
|---|---|
| Clip bounds equal the training IQR fences and differ from the full-data fences | Pass (`check_no_leakage`) |
| Numeric values changed (clipped) in training | 103,847 |
| Values beyond the bounds after clipping | 0 |
| Rows removed | 0 |
| Binary features identical before and after | True |
| Class distribution before vs after | unchanged (1: 36.46%, 2: 48.76%, 3: 6.15%, 4: 0.47%, 5: 1.63%, 6: 2.99%, 7: 3.53%) |

### Usage

```python
from sklearn.pipeline import Pipeline

from outlier_treatment import build_outlier_preprocessor
from feature_scaling import build_preprocessor

pipeline = Pipeline([
    ("outliers", build_outlier_preprocessor()),   # clip, fitted on training data only
    ("scaler", build_preprocessor()),             # then scale
    ("model", ...),
])
pipeline.fit(X_train, y_train)
```

Clipping is most useful for linear and distance-based models; for tree-based
models it can be left out of the pipeline without affecting results.
