# Spec: feature/39-cloud-deployment

| | |
|---|---|
| Issue | #39 - [M6] Cloud deployment (Render/Vercel/AWS) |
| Milestone | M6 |
| Branch | `feature/39-cloud-deployment` (from `develop`) |
| Owner | @levifvy |
| Depends on | #32 (model export, merged), #34 (FastAPI backend, merged), #35 (feedback & metrics endpoints, merged), #37 (database integration, merged), #1 (base `Dockerfile`, merged), #52 (A/B testing: model B and `LabelOffsetClassifier`, merged) |

## Goal

Deploy the Streamlit frontend and the FastAPI backend (`/health`, `/predict`,
`/feedback`, `/metrics`) to a free cloud host **serving a real trained model**,
with a reproducible startup entrypoint (`scripts/start_cloud.py`) and the
deployment procedure documented in `docs/APP.md`.

## Scope

- In scope:
  - Provider: **Render, free plan** (512 MB RAM, 0.1 CPU), Blueprint
    `render.yaml`. Streamlit Community Cloud and Vercel discarded (see
    Decisions).
  - Served model: **model B of #52** (tuned XGBoost), downloaded at startup
    from the GitHub release `model-b-v1` and checked against its SHA-256.
    Single model, no A/B split (`AB_TRAFFIC_B=0`).
  - `scripts/start_cloud.py`: model download + SHA-256 check, provisioning in
    a child process, configurable API startup timeout, `--check` self-test.
  - `render.yaml`: free plan, model variables, timeouts for 0.1 CPU.
  - `app/main.py` (minimal change, see Boundary notes).
  - `docs/APP.md`: `## Deployment` rewritten for Render.
