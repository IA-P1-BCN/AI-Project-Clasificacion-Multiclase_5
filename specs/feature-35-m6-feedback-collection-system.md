# Spec: feature/35-m6-feedback-collection-system

| | |
|---|---|
| Issue | #35 - [M6] Feedback collection system (production metrics) |
| Milestone | M6 |
| Branch | `feature/35-m6-feedback-collection-system` (from `develop`) |
| Owner | @carovasq |
| Depends on | #34 (FastAPI backend, merged), #37 (database integration, merged), #32 (exported model, merged) |

## Goal

Let the running API collect the true label for a past prediction and expose
basic production-monitoring metrics, so the team can measure how the deployed
model performs on real feedback. Adds a `POST /feedback` endpoint and a
`GET /metrics` endpoint on top of the existing backend (#34) and feedback
storage (#37).

## Scope

- In scope: the feedback payload schema and response schema; the
  `POST /feedback` endpoint that validates the payload and stores it; a
  `GET /metrics` endpoint that returns production metrics (prediction and
  feedback counts, feedback coverage, live accuracy from feedback, average
  confidence, and per-class feedback accuracy); a `feedback_metrics()`
  aggregation in `src/database.py`; the self-check and documentation.
- Out of scope: the Streamlit UI that calls these endpoints (M6 frontend
  issue), retraining from collected feedback (#36), the prediction endpoint and
  `save_prediction` / `save_feedback` storage themselves (owned by #34 / #37 —
  reused, not modified), dashboards or external monitoring tools. Metrics are
  returned as JSON; a visual dashboard is not required for *Medio*.

## Design

| File | Change |
|---|---|
| `app/schemas.py` | New `FeedbackRequest`, `FeedbackResponse`, `ClassMetric`, `MetricsResponse`. |
| `app/api.py` | New `POST /feedback` and `GET /metrics` endpoints. |
| `src/database.py` | New `feedback_metrics()` aggregation; extend `_run_self_checks` and `main()` to verify it. |
| `docs/APP.md` | Document the two endpoints (payloads, examples, status codes). |

Decisions:

- **Reuse the #37 storage, do not modify it.** `save_feedback`,
  `get_prediction`, `list_feedback` and the `feedback` table already exist.
  `POST /feedback` calls `save_feedback`; the only new database code is the
  read-only `feedback_metrics()` aggregation, which belongs to this monitoring
  issue.
- **Feedback payload:** `prediction_id` (the id returned by `POST /predict`),
  `true_cover_type` (1-7, validated by pydantic so an out-of-range value returns
  HTTP 422 before touching the database) and an optional free-text `comment`.
  The response echoes the stored feedback plus the model's original
  `predicted_cover_type` and the derived `is_correct` flag.
- **Status codes:** unknown `prediction_id` -> 404; invalid payload -> 422
  (pydantic); database unavailable -> 503, mirroring how `POST /predict` already
  degrades. The metrics endpoint returns 503 if the database is unreachable.
- **Metrics (`feedback_metrics()`):** backend-agnostic SQL (works on SQLite and
  MySQL) returning `predictions_total`, `feedback_total`, `feedback_coverage`,
  `correct_total`, `live_accuracy` (accuracy measured on labelled feedback),
  `average_confidence` (mean confidence of predictions that received feedback)
  and `per_class` (feedback count and accuracy per true `Cover_Type`).
  Denominators of zero yield `null` rather than a division error, so the
  endpoint works from the first request.
- No new dependency: FastAPI, pydantic, PyMySQL and the SQLite fallback are
  already pinned.

## Acceptance criteria

- [x] Define feedback payload (prediction, true label, timestamp) — schema +
      stored `created_at_utc`.
- [x] Add `/feedback` endpoint.
- [x] Store feedback (DB) — via `save_feedback` (#37).
- [x] Expose basic monitoring metrics — `GET /metrics` + `feedback_metrics()`.
- [x] Feedback can be collected and stored; basic production metrics visible.

## Verification

```
python src/database.py
# self-checks now also verify feedback_metrics() (counts, live accuracy, per class)

python scripts/check_imports.py
# app.api and app.schemas import with the new endpoints and schemas

# Manual end-to-end (optional, needs the exported model):
uvicorn app.api:app --port 8000
#   POST /predict  -> returns prediction_id
#   POST /feedback {prediction_id, true_cover_type} -> stores feedback
#   GET  /metrics  -> production metrics
```
