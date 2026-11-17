# Spec: feature/38-m6-dockerize-application

| | |
|---|---|
| Issue | #38 - [M6] Dockerize the application (Dockerfile + docker-compose) |
| Milestone | M6 |
| Branch | `feature/38-m6-dockerize-application` (from `develop`) |
| Owner | @carovasq |
| Depends on | #34 (backend API), #35/#37 (feedback + database), #1/M0 base `Dockerfile` and `docker-compose.yml` — all merged into `develop` |

## Goal

Orchestrate the full application with Docker Compose: run the FastAPI backend
and the Streamlit frontend as separate services on top of the existing `db`
service, so `docker compose up` brings up the whole stack with no manual install
or run steps. This is the ticket that adds the `api` service and the
multi-process orchestration that `#47`/`docs/APP.md` explicitly defer here.

## Scope

- In scope:
  - A new `api` service in `docker-compose.yml` that runs `uvicorn app.api:app`
    on port `8000`, waits for `db` to be healthy, and has its own `/health`
    healthcheck.
  - The existing `app` service kept as the Streamlit **frontend** on port
    `8501`, now depending on `api` being healthy so the stack comes up in order.
  - Mount the model artifact (`./models`) into both services; read-only in the
    `api` service, which only serves it.
  - `Dockerfile`: keep a single shared image; the default `CMD` launches the
    Streamlit frontend, the `api` service overrides the command. Add an image
    `HEALTHCHECK`-friendly setup (no new system packages; healthchecks use the
    Python interpreter already in the image).
  - `.env.example`: document `MODEL_PATH` and the `API_URL` the frontend uses to
    reach the backend.
  - Update the Dockerization table in `docs/APP.md` to list the three services.
- Out of scope:
  - Building the Streamlit prediction UI / wiring it to call the API
    (`app/main.py` stays the current page; the UI that consumes `API_URL`
    belongs to the frontend ticket, e.g. #33).
  - The standalone Docker usage guide `docs/DOCKER.md` (#47).
  - Exporting the model artifact (#32) and choosing the final model.
  - Cloud deployment (#39) and CI changes (#41).
  - Adding Python dependencies — none are needed.

## Design

| File | Change |
|---|---|
| `docker-compose.yml` | Add `api` service (uvicorn, port 8000, `models` read-only, `/health` healthcheck, `depends_on: db healthy`). Keep `app` as the Streamlit frontend; make it `depends_on: api healthy`. Keep `db` unchanged. |
| `Dockerfile` | Keep `python:3.11-slim` + `libgomp1` + pinned `requirements.txt`; default `CMD` stays the Streamlit frontend. Minor comments to reflect the shared-image / per-service-command design. |
| `.env.example` | Document `MODEL_PATH` and `API_URL` (`http://api:8000`). |
| `docs/APP.md` | Replace the two-service Dockerization table with the `api` + `app` + `db` layout and the startup order. |

Decisions and reasons:

- **One image, two commands.** Frontend and backend share the same code,
  dependencies and image, so there is a single `Dockerfile`. The `api` service
  overrides the command with `uvicorn app.api:app --host 0.0.0.0 --port 8000`;
  the frontend keeps the image default (`streamlit run app/main.py`). This keeps
  the build cache shared and avoids a second Dockerfile.
- **Service names match the service-to-service DNS.** Compose resolves a service
  by name, so the frontend reaches the backend at `http://api:8000`
  (exposed as `API_URL`) and both reach the database at `db:3306`.
- **Startup order via healthchecks.** `api` waits for `db`
  (`condition: service_healthy`) and exposes a `/health` healthcheck; `app`
  waits for `api` (`condition: service_healthy`). `GET /health` returns 200 even
  when the model or DB is absent (by the #34 contract), so a missing artifact
  slows nothing and the stack still comes up.
- **Model artifact mounted read-only in `api`.** The backend only reads
  `models/model.joblib`; mounting `./models:/app/models:ro` there prevents
  accidental writes. The `app` service keeps it writable because
  `export_model.py` / `retraining.py` are run through it (`docker compose exec
  app ...`, per `docs/APP.md`).
- **Healthchecks use the bundled Python, not `curl`.** Avoids adding a system
  package; `python -c "import urllib.request; urllib.request.urlopen(...)"`
  is already available in the image.
- **No manual install steps.** Dependencies are installed at image build from
  pinned `requirements.txt`; `docker compose up --build` is the only command.
  The model artifact (#32) is a data prerequisite, documented, not an install
  step.

## Acceptance criteria

Copied from issue #38:

- [x] Finalize Dockerfile for the app
- [x] Add frontend/backend services to docker-compose
- [x] Mount model artifact
- [x] Verify `docker compose up` runs the full app
- [x] Full app runs via docker compose
- [x] No manual install steps

## Verification

1. `docker compose config` renders the merged configuration with three services
   (`api`, `app`, `db`), `api` published on `8000`, `app` on `8501`, and the
   `models` mount read-only on `api`.
2. `docker compose up -d --build`:
   - `db` becomes healthy, then `api` starts and its `/health` healthcheck turns
     healthy, then `app` starts.
   - `curl http://localhost:8000/health` returns 200 with `status: "ok"`.
   - `http://localhost:8501` serves the Streamlit frontend.
3. `docker compose ps` shows `api`, `app` and `db` up; `docker compose down`
   stops them and keeps the `db_data` volume.
4. No manual `pip install` or source edit is needed between clone and a running
   stack (model artifact prerequisite aside).

Result (2026-11-17, Windows + Docker Desktop, Compose v5.7.0, Engine 29.9.3):

- `docker compose config` renders three services (`api`, `app`, `db`) with
  `api` on `8000`, `app` on `8501`, and `./models` mounted `read_only: true` on
  `api`.
- `docker compose up -d --build` built both images from the shared `Dockerfile`
  and started in order: `db` healthy -> `api` healthy (its `/health` check) ->
  `app` started. `docker compose ps` showed all three up (`api` and `db`
  healthy).
- `GET http://localhost:8000/health` -> HTTP 200
  `{"status":"ok","model_loaded":false,"db_connected":true,...}`. `model_loaded`
  is false only because no `models/model.joblib` is present yet (#32 export);
  `db_connected` is true, so the backend reaches MySQL. `http://localhost:8501`
  -> HTTP 200 (Streamlit frontend).
- Model mount is read-only in `api` (`touch /app/models/...` -> "Read-only file
  system") and writable in `app`. `docker compose down` stopped the stack and
  kept the `db_data` volume.
