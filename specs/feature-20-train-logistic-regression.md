# Spec: feature/20-train-logistic-regression

| | |
|---|---|
| Issue | #20 - [M4] Train simple model (Logistic Regression) |
| Milestone | M4 |
| Branch | `feature/20-train-logistic-regression` (from `develop`) |
| Owner | @levifvy |
| Depends on | #19 (baseline and CV protocol, merged), #14 (scaling, merged), #16 (split, merged) |

## Goal

Train a multiclass logistic regression as the first supervised benchmark and
record its metrics under the cross-validation protocol, so that every later
model has a simple learned reference to beat in addition to the baseline.

## Scope

- In scope: a `Pipeline` (preprocessor + `LogisticRegression`), its evaluation
  with the CV protocol on the train set, per-class metrics from out-of-fold
  predictions, documentation in `docs/MODELING.md`.
- Out of scope: imbalance handling / class weights (#17), feature engineering
  (#18), Random Forest (#21), model comparison and shortlist (#23), final
  metrics and confusion matrix on validation / test (#25), overfitting check
  (#28), hyperparameter optimization (#29), exporting the pipeline (#32).

## Design

| File | Change |
|---|---|
| `src/logistic_regression.py` | New. `build_pipeline()`, `per_class_report(model, X, y)`, `main()`. |
| `docs/MODELING.md` | New section *Simple model: Logistic Regression*; one row in *Models comparison*. |

Decisions:

- **Pipeline = preprocessor + estimator.** `build_pipeline()` returns an
  unfitted `Pipeline` of `build_preprocessor("standard")` (#14) and
  `LogisticRegression(max_iter=1000, random_state=42)`. Cross-validation refits
  the scaler on each training fold, so there is no data leakage. Scaling is
  required: without it the solver does not converge (`docs/PREPROCESSING.md`,
  *Feature scaling*).
- **Default hyperparameters** (multinomial loss, L2, `C=1.0`, `lbfgs`).
  Tuning belongs to #29 and class weights to #17; this issue records the
  untuned reference.
- **Reuse the protocol.** Accuracy and macro F1 come from
  `baseline.evaluate_model` (#19), unchanged.
- **Per-class metrics** come from out-of-fold predictions
  (`cross_val_predict`) over the same `StratifiedKFold(n_splits=5,
  shuffle=True, random_state=42)`, so every training row is predicted by a
  model that did not see it.
- **Canonical split.** The train set comes from
  `data_split.split_train_val_test` (#16). The validation and test sets are
  not touched in this issue.
- `Cover_Type` is used as is (1-7); scikit-learn does not need it re-encoded.
- No new dependency.

## Acceptance criteria

- [x] Train LogisticRegression (multiclass)
- [x] Evaluate with the CV protocol
- [x] Record baseline-supervised metrics
- [x] Simple model trained and metrics recorded
- [x] The solver converges within `max_iter` on every fit
- [x] Macro F1 beats both baselines of #19

## Verification

```bash
python src/logistic_regression.py
```

Expected: the size of the train set (406,708 rows), accuracy and macro F1 as
mean ± standard deviation over the 5 folds, a per-class precision / recall /
F1 table, and the line `Converged: True`. Observed results are recorded in
`docs/MODELING.md`.
