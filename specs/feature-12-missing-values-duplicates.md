# Spec: feature/12-missing-values-duplicates

| | |
|---|---|
| Issue | #12 - [M3] Handle missing values and duplicates |
| Milestone | M3 |
| Branch | `feature/12-missing-values-duplicates` (from `develop`) |
| Owner | @levifvy |
| Depends on | #7 (M2 audit, merged) |

## Goal

Decide, apply and document the strategy for missing values and duplicates.
The M2 audit found none; this branch confirms it with deeper checks and leaves
a guard for data that arrives later.

## Scope

- In scope: inspection of explicit and disguised missing values, duplicate
  rows and conflicting labels; a `clean()` function; documentation of the
  decision.
- Out of scope: outliers (#13), target encoding (#15), split (#16), scaling (#14).

## Design

| File | Change |
|---|---|
| `src/data_cleaning.py` | New. `missing_report(df)`, `duplicate_report(df)`, `clean(df)`, `main()`. |
| `docs/PREPROCESSING.md` | New. M3 decisions; section *Missing values and duplicates*. |
| `README.md` | Add `PREPROCESSING.md` to the repository tree. |

Decisions:

- **No imputation, no removal**: the dataset has no nulls and no duplicates.
- **Disguised missing values** are checked through the one-hot groups (each
  row must have exactly one `Wilderness_Area` and one `Soil_Type`).
- **`clean()` fails on nulls** instead of imputing: no imputation strategy was
  chosen by the team, so silently applying one would hide a data problem.
- **`clean()` drops exact duplicates only** (keep first). Equal features with
  different targets are label noise and are kept.
- Zeros in numeric features are reported but not treated as missing; they are
  inside the documented ranges.

## Acceptance criteria

- [x] Inspect missing value patterns
- [x] Choose strategy (drop / impute) with justification
- [x] Apply the strategy and verify no nulls remain
- [x] Handle duplicates (drop or keep with reason)
- [x] Dataset has no remaining nulls (or documented reason)
- [x] Duplicates handled and documented

## Verification

Run on 2026-11-12 with `python src/data_cleaning.py`:

| Check | Result |
|---|---|
| Explicit nulls | 0 |
| Rows without exactly one `Wilderness_Area` / `Soil_Type` | 0 / 0 |
| Exact duplicate rows / conflicting rows | 0 / 0 |
| Rows before and after `clean()` | 581,012 / 581,012 |

Synthetic checks (ad hoc, not committed as tests): a frame with one exact
duplicate and one conflicting row returns 2 of 3 rows; a frame with a `NaN`
raises `ValueError`; a row with no active `Soil_Type` is counted.