- Out of scope:
  - Editing `Dockerfile` or `docker-compose.yml` (#38, @carovasq).
  - Training or exporting models (#32, #52); this branch only serves model B.
  - Persistent cloud database: Render uses ephemeral SQLite unless
    `DATABASE_URL` points to an external MySQL server.

## Design

| File | Change |
|---|---|
| `render.yaml` | `plan: free`; `MODEL_URL`, `MODEL_METADATA_URL`, `MODEL_SHA256` of release `model-b-v1`; `AB_TRAFFIC_B=0`; `OMP_NUM_THREADS=1`; `API_STARTUP_TIMEOUT=300`; `branch: feature/39-cloud-deployment` (temporary). |
| `scripts/start_cloud.py` | Heavy imports moved inside functions; new `--provision` mode (model + DB) run as a child process by `run_services`; `API_STARTUP_TIMEOUT` (default 300 s, was 30 s); `wait_for_url(..., proc=)` fails at once if the API process dies; `--check` waits up to 60 s (was 25 s) for its test servers; docstring targets Render. |
| `app/main.py` | Footer reads the model name from `model_metadata.json` next to `MODEL_PATH`; *Aspen* example replaced; comment on the examples updated. |
| `docs/APP.md` | `## Deployment`: provider and model comparison, model origin, architecture, free-plan limitations, variables, Render steps, verification. |

Decisions and reasons:

- **Render free.** It builds the project `Dockerfile` directly from GitHub
  and runs a long-lived container (FastAPI + Streamlit) at no cost.
  Streamlit Community Cloud runs no FastAPI process and Vercel is serverless
  (no long-running Streamlit/WebSocket server).
- **Model B (XGBoost) instead of the Random Forest.** The Random Forest of #32
  needs ~1.17 GiB of RAM in the running container; Render free has 512 MB.
  Model B: validation accuracy 0.9471 vs 0.9520 (RF), macro F1 0.9244 vs
  0.9186 (RF), 19.6 MB on disk, ~307 MiB of RAM for the whole container.
- **Model hosted as a GitHub release asset.** Keeps `*.joblib` out of Git
  (hard rule #5); public URL, no token. Reproducible with
  `python src/export_challenger.py`. Download uses `urllib`: **no new
  dependency**.
- **Provisioning in a child process.** In the first 512 MB simulation the
  launcher kept the ML imports and a loaded copy of the model (~230 MiB) while
  FastAPI loaded its own, and FastAPI was OOM-killed. Running provisioning in a
  child process that exits first, and keeping the launcher on the standard
  library, leaves it at ~25 MiB.
- **Longer startup timeout.** With 0.1 CPU, FastAPI took ~1 min to import and
  load the model, more than the previous fixed 30 s.
- **No silent fallback when `MODEL_URL` is set.** A misconfigured deployment
  must fail instead of serving the synthetic bootstrap model.

Boundary notes:

- `app/main.py` belongs to #33 (@nagicome03, @carovasq). Minimal change only:
  (1) the footer said "Random Forest"; it now reads `estimator`, `tuned` and
  `model_version` from `model_metadata.json` next to `MODEL_PATH` (falls back
  to a generic text), so it shows *Random Forest (v0.1.0)* locally and
  *XGBoost optimizado (v0.2.0)* on Render; (2) the *Aspen* example button
  predicted *Lodgepole Pine* (0.73) with model B, so it was replaced by another
  real Aspen training cell (Elevation 2802, Wilderness 3, Soil 33) that both
  models classify as Aspen (RF 0.72, XGBoost 0.62). The other six examples
  were unchanged and predict their class with both models.
- `render.yaml` points to `branch: feature/39-cloud-deployment` only to test
  on Render before the PR. **After the merge it must go back to
  `branch: develop`.**
- Removed with the owner's approval: `deploy/huggingface/` (abandoned
  hosting plan) and, outside Git, the abandoned "lite model" files
  (`src/lite_model.py`, untracked; `models/lite_candidates/`, git-ignored).

## Acceptance criteria

- [x] Choose provider (Render/Vercel/AWS) — Render free, justified above
- [x] Prepare deployment config (`render.yaml`)
- [x] Deploy and verify public URL — https://multiclass-covertype-app.onrender.com
- [x] Document deployment steps
- [x] App accessible via a public URL
- [x] `python scripts/start_cloud.py --check` verifies model availability, `MODEL_URL` download, database initialization, FastAPI (`/health`, `/predict`, `/feedback`, `/metrics`) and Streamlit (`/_stcore/health`) end-to-end and exits 0 (added)
- [x] The container fits in 512 MB with the real model B (added)

## Verification

Self-check and tests, project image, repository mounted (with `data/` and
`models/`):

```bash
docker run --rm -v "$PWD:/app" -w /app -e DATABASE_URL= \
  ai-project-clasificacion-multiclase_5-app python scripts/start_cloud.py --check
docker run --rm -v "$PWD:/app" -w /app -e DATABASE_URL= \
  ai-project-clasificacion-multiclase_5-app sh -c "pip install pytest httpx && python -m pytest -q"
```

Observed on 2026-11-18 after merging `origin/develop` (#52): `--check` passes
all six steps; `pytest` 45 passed, 0 skipped.

Render free-plan simulation, same image:

```bash
docker run --memory=512m --memory-swap=512m --cpus=0.1 -p 10000:10000 -e PORT=10000 \
  -e SERVICE_ROLE=all -e API_URL=http://127.0.0.1:8000 -e MODEL_PATH=/app/models/model.joblib \
  -e MODEL_URL=<release model_b.joblib> -e MODEL_METADATA_URL=<release model_b_metadata.json> \
  -e MODEL_SHA256=d679fe0e27d76b565a4375fb58f014f9f30af83c29dd9f7f6af70fb86f0be604 \
  -e AB_TRAFFIC_B=0 -e OMP_NUM_THREADS=1 -e API_STARTUP_TIMEOUT=300 \
  -e DATABASE_URL=sqlite:////app/data/processed/multiclass.db \
  <image> python scripts/start_cloud.py
```

- Logs: `model status: downloaded at /app/models/model.joblib`,
  `database initialized.`, `FastAPI healthy`; `/_stcore/health` = `ok` after
  **301 s**.
- `GET /health`: `status: ok`, `model_loaded: true`, `db_connected: true`,
  `ab_test.enabled: false`.
- Streamlit `AppTest` against the running API: *Aspen* → Aspen 62 %,
  *Ponderosa Pine* → Ponderosa Pine 47 %, no errors, footer
  *XGBoost optimizado (v0.2.0)*, 2 rows in SQLite.
- `docker stats`: **305 MiB** ready, **307 MiB** after predicting; no OOM.
- With the previous launcher (provisioning in-process) the same run was
  OOM-killed while FastAPI loaded the model.

After merging `develop` with #53 (2026-11-18): `/health` also reports
`drift.enabled: false`; `docker stats` **292 MiB** ready, **294 MiB** after
predicting, no OOM; direct `/predict` 4.9 s first call, 0.3 s next ones. The
first `AppTest` prediction exceeded the UI's 15 s timeout (the API still
stored it), most likely because the test process shared the 0.1 CPU; the
second returned Ponderosa Pine 47 %. Cold-start time not measured (the local
Docker engine stopped responding during the run).

Tests and self-check after merging `develop` with #42 and #53
(2026-11-18, `docker compose` stopped, one run at a time): `--check` passes
all six steps; `pytest` 77 passed with
`--deselect tests/test_end_to_end.py::test_predict_real_test_set`, and that
test passes when run alone (155 s), so 78/78. In a single full run the Docker
VM (~3.7 GB) runs out of memory at that test, because it loads the Random
Forest and the whole dataset after the earlier tests; it behaves the same on
`origin/develop` (passes alone in 162 s).

On Render (deployed from this branch with `render.yaml`):
https://multiclass-covertype-app.onrender.com — the *Aspen* example predicts
Aspen (62.1 %) and the footer reads *XGBoost optimizado (v0.2.0)*.

Not verified: the real cold-start / wake-up time on Render (the local cold
start at 0.1 CPU took ~5 min, longer than the ~1 min Render announces).
