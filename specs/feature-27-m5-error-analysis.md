# Spec: feature/27-m5-error-analysis

| | |
|---|---|
| Issue | #27 - [M5] Error analysis |
| Milestone | M5 |
| Branch | `feature/27-m5-error-analysis` (from `develop`) |
| Owner | @carovasq |
| Depends on | #25 (final metrics + confusion matrix, merged), #32 (exported pipeline, merged), #16 (split, merged), #26 (feature importance, merged) |

## Goal

Analyze where the chosen model (the exported Random Forest pipeline) fails and
why, per class: rank the most confused class pairs, characterize the
misclassified rows (model confidence and the driving feature), and turn the
findings into concrete, documented improvement proposals. This fills the
`## Error analysis` stub in `docs/MODELING.md` that #25 left open and completes
the *Esencial* M5 evaluation.

## Scope

- In scope: a `src/error_analysis.py` module that, on the shared split and the
  same pipeline as #25/#32 (fitted on train only), computes (a) the ranked
  directed confused class pairs (True → Pred) with counts and per-class error
  shares, (b) a model-confidence contrast between correct and misclassified
  predictions, (c) for the dominant confused pair, a contrast of the top
  discriminative feature (`Elevation`) that explains the confusion, and
  (d) a sample of the most confident errors to inspect. It saves one figure
  (`docs/figures/error_analysis.png`) and documents the insights and
  improvement proposals in `docs/MODELING.md`.
- Out of scope: acting on the proposals — hyperparameter tuning (#29),
  imbalance handling (#17, already evaluated), feature engineering (#18),
  regularization / overfitting gate (#28). SHAP and per-example explanations
  beyond confidence are not required for *Esencial*. No model is re-trained
  with a new configuration here; this ticket only diagnoses.

## Design

| File | Change |
|---|---|
| `src/error_analysis.py` | New. `confused_pairs(y_true, y_pred)`, `confidence_contrast(y_true, y_pred, proba)`, `feature_contrast(X, y_true, y_pred, cls_a, cls_b, feature)`, `top_confident_errors(X, y_true, y_pred, proba, n)`, `plot_error_analysis(...)`, `main()`. |
| `docs/figures/error_analysis.png` | New figure: confused-pair bar chart + confidence histogram (correct vs wrong). |
| `docs/MODELING.md` | Replace the `## Error analysis` stub with the ranked confused pairs, the confidence and feature contrasts, the figure and the improvement proposals. |

Decisions:

- **Model & data.** Reuse `export_model.build_pipeline` / `fit_pipeline` (the
  exported pipeline of #32: 54-feature passthrough + `RandomForestClassifier`,
  `random_state=42`) and `split_train_val_test` (#16). The pipeline is fitted on
  `(X_train, y_train)` only; the analysis runs on the **validation** partition,
  consistent with #26, with the same reasoning reported for the test partition
  in `main()`. No leakage: the analyzed rows were never passed to `fit`.
- **Confused pairs.** Rank the off-diagonal confusion-matrix cells as directed
  pairs `True i → Pred j` by raw count, and also report each as a share of the
  true class's errors, so both the high-volume majority-class confusions and the
  high-rate minority-class confusions (e.g. Aspen → Lodgepole Pine) surface.
- **Why they are confused.** `Elevation` is the most discriminative feature
  (eta² 0.616, ontology; top of #26). For the dominant confused pair the module
  contrasts the `Elevation` distribution of the two classes to show the overlap
  that drives the errors — a concrete, reproducible insight, not a guess.
- **Inspect misclassified examples.** Report the model's confidence (top
  `predict_proba`) for correct vs wrong predictions, and list the most confident
  errors so the reader can see representative hard cases.
- No new dependency: `predict_proba`, `confusion_matrix`, pandas and matplotlib
  are already used in the repo. `random_state=42` throughout.

## Acceptance criteria

- [x] Identify most confused class pairs (ranked, by count and by error share).
- [x] Inspect misclassified examples (confidence contrast + most confident
      errors + driving-feature contrast).
- [x] Propose possible improvements (documented, tied to the findings).
- [x] Error analysis documented with concrete insights in `docs/MODELING.md`,
      with the reproducing command and a figure.

## Verification

```
python src/error_analysis.py
# prints the ranked confused pairs, the correct-vs-wrong confidence contrast,
# the Elevation contrast for the dominant pair and a sample of confident errors
# for the validation and test partitions; writes docs/figures/error_analysis.png
```
