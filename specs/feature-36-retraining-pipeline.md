# Spec: feature/36-retraining-pipeline

| | |
|---|---|
| Issue | #36 - [M6] New data collection + retraining pipeline |
| Milestone | M6 |
| Branch | `feature/36-retraining-pipeline` (from `develop`) |
| Owner | @levifvy |
| Depends on | #12 (cleaning, merged), #16 (split, merged), #32 (export pipeline, merged), #34 (API schemas, merged) |

## Goal

Define a validated storage format and ingestion path for newly collected labeled
observations (`data/processed/new_samples.csv`), and provide a leakage-free
retraining pipeline (`src/retraining.py`) that appends validated samples only to
the training partition, evaluates against the fixed canonical validation set, and
exports an updated artifact when the validation macro F1 gate holds.

## Scope

- In scope:
  - `src/retraining.py`: `NUMERIC_BOUNDS`, `expand_compact_sample`,
    `validate_samples`, `load_new_samples`, `ingest_samples`,
    `prepare_retraining_splits`, `retrain_pipeline`, `main`.
  - `docs/APP.md`: new *New data collection and retraining pipeline* section
    documenting the storage format, ingestion API/CLI and retraining procedure.
- Out of scope:
  - The `/feedback` HTTP endpoint and real-time production monitoring metrics
    (#35, @carovasq; #35 can call `ingest_samples` directly once a true label is
    confirmed).
  - Relational/NoSQL database persistence (#37).
  - Hyperparameter tuning (#29) and automated A/B testing or drift alerts (#52,
    #53).

## Design

| File | Change |
|---|---|
| `src/retraining.py` | New. Storage schema validation, compact-to-55-column conversion, deduplicated CSV ingestion under `data/processed/new_samples.csv`, leakage-free retraining split assembly, and conditional model promotion. |
| `docs/APP.md` | New section *New data collection and retraining pipeline* with storage schema, ingestion usage and retraining steps. |

Decisions and reasons:

- **Storage format: `data/processed/new_samples.csv` with the 55 canonical
  `COLUMNS` (`FEATURES` + `Cover_Type`).**
  - `data/raw/covtype.data` is strictly immutable (Rule 5 of `AGENTS.md`), so
    newly collected rows are never appended to `data/raw/`.
  - `data/processed/` is the ontology's directory for processed/collected
    datasets and is git-ignored.
  - Storing the 55 integer columns (`int64`, header `COLUMNS`) makes the file
    directly compatible with `data_cleaning.clean()` (#12) and the training
    pipelines without a separate parser.
- **Dual input support (compact 13-field records or full 55-column rows).**
  - In production (#34 / #35), users and API payloads provide the 10
    `NUMERIC_FEATURES`, `Wilderness_Area` (1-4), `Soil_Type` (1-40) and the
    verified `Cover_Type` (1-7). `expand_compact_sample()` converts that compact
    representation into the 55 one-hot-expanded columns, while `ingest_samples()`
    accepts either compact records (`dict` / `list[dict]` / `DataFrame`) or
    already-expanded 55-column frames.
- **Strict validation (`validate_samples`) before storage.**
  - Checks: exact column set (`COLUMNS`), no nulls (`NaN`), integer values
    only (the numeric features of a compact record are rounded to whole units,
    as in the dataset; a decimal label, indicator or 55-column value is
    rejected instead of truncated), physical bounds on
    the 10 numeric features matching `app/schemas.py` (`Elevation` 0-5000,
    `Aspect` 0-360, `Slope` 0-90, horizontal distances 0-10000,
    `Vertical_Distance_To_Hydrology` -500 to 1000, `Hillshade_*` 0-255), binary
    values `{0, 1}` on the 44 indicators with **exactly one active
    `Wilderness_Area` and one active `Soil_Type` per row** (#12 disguised-null
    check), and `Cover_Type` in `1..7` (#15). Invalid batches raise `ValueError`
    before touching disk.
- **Deduplication on ingestion.**
  - `ingest_samples()` combines existing stored samples with the new batch and
    runs `clean()` (#12) to drop exact duplicate rows (keeping the first).
- **No data leakage during retraining (`prepare_retraining_splits`).**
  - The raw dataset (`clean(load_raw())`) is split first with the canonical
    `split_train_val_test` (#16, `random_state=42`). This keeps `validation`
    (87,152 rows) and `test` (87,152 rows) **fixed and untouched** across
    retraining cycles so metrics remain apples-to-apples.
  - Validated `new_samples` are appended **only to `(X_train, y_train)`** (after
    dropping any row that is an exact duplicate of an existing training,
    validation or test row, preventing leakage of held-out rows into training).
- **Quality-gated promotion (`retrain_pipeline`).**
  - Fits the pipeline (`export_model.fit_pipeline`) on the augmented training
    set, computes accuracy and macro F1 on the fixed validation set, and only
    writes `models/model.joblib` + `models/model_metadata.json` when
    `promote=True` and validation `macro_f1 >= min_macro_f1`.
- No new dependency.

## Acceptance criteria

- [x] Define storage format for new data
- [x] Add ingestion path for new samples
- [x] Document retraining procedure
- [x] New data can be ingested and stored for retraining
- [x] Invalid samples (missing fields, out-of-range values, invalid one-hot or class labels) are rejected with `ValueError` (added)
- [x] Retraining appends new samples to the training partition only; `validation` and `test` partitions remain unchanged (added)

## Verification

```bash
docker compose up -d --build
docker compose exec app python src/retraining.py
docker compose exec app python src/retraining.py --full
```

Observed (2026-11-16, Docker, Python 3.11.18, scikit-learn 1.5.1):

- `python src/retraining.py` exited 0 in ~1 min:
  - Compact & 55-column ingestion + deduplication check passed (2 unique rows).
  - Out-of-bounds (`Elevation=9999`), invalid label (`Cover_Type=9`) and
    invalid one-hot (`Soil_Type=99`) rejection checks passed.
  - Canonical split protection passed: `train=406,708 + 2 new -> 406,710`,
    while `validation=87,152` and `test=87,152` remained unchanged and a
    held-out validation row injected into the incoming batch was filtered out
    before training.
  - End-to-end sample retraining and artifact export check (20,000 stratified
    rows) passed: validation accuracy `0.8197`, validation macro F1 `0.6992`,
    and temporary `model.joblib` + `model_metadata.json` written and verified.
- `python src/retraining.py --full`, after ingesting 2 samples into
  `data/processed/new_samples.csv` with `ingest_samples`, exited 0 in ~2 min:
  rows `train_base=406,708`, `new_samples_added=2`, `train_total=406,710`,
  `validation=87,152`; validation accuracy `0.9520`, macro F1 `0.9183`, gate
  (>= 0.90) passed. `models/` was not modified (`--full` does not promote).
- Extra rejection cases, all `ValueError` and storage left unchanged: missing
  or extra field, `NaN`, `None`, text value, `Wilderness_Area=0`,
  `Cover_Type=0`, `Cover_Type=2.7`, negative `Elevation`, two active
  `Soil_Type` indicators, decimal value in a 55-column row, empty list.
- `git status --short` shows nothing under `data/` or `models/`.

Known limits:

- Promotion (`promote=True`) is only available from Python
  (`retrain_pipeline`); the command line evaluates without replacing
  `models/model.joblib`.
- Two samples with the same 54 features and different `Cover_Type` are both
  stored; only exact duplicates are dropped.
- Feedback stored in the database (#37, `list_feedback`) is not ingested
  automatically; that link belongs to the feedback system (#35).
