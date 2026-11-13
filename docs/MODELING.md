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
| MLP (128, 64) | 0.9035 | 0.8716 | 0.8420 | 0.8557 |

> Values are the mean over 5-fold stratified cross-validation on the training
> split (see `specs/feature-22-m4-train-ensemble-model-xgboost-lightgbm.md`).

## Neural network (MLP)

Issue #24. Reproduce with: `python src/neural_network.py` (about one hour on
8 CPU cores; a single fit on the train set takes about 10 minutes).

- **Model:** `Pipeline` of the preprocessor from #14 (`StandardScaler` on
  `NUMERIC_FEATURES`, `BINARY_FEATURES` passed through) and scikit-learn
  `MLPClassifier(hidden_layer_sizes=(128, 64), batch_size=512, max_iter=200,
  random_state=42)`: two hidden ReLU layers, softmax output over the 7
  classes, Adam optimizer. An MLP rather than a CNN because the Covertype
  dataset is tabular. No new dependency.
- **Early stopping:** `early_stopping=True`, `validation_fraction=0.1`,
  `n_iter_no_change=10`. The hold-out is taken from the rows passed to `fit`
  (training rows only). On the full train set training stopped at epoch 99 of
  200, with a best internal hold-out accuracy of 0.9122.
- **Data:** the train set of the canonical split (`split_train_val_test`,
  #16), 406,708 rows. Validation and test sets are not used.
- **No leakage:** the scaler is a `Pipeline` step, so it is refitted on each
  training fold. No class weights (#17) and no tuning (#29).

### Cross-validation scores (5 folds)

| Model | Accuracy | Macro F1 |
|---|---|---|
| MLP (128, 64) | 0.9035 ± 0.0049 | 0.8557 ± 0.0090 |

### Per-class metrics (out-of-fold predictions on the train set)

| `Cover_Type` | Name | Precision | Recall | F1 | Support |
|---|---|---|---|---|---|
| 1 | Spruce/Fir | 0.9082 | 0.8895 | 0.8987 | 148,288 |
| 2 | Lodgepole Pine | 0.9077 | 0.9290 | 0.9182 | 198,311 |
| 3 | Ponderosa Pine | 0.8923 | 0.9058 | 0.8990 | 25,028 |
| 4 | Cottonwood/Willow | 0.8332 | 0.7951 | 0.8137 | 1,923 |
| 5 | Aspen | 0.8025 | 0.6715 | 0.7312 | 6,645 |
| 6 | Douglas-fir | 0.8196 | 0.8027 | 0.8110 | 12,157 |
| 7 | Krummholz | 0.9376 | 0.9005 | 0.9187 | 14,356 |
| | Macro average | 0.8716 | 0.8420 | 0.8558 | 406,708 |

### Comparison against the ensemble models (#22)

| Model | Accuracy | Macro F1 | Macro F1 std |
|---|---|---|---|
| MLP (128, 64) | 0.9035 | 0.8557 | 0.0090 |
| XGBoost | 0.8690 | 0.8494 | 0.0012 |
| LightGBM | 0.8540 | 0.8175 | 0.0266 |

F1 per class:

| `Cover_Type` | Name | MLP | XGBoost | LightGBM |
|---|---|---|---|---|
| 1 | Spruce/Fir | 0.8987 | 0.8510 | 0.8332 |
| 2 | Lodgepole Pine | 0.9182 | 0.8820 | 0.8698 |
| 3 | Ponderosa Pine | 0.8990 | 0.8999 | 0.8927 |
| 4 | Cottonwood/Willow | 0.8137 | 0.8553 | 0.7084 |
| 5 | Aspen | 0.7312 | 0.7213 | 0.7042 |
| 6 | Douglas-fir | 0.8110 | 0.8137 | 0.8088 |
| 7 | Krummholz | 0.9187 | 0.9226 | 0.9052 |

- The MLP has the best accuracy (+3.5 points over XGBoost) because it
  separates the two majority classes, Spruce/Fir and Lodgepole Pine, better.
- On macro F1 the MLP and XGBoost are close (0.8557 against 0.8494). XGBoost
  is better on the rarest class, Cottonwood/Willow (0.8553 against 0.8137),
  and is more stable across folds.
- Aspen (5) is the hardest class for all three models.
- Cost: one MLP fit takes about 10 minutes on CPU, far more than the
  gradient-boosted models.
- Caveats: all three models are untuned (#29), and the ensemble scores were
  obtained in #22 on a different 70% train partition of the same size
  (406,708 rows), so differences of a few thousandths are not conclusive.
  Random Forest (#21) is not merged yet and is not compared. The shortlist
  decision belongs to #23.

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
