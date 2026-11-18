# Spec: feature/31-m5-document-modeling-results

| | |
|---|---|
| Issue | #31 - [M5] Document modeling results (docs/MODELING.md) |
| Milestone | M5 |
| Branch | `feature/31-m5-document-modeling-results` (from `develop`) |
| Owner | @nagicome03 |
| Depends on | #25 (final metrics), #28 (overfitting) |

## Goal

Consolidate the modeling strategy, the model comparison and the evaluation into
`docs/MODELING.md`, filling the gaps left by the earlier tickets.

## Scope

- In scope:
  - Update the `Strategy` section so it lists every step actually done (MLP,
    hyperparameter optimization, final metrics, error analysis, SHAP) and the
    real tuning method (`RandomizedSearchCV`).
  - Add a dedicated `Ensemble models: XGBoost / LightGBM` section (#22), to match
    the per-model sections of Logistic Regression, MLP and Random Forest.
- Out of scope:
  - Re-running any model: the numbers are taken from the existing sections and
    the comparison (#23).
  - The final metrics (#25), the overfitting check (#28), the error analysis
    (#27) and the SHAP analysis (#30), which already have their own sections.

## Design

- The document already contains, from the earlier tickets, the protocol (#19),
  the baselines, LogReg (#20), the comparison and shortlist (#23), the MLP
  (#24), the Random Forest (#21), the tuning (#29), the final metrics (#25), the
  error analysis (#27) and the SHAP (#30).
- Two gaps are filled: the `Strategy` list is updated to the real scope, and the
  XGBoost/LightGBM numbers (cross-validation scores and F1 per class) get their
  own section, reusing the canonical-split figures from #23 (the original #22 run
  used a different 70/30 partition).
- No data is re-computed; the change is documentation only.

## Acceptance criteria

Copied from issue #31:

- [x] Document strategy and CV protocol
- [x] Fill comparison table and metrics
- [x] Summarize error analysis and overfitting check
- [x] docs/MODELING.md complete

## Verification

The document is self-contained: every model has a section with its CV scores and
its per-class metrics, the comparison table ranks all of them on the same split,
and the results, error analysis and SHAP sections close the evaluation. The
XGBoost/LightGBM numbers reproduce with:
`python src/model_comparison.py XGBoost LightGBM "DummyClassifier (most_frequent)" "DummyClassifier (stratified)"`.
