# Spec: feature/14-feature-scaling

| | |
|---|---|
| Issue | #14 - [M3] Feature scaling / normalization |
| Milestone | M3 |
| Branch | `feature/14-feature-scaling` (from `develop`) |
| Owner | @levifvy |
| Depends on | #12 (missing values and duplicates, merged) |

The branch was first stacked on `feature/12-missing-values-duplicates`. After
#12 was squash-merged it was rebased onto `develop`, so it contains only the
scaling commit. It reuses the column constants and `clean()` from
`src/data_cleaning.py`.

## Goal

Provide a leakage-free scaling step for the 10 numeric features, ready to be
used inside the modeling pipeline, and document why the scaler was chosen.

## Scope

- In scope: a preprocessor that scales `NUMERIC_FEATURES` and passes
  `BINARY_FEATURES` through; evidence for the scaler choice; documentation.
- Out of scope: the project split protocol (#16), outliers (#13), target
  encoding (#15), imbalance (#17), feature engineering (#18), training the
  logistic regression model (#20), exporting the fitted pipeline (#32),
  unit tests (#40).

## Design

| File | Change |
|---|---|
| `src/feature_scaling.py` | New. `build_preprocessor(scaler)`, `scale_train_test(X_train, X_test, scaler)`, `check_scaling(...)`, `compare_scalers(X, y)`, `main()`. |
| `docs/PREPROCESSING.md` | New section *Feature scaling*. |

Decisions:

- **`ColumnTransformer`** with a scaler on `NUMERIC_FEATURES` and
  `"passthrough"` on `BINARY_FEATURES`; pandas output, original column names
  and order.
- **Unfitted by design**: `build_preprocessor()` returns an unfitted object to
  be placed in a `Pipeline`. The module never fits on the full dataset.
- **Default `StandardScaler`**; `"robust"` and `"minmax"` selectable. Reason
  and evidence in `docs/PREPROCESSING.md`.
- **No saved artifact and no scaled dataset written to `data/processed/`**:
  a pre-scaled file would have to be fitted before the split defined in #16,
  which is exactly the leakage this issue must avoid.
- The 80/20 split in `main()` is a demonstration; #16 owns the real protocol.
- No new dependency.

## Acceptance criteria

- [x] Choose scaler (StandardScaler/MinMax) based on models
- [x] Fit scaler on training only
- [x] Apply within the preprocessing pipeline
- [x] Scaling integrated in the pipeline (no leakage)
- [x] Reason for scaler choice documented
- [x] Only the 10 numeric features are scaled; the 44 binary features are unchanged

## Verification

Run on 2026-11-12 with `python src/feature_scaling.py`:

| Check | Result |
|---|---|
| `check_scaling()` on a stratified 80/20 split (464,809 / 116,203 rows) | Passed |
| Training numeric features after scaling | Mean 0, standard deviation 1 |
| Test numeric features after scaling | Means -0.0077 to 0.0030, standard deviations 0.9970 to 1.0054 |
| Binary features before vs after | Identical (train and test) |
| Scaler comparison, macro F1 (none / standard / robust / minmax) | 0.3296 / 0.5257 / 0.5253 / 0.4987 |

Ad hoc checks on an 8,000-row sample (not committed as tests): the three
scalers return 54 columns in the original order with `int64` binary columns;
the fitted mean differs from the full-sample mean; an unknown scaler name
raises `ValueError`; the preprocessor works inside `cross_val_score` with
`StratifiedKFold`; input frames are not modified.
