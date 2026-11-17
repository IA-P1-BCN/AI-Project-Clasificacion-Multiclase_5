# Spec: feature/40-m6-unit-tests

| | |
|---|---|
| Issue | #40 - [M6] Unit tests (data integrity, model works, minimum metrics) |
| Milestone | M6 |
| Branch | `feature/40-m6-unit-tests` (from `develop`) |
| Owner | @carovasq |
| Depends on | #32 (model export), #25 (final metrics), #34 (serving) — all merged into `develop` |

## Goal

Add a `pytest` suite that validates data integrity, model behavior and minimum
metrics, and wire it into the existing CI. The suite must pass both locally and
in CI, where the raw dataset and the model artifact are git-ignored and absent.

## Scope

- In scope:
  - `tests/` with `test_data_integrity.py`, `test_model.py`, `test_metrics.py`
    and a `conftest.py` that puts `src/` and the repo root on `sys.path`.
  - `pytest` (and `pytest`-only config) added to `requirements.txt`; a minimal
    `pytest.ini`.
  - Tests that always run on small synthetic fixtures (schema, integrity-check
    logic, the serving/prediction contract, that the pipeline learns signal).
  - Tests gated with `skipif` on the presence of the artifacts
    (`data/raw/covtype.data`, `models/model.joblib`,
    `models/model_metadata.json`) that assert the real dataset / model /
    recorded metrics meet their thresholds.
  - `docs/` note on how to run the suite.
- Out of scope:
  - Changing the CI workflow logic (it already runs `pytest` when
    `tests/**/test_*.py` exist) beyond what the suite needs.
  - API integration tests over HTTP (`httpx`/`TestClient`); the serving layer is
    tested directly through `app/serving.py`.
  - Retraining the model or changing any `src/` behavior.

## Design

| File | Change |
|---|---|
| `tests/conftest.py` | New. `sys.path` setup + shared synthetic fixtures. |
| `tests/test_data_integrity.py` | New. Schema/constants, `audit()` nulls, one-hot invariants; gated full-dataset check. |
| `tests/test_model.py` | New. `build_pipeline` fit/predict contract, `app.serving` round-trip; gated real-model check. |
| `tests/test_metrics.py` | New. Synthetic pipeline beats a trivial floor; gated metadata-threshold check. |
| `pytest.ini` | New. `testpaths = tests`, quiet options. |
| `requirements.txt` | Add `pytest` (test-only dependency). |
| `docs/APP.md` or `docs/REPRODUCIBILITY.md` | One line: `python -m pytest`. |

Decisions and reasons:

- **Two layers: synthetic (always) + artifact-gated (skipif).** CI checks out a
  fresh repo with no dataset and no model (both git-ignored), so the core suite
  runs on tiny in-memory fixtures and always passes. The heavier assertions that
  need the real dataset/model are `skipif`-gated on file existence, so they run
  locally / nightly without ever failing CI for a missing artifact.
- **Minimum-metrics thresholds come from the recorded export.** The exported
  `models/model_metadata.json` stores `validation_metrics` (accuracy ~0.952,
  macro_f1 ~0.919 for the untuned RandomForest). The gated test asserts
  `accuracy >= 0.90` and `macro_f1 >= 0.85`, comfortably below the achieved
  values so a normal re-export never makes it flaky, while still catching a
  real regression. The always-run synthetic test only asserts the pipeline
  beats a trivial floor, proving the metric plumbing works.
- **Serving tested directly, not over HTTP.** `app/serving.py` is import-safe and
  deterministic; testing `to_frame`/`predict` and `load_model` avoids adding
  `httpx` and running a server.
- **`random_state=42`** for every synthetic dataset and model, per the project
  convention, so the tests are deterministic.
- **`pytest` is test-only.** It is added to `requirements.txt` (the single file
  CI installs) rather than a new `requirements-dev.txt`, so CI needs no change.

## Acceptance criteria

Copied from issue #40:

- [x] Test data integrity (schema, no nulls)
- [x] Test model loads and returns valid predictions
- [x] Test metrics meet minimum thresholds
- [x] Add pytest runner
- [x] Test suite passes in CI/local
- [x] Tests cover data, model and metrics

## Verification

1. `python -m pytest` passes locally with the artifacts present (gated tests
   run).
2. `python -m pytest` passes with the artifacts absent (gated tests skip, core
   tests run) — the CI condition.
3. `python scripts/check_imports.py` still passes (tests are not imported by it).

Result (2026-11-17, in the project image `python:3.11-slim` + pinned
`requirements.txt`, so the environment matches CI):

- **With artifacts mounted** (`docker compose run --rm --no-deps app python -m
  pytest`): `23 passed in 11.21s`. The gated tests ran against the real dataset,
  the real `model.joblib` and the recorded `validation_metrics`
  (accuracy 0.9520 >= 0.90, macro_f1 0.9186 >= 0.85).
- **Without artifacts** (image run with no bind mounts, i.e. the CI checkout):
  `18 passed, 5 skipped` — the 5 gated tests skipped with a clear reason, none
  failed.
- `python scripts/check_imports.py` in the image: `All 28 modules import
  correctly.` (tests are not imported by it).
