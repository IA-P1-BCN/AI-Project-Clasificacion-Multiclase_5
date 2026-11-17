# Spec: feature/39-cloud-deployment

| | |
|---|---|
| Issue | #39 - [M6] Cloud deployment (Render/Vercel/AWS) |
| Milestone | M6 |
| Branch | `feature/39-cloud-deployment` (from `develop`) |
| Owner | @levifvy |
| Depends on | #32 (model export, merged), #34 (FastAPI backend, merged), #35 (feedback & metrics endpoints, merged), #37 (database integration, merged), #1 (base `Dockerfile`, merged) |

## Goal

Deploy the Streamlit frontend and the FastAPI backend (`/health`, `/predict`,
`/feedback`, `/metrics`) to a free cloud host **serving the real exported
model**, with a reproducible startup entrypoint (`scripts/start_cloud.py`) and
the deployment procedure documented in `docs/APP.md`.

## Scope

- In scope:
  - Provider selection and justification: **Hugging Face Spaces** (Docker SDK);
    Render, Vercel and Streamlit Community Cloud discarded.
  - `deploy/huggingface/README.md` + `deploy/huggingface/Dockerfile`: the two
    files of the Space repository. The Dockerfile clones this public GitHub
    repository at build time (`REPO_REF`, default `develop`), runs as UID 1000
    and starts `scripts/start_cloud.py` on port 7860.
  - `scripts/start_cloud.py`:
    1. `ensure_cloud_model`: keeps an existing `MODEL_PATH`; otherwise
       downloads the exported model from `MODEL_URL` (atomic write, optional
       `MODEL_SHA256` check, optional `MODEL_METADATA_URL`, optional
       `HF_TOKEN`), failing loudly on any error; only without `MODEL_URL` does
       it fit the synthetic bootstrap model (`0.1.0-cloud-bootstrap`), logging
       a warning.
    2. Initializes the database (`src/database.py::init_db`).
    3. Runs FastAPI on loopback and Streamlit on `0.0.0.0:$PORT`
       (`SERVICE_ROLE=all`, or `api` / `app` alone).
    4. `--check`: self-cleaning end-to-end verification, including the
       `MODEL_URL` download path through a `file://` URL and a rejected
       SHA-256 mismatch.
  - `render.yaml`: removed (Render is no longer a deployment target).
  - `docs/APP.md`: `## Deployment` rewritten for Hugging Face Spaces.
- Out of scope:
  - Editing `Dockerfile` or `docker-compose.yml` (#38, @carovasq).
  - Shrinking or retraining the model (modeling issues) to fit 512 MB tiers.
  - Persistent cloud database: the Space uses ephemeral SQLite unless
    `DATABASE_URL` points to an external MySQL server.
  - The Streamlit prediction form (#33, @nagicome03).

## Design

| File | Change |
|---|---|
| `deploy/huggingface/Dockerfile` | New. Space image: clone repo at `REPO_REF`, install requirements, `PORT=7860`, `CMD python scripts/start_cloud.py`. |
| `deploy/huggingface/README.md` | New. Space card with front matter (`sdk: docker`, `app_port: 7860`). |
| `scripts/start_cloud.py` | `sha256_of`, `download_file`, `fetch_remote_model`; `ensure_cloud_model` resolution order; `--check` step 1b; fixes in `label_mapping` call and `/metrics` keys. |
| `render.yaml` | Deleted. |
| `docs/APP.md` | `## Deployment` section. |

Decisions and reasons:

- **Hugging Face Spaces over Render.** The exported model
  (`RandomForestClassifier`, 100 trees, `max_depth=None`) is 136.3 MB on disk
  and the running container uses ~1.17 GiB of RAM (`docker stats`). Render's
  free plan has 512 MB, so on Render the app could only serve a synthetic
  model whose predictions are not the project's. Free Spaces offer 16 GB RAM
  and 2 vCPU, build Docker images, and sleep only after ~48 h idle.
- **Vercel and Streamlit Community Cloud discarded.** Vercel is serverless
  (250 MB bundle, no long-running Streamlit/WebSocket process). Streamlit
  Community Cloud runs no FastAPI process, has ~1 GB RAM and needs the model
  in GitHub (100 MB file limit, hard rule #5).
- **Space clones GitHub instead of mirroring the repository.** Spaces reject
  binary files outside LFS/Xet (`docs/figures/*.png`); cloning keeps the Space
  to two text files and avoids any CI secret. Redeploy = *Factory rebuild*.
- **Model hosted in a Hugging Face model repository, downloaded at startup.**
  Keeps `*.joblib` out of Git (hard rule #5). Download uses `urllib` from the
  standard library: **no new dependency**. `MODEL_SHA256` (from
  `model_metadata.json`) guarantees the served model is the exported one.
- **No silent fallback when `MODEL_URL` is set.** A misconfigured deployment
  must fail instead of serving synthetic predictions.

## Acceptance criteria

- [x] Choose provider (Render/Vercel/AWS) — Hugging Face Spaces, justified above
- [x] Prepare deployment config
- [ ] Deploy and verify public URL
- [x] Document deployment steps
- [ ] App accessible via a public URL
- [x] `python scripts/start_cloud.py --check` verifies model availability, `MODEL_URL` download, database initialization, FastAPI (`/health`, `/predict`, `/feedback`, `/metrics`) and Streamlit (`/_stcore/health`) end-to-end and exits 0 (added)

## Verification

```bash
docker run --rm -v "$PWD:/app" -w /app -e DATABASE_URL= \
  ai-project-clasificacion-multiclase_5-app python scripts/start_cloud.py --check
```

Observed (2026-11-17, project image, Python 3.11):

```
1. Model artifact check: bootstrapped (71.6 KB)
1b. MODEL_URL download check: downloaded + SHA-256 verified, mismatch rejected
2. Database schema check: initialized (SQLite cloud fallback)
3. FastAPI /health check: {'status': 'ok', 'model_loaded': True, 'db_connected': True, ...}
4. FastAPI /predict check: cover_type=5 (Aspen), confidence=0.7272, prediction_id=1
5. FastAPI /feedback & /metrics check: feedback_total=1, live_accuracy=1.0
6. Streamlit /_stcore/health check: ok
All cloud deployment checks passed.
```

Space runtime simulation with the real model (project image, UID 1000,
`PORT=7860`, empty `MODEL_PATH`, `MODEL_URL=file:///remote/model.joblib`,
`MODEL_SHA256` from `model_metadata.json`): logs `model status: downloaded`,
FastAPI healthy, Streamlit `/_stcore/health` = `ok` after ~60 s,
`/predict` on the sample above returns `Lodgepole Pine` (0.95), memory
1.171 GiB.

Not verified: building `deploy/huggingface/Dockerfile` itself (it clones
`develop`, which does not contain these changes until the merge) and the
public Space URL, which needs a Hugging Face account.
