# Spec: feature/28-m5-verify-overfitting-5

| | |
|---|---|
| Issue | #28 - [M5] Verify overfitting < 5% |
| Milestone | M5 |
| Branch | `feature/28-m5-verify-overfitting-5` (from `develop`) |
| Owner | @nagicome03 |
| Depends on | #25 (final metrics) |

## Goal

Confirm that the train/validation accuracy gap of the champion model (the untuned
Random Forest exported by #32) is below the 5 % hard requirement, and document
the verified result.

## Scope

- In scope: verification and documentation of the `overfitting_gap`
  (`accuracy(train) - accuracy(validation)`) of the champion model, plus a spec
  and an explicit closed note in `docs/MODELING.md`.
- Out of scope:
  - The A/B challenger model (tuned XGBoost, #52) and its own metrics — it is a
    separate model with its own evaluation.
  - Any regularization / simpler model / extra data: not needed here because the
    gap is already below 5 %.

## Design

- The gap is already computed by `src/final_metrics.py`
  (`overfitting_gap = accuracy_by_part["train"] - accuracy_by_part["validation"]`).
- Observed (champion model, 5-fold-free single split from #16/#25):
  - `train` accuracy: **1.0000** (406,708 rows).
  - `validation` accuracy: **0.9520** (87,152 rows).
  - `overfitting_gap = 1.0000 - 0.9520 = +0.0480` → **+4.80 percentage points**.
- Since `4.80 < 5.0`, the second task of the issue ("if > 5 %, apply
  regularization / simpler model / more data") does not apply.
- The result remains documented in `docs/MODELING.md` (*Headline metrics across
  partitions*), now marked as verified in #28.

## Acceptance criteria

Copied from issue #28:

- [x] Overfitting gap < 5% verified and documented

## Verification

Reproduce with:

```bash
python src/final_metrics.py
```

Expected: the *Train vs validation accuracy gap* line prints
`train - validation = +0.0480 (+4.80 percentage points)`, i.e. below the 5 %
quality gate.
