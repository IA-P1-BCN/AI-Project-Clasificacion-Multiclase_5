# Spec: feature/46-reproducibility-requirements-run-steps

| | |
|---|---|
| Issue | #46 - [M7] Reproducibility (final requirements.txt and run steps) |
| Milestone | M7 |
| Branch | `feature/46-reproducibility-requirements-run-steps` (from `develop`) |
| Owner | @Leandroletoile |
| Depends on | M6 Docker (`Dockerfile` and `docker-compose.yml` already in `develop`) |

## Goal

Anyone with a clean clone gets the same environment and the same running
application by following written steps. `requirements.txt` becomes the final,
fully pinned list, and the run steps (Docker and local) are documented and
checked from a fresh clone.

## Scope

- In scope:
  - Pin the libraries that `requirements.txt` still leaves to the resolver and
    that the code depends on (`pydantic`, imported by `app/schemas.py`, and
    `scipy`, required by scikit-learn).
  - New `docs/REPRODUCIBILITY.md`: run steps with Docker and without Docker,
    how the pins are produced, a clean-clone checklist and known limits.
  - Fix stale statements in `README.md` (the PostgreSQL note, the Python
    version for local setup, the repository tree) and link the new page from
    `README.md` and `docs/APP.md`.
  - Verify the steps from a clean clone and record the result.
  - Make the MySQL host port configurable (`MYSQL_PORT`, default 3306) in `docker-compose.yml` and `.env.example`: the first clean-clone run failed on a machine with a local MySQL on 3306.
- Out of scope:
  - A script that downloads the dataset (the manual download in `data/README.md`
    stays, with its checksum).
  - Publishing the FastAPI service in `docker-compose.yml` (a separate change;
    the steps use `docker compose run -p` meanwhile).
  - The Streamlit UI (still the M0 placeholder) and unit tests (#40; `pytest`
    will be pinned there).
  - Cloud deployment.

## Design

| File | Change |
|---|---|
| `requirements.txt` | Add `pydantic==<x>` and `scipy==<x>`, with the versions that a clean Docker build resolves today (measured in the Verification step). |
| `docs/REPRODUCIBILITY.md` | New. |
| `README.md` | Fix the stale PostgreSQL note, state Python 3.11 for the local setup, add `scripts/` and the new page to the tree, link to the page. |
| `docs/APP.md` | Replace the "To be filled in M6" usage line with a link to the new page. |
| `docker-compose.yml` | Publish MySQL on `${MYSQL_PORT:-3306}`; the default does not change. |
| `.env.example` | Document `MYSQL_PORT` (commented). |

Decisions and reasons:

- **Pin only what is missing, not a full lock file.** Every direct dependency is
  already pinned with `==`. The two gaps are `pydantic` (imported by the code, only
  bounded `<3` by FastAPI) and `scipy` (a scikit-learn dependency with no upper
  bound, and the one most likely to move under a pinned numpy). A full lock file
  would be a second file to keep in step; it can be added later if drift
  appears.
- **Pin the versions that were just tested together,** taken from `pip freeze`
  inside the image built from the current `requirements.txt`. CI installs the
  same file on Python 3.11, so it checks the pins on every pull request.
- **Python 3.11 is the reference** (`.python-version`, CI, Docker). 3.12 is known
  to work (the export of #32 ran on it); 3.13 is not supported by the pinned
  numpy and scikit-learn wheels.
- **Docker is the primary path** because it fixes the interpreter and the system
  libraries (`libgomp1`); the local path is documented for development.
- **The model file is not in Git,** so the steps include the export (about two
  minutes) before the API can serve predictions.

## Acceptance criteria

Copied from issue #46:

- [x] `requirements.txt` pinned (final)
- [x] Run steps documented (local + Docker)
- [x] Clean clone reproduces the environment and app

## Verification

Reference environment: the image built from `develop`.

1. `docker build -t multiclass-ref .` then
   `docker run --rm multiclass-ref pip freeze` and read the `pydantic` and
   `scipy` versions; they go into `requirements.txt`.
2. Clone the branch into an empty folder, copy only
   `data/raw/covtype.data` (checksum in `data/README.md`) and follow
   `docs/REPRODUCIBILITY.md` step by step with no other local file.
3. Expected: `docker compose up --build` starts `app` and a healthy `db`;
   `python scripts/check_imports.py` exits 0 in the container;
   `python src/export_model.py` ends with validation accuracy 0.9520 and macro
   F1 0.9186; `GET /health` returns `model_loaded: true` and
   `db_connected: true`; `POST /predict` with the example of `docs/APP.md`
   returns `cover_type` 2.
4. The CI of the pull request is green with the new pins.

Result (2026-11-17, clean clone of the branch on Windows with Docker Desktop):

- The image built from the pinned file (`pip install` took 89 s). Resolved: `pydantic` 2.14.3 and `scipy` 1.17.1 (both now pinned), `numpy` 1.26.4, `scikit-learn` 1.5.1, `pandas` 2.2.2, `starlette` 0.38.6.
- `docker compose up` started `app` and a healthy `db`.
- `scripts/check_imports.py`: all 24 modules import.
- A `LogisticRegression` fit (it uses `scipy`) ran with the new pin.
- `src/export_model.py`: validation accuracy 0.9520, macro F1 0.9186, serving contract check passed.
- `src/database.py`: the SQLite checks passed and the MySQL connection worked.
- `GET /health`: `model_loaded` and `db_connected` true. `POST /predict` with the example of `docs/APP.md`: `cover_type` 2, confidence 0.95, `prediction_id` 1.
- The first attempt failed because a local MySQL service already used host port 3306. The run passed with the port moved to 3307; `MYSQL_PORT` makes that a setting (checked with `docker compose config`: 3307 with the variable, 3306 by default).
- Not checked: the Streamlit page in a browser (the container started and published port 8501) and the CI run of the pull request.