# Spec: feature/7-audit-dataset

| | |
|---|---|
| Issue | #7 - [M2] Audit the dataset (rows, columns, dtypes, nulls, duplicates) |
| Milestone | M2 |
| Branch | `feature/7-audit-dataset` (from `develop`) |
| Owner | @Leandroletoile |
| Depends on | M1 dataset download (`data/raw/covtype.data`) |

> Written retroactively (ticket #7 was merged in PR #54 before the spec-driven
> workflow of PR #63 existed). It records what was built and verified.

## Goal

Produce a complete profile of the Covertype dataset (size, shape, dtypes, nulls
and duplicates) so later cleaning decisions start from facts.

## Scope

- In scope: loading the raw file with the column names of `covtype.info`,
  reporting rows, columns, dtypes, nulls and duplicates, and an audit table in
  `docs/EDA.md`.
- Out of scope: removing or imputing anything (#12), class analysis (#8, #9),
  and splitting (#16).

## Design

| File | Change |
|---|---|
| `src/data_audit.py` | New. `load_raw()` (raises a clear error if the dataset is missing), audit report and `main()`. |
| `docs/EDA.md` | *Dataset audit* section: metrics table, data types table and audit findings. |

Decision: the audit only reports. The raw file has no header, so column names
come from the official documentation.

## Acceptance criteria

- [x] Audit table (rows, columns, dtypes, nulls, duplicates) filled in `docs/EDA.md`
- [x] Unexpected issues flagged (none found: 0 nulls, 0 duplicates)

## Verification

```bash
python src/data_audit.py
```

Expected: 581,012 rows x 55 columns (54 features + `Cover_Type`), all `int64`,
0 nulls and 0 duplicated rows. The counts match the official metadata.
