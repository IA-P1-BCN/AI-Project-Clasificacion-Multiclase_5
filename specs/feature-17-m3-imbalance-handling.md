# Spec: feature/17-m3-imbalance-handling

| | |
|---|---|
| Issue | #17 - [M3] Imbalance handling (class weights / SMOTE) |
| Milestone | M3 |
| Branch | `feature/17-m3-imbalance-handling` (from `develop`) |
| Owner | @nagicome03 |
| Depends on | M2 EDA (done), M3 split (#16, merged), M4 models (#21, #22) and shortlist (#23, merged) |

## Goal

Mitigate the strong class imbalance (`Cover_Type` min/max ratio about 1:103)
with inverse-frequency class weights, applied only on the training folds, and
measure whether they improve macro F1 and the minority-class F1 for the two
shortlisted models (Random Forest, XGBoost).

## Scope

- In scope: `src/imbalance_handling.py` (class weights + weighted CV + a
  with/without comparison), a backward-compatible `sample_weight` parameter on
  `model_comparison.LabelOffsetClassifier`, and a `docs/PREPROCESSING.md`
  section documenting the strategy.
- Out of scope:
  - SMOTE and other resampling methods (documented as the rejected alternative).
  - Hyperparameter tuning (#29); this branch keeps default hyperparameters.
  - Feature engineering / selection (#18, done); class weights are independent
    of the feature set.
  - Final metrics and error analysis (#25, #27, M5).

## Design

| File | Change |
|---|---|
| `src/imbalance_handling.py` | New. `build_shortlist`, `balanced_class_weights`, `to_sample_weight`, `cross_val_evaluate`, `compare_with_without`, `main()`. |
| `src/model_comparison.py` | `LabelOffsetClassifier.fit` accepts and forwards `sample_weight` (backward-compatible). |
| `docs/PREPROCESSING.md` | New "Imbalance handling" section. |

Decisions and reasons:

- **Needed:** yes. The ontology records an imbalance of ~1:103; the
  `most_frequent` baseline reaches macro F1 0.0937, so accuracy alone is
  misleading. Macro F1 (the main metric) penalizes ignoring the minority
  classes.
- **Class weights, not SMOTE:** inverse-frequency ("balanced") weights computed
  with `sklearn.utils.class_weight.compute_class_weight`. Reasons: (1) no new
  dependency (`imbalanced-learn`); (2) no synthetic samples, which can overfit
  tree models; (3) trivially leakage-safe (weights from the training fold's `y`
  only); (4) native `sample_weight` support in both shortlisted models.
- **Models:** the two shortlisted models from #23 — Random Forest (primary) and
  XGBoost (secondary) — reusing `random_forest.build_model` and
  `gradient_boosting.build_models` wrapped in `LabelOffsetClassifier`.
- **Leakage:** weights are recomputed from each training fold's `y` inside the
  CV loop; validation folds are scored unweighted. Nothing is fitted on the
  full dataset or on validation/test.

## Acceptance criteria

Copied from issue #17:

- [x] Decide if imbalance handling is needed (from M2)
- [x] Choose class weights or SMOTE
- [x] Apply only on training data
- [x] Compare with/without
- [x] Imbalance strategy applied and documented (if needed)

## Verification

Reproduced with `python src/imbalance_handling.py` (exit 0). Observed:

- Inverse-frequency weights: class 1 = 0.3918, class 2 = 0.2930, class 4 = 30.2138
  (the rarest class gets the largest weight, the two majority classes the smallest).
- Default vs weighted (5-fold CV): Random Forest macro F1 0.9123 → 0.9103
  (unchanged within noise), XGBoost macro F1 0.8489 → 0.8005 (worse).
- Weights are computed from each training fold's `y` only; validation folds are
  scored unweighted.

**Conclusion:** class weights do not improve the shortlisted tree models, so the
applied strategy is none (the issue is conditional: "if needed").
