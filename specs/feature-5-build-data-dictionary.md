# Spec: feature/5-build-data-dictionary

| | |
|---|---|
| Issue | #5 - [M1] Build the data dictionary |
| Milestone | M1 |
| Branch | `feature/5-build-data-dictionary` (from `develop`) |
| Owner | @carovasq |
| Depends on | M1 dataset download (#4, done) |

## Goal

Give the team a single reference that documents every column of the Covertype
dataset (name, type, unit, range, meaning) plus the target and its class labels,
so everyone shares the same understanding of the data.

## Scope

- In scope: `docs/DATA_DICTIONARY.md` describing all 55 columns (10 numeric
  features, 4 wilderness-area indicators, 40 soil-type indicators, 1 target),
  and a link to it from `README.md` and `SPEC.md` section 3.
- Out of scope:
  - EDA statistics beyond ranges (distributions, correlations, class
    separation) — already in `docs/EDA.md` (M2).
  - Dataset source/version/checksum — `data/README.md`, issue #4.
  - Any change to `specs/ontology.md` terms (reused, not redefined here).

## Design

| File | Change |
|---|---|
| `docs/DATA_DICTIONARY.md` | New. Per-column reference tables for the numeric features, wilderness areas, soil types and target. |
| `README.md` | *Dataset* section: link to the data dictionary. |
| `SPEC.md` | Section 3: link to the data dictionary. "Source & version" line left untouched (issue #4). |

Sources of truth (no new facts invented):

- Column names, types, units and descriptions: `data/raw/covtype.info` (official
  UCI documentation) and `src/data_audit.py` (`COLUMNS`).
- Feature means / std: official summary statistics in `covtype.info`.
- Observed min/max ranges: computed from `data/raw/covtype.data` with
  `load_raw` (recorded in the dictionary, reproducible with the command below).
- Class shares and audit facts (no nulls, no duplicates, all int64): `docs/EDA.md`
  and `specs/ontology.md`.

## Acceptance criteria

Copied from issue #5:

- [ ] List all columns and their data types
- [ ] Describe the meaning and units of each feature
- [ ] Identify the target column and its class labels
- [ ] Add the dictionary to docs/ or SPEC.md
- [ ] Every column documented with type and meaning
- [ ] Dictionary available in the repo

## Verification

- The dictionary lists 55 columns: 10 numeric + 4 `Wilderness_Area` + 40
  `Soil_Type` + `Cover_Type`, each with type, unit/values, range and meaning.
- Target `Cover_Type` documented with its 7 class labels and shares.
- Ranges reproduce with:

  ```bash
  python -c "import sys; sys.path.insert(0,'src'); from data_audit import load_raw, COLUMNS; print(load_raw()[COLUMNS[:10]].agg(['min','max']).T)"
  ```

- `git diff --name-only origin/develop` lists only the three files above.
