# Spec: feature/30-m5-model-interpretability-shap

| | |
|---|---|
| Issue | #30 - [M5] Model interpretability (SHAP) |
| Milestone | M5 |
| Branch | `feature/30-m5-model-interpretability-shap` (from `develop`) |
| Owner | @carovasq |
| Depends on | #23 (shortlist, merged), #21 (Random Forest, merged), #32 (exported pipeline, merged), #16 (split, merged) |

## Goal

Explain the chosen model's predictions with SHAP values (optional *Could* /
*Experto* task). Produce a global SHAP summary, a per-class beeswarm and a
dependence plot, and document what they reveal in `docs/MODELING.md`, so the
impurity/permutation importances of #26 are complemented with a signed,
per-prediction attribution of why the model decides each class.

## Scope

- In scope: a `src/shap_interpretability.py` module that, on the shared split
  and the same pipeline as #25/#27/#32 (fitted on train only), builds a
  `shap.TreeExplainer` for the Random Forest, computes SHAP values on a
  held-out **validation** sample, and saves (a) a multiclass summary bar of mean
  |SHAP| per feature, (b) a beeswarm for a representative class and (c) a
  dependence plot for the most important feature (`Elevation`). Documents the
  findings in `docs/MODELING.md` and pins `shap` in `requirements.txt`.
- Out of scope: acting on the interpretation, hyperparameter tuning (#29),
  feature engineering (#18), per-example explanations in the app (app issues).
  SHAP is computed on a sample, not the full dataset, by design (cost); this is
  a *Could* task and does not change the model.

## Design

| File | Change |
|---|---|
| `src/shap_interpretability.py` | New. `build_explainer(pipeline)`, `shap_sample(X, n)`, `shap_values(explainer, X)`, `mean_abs_importance(values)`, `plot_summary_bar(...)`, `plot_beeswarm(...)`, `plot_dependence(...)`, `main()`. |
| `docs/figures/shap_summary_bar.png` | New: mean \|SHAP\| per feature, stacked by class. |
| `docs/figures/shap_beeswarm.png` | New: beeswarm for the representative class. |
| `docs/figures/shap_dependence_elevation.png` | New: dependence plot for `Elevation`. |
| `docs/MODELING.md` | New *Model interpretability (SHAP)* subsection under the M5 results. |
| `requirements.txt` | Add `shap==0.54.1` (new dependency). |

Decisions:

- **Model & data.** Reuse `export_model.build_pipeline` / `fit_pipeline`
  (54-feature passthrough + `RandomForestClassifier`, `random_state=42`) and
  `split_train_val_test` (#16). The pipeline is fitted on `(X_train, y_train)`
  only; SHAP values are computed on a **validation** sample the model never saw.
  No leakage.
- **Explainer.** `shap.TreeExplainer` on `pipeline.named_steps["model"]`,
  needing no background dataset, so nothing extra is fitted. The sample is passed
  through `pipeline.named_steps["preprocessor"].transform` (passthrough) to keep
  the exact feature names the forest saw.
- **Approximate SHAP.** The forest grows unpruned on 406,708 rows (measured max
  depth 64, ~80k nodes per tree), so *exact* TreeSHAP costs ~3 s/row — hours for
  a useful sample. The module uses the fast approximate (Saabas) attribution
  (`approximate=True`, `check_additivity=False`): near-instant and it preserves
  the qualitative ranking and sign the summary/dependence plots rely on. The
  exact-vs-approx cost was verified before deciding.
- **Sample.** `SAMPLE_SIZE = 2000` validation rows, `random_state=42`
  (reproducible). Output is `(n_samples, n_features, n_classes)`; global
  importance is the mean |SHAP| over samples, reported per class and aggregated
  over classes.
- **Plots.** Summary bar (all classes), beeswarm for the majority class
  Lodgepole Pine (shows effect direction), dependence for `Elevation` (the top
  feature of #26 and η² 0.616). matplotlib `Agg`, headless.
- **New dependency:** `shap==0.54.1` (declared here and in the PR). No other new
  dependency: numpy, pandas, matplotlib, scikit-learn are already pinned.

## Acceptance criteria

- [x] Compute SHAP values for the model (TreeExplainer on the Random Forest).
- [x] Plot summary / dependence plots (summary bar + beeswarm + dependence).
- [x] Add to the report (`docs/MODELING.md`), with the reproducing command.
- [x] SHAP analysis included (optional *Experto* task).

## Verification

```
python src/shap_interpretability.py
# prints the global and per-class mean |SHAP| feature ranking on the validation
# sample and writes the three figures under docs/figures/
```
