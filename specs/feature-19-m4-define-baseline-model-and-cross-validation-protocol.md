# Spec: feature/19-m4-define-baseline-model-and-cross-validation-protocol

| | |
|---|---|
| Issue | #19 - [M4] Define baseline model and cross-validation protocol |
| Milestone | M4 |
| Branch | `feature/19-m4-define-baseline-model-and-cross-validation-protocol` (from `develop`) |
| Owner | @nagicome03 |
| Depends on | #16 (split, PR pending) |

## Goal

Define the baselines (reference models every real model must beat) and the
cross-validation protocol used to compare all models.

## Scope

- In scope: `src/baseline.py` (reusable `evaluate_model()` + the two baselines),
  documentation in `docs/MODELING.md`.
- Out of scope: any real model (Logistic Regression #20, Random Forest #21,
  XGBoost/LightGBM #22), hyperparameter tuning (#29).

## Design

| File | Change |
|---|---|
| `src/baseline.py` | New. `evaluate_model()`, `BASELINES`, `main()`. |
| `docs/MODELING.md` | New section *Baseline & evaluation protocol*. |

Decisions:

- **Two baselines** (agreed in PR discussion): `DummyClassifier(strategy="most_frequent")`
  and `DummyClassifier(strategy="stratified")`.
- **Protocol:** `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)` on
  the training partition; metrics `accuracy` and **macro F1** (the main metric,
  per `specs/ontology.md`).
- **`evaluate_model(model, X, y)`** is the single reusable entry point, so every
  model is compared on the same protocol.
- **`zero_division=0`** in the macro-F1 scorer so the dummy baselines do not warn.
- **No leakage:** CV runs only on the training partition.
- The canonical 70/15/15 split belongs to #16; `main()` uses a demonstration
  70/30 split and will import `split_train_val_test` once #16 is merged.

## Acceptance criteria

- [x] Define a simple baseline (majority class / dummy)
- [x] Set cross-validation protocol (StratifiedKFold, k, scoring)
- [x] Document the comparison methodology
- [x] Baseline score recorded
- [x] CV protocol documented and reused by all models

## Verification

Run on 2026-11-12 with `python src/baseline.py` (stratified 5-fold CV on
406,708 training rows):

| Baseline | Accuracy | Macro F1 |
|---|---|---|
| DummyClassifier(most_frequent) | 0.4876 ± 0.0000 | 0.0937 ± 0.0000 |
| DummyClassifier(stratified) | 0.3770 ± 0.0011 | 0.1426 ± 0.0009 |

Every real model must beat these scores, especially macro F1.
