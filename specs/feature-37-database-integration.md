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
  - `requirements.txt`: pin `PyMySQL==1.1.1` (pure-Python MySQL driver) and
    `cryptography==43.0.1` (new dependencies, see *Decisions*).
  - `app/api.py` and `app/schemas.py`: initialize the database at startup,
    report `db_connected` and `db_detail` in `GET /health`, log every `POST /predict` call on a
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
| `requirements.txt` | Add `PyMySQL==1.1.1` and `cryptography==43.0.1`. |
| `app/schemas.py` | Add optional `prediction_id: int | None = None` to `PredictionResponse`. |
| `app/api.py` | Initialize DB in `lifespan`, add `db_connected` and `db_detail` (the connection error, if any) to `GET /health`, and call `save_prediction` in `POST /predict` without failing the prediction if the DB is unreachable. |
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
  inference stays available even if the DB container is restarting. The error
  is logged as a warning and exposed in `/health` (`db_detail`), so a broken
  connection is visible instead of silent.
- **New dependencies: `PyMySQL==1.1.1` and `cryptography==43.0.1`.** MySQL 8
  creates users with the `caching_sha2_password` plugin, and PyMySQL needs
  `cryptography` to log in with it over a non-TLS connection. Without it every
  connection from the `app` container fails with `'cryptography' package is
  required for sha256_password or caching_sha2_password auth methods`.
- **Healthcheck over TCP with the configured root password.**
  `mysqladmin ping -h 127.0.0.1 -p$$MYSQL_ROOT_PASSWORD` follows
  `MYSQL_ROOT_PASSWORD` from `.env` and does not report healthy while the
  first-start bootstrap server (socket only) is still running.

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
docker compose up -d --build
docker compose exec app python src/database.py
docker compose exec app python scripts/check_imports.py
```

Observed (2026-11-16, Docker, Python 3.11.18, MySQL 8.0, from an empty
`db_data` volume):

- `docker compose up -d --build`: `multiclass_db` reaches `healthy` and
  `multiclass_app` starts after it.
- `python src/database.py` exited 0: SQLite self-checks passed (schema, CRUD,
  join, `ValueError` on `true_cover_type=99` and on `prediction_id=9999`) and
  the last line reports `Configured DATABASE_URL: connected (mysql, ...)`.
- `python scripts/check_imports.py`: all 22 modules import.
- Against MySQL, from the `app` container: `save_prediction`, `get_prediction`,
  `list_predictions`, `save_feedback` and `list_feedback` round-trip a row;
  `SHOW CREATE TABLE feedback` shows the foreign key to `predictions(id)`.
- API (`uvicorn app.api:app --port 8000` inside the `app` container):
  `GET /health` returns `db_connected: true`; two `POST /predict` calls return
  `prediction_id` 2 and 3 and the rows are in `predictions`; an invalid
  `Soil_Type=99` returns 422.
- Persistence: after `docker compose down` and `docker compose up -d` the
  `predictions` and `feedback` rows are still there (volume `db_data`).
- Database down (`docker compose stop db`): `POST /predict` still returns 200
  with `prediction_id: null`, the API logs `Prediction not persisted: ...` and
  `/health` returns `db_connected: false` with the error in `db_detail`.

Not verified: the Streamlit app does not call the API or the database yet
(#35, #38), so nothing is persisted from the UI.

Found during verification and fixed: with only `PyMySQL` installed the `app`
container could not log in to MySQL 8 (missing `cryptography`), and the API
hid the error, so nothing was persisted under Docker.
