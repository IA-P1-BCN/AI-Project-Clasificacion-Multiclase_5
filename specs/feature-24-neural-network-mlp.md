# Spec: feature/24-neural-network-mlp

| | |
|---|---|
| Issue | #24 - [M4] Neural network with multiclass support (CNN if visual) |
| Milestone | M4 |
| Branch | `feature/24-neural-network-mlp` (from `develop`) |
| Owner | @levifvy |
| Depends on | #19 (CV protocol, merged), #14 (scaling, merged), #16 (split, merged), #22 (XGBoost / LightGBM, merged) |

## Goal

Train a neural network for the 7-class problem with early stopping and compare
it against the ensemble models already recorded, to know whether a neural
model is a candidate for the shortlist.

## Scope

- In scope: a `Pipeline` (preprocessor + multilayer perceptron), its
  evaluation with the CV protocol on the train set, per-class metrics from
  out-of-fold predictions, the comparison against XGBoost and LightGBM (#22),
  documentation in `docs/MODELING.md`.
- Out of scope: imbalance handling (#17), Random Forest (#21; its results are
  not merged yet, so it is not part of the comparison), the shortlist decision
  (#23), final metrics on validation / test (#25), overfitting check (#28),
  hyperparameter optimization (#29), exporting the pipeline (#32).

## Design

| File | Change |
|---|---|
| `src/neural_network.py` | New. `build_pipeline()`, `per_class_report(model, X, y)`, `main()`. |
| `docs/MODELING.md` | New section *Neural network (MLP)*; one row in *Models comparison*. |

Decisions:

- **MLP, not CNN.** The Covertype dataset is tabular (54 features, no spatial
  or image structure), so the issue's "CNN if visual" branch does not apply.
- **scikit-learn `MLPClassifier`.** It supports multiclass output (softmax)
  and early stopping, and needs **no new dependency**. A deep learning
  framework is not justified for a network of this size.
- **Pipeline = preprocessor + estimator.** `build_preprocessor("standard")`
  (#14) followed by the network. Neural networks need scaled inputs; the
  scaler is refitted on each training fold, so there is no data leakage.
- **Early stopping.** `early_stopping=True` holds out
  `validation_fraction=0.1` of the rows it is fitted on (a stratified internal
  hold-out taken from the training fold only) and stops when its score has not
  improved for `n_iter_no_change` epochs. The project validation and test sets
  are never used.
- **Reuse the protocol.** Accuracy and macro F1 come from
  `baseline.evaluate_model` (#19); per-class metrics come from out-of-fold
  predictions over the same `StratifiedKFold(n_splits=5, shuffle=True,
  random_state=42)`.
- **Canonical split.** The train set comes from
  `data_split.split_train_val_test` (#16).
- **Comparison.** The ensemble scores are the ones recorded for #22 in
  `docs/MODELING.md`; they are not recomputed here. Both were obtained with
  5-fold stratified CV on a 70% train partition of 406,708 rows, but #22 used
  its own demonstration split, so the rows are not identical.
- **Architecture:** two hidden layers `(128, 64)`, ReLU, Adam,
  `batch_size=512`, `max_iter=200`, `n_iter_no_change=10`. Fixed, not tuned
  (#29). `random_state=42`.
- `per_class_report` repeats the helper of `src/logistic_regression.py`
  (#20), which is not merged into `develop` yet; unify them once both are.

## Acceptance criteria

- [x] Build a simple NN (MLP, or CNN if the dataset is visual)
- [x] Train with early stopping
- [x] Compare against ensemble models
- [x] Neural network trained and compared (only if time allows)
- [x] Early stopping triggers before `max_iter` on the full train set
- [x] Macro F1 beats both baselines of #19

## Verification

```bash
python src/neural_network.py
```

Expected: the size of the train set (406,708 rows), accuracy and macro F1 as
mean ± standard deviation over the 5 folds, a per-class precision / recall /
F1 table, and the number of epochs with the line `Stopped early: True`.
The run takes about one hour on 8 CPU cores.

Observed: accuracy 0.9035 ± 0.0049, macro F1 0.8557 ± 0.0090; early stopping
at epoch 99 of 200 on the full train set. Early stopping was checked on that
fit only, not on each fold. Full results in `docs/MODELING.md`.
