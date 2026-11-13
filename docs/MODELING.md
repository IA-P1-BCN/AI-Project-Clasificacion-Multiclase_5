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
- **Convergence:** every fit stops below `max_iter`: 223, 233, 269, 240 and
  234 iterations on the five CV folds, 219 on the full train set. The script
  reads `n_iter_` of each fold's model and fails if any fit reaches
  `max_iter`.

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

The macro F1 of this table (0.5325) is computed once over all out-of-fold
predictions pooled together, while the one in the cross-validation scores
(0.5324) is the mean of the five per-fold macro F1 values.

Logistic regression clearly beats both baselines (macro F1 0.5324 against
0.1426), so the features carry signal that a linear model can use. It is
stable across folds, but its macro F1 is far below its accuracy: the two
majority classes are predicted reasonably well while Aspen (5) is almost
never predicted (recall 0.0063) and Douglas-fir (6) is missed three times out
of four. A linear decision boundary and the class imbalance both contribute;
#17 (imbalance handling) and the non-linear models address them.

## Models comparison and shortlist

Issue #23. Reproduce every model (the MLP CV takes about an hour) with:
`python src/model_comparison.py`. The fast subset — the gradient-boosted models
and the baselines — reproduces with:
`python src/model_comparison.py XGBoost LightGBM "DummyClassifier (most_frequent)" "DummyClassifier (stratified)"`

