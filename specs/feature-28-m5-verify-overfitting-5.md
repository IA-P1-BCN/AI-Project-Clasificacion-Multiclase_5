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

- The gap is computed by `src/final_metrics.py`
  (`overfitting_gap = accuracy_by_part["train"] - accuracy_by_part["validation"]`).
- **The criterion is measured in accuracy** (the D0.5 definition). Observed on
  the single train/validation split from #16/#25 (champion model, untuned Random
  Forest):
  - `train` accuracy: **1.0000** (406,708 rows).
  - `validation` accuracy: **0.9520** (87,152 rows).
  - `overfitting_gap = 1.0000 - 0.9520 = +0.0480` → **+4.80 percentage points**.
- **The margin is thin:** 4.80 against the 5.0 limit (only 0.2 points of room),
  and the model memorises the train set (100 % accuracy). The requirement is met,
  but not comfortably.
- **Caveat — this is accuracy only.** On the project's main metric, macro F1, the
  gap is larger: train 1.0000 vs validation 0.9186 = **8.1 percentage points**,
  and on macro recall 1.0000 vs 0.8990 = **10.1 points** — both above 5 %. So the
  "requirement met" applies to accuracy, not to macro F1; state this if anyone
  asks why the model is not regularised.
- Since the *accuracy* gap is below 5 %, the second task of the issue ("if > 5 %,
  apply regularization / simpler model / more data") does not apply.
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

Observed (Docker, Python 3.11.18 + the pinned requirements):

```
== Headline metrics by partition ==
 Partition   Rows  Accuracy  Precision (macro)  Recall (macro)  F1 (macro)
     train 406708     1.000             1.0000          1.0000      1.0000
validation  87152     0.952             0.9416          0.8990      0.9186
      test  87152     0.951             0.9423          0.9012      0.9199

== Train vs validation accuracy gap ==
train - validation = +0.0480 (+4.80 percentage points)
```

The accuracy gap (+4.80 points) is below the 5 % gate; the macro-F1 gap (8.1
points) and the macro-recall gap (10.1 points) are not, which is why this
verification is explicitly about **accuracy**.
