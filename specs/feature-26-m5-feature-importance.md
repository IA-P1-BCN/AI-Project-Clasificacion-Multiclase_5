# Spec: feature/26-m5-feature-importance

| | |
|---|---|
| Issue | #26 - [M5] Feature importance |
| Milestone | M5 |
| Branch | `feature/26-m5-feature-importance` (from `develop`) |
| Owner | @carovasq |
| Depends on | #23 (shortlist, merged), #21 (Random Forest, merged), #16 (split, merged) |

## Goal

Report which features matter most for the shortlist model (Random Forest, the
strongest model in #23). Produce a ranked figure of the top features and a
model-agnostic permutation importance that complements the impurity-based (MDI)
ranking already noted in `docs/MODELING.md`, so the *Esencial* report has a
documented, reproducible feature-importance analysis with a plot.

## Scope

- In scope: a `src/feature_importance.py` module that, on the shared split,
  computes (a) MDI importance of the Random Forest fitted on the training
  partition and (b) permutation importance measured on the **validation**
  partition; ranks and saves a bar-chart figure of the top features to
  `docs/figures/feature_importance.png`; and documents the ranking and figure
  in `docs/MODELING.md`.
- Out of scope: hyperparameter optimization (#29), final validation/test
  metrics and confusion matrix (#25), error analysis (#27/#25), imbalance
  handling (#17), feature engineering/selection (#18, already merged),
  exporting the pipeline (#32). SHAP / per-class importance are not required for
  *Esencial*.

## Design

| File | Change |
|---|---|
| `src/feature_importance.py` | New. `mdi_importance(model, X, y)`, `permutation_importance_val(model, X_train, y_train, X_val, y_val)`, `plot_top_importances(mdi, perm, path)`, `main()`. |
| `docs/figures/feature_importance.png` | New figure: top-15 features, MDI vs permutation. |
| `docs/MODELING.md` | Extend the *Feature importance* section with permutation importance and the figure; fill the M5 *Results* stub for feature importance. |

Decisions:

- **Model:** Random Forest (`build_model()` from `src/random_forest.py`), the
  shortlist winner in #23. Reuse `split_train_val_test` (#16) and the cleaned
  `FEATURES`/`TARGET` (#12) — single source, no redefinition.
- **No leakage.** The forest is fitted on the training partition only.
  Permutation importance is computed on the validation partition, which the
  model never saw, so the drop in macro F1 when a column is shuffled is an
  honest, model-agnostic measure. `random_state=42`, `n_repeats=5`.
- **Why permutation importance.** `docs/MODELING.md` already flags that MDI is
  biased toward continuous, high-cardinality features and understates the
  one-hot `Wilderness_Area`/`Soil_Type` indicators. Permutation importance does
  not have that bias and closes the gap the existing note left open.
- **Metric for permutation:** macro F1 (`scoring="f1_macro"`), consistent with
  the CV protocol's main metric (#19).
- No new dependency: `sklearn.inspection.permutation_importance` ships with the
  pinned scikit-learn 1.5.1; matplotlib is already used for every figure.

## Acceptance criteria

- [x] Compute feature importance (model-specific): MDI + permutation importance
      on the Random Forest.
- [x] Plot and rank top features: `docs/figures/feature_importance.png` saved,
      features ranked descending.
- [x] Add to the report: `docs/MODELING.md` updated with the ranking, the
      figure and the reproducing command.
- [x] Feature importance reported (required for *Esencial* report).

## Verification

```
python src/feature_importance.py
# prints the top-15 MDI and permutation rankings and the figure path;
# writes docs/figures/feature_importance.png
```
