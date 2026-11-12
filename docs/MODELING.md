# MODELING — Strategy and Evaluation

> Modeling strategy, comparison and evaluation of models.

## Strategy

- Baseline + cross-validation protocol (StratifiedKFold)
- Simple model (Logistic Regression)
- Ensemble models (Random Forest, XGBoost, LightGBM)
- Hyperparameter optimization (GridSearchCV / RandomizedSearch / Optuna)

## Baseline & evaluation protocol

Issue #19. Reproduce with: `python src/baseline.py`

- **Protocol:** `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)` on
  the training partition; metrics `accuracy` and **macro F1** (the main metric).
- **Entry point:** every model is evaluated with `evaluate_model(model, X, y)`
  so they are all compared on the same protocol.

### Baselines (5-fold CV on 406,708 training rows)

| Baseline | Accuracy | Macro F1 |
|---|---|---|
| DummyClassifier(most_frequent) | 0.4876 ± 0.0000 | 0.0937 ± 0.0000 |
| DummyClassifier(stratified) | 0.3770 ± 0.0011 | 0.1426 ± 0.0009 |

`most_frequent` has the best accuracy (it always guesses the majority class)
but the worst macro F1, because it never predicts the minority classes — which
is why macro F1 is the main metric on this imbalanced dataset. Every real model
must beat these scores.

## Models comparison

| Model | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) |
|---|---|---|---|---|
| DummyClassifier (most_frequent) | 0.4876 | — | — | 0.0937 |
| DummyClassifier (stratified) | 0.3770 | — | — | 0.1426 |
| XGBoost | 0.8690 | 0.8747 | 0.8297 | 0.8494 |
| LightGBM | 0.8540 | 0.8382 | 0.8098 | 0.8175 |

> Values are the mean over 5-fold stratified cross-validation on the training
> split (see `specs/feature-22-m4-train-ensemble-model-xgboost-lightgbm.md`).

## Evaluation metrics

- Accuracy
- Precision, recall and F1 per class
- Confusion matrix
- Feature importance
- Error analysis
- Overfitting check (< 5%)

## Results

_To be filled in M5._

## Error analysis

_To be filled in M5._
