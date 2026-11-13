# Spec: feature/8-class-distribution

| | |
|---|---|
| Issue | #8 - [M2] Analyze class distribution (frequencies and imbalance) |
| Milestone | M2 |
| Branch | `feature/8-class-distribution` (from `develop`) |
| Owner | @Leandroletoile |
| Depends on | #7 (audit) |

> Written retroactively (ticket #8 was merged in PR #56 before the spec-driven
> workflow of PR #63 existed). It records what was built and verified.

## Goal

Measure how many samples each class has and quantify the imbalance, to decide
whether M3 needs imbalance handling.

## Scope

- In scope: class frequencies and percentages, the min/max imbalance ratio, a
  bar chart and a note on whether imbalance handling is needed.
- Out of scope: applying class weights or resampling (#17) and the stratified
  split (#16).

## Design

| File | Change |
|---|---|
| `src/class_distribution.py` | New. Counts per class, percentages, min/max ratio, saves `docs/figures/class_distribution.png`. |
| `docs/EDA.md` | *Class distribution* section: table, figure and the imbalance discussion. |

Decision: nothing was balanced here (analysis only). The result motivates
macro F1 as the main metric and stratified splits and cross-validation.

## Acceptance criteria

- [x] Class frequencies and imbalance ratio documented
- [x] Chart included in `docs/EDA.md`

## Verification

```bash
python src/class_distribution.py
```

Expected: class 2 has 283,301 rows (48.76%) and class 4 has 2,747 (0.47%); the
min/max ratio is 0.0097 (about 1:103); classes 1 and 2 hold about 85% of the rows.
