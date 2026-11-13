# Spec: feature/23-m4-compare-shortlist-models

| | |
|---|---|
| Issue | #23 - [M4] Compare models and shortlist candidates |
| Milestone | M4 |
| Branch | `feature/23-m4-compare-shortlist-models` (from `develop`) |
| Owner | @carovasq |
| Depends on | #19 (baseline/CV protocol), #16 (split), #20, #21, #22, #24 (models) — all merged |

## Goal

Compare every M4 model on equal footing — the same canonical train split and the
same cross-validation protocol — build one comparison table (accuracy, macro
precision / recall / F1 and per-class F1), rank the models and propose a
shortlist of 1-2 candidates for tuning and deployment.

## Scope

- In scope: a `src/model_comparison.py` script that evaluates every model on the
  canonical train split of #16 with the shared protocol of #19, prints the
  comparison table, the per-class F1 table and the top model; the comparison
  table, ranking and shortlist written to `docs/MODELING.md`.
- Out of scope: training any new model or changing hyperparameters (#20-#24),
  imbalance handling (#17), hyperparameter optimization (#29), final metrics and
  confusion matrix on validation / test (#25), overfitting check (#28),
  permutation / gain-based feature importance, exporting the pipeline (#32).

## Design

| File | Change |
|---|---|
| `src/model_comparison.py` | New. `LabelOffsetClassifier`, `build_registry()`, `evaluate(model, X, y)`, `comparison_table(results)`, `per_class_table(results)`, `main()`. |
| `docs/MODELING.md` | Rewrite *Models comparison* into *Models comparison and shortlist*: equal-footing table, per-class F1 table, ranking and shortlist. Update the stale `#23` forward-reference in the MLP section. |

Decisions:

- **Equal footing.** Every model is evaluated on the same canonical train split
  (`split_train_val_test`, #16; 406,708 rows) with the same
  `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)` and
  `baseline.evaluate_model` (#19). This replaces the previous table, whose rows
  used each ticket's own split.
- **Reuse each ticket's builder.** The registry calls
  `logistic_regression.build_pipeline` (#20), `random_forest.build_model` (#21),
  `gradient_boosting.build_models` (#22) and `neural_network.build_pipeline`
  (#24), plus the two `DummyClassifier` baselines (#19). No hyperparameter is
  redefined here, so the comparison reflects the models as they were trained.
- **`LabelOffsetClassifier`.** Modern XGBoost rejects labels that do not start at
  0, while the shared protocol uses the raw `Cover_Type` (1-7). A thin adapter
  maps `y` to 0-based for `fit` and shifts predictions back, so XGBoost runs
  under the shared protocol like the others. LightGBM encodes labels itself and
  is not wrapped.
- **Metrics in one place.** Accuracy and macro F1 (mean ± std over folds) come
  from `evaluate_model`; macro precision / recall and per-class F1 come from
  pooled out-of-fold predictions (`cross_val_predict`) over the same folds —
  exactly how #20 / #21 / #24 produced their per-class tables, so reused numbers
  stay consistent.
- **Runtime.** The script accepts model names as CLI arguments and runs all
  models by default. `LogisticRegression`, `RandomForest` and `MLP` were already
  produced on the canonical split, so only `XGBoost`, `LightGBM` and the
  baselines were re-run here (the MLP CV alone takes ~1 hour); the reused numbers
  are the ones already in `docs/MODELING.md`.
- **Shortlist is a recommendation.** The script ranks by macro F1; the shortlist
  in the docs is marked *proposed, pending team sign-off*, since the acceptance
  criterion requires team agreement.
- No new dependency (`xgboost` and `lightgbm` are already pinned in
  `requirements.txt` for #22).

## Acceptance criteria

- [x] Build a comparison table (accuracy, macro F1, per-class)
- [x] Rank models
- [x] Shortlist 1-2 candidates for tuning/deployment
- [x] Comparison table filled in `docs/MODELING.md`
- [ ] Shortlist agreed by the team (proposed here; needs team sign-off)

## Verification

```bash
# Fast subset re-evaluated on the canonical split (used for the docs):
python src/model_comparison.py XGBoost LightGBM "DummyClassifier (most_frequent)" "DummyClassifier (stratified)"
# Full reproduction (every model; the MLP CV takes about an hour):
python src/model_comparison.py
```

Expected: a comparison table ranked by macro F1 and a per-class F1 table on the
canonical train split (406,708 rows). Random Forest ranks first (macro F1
0.9124), ahead of MLP (0.8557) and XGBoost (0.8514, re-run here on the canonical
split), with LightGBM (0.8261) and LogisticRegression (0.5324) behind, all above
the baselines. Results are recorded in `docs/MODELING.md`.

## Results

5-fold stratified cross-validation on the canonical train split (406,708 rows).
XGBoost / LightGBM / baselines reproduced with
`python src/model_comparison.py XGBoost LightGBM "DummyClassifier (most_frequent)" "DummyClassifier (stratified)"`;
the other rows are reused from #20 / #21 / #24 (already on this split).

| Rank | Model | Accuracy | F1 (macro) |
|---|---|---|---|
| 1 | RandomForest (100 trees) | 0.9470 | 0.9124 ± 0.0023 |
| 2 | MLP (128, 64) | 0.9035 | 0.8557 ± 0.0090 |
| 3 | XGBoost | 0.8693 | 0.8514 ± 0.0038 |
| 4 | LightGBM | 0.8561 | 0.8261 ± 0.0082 |
| 5 | LogisticRegression | 0.7248 | 0.5324 ± 0.0037 |

Proposed shortlist: **Random Forest** (primary) and **XGBoost** (secondary; the
MLP is a close alternative but ~10x slower to train). Pending team sign-off.
