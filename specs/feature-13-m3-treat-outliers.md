# Spec: feature/13-m3-treat-outliers

| | |
|---|---|
| Issue | #13 - [M3] Treat outliers |
| Milestone | M3 |
| Branch | `feature/13-m3-treat-outliers` (from `develop`) |
| Owner | @carovasq |
| Depends on | M2 EDA (#done), M3 split (#16, merged), scaling (#14, merged) |

## Goal

Detect outliers in the 10 numeric features and apply a documented, leakage-safe
treatment, so that preprocessing has a defined outlier step and the decision is
reproducible. The EDA (`docs/EDA.md`) already found these are long tails of
skewed variables, not confirmed errors; this branch turns that observation into
an applied decision.

## Scope

- In scope: `src/outlier_treatment.py` (detection report + a scikit-learn
  outlier transformer fitted on training data only), a `docs/PREPROCESSING.md`
  section documenting the strategy and its impact on the class distribution.
- Out of scope:
  - Scaling (#14) and the split protocol (#16); this module reuses them.
  - Feature engineering / transformations of skewed features (#15, M3).
  - Removing or imputing missing values and duplicates (#12, done).

## Design

| File | Change |
|---|---|
| `src/outlier_treatment.py` | New. `outlier_report`, `OutlierClipper` (sklearn transformer), `build_outlier_preprocessor`, `removal_impact`, `check_no_leakage`, `main()`. |
| `docs/PREPROCESSING.md` | New "Outliers" section: detection, decision, impact, reproduce command. |

Decisions and reasons:

- **Detection:** IQR rule (beyond Q1 - 1.5*IQR or Q3 + 1.5*IQR) and z-score
  (|z| > 3), on the 10 `NUMERIC_FEATURES` only. The 44 binary indicators cannot
  have outliers in this sense.
- **Treatment: clip (winsorize), not remove.** Reasons: (1) the EDA shows these
  are legitimate long tails of skewed variables, not confirmed errors; (2) the
  project's main models are tree-based (RF/XGBoost/LightGBM), insensitive to
  monotonic outliers, while clipping still caps extremes for the linear and
  distance-based baselines; (3) clipping removes no rows, so the class
  distribution is preserved exactly, whereas removing any row flagged by the IQR
  rule would drop a large share and distort the already imbalanced classes
  (quantified by `removal_impact`).
- **Leakage:** `OutlierClipper` learns the clip bounds in `fit` from the
  training partition only and applies them in `transform` to any partition. It is
  a `ColumnTransformer` step (clip numeric, passthrough binary) meant to run
  before the scaler inside a scikit-learn `Pipeline`, exactly like
  `feature_scaling.build_preprocessor`.

## Acceptance criteria

Copied from issue #13:

- [ ] Detect outliers (IQR / z-score)
- [ ] Decide treatment (clip / remove / keep) with justification
- [ ] Apply and verify
- [ ] Outlier strategy documented and applied
- [ ] Impact on class distribution checked

## Verification

Reproduce with `python src/outlier_treatment.py`. Expected:

- A detection table with IQR and z-score outlier counts per numeric feature.
- `removal_impact` reports how many rows the IQR rule would drop and the class
  share shift (evidence for rejecting removal).
- After clipping: no numeric value lies outside the training bounds; binary
  features are byte-identical; the class distribution is unchanged (no row
  dropped). `check_no_leakage` asserts the bounds equal the training quantiles
  and that fitting on train vs. full data gives different bounds.
