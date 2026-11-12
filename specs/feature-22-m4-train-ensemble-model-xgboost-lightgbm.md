# Spec: feature/22-m4-train-ensemble-model-xgboost-lightgbm

| | |
|---|---|
| Issue | #22 - [M4] Train ensemble model (XGBoost / LightGBM) |
| Milestone | M4 |
| Branch | `feature/22-m4-train-ensemble-model-xgboost-lightgbm` (from `develop`) |
| Owner | @nagicome03 |
| Depends on | #19 (M4 baseline, for the CV protocol) |

## Goal

Train the two gradient-boosted ensembles (XGBoost and LightGBM) with default
hyperparameters, evaluate them with the cross-validation protocol, and record
their metrics so they can be compared against the M4 baseline.

## Scope

- **In scope:**
  - Train XGBoost and LightGBM (default hyperparameters).
  - Evaluate with 5-fold stratified cross-validation (accuracy, precision /
    recall / F1 macro, and F1 per class).
  - Record the top feature importances for each model.
- **Out of scope:** class-imbalance handling (#17), hyperparameter tuning (#29),
  overfitting analysis (#28), final test-set evaluation and full write-up (#31).

## Design

New file `src/gradient_boosting.py`, self-contained (see the dependency note
below), reusing the shared data helpers:

- `load_raw` and `COLUMNS` from `data_audit`; `clean`, `FEATURES` and `TARGET`
  from `data_cleaning`.
- `build_models()` -> `{"XGBoost": XGBClassifier, "LightGBM": LGBMClassifier}`
  with default hyperparameters and `random_state=42`.
- `cross_val_evaluate(model, X, y)` -> runs 5-fold `StratifiedKFold(shuffle=True,
  random_state=42)` and returns, per metric, the mean and std across folds, plus
  the F1 per class. It fits the model once per fold.
- `feature_importances(model, X, y)` -> fits on the training rows and returns the
  feature importances sorted descending.
- `main()` -> loads, cleans, does a stratified 70/30 demonstration split, runs
  the CV evaluation for both models and prints reproducible summary tables.

Decisions and reasons:

- **No scaling.** Tree ensembles split on thresholds, so rescaling numeric
  features has no effect. We train on the raw (cleaned) features.
- **No class weights / SMOTE.** That is #17; here we record the "vanilla" result
  to measure the gain later.
- **Default hyperparameters.** Tuning is #29.
- **70/30 demonstration split.** `src/data_split.py` (#16) and
  `src/baseline.py` (#19) are not merged yet, so this module cannot import
  `split_train_val_test` or `baseline.evaluate_model`. Once both merge, replace
  the local split with `split_train_val_test` and the local CV with
  `baseline.evaluate_model`.

Environment note: the local environment runs numpy 2.5.4 / pandas 3.1.0, so
xgboost 3.4.1 and lightgbm 4.7.0 were installed (newer than the pins
`xgboost==2.1.1` / `lightgbm==4.5.0` in `requirements.txt`, which require numpy
< 2). `libomp` was installed via Homebrew so both native libraries load.

## Acceptance criteria

- [x] XGBoost and LightGBM trained
- [x] Evaluated with the CV protocol
- [x] Metrics recorded (accuracy, precision/recall/F1 macro, F1 per class)

## Verification

Command (run from the repository root):

```bash
python3 src/gradient_boosting.py
```

Expected result: two summary tables (one per model) with the mean and std of
accuracy, precision (macro), recall (macro) and F1 (macro) over the 5 folds,
plus an F1-per-class table and the top-10 feature importances. Both models must
beat the M4 baseline (`DummyClassifier("most_frequent")`: accuracy 0.4876,
macro F1 0.0937).

## Results

5-fold stratified cross-validation on the training split (406,708 rows).
Values are the mean (± std) across folds.

| Model | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) |
|---|---|---|---|---|
| XGBoost | 0.8690 (±0.0019) | 0.8747 (±0.0011) | 0.8297 (±0.0015) | 0.8494 (±0.0012) |
| LightGBM | 0.8540 (±0.0033) | 0.8382 (±0.0316) | 0.8098 (±0.0071) | 0.8175 (±0.0266) |

Both models far exceed the M4 baseline (`DummyClassifier("most_frequent")`:
accuracy 0.4876, macro F1 0.0937). XGBoost is the stronger of the two on every
macro metric and clearly more stable (smaller standard deviations).

### F1 per class (mean across folds)

| Cover_Type | Name | XGBoost | LightGBM |
|---|---|---|---|
| 1 | Spruce/Fir | 0.8510 | 0.8332 |
| 2 | Lodgepole Pine | 0.8820 | 0.8698 |
| 3 | Ponderosa Pine | 0.8999 | 0.8927 |
| 4 | Cottonwood/Willow | 0.8553 | 0.7084 |
| 5 | Aspen | 0.7213 | 0.7042 |
| 6 | Douglas-fir | 0.8137 | 0.8088 |
| 7 | Krummholz | 0.9226 | 0.9052 |

The hardest classes are Aspen (5) and Cottonwood/Willow (4). The latter is the
rarest class (0.47% of rows) and shows the highest variance across folds for
LightGBM (std 0.1670) — a symptom of the class imbalance that #17 will address.

### Feature importance

XGBoost top features: `Soil_Type17`, `Soil_Type3`, `Elevation`,
`Wilderness_Area3`, `Soil_Type2`. LightGBM top features:
`Horizontal_Distance_To_Roadways`, `Horizontal_Distance_To_Fire_Points`,
`Elevation`, `Horizontal_Distance_To_Hydrology`.

The two models measure importance differently (LightGBM counts splits by
default), so the rankings are not directly comparable. `Elevation` appears near
the top for both, consistent with the EDA (most discriminative feature).

### Command

```bash
python3 src/gradient_boosting.py
```
