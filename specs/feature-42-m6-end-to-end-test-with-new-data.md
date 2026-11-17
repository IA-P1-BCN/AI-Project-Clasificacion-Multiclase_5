# Spec: feature/42-m6-end-to-end-test-with-new-data

| | |
|---|---|
| Issue | #42 - [M6] End-to-end test with new data |
| Milestone | M6 |
| Branch | `feature/42-m6-end-to-end-test-with-new-data` (from `develop`) |
| Owner | @nagicome03 |
| Depends on | #33 (Streamlit app), #34 (FastAPI backend) |

## Goal

Validate the full prediction flow (FastAPI validation -> serving layer -> model
-> response) with data the model never saw, and document the result.

## Scope

- In scope:
  - `tests/test_end_to_end.py` — a pytest test that calls the real `POST
    /predict` endpoint through FastAPI's `TestClient`.
  - `requirements.txt` — add `httpx` (needed by the `TestClient`; pinned to a
    version compatible with the pinned `starlette`).
  - `docs/TESTING.md` — a short guide to the test suite.
- Out of scope:
  - A manual check in the Streamlit UI: the UI is a thin client of this API, so
    the API path is the end-to-end contract that can be automated (and run in
    CI). The UI was already exercised during #33.

## Design

- **Two layers:**
  - **Synthetic (always runs, CI-friendly):** fits the real project pipeline on
    70 % of the synthetic frame from `tests/conftest.py`, serves it through the
    real FastAPI app, and calls `POST /predict` with the held-out 30 %. Asserts
    the response obeys the `PredictionResponse` contract and the accuracy is
    >= 85 %.
  - **Real (gated):** when `models/model.joblib` and `data/raw/covtype.data` are
    present, loads the exported model and predicts 20 random rows of the real
    test split (never used for training). Asserts the same contract and accuracy
    >= 70 % (the model's offline accuracy is ~95 %).
- **DB isolation:** the test points `DATABASE_URL` to a temporary SQLite file, so
  `POST /predict` does not touch the real database.
- **New dependency:** `httpx` (test-only, required by the FastAPI `TestClient`).
  Pinned below 0.28 because `starlette` 0.38 (used by `fastapi` 0.112) breaks
  with `httpx` 0.28.

## Acceptance criteria

Copied from issue #42:

- [x] End-to-end prediction works with new data

## Verification

```bash
docker compose run --rm --no-deps app python -m pytest tests/test_end_to_end.py -v -s
```

Observed (Python 3.11.18, the pinned requirements): **2 passed in 9.44 s**.

- Synthetic: **91 %** accuracy on 126 unseen rows.
- Real test set: **100 %** accuracy on 20 rows (the random sample happened to be
  all correct; the model's offline accuracy is ~95 %).
