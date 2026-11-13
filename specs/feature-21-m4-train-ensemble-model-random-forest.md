# Spec: feature/21-m4-train-ensemble-model-random-forest

| | |
|---|---|
| Issue | #21 - [M4] Train ensemble model (Random Forest) |
| Milestone | M4 |
| Branch | `feature/21-m4-train-ensemble-model-random-forest` (from `develop`) |
| Owner | @carovasq |
| Depends on | #19 (baseline and CV protocol, merged), #16 (split, merged) |

## Goal

Train a Random Forest ensemble as the bagging reference for M4 and record its
metrics and feature importances under the shared cross-validation protocol, so
it can be compared against the baseline, the simple model and the other
ensembles.

## Scope

- In scope: a `RandomForestClassifier` with default hyperparameters, its
  evaluation with the CV protocol on the train set (accuracy and macro F1),
  per-class metrics from out-of-fold predictions, the feature importances, and
  documentation in `docs/MODELING.md`.
- Out of scope: imbalance handling / class weights (#17), feature engineering
  (#18), model comparison and shortlist (#23), final metrics and confusion
  matrix on validation / test (#25), overfitting check (#28), hyperparameter
  optimization (#29), exporting the pipeline (#32).

## Design

| File | Change |
|---|---|
| `src/random_forest.py` | New. `build_model()`, `per_class_report(model, X, y)`, `feature_importances(model, X, y)`, `main()`. |
| `docs/MODELING.md` | New section *Ensemble model: Random Forest*; one row in *Models comparison*. |

Decisions:

- **No scaling / no preprocessor.** A Random Forest splits on thresholds, so
  rescaling the numeric features has no effect. The model is trained on the raw
  (cleaned) `FEATURES`, like the gradient-boosted ensembles of #22. The
  ontology `Pipeline` is therefore unnecessary here (there is no transformer to
  refit per fold); the only data-derived learning is the forest itself, which
  `cross_validate` / `cross_val_predict` already refit on each training fold, so
  there is no leakage.
- **Default hyperparameters** (`n_estimators=100`, Gini, no depth limit,
  `random_state=42`, `n_jobs=-1`). Tuning belongs to #29 and class weights to
  #17; this issue records the untuned reference.
- **Reuse the protocol.** Accuracy and macro F1 come from
  `baseline.evaluate_model` (#19), unchanged, so this model is compared on the
  exact same `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)` as the
  others.
- **Per-class metrics** come from out-of-fold predictions
  (`cross_val_predict`) over the same folds, so every training row is predicted
  by a forest that did not see it. The last row holds the macro averages.
- **Feature importances** are the mean decrease in impurity of a single forest
  fitted on the full train set, indexed by `FEATURES` and sorted descending.
- **Canonical split.** The train set comes from
  `data_split.split_train_val_test` (#16). The validation and test sets are not
  touched in this issue.
- `Cover_Type` is used as is (1-7); scikit-learn does not need it re-encoded.
- No new dependency (`RandomForestClassifier` ships with scikit-learn).

## Acceptance criteria

- [x] Train RandomForestClassifier
- [x] Evaluate with the CV protocol
- [x] Record metrics and feature importances
- [x] Random Forest trained and metrics recorded
- [x] Macro F1 beats both baselines of #19

## Verification

```bash
python src/random_forest.py
```

Expected: the size of the train set (406,708 rows), accuracy and macro F1 as
mean ± standard deviation over the 5 folds, a per-class precision / recall / F1
table from out-of-fold predictions, and the top-10 feature importances. Macro
F1 must beat both baselines of #19 (`most_frequent`: 0.0937, `stratified`:
0.1426). Observed results are recorded in `docs/MODELING.md`.

## Results

5-fold stratified cross-validation on the training split (406,708 rows).
Reproduced with `python src/random_forest.py`.

| Model | Accuracy | Macro F1 |
|---|---|---|
| RandomForest (100 trees) | 0.9470 ± 0.0006 | 0.9124 ± 0.0023 |

Macro F1 (0.9124) far exceeds both baselines of #19 (`most_frequent` 0.0937,
`stratified` 0.1426) and is the best of all M4 models so far (MLP 0.8557,
XGBoost 0.8494, LightGBM 0.8175, LogisticRegression 0.5324).

### Per-class metrics (out-of-fold predictions)

| Cover_Type | Name | Precision | Recall | F1 | Support |
|---|---|---|---|---|---|
| 1 | Spruce/Fir | 0.9577 | 0.9344 | 0.9459 | 148,288 |
| 2 | Lodgepole Pine | 0.9420 | 0.9686 | 0.9551 | 198,311 |
| 3 | Ponderosa Pine | 0.9307 | 0.9539 | 0.9422 | 25,028 |
| 4 | Cottonwood/Willow | 0.9058 | 0.8346 | 0.8687 | 1,923 |
| 5 | Aspen | 0.9317 | 0.7344 | 0.8213 | 6,645 |
| 6 | Douglas-fir | 0.9214 | 0.8782 | 0.8993 | 12,157 |
| 7 | Krummholz | 0.9717 | 0.9383 | 0.9547 | 14,356 |
| | Macro average | 0.9373 | 0.8918 | 0.9125 | 406,708 |

Aspen (5) has the lowest recall (0.7344), the usual minority-class symptom
(#17).

### Top 10 feature importances (mean decrease in impurity)

`Elevation` (0.2415), `Horizontal_Distance_To_Roadways` (0.1176),
`Horizontal_Distance_To_Fire_Points` (0.1094),
`Horizontal_Distance_To_Hydrology` (0.0606),
`Vertical_Distance_To_Hydrology` (0.0578), `Aspect` (0.0481),
`Hillshade_Noon` (0.0433), `Hillshade_9am` (0.0414), `Hillshade_3pm` (0.0411),
`Slope` (0.0333). `Elevation` dominates, consistent with the EDA.
