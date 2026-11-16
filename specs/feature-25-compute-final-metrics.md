# Spec: feature/25-compute-final-metrics

| | |
|---|---|
| Issue | #25 - [M5] Compute final metrics (accuracy, precision/recall/F1 per class, confusion matrix) |
| Milestone | M5 |
| Branch | `feature/25-compute-final-metrics` (from `develop`) |
| Owner | @levifvy |
| Depends on | #16 (canonical split, merged), #21 (Random Forest, merged), #23 (shortlist, merged), #17 (imbalance handling, merged), #32 (export pipeline, merged) |

## Goal

Compute the full multiclass metric set — train vs validation accuracy, macro and
per-class precision / recall / F1, and the 7x7 confusion matrix (raw counts and
row-normalized percentages) — for the chosen primary model of the shortlist
(#23 / #32: Random Forest pipeline), fitted strictly on the canonical training
split and evaluated on the validation and held-out test partitions, and record
the results in `docs/MODELING.md`.

## Scope

- In scope:
  - `src/final_metrics.py`: fit the chosen pipeline (`export_model.fit_pipeline`)
    on `X_train, y_train` only (#16 canonical split), compute headline metrics
    (`accuracy`, `precision_macro`, `recall_macro`, `macro_f1`) on `train`,
    `validation` and `test`, compute the train-vs-validation accuracy difference,
    build per-class `precision` / `recall` / `f1-score` / `support` tables and
    7x7 confusion matrices (counts and row-normalized recall %) on `validation`
    and `test`, and print a reproducible summary.
  - `docs/MODELING.md`: fill the *Results* section with the reproduce command
    (`python src/final_metrics.py`) and the observed tables.
- Out of scope:
  - Feature importance ranking and plots (#26, @carovasq).
  - Error analysis narrative, inspection of misclassified rows and improvement
    proposals (#27, @carovasq; #27 consumes the per-class metrics and confusion
    matrices produced here).
  - Regularizing or modifying models to enforce `overfitting_gap < 5%` (#28,
    @nagicome03; this branch reports the observed train vs validation accuracy
    required by task 1 of #25 so #28 can verify and remediate if needed).
  - Hyperparameter optimization (#29, @nagicome03; still open — this branch
    evaluates the untuned primary model of #23 / #32 and can be re-run with one
    command once #29 merges).
  - SHAP interpretability (#30, @carovasq) and final consolidation of
    `docs/MODELING.md` (#31, @nagicome03).

## Design

| File | Change |
|---|---|
| `src/final_metrics.py` | New. `partition_metrics`, `headline_table`, `per_class_table`, `confusion_matrix_tables`, `evaluate_final_model`, `main`. |
| `docs/MODELING.md` | Fill *Results* with train vs validation accuracy, validation and test per-class metrics, and 7x7 confusion matrices for the chosen model. |

Decisions and reasons:

- **Chosen model: the primary model of the shortlist (#23) and exported pipeline
  of #32.** Reuses `export_model.build_pipeline` / `fit_pipeline`, which chains
  the 54-feature passthrough `ColumnTransformer` and `random_forest.build_model`
  (`RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)`). Per
  #17 (`docs/PREPROCESSING.md`), inverse-frequency class weights did not improve
  CV macro F1, so the unweighted model remains canonical. Reusing `export_model`
  and `target_encoding` also keeps `src/final_metrics.py` free of optional
  third-party imports (`xgboost`, `lightgbm`) at module load time, so
  `scripts/check_imports.py` passes in minimal scikit-learn environments as well
  as in CI.
- **Partitions: canonical `split_train_val_test` (#16).** 406,708 training rows
  (70%), 87,152 validation rows (15%), and 87,152 test rows (15%). The pipeline
  is fitted once on `(X_train, y_train)` only. Neither `validation` nor `test`
  is ever passed to `fit`.
- **Why report both validation and test:**
  1. Task 1 of #25 requires `accuracy (train vs validation)`, which also feeds
     #28 (*Verify overfitting < 5%*).
  2. `specs/ontology.md` defines the test set as the partition used for the
     final evaluation, and `docs/MODELING.md` (§ *Shortlist*) and
     `specs/feature-32-export-model-pipeline.md` explicitly assign final
     validation / test metrics to #25. Reporting both partitions (without using
     test to tune or select anything) gives a complete evaluation now and can be
     re-run after #29 if hyperparameters change.
- **Confusion matrix in two views.** With a ~1:103 class imbalance (Lodgepole
  Pine 48.76% vs Cottonwood/Willow 0.47%), raw counts show absolute error volume
  while row-normalized percentages (`% of true class`) make minority-class
  confusions legible for #27 (*Error analysis*).
- No new dependency.

## Acceptance criteria

- [x] Compute accuracy (train vs validation)
- [x] Compute precision/recall/F1 per class
- [x] Build confusion matrix
- [x] Record in `docs/MODELING.md`
- [x] All metrics computed and recorded
- [x] Per-class metrics available
- [x] The pipeline is fitted on `X_train, y_train` only; no validation or test rows leak into `fit` (added)

## Verification

```bash
python src/final_metrics.py
```

Observed (2026-11-16, Python 3.12.10, scikit-learn 1.5.1):

- `python src/final_metrics.py` exited 0 in ~65 s on 406,708 training rows,
  87,152 validation rows and 87,152 test rows:
  - `train`: accuracy `1.0000`, macro precision `1.0000`, macro recall `1.0000`,
    macro F1 `1.0000`.
  - `validation`: accuracy `0.9520`, macro precision `0.9416`, macro recall
    `0.8990`, macro F1 `0.9186` (matches `export_model.py` in #32).
  - `test`: accuracy `0.9510`, macro precision `0.9423`, macro recall `0.9012`,
    macro F1 `0.9199`.
  - Train vs validation accuracy gap (`overfitting_gap`): `+0.0480` (`+4.80`
    percentage points, `< 5%`).
  - Per-class precision, recall, F1 and support, plus 7x7 confusion matrices
    (raw counts and row-normalized recall %) printed for both `validation` and
    `test` and recorded in `docs/MODELING.md`.
- `python -c "import sys; sys.path.insert(0, 'src'); import final_metrics; print('ok    final_metrics')"`
  printed `ok    final_metrics`.
- `git status --short` shows only `specs/feature-25-compute-final-metrics.md`,
  `src/final_metrics.py` and `docs/MODELING.md`; nothing under `data/` or
  `models/`.