Every model is evaluated on the **same** canonical train split
(`split_train_val_test`, #16; 406,708 rows) with the **same** protocol
(`StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`, macro F1 the main
metric), so the rows are comparable. `LogisticRegression` (#20),
`RandomForest` (#21) and `MLP` (#24) were already produced on this split, so
their numbers are reused; `XGBoost`, `LightGBM` and the `DummyClassifier`
baselines were re-run here on the canonical split (in #22 / #19 they used a
different 70% partition). Accuracy and macro F1 are the mean ± standard
deviation over the five folds; macro precision / recall come from pooled
out-of-fold predictions.

| Rank | Model | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) |
|---|---|---|---|---|---|
| 1 | RandomForest (100 trees) | 0.9470 | 0.9373 | 0.8918 | **0.9124 ± 0.0023** |
| 2 | MLP (128, 64) | 0.9035 | 0.8716 | 0.8420 | 0.8557 ± 0.0090 |
| 3 | XGBoost | 0.8693 | 0.8833 | 0.8288 | 0.8514 ± 0.0038 |
| 4 | LightGBM | 0.8561 | 0.8504 | 0.8122 | 0.8261 ± 0.0082 |
| 5 | LogisticRegression | 0.7248 | 0.6042 | 0.5112 | 0.5324 ± 0.0037 |
| — | DummyClassifier (stratified) | 0.3767 | 0.1433 | 0.1433 | 0.1433 ± 0.0013 |
| — | DummyClassifier (most_frequent) | 0.4876 | 0.0697 | 0.1429 | 0.0937 ± 0.0000 |

### F1 per class (same split and protocol)

| `Cover_Type` | Name | RandomForest | MLP | XGBoost | LightGBM | LogReg |
|---|---|---|---|---|---|---|
| 1 | Spruce/Fir | 0.9459 | 0.8987 | 0.8508 | 0.8343 | 0.7047 |
| 2 | Lodgepole Pine | 0.9551 | 0.9182 | 0.8816 | 0.8705 | 0.7736 |
| 3 | Ponderosa Pine | 0.9422 | 0.8990 | 0.9046 | 0.8924 | 0.7369 |
| 4 | Cottonwood/Willow | 0.8687 | 0.8137 | 0.8728 | 0.7817 | 0.5105 |
| 5 | Aspen | 0.8213 | 0.7312 | 0.6968 | 0.7109 | 0.0123 |
| 6 | Douglas-fir | 0.8993 | 0.8110 | 0.8270 | 0.8066 | 0.3480 |
| 7 | Krummholz | 0.9547 | 0.9187 | 0.9266 | 0.9055 | 0.6413 |

### Ranking

1. **Random Forest** is the clear winner: best macro F1 (0.9124), best accuracy
   (0.9470), the most stable (std 0.0023) and the best or near-best F1 on every
   class, including the hardest one, Aspen (0.8213).
2. **MLP** and **XGBoost** are a near tie on macro F1 (0.8557 vs 0.8514, within
   one standard deviation). The MLP has higher accuracy (+3.4 points) and is
   stronger on the two majority classes; XGBoost is more stable (std 0.0038 vs
   0.0090), the best model on the rarest class, Cottonwood/Willow (0.8728), and
   trains in minutes rather than ~1 hour.
3. **LightGBM** trails XGBoost in six of the seven classes (it is slightly
   ahead only on Aspen, 0.7109 vs 0.6968), and **logistic regression**, while
   far above the baselines, is well behind the non-linear models and barely
   predicts Aspen (F1 0.0123).

### Shortlist (proposed, pending team sign-off)

- **Primary — Random Forest:** strongest and most stable model; carry it to
  tuning (#29) and deployment (#32 / #34).
- **Secondary — XGBoost:** the more practical of the two near-tied runners-up —
  stable across folds (std 0.0038 vs the MLP's 0.0090) and trains in minutes
  rather than ~1 hour, at essentially the same macro F1. On the rarest class,
  Cottonwood/Willow, it is on par with Random Forest (0.8728 vs 0.8687, within
  the fold-to-fold noise). The **MLP** is a close alternative if accuracy on the
  majority classes is prioritized, but it is an order of magnitude slower to
  train.

Before Random Forest is carried to deployment, two things still need measuring:
its overfitting gap (#28) — the forest runs without `max_depth`, so the < 5%
criterion may not hold as is — and the size of the serialized model
(`.joblib`), which the API loads at start-up and Docker packages (#34). Tuning
(#29) should also try the eight selected features of #18 on Random Forest; they
lifted XGBoost in validation but have not been tested on the forest.

> All models are untuned (#29) and use default hyperparameters without class
> weights (#17), so the ranking may shift after tuning and imbalance handling.
> Scores are on the train split under cross-validation; final metrics on the
> validation / test partitions belong to #25.

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
  Random Forest (#21) is added below (section *Ensemble model: Random Forest*).
  The equal-footing comparison and the shortlist are in *Models comparison and
  shortlist* (#23), where XGBoost / LightGBM are re-evaluated on the canonical
  split.

## Ensemble model: Random Forest

Issue #21. Reproduce with: `python src/random_forest.py` (about ten minutes on
8 CPU cores).

- **Model:** `RandomForestClassifier(n_estimators=100, random_state=42,
  n_jobs=-1)` with default hyperparameters (Gini impurity, no depth limit,
  bootstrap sampling, `sqrt` features per split). A bagging ensemble to set
  against the gradient-boosted ones (#22).
- **No scaling / no preprocessor:** a Random Forest splits on thresholds, so
  rescaling the numeric features has no effect; the model trains on the raw
  (cleaned) `FEATURES`. The forest is the only thing learned from data, and the
  CV routines refit it on each training fold, so there is no leakage.
- **Data:** the train set of the canonical split (`split_train_val_test`, #16),
  406,708 rows. Validation and test sets are not used.
- **Default hyperparameters.** Tuning belongs to #29 and class weights to #17;
  this issue records the untuned reference.
- **Reuse the protocol.** Accuracy and macro F1 come from
  `baseline.evaluate_model` (#19); per-class metrics come from out-of-fold
  predictions (`cross_val_predict`) over the same
  `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`.

### Cross-validation scores (5 folds)

| Model | Accuracy | Macro F1 |
|---|---|---|
| RandomForest (100 trees) | 0.9470 ± 0.0006 | 0.9124 ± 0.0023 |

### Per-class metrics (out-of-fold predictions on the train set)

| `Cover_Type` | Name | Precision | Recall | F1 | Support |
|---|---|---|---|---|---|
| 1 | Spruce/Fir | 0.9577 | 0.9344 | 0.9459 | 148,288 |
| 2 | Lodgepole Pine | 0.9420 | 0.9686 | 0.9551 | 198,311 |
| 3 | Ponderosa Pine | 0.9307 | 0.9539 | 0.9422 | 25,028 |
| 4 | Cottonwood/Willow | 0.9058 | 0.8346 | 0.8687 | 1,923 |
| 5 | Aspen | 0.9317 | 0.7344 | 0.8213 | 6,645 |
| 6 | Douglas-fir | 0.9214 | 0.8782 | 0.8993 | 12,157 |
| 7 | Krummholz | 0.9717 | 0.9383 | 0.9547 | 14,356 |
| | Macro average | 0.9373 | 0.8918 | 0.9125 | 406,708 |

Random Forest is the strongest model so far on both accuracy (0.9470) and macro
F1 (0.9124), ahead of the MLP (0.9035 / 0.8557) and XGBoost (0.8690 / 0.8494),
and it is very stable across folds (macro F1 std 0.0023). The imbalance still
shows: Aspen (5) has the lowest recall (0.7344) despite high precision, so the
forest predicts it conservatively — the classic minority-class pattern that #17
will address.

### Feature importance (mean decrease in impurity, full train set)

| Rank | Feature | Importance |
|---|---|---|
| 1 | `Elevation` | 0.2415 |
| 2 | `Horizontal_Distance_To_Roadways` | 0.1176 |
| 3 | `Horizontal_Distance_To_Fire_Points` | 0.1094 |
| 4 | `Horizontal_Distance_To_Hydrology` | 0.0606 |
| 5 | `Vertical_Distance_To_Hydrology` | 0.0578 |
| 6 | `Aspect` | 0.0481 |
| 7 | `Hillshade_Noon` | 0.0433 |
| 8 | `Hillshade_9am` | 0.0414 |
| 9 | `Hillshade_3pm` | 0.0411 |
| 10 | `Slope` | 0.0333 |

`Elevation` dominates (0.24), consistent with the EDA (most discriminative
feature, eta squared 0.616). The distance features follow. The top 10 are all
numeric, but this partly reflects a known bias of impurity-based importance
(MDI): it favours continuous, high-cardinality features over binary ones, so
the low individual scores of the one-hot `Wilderness_Area` and `Soil_Type`
indicators understate their role rather than measure it. A permutation
importance, or a gain-based importance (as explored in #18, where `Soil_Type`
columns rank highly), would order them differently; #23 can revisit this on the
shared split.

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
