# Spec: feature/37-database-integration

| | |
|---|---|
| Issue | #37 - [M6] Database integration (MySQL/MongoDB) |
| Milestone | M6 |
| Branch | `feature/37-database-integration` (from `develop`) |
| Owner | @levifvy, @nagicome03 |
| Depends on | #34 (Backend API, merged), #32 (Model export, merged) |

## Goal

Integrate a relational database (**MySQL 8.0** in `docker-compose.yml`, with a
zero-config SQLite fallback for local script/dev execution) to persist model
predictions and user feedback, expose read/write operations in `src/database.py`,
wire prediction logging into the FastAPI backend, and document the schema in
`docs/APP.md`.

## Scope

- In scope:
  - `src/database.py`: schema creation (`init_db`), health check (`db_status`),
    and CRUD helpers for `predictions` (`save_prediction`, `get_prediction`,
    `list_predictions`) and `feedback` (`save_feedback`, `list_feedback`),
    plus a self-cleaning end-to-end verification in `main()`.
  - `docker-compose.yml` and `.env.example`: active `db` service running
    `mysql:8.0` with a healthcheck and persistent volume `db_data`, wired to the
    `app` service via `DATABASE_URL`.
  - `requirements.txt`: pin `PyMySQL==1.1.1` (pure-Python MySQL driver).
  - `app/api.py` and `app/schemas.py`: initialize the database at startup,
    report `db_connected` in `GET /health`, log every `POST /predict` call on a
    best-effort basis, and return `prediction_id` (`int | None`) in
    `PredictionResponse`.
  - `docs/APP.md`: new *Database integration* section documenting the database
    choice, `predictions` and `feedback` schemas, configuration and usage.
- Out of scope:
  - The `POST /feedback` HTTP endpoint and production monitoring dashboard (#35,
    @carovasq; `src/database.py` exposes `save_feedback` and `list_feedback` for
    #35 to call).
  - Full multi-container orchestration of frontend + backend processes (#38,
    @carovasq).
  - Cloud deployment (#39).

## Design

| File | Change |
|---|---|
| `src/database.py` | New. Dual-driver (`mysql` via `pymysql`, `sqlite` via stdlib `sqlite3`) persistence layer for `predictions` and `feedback`, with `main()` verification. |
| `docker-compose.yml` | Enable the `db` service with `mysql:8.0`, healthcheck, port `3306:3306`, persistent `db_data` volume, and `DATABASE_URL` on `app`. |
| `.env.example` | Replace commented Postgres placeholders with MySQL variables (`MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD`, `DATABASE_URL`). |
| `requirements.txt` | Add `PyMySQL==1.1.1`. |
| `app/schemas.py` | Add optional `prediction_id: int | None = None` to `PredictionResponse`. |
| `app/api.py` | Initialize DB in `lifespan`, add `db_connected` to `GET /health`, and call `save_prediction` in `POST /predict` without failing the prediction if the DB is unreachable. |
| `docs/APP.md` | Document the MySQL / SQLite configuration, the `predictions` and `feedback` tables, and the read/write API. |

Decisions and reasons:

- **MySQL 8.0 over MongoDB.** Every prediction and feedback record has a fixed
  tabular schema (the 10 numeric features, `Wilderness_Area` 1–4, `Soil_Type`
  1–40, `predicted_cover_type` 1–7, `confidence`, and `true_cover_type` 1–7
  linked by `prediction_id`). A relational schema enforces types and foreign-key
  integrity between `feedback` and `predictions`.
- **Dual-driver adapter (`mysql` + `sqlite`).** In Docker Compose,
  `DATABASE_URL=mysql+pymysql://app:app@db:3306/multiclass` connects to the
  `mysql:8.0` container using `pymysql` (pure Python, no C compiler needed in
  `python:3.11-slim`). When `DATABASE_URL` is unset or starts with `sqlite://`,
  `src/database.py` uses Python's built-in `sqlite3` at
  `data/processed/multiclass.db` (git-ignored) with the same two tables, so
  `python src/database.py` and local development work out of the box without a
  running MySQL daemon. `pymysql` is imported lazily when a `mysql` URL is used,
  so `scripts/check_imports.py` passes even in environments where `pymysql` is
  not installed yet.
- **Best-effort logging in `/predict`.** Just as `app/serving.py` never crashes
  the API when `models/model.joblib` is missing (#34), a database connection
  error during `POST /predict` is caught and returns `prediction_id: None` so
  inference stays available even if the DB container is restarting.

## Acceptance criteria

- [x] Choose DB (MySQL or MongoDB)
- [x] Add DB service to docker-compose
- [x] Implement read/write for feedback and predictions
- [x] Document schema
- [x] Data persisted in a database
- [x] DB service runs with docker-compose
- [x] Invalid `true_cover_type` (outside 1–7) or unknown `prediction_id` is rejected with `ValueError` (added)

## Verification

```bash
python src/database.py
```

Observed (2026-11-16, Python 3.12.10):

- `python src/database.py` exited 0:
  - Verified `predictions` (19 columns) and `feedback` (7 columns, FK to
    `predictions.id`) schema creation.
  - Verified `save_prediction`, `get_prediction`, `list_predictions`,
    `save_feedback` (both matching `is_correct=True` and mismatching
    `is_correct=False`), `list_feedback` (joined query), and `db_status`.
  - Verified `ValueError` rejection for invalid `true_cover_type` (`99`) and
    non-existent `prediction_id` (`9999`).
- `git status --short` shows only the expected tracked files; no database file
  is left under `data/` or `models/`.
