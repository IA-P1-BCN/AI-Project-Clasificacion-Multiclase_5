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

## Simple model: Logistic Regression

Issue #20. Reproduce with: `python src/logistic_regression.py`

- **Model:** `Pipeline` of the preprocessor from #14 (`StandardScaler` on
  `NUMERIC_FEATURES`, `BINARY_FEATURES` passed through) and
  `LogisticRegression(max_iter=1000, random_state=42)` with default
  hyperparameters (multinomial loss, L2, `C=1.0`). No class weights (#17) and
  no tuning (#29): this is the untuned supervised reference.
- **Data:** the train set of the canonical split (`split_train_val_test`,
  #16), 406,708 rows. Validation and test sets are not used.
- **No leakage:** the scaler is a `Pipeline` step, so it is refitted on each
  training fold.
- **Convergence:** 219 iterations on the full train set, below `max_iter`.

### Cross-validation scores (5 folds)

| Model | Accuracy | Macro F1 |
|---|---|---|
| LogisticRegression | 0.7248 ± 0.0008 | 0.5324 ± 0.0037 |

### Per-class metrics (out-of-fold predictions on the train set)

| `Cover_Type` | Name | Precision | Recall | F1 | Support |
|---|---|---|---|---|---|
| 1 | Spruce/Fir | 0.7116 | 0.6979 | 0.7047 | 148,288 |
| 2 | Lodgepole Pine | 0.7483 | 0.8007 | 0.7736 | 198,311 |
| 3 | Ponderosa Pine | 0.6805 | 0.8035 | 0.7369 | 25,028 |
| 4 | Cottonwood/Willow | 0.6381 | 0.4254 | 0.5105 | 1,923 |
| 5 | Aspen | 0.2360 | 0.0063 | 0.0123 | 6,645 |
| 6 | Douglas-fir | 0.4891 | 0.2701 | 0.3480 | 12,157 |
| 7 | Krummholz | 0.7262 | 0.5742 | 0.6413 | 14,356 |
| | Macro average | 0.6042 | 0.5112 | 0.5325 | 406,708 |

Logistic regression clearly beats both baselines (macro F1 0.5324 against
0.1426), so the features carry signal that a linear model can use. It is
stable across folds, but its macro F1 is far below its accuracy: the two
majority classes are predicted reasonably well while Aspen (5) is almost
never predicted (recall 0.0063) and Douglas-fir (6) is missed three times out
of four. A linear decision boundary and the class imbalance both contribute;
#17 (imbalance handling) and the non-linear models address them.

## Models comparison

| Model | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) |
|---|---|---|---|---|
| DummyClassifier (most_frequent) | 0.4876 | — | — | 0.0937 |
| DummyClassifier (stratified) | 0.3770 | — | — | 0.1426 |
| LogisticRegression | 0.7248 | 0.6042 | 0.5112 | 0.5324 |
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
