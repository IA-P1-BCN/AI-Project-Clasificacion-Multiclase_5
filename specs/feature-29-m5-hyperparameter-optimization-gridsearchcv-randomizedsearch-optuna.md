# Spec: feature/29-m5-hyperparameter-optimization-gridsearchcv-randomizedsearch-optuna

| | |
|---|---|
| Issue | #29 - [M5] Hyperparameter optimization (GridSearchCV / RandomizedSearch / Optuna) |
| Milestone | M5 |
| Branch | `feature/29-m5-hyperparameter-optimization-gridsearchcv-randomizedsearch-optuna` (from `develop`) |
| Owner | @nagicome03 |
| Depends on | M4 shortlist (#23, merged), models #21 / #22 (merged) |

## Goal

Tune the hyperparameters of the two shortlisted models (Random Forest primary,
XGBoost secondary) with `RandomizedSearchCV` under the shared CV protocol, keep
the parameters that improve macro F1 over the defaults recorded in #23, and
document the chosen parameters.

## Scope

- In scope: `src/hyperparameter_optimization.py` (search spaces, randomized
  search for Random Forest and XGBoost, a default-vs-tuned comparison) and a
  `docs/MODELING.md` section with the tuned parameters and scores.
- Out of scope:
  - Final metrics on validation / test (#25, #28).
  - Feature engineering / selection (#18).
  - Class weights (#17, done: none applied).
  - Model export (#32, done): re-export after this branch lands.

## Design

| File | Change |
|---|---|
| `src/hyperparameter_optimization.py` | New. `rf_search_space`, `xgb_search_space`, `tune_random_forest`, `tune_xgboost`, `evaluate_defaults`, `main()`. |
| `docs/MODELING.md` | New "Hyperparameter optimization" section. |

Decisions and reasons:

- **Method — `RandomizedSearchCV`** (scikit-learn). Reasons: (1) no new
  dependency (`Optuna` would add one); (2) `GridSearchCV` is combinatorially too
  slow for Random Forest on 406,708 rows; (3) random search covers the
  high-impact dimensions with a controllable budget. `Optuna` is rejected for
  the dependency it would add, and because its pruning does not apply to
  Random Forest.
- **Models — the shortlist** from #23: Random Forest (primary) and XGBoost
  (secondary), reusing `random_forest.build_model` and
  `gradient_boosting.build_models`. XGBoost is tuned directly on 0-indexed
  labels (`y - 1`, XGBoost 2.1 rejects 1-based labels) and then wrapped in
  `model_comparison.LabelOffsetClassifier` for the shared-protocol comparison;
  macro F1 is invariant to the label offset, so the best parameters are
  identical.
- **Metric and protocol:** `scoring=baseline.MACRO_F1` (macro F1, the project's
  main metric, `zero_division=0`) and `StratifiedKFold(n_splits=5, shuffle=True,
  random_state=42)`, reusing `baseline.N_SPLITS` and `baseline.RANDOM_STATE`.
- **No leakage:** the search fits only on the train split
  (`split_train_val_test`, #16). Validation and test are untouched. The final
  unbiased verdict comes from #28 (validation) and #25 (test); the search's CV
  score is optimistic because the best parameters are selected on those folds.
- **Budget — exhaustive:** Random Forest `n_iter=40`, XGBoost `n_iter=50`.
- **Comparison:** the best estimator is re-evaluated with
  `baseline.evaluate_model` (the shared protocol) against the defaults recorded
  in #23 (Random Forest macro F1 0.9124, XGBoost 0.8514). If a model does not
  improve, its defaults are kept and documented.

## Acceptance criteria

Copied from issue #29:

- [ ] Tuned model improves over default
- [ ] Best params documented

## Verification

Reproduce with `python src/hyperparameter_optimization.py` (exit 0). Observed:

_(to be filled after the search run)_
