# Spec: feature/39-cloud-deployment

| | |
|---|---|
| Issue | #39 - [M6] Cloud deployment (Render/Vercel/AWS) |
| Milestone | M6 |
| Branch | `feature/39-cloud-deployment` (from `develop`) |
| Owner | @levifvy |
| Depends on | #32 (model export, merged), #34 (FastAPI backend, merged), #35 (feedback & metrics endpoints, merged), #37 (database integration, merged), #1 (base `Dockerfile`, merged) |

## Goal

Select the cloud provider (**Render**), add the declarative deployment
configuration (`render.yaml`) and cloud startup entrypoint
(`scripts/start_cloud.py`) so a fresh Git clone deployed to Render serves both
the Streamlit frontend and the FastAPI backend (`/health`, `/predict`,
`/feedback`, `/metrics`) without manual intervention, and document the
deployment and verification procedure in `docs/APP.md`.

## Scope

- In scope:
  - Provider selection and justification (**Render** Docker Web Service over
    Vercel and AWS).
  - `render.yaml`: Render Blueprint declaring the Docker web service, runtime
    environment variables (`PORT`, `SERVICE_ROLE`, `API_URL`, `MODEL_PATH`,
    `DATABASE_URL`) and health check path (`/_stcore/health`).
  - `scripts/start_cloud.py`: cloud container entrypoint that:
    1. Verifies whether `MODEL_PATH` (`models/model.joblib`) exists; when
       deploying from a clean Git checkout where `models/` and `data/raw/` are
       git-ignored, builds and exports a lightweight, memory-safe fallback
       `RandomForestClassifier` `Pipeline` (`model_version = "0.1.0-cloud-bootstrap"`)
       that satisfies the 54-feature serving contract (`app.serving.load_model`).
    2. Initializes the database schema (`src/database.py::init_db`, using the
       configured `DATABASE_URL` or the built-in SQLite fallback).
    3. Launches the FastAPI backend (`uvicorn app.api:app` on `127.0.0.1:8000`)
       and the Streamlit frontend (`streamlit run app/main.py` on
       `0.0.0.0:$PORT`) in `SERVICE_ROLE=all` mode (or either service
       individually when `SERVICE_ROLE=api` / `SERVICE_ROLE=app`), and exposes a
       reproducible `--check` mode that verifies `/health`, `/predict`,
       `/feedback`, `/metrics` and Streamlit `/_stcore/health`.
  - `docs/APP.md`: complete the `## Deployment` section with the provider
    decision, cloud architecture, step-by-step Render deployment instructions
    and verification commands.
- Out of scope:
  - Editing `Dockerfile` or `docker-compose.yml` (#38, @carovasq).
  - Building the interactive Streamlit prediction form in `app/main.py` (#33,
    @nagicome03; once #33 merges into `develop`, Render auto-deploys the updated
    UI without any change to `render.yaml`).

## Design

| File | Change |
|---|---|
| `render.yaml` | New. Render Blueprint configuring the Docker web service (`env: docker`, `plan: free`, `dockerCommand: python scripts/start_cloud.py`, `healthCheckPath: /_stcore/health`). |
| `scripts/start_cloud.py` | New. `ensure_cloud_model`, `wait_for_url`, `run_self_check`, `run_services`, `main`. |
| `docs/APP.md` | Expand `## Deployment` with provider selection (Render vs Vercel vs AWS), cloud startup flow, Render Blueprint deployment steps and URL verification. |

Decisions and reasons:

- **Render over Vercel and AWS.**
  - **Vercel** targets serverless functions and static frontends (250 MB bundle
    limit, short request timeouts, no persistent WebSocket server for Streamlit).
  - **AWS (App Runner / ECS)** requires IAM roles, ECR image pushes and billing
    setup with no zero-config Git-connected Docker free tier.
  - **Render** natively builds the repository's `Dockerfile` from GitHub via
    `render.yaml`, offers a free tier (`plan: free`), injects `$PORT`, checks
    `/_stcore/health` (or `/health`), and auto-deploys every merge to `develop`.
- **Single-service default (`SERVICE_ROLE=all`) with `API_URL=http://127.0.0.1:8000`.**
  On Render's free tier, separate web services spin down after 15 minutes of
  inactivity and incur cross-service cold-start timeouts. Running `uvicorn` on
  `127.0.0.1:8000` and `streamlit` on `0.0.0.0:$PORT` inside the same container
  keeps frontend-to-backend latency sub-millisecond over loopback while still
  allowing `SERVICE_ROLE=api` or `SERVICE_ROLE=app` if deployed as two services.
- **Bootstrap model when `models/model.joblib` is absent in the cloud.**
  Because `data/raw/covtype.data` (71.7 MiB) and `models/model.joblib` (136.3
  MB) are git-ignored (Hard rule #5), a cloud container built from GitHub has
  neither file, and training the full 406,708-row forest would exceed the 512 MB
  RAM limit of a free cloud instance. `ensure_cloud_model()` leaves any existing
  `models/model.joblib` untouched; only when the file is missing does it fit the
  canonical `export_model.build_pipeline` on a small, deterministic 7-class
  synthetic cartographic sample (`random_state=42`, 54 `FEATURES`, physical
  bounds from `app/schemas.py`) so `/health` reports `model_loaded: true` and
  `/predict` works immediately in the cloud.
- **Zero conflict with #38.** `Dockerfile` and `docker-compose.yml` are not
  modified, and only `## Deployment` in `docs/APP.md` is updated.

## Acceptance criteria

- [x] Choose provider (Render/Vercel/AWS)
- [x] Prepare deployment config
- [ ] Deploy and verify public URL
- [x] Document deployment steps
- [ ] App accessible via a public URL
- [ ] `python scripts/start_cloud.py --check` verifies model availability, database initialization, FastAPI (`/health`, `/predict`, `/feedback`, `/metrics`) and Streamlit (`/_stcore/health`) end-to-end and exits 0 (added)

## Verification

```bash
docker compose exec app python scripts/start_cloud.py --check
```

Expected: verifies that `models/model.joblib` loads through `app.serving.load_model`,
starts FastAPI and Streamlit on temporary local ports, checks HTTP 200 on
`GET /health`, `POST /predict`, `POST /feedback`, `GET /metrics` and Streamlit
`GET /_stcore/health`, cleans up temporary files if a bootstrap model was
created, and exits 0.

Observed (2026-11-17):

- Provider chosen (**Render** via `render.yaml`), cloud entrypoint written in
  `scripts/start_cloud.py`, and deployment steps documented in `docs/APP.md`
  (all relative links verified: `All links in docs/APP.md resolve`).
- Container self-check (`scripts/start_cloud.py --check`) and live Render URL
  verification pending execution.
