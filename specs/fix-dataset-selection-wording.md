# Spec: fix/dataset-selection-wording

| | |
|---|---|
| Issue | Follow-up to #3 (no dedicated issue); corrections from a review of PR #71 |
| Milestone | M1 |
| Branch | `fix/dataset-selection-wording` (from `develop`) |
| Owner | @carovasq |
| Depends on | #3 (merged via PR #71) |

## Goal

Fix two documentation defects in `docs/DATASET_SELECTION.md` that were raised in
a review of PR #71 after it had already been merged into `develop`. No decision
or number changes; only the prose is made consistent with the data and with the
scripts that actually produce the reported facts.

## Scope

- In scope: `docs/DATASET_SELECTION.md` prose only.
- Out of scope: the selection decision itself, the comparison table figures
  (which are correct), `README.md` / `SPEC.md` links (already merged without
  conflict), and any code change.

## Design

| File | Change |
|---|---|
| `docs/DATASET_SELECTION.md` | (1) Balance wording: Dry Bean is moderately imbalanced (~1:7), not "close to balanced", consistent with the table. (2) Reproduce block: `data_audit.py` reports shape/dtypes/nulls; per-class shares come from `class_distribution.py`. |

Reasons:

- **Balance wording.** The table labels Dry Bean `moderate (~1:7)`, but the
  justification called both Wine and Dry Bean "close to balanced". ~1:7 is not
  close to balanced. Reworded so prose and table agree.
- **Reproduce command.** The doc claimed `python src/data_audit.py` verifies
  "shape and class shares". Verified in code: `data_audit.py` prints the audit
  summary (rows, columns, dtypes, nulls, duplicates) but no per-class shares;
  `class_distribution.py` prints the per-class counts, percentages and imbalance
  ratio. Both commands are now listed with what each produces.

## Acceptance criteria

- [x] Balance justification is consistent with the comparison table.
- [x] Reproduce block names the script that actually prints class shares.
- [x] No figures or decisions changed.

## Verification

- `grep` confirms the "close to balanced" phrasing is gone and Dry Bean's ~1:7 is
  referenced in the justification.
- `python src/class_distribution.py` prints per-class percentages and the
  imbalance ratio (the facts the doc now attributes to it); `python
  src/data_audit.py` prints shape/dtypes/nulls (no class shares).
