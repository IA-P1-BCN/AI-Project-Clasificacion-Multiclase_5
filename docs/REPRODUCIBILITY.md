# Reproducibility

How to get the same environment and the same running application from a clean
clone. Ticket #46. Docker is the recommended path; the local path is for
development.

## What you need

| | Docker path | Local path |
|---|---|---|
| Software | Docker with Compose v2 | Python 3.11 |
| Dataset | `data/raw/covtype.data` (see below) | same |
| Disk | a few GB for the images, 72 MB for the dataset | a few GB for the packages |

Python 3.11 is the reference version (`.python-version`, CI and the Docker
image). 3.12 is known to work (the export of #32 ran on it). 3.13 is **not**
supported: the pinned `numpy` and `scikit-learn` have no wheels for it.

## 1. Get the code and the dataset

```bash
git clone https://github.com/IA-P1-BCN/AI-Project-Clasificacion-Multiclase_5.git
cd AI-Project-Clasificacion-Multiclase_5
```

The dataset is not in Git. Download `covertype.zip` from
<https://archive.ics.uci.edu/static/public/31/covertype.zip>, extract
`covtype.data.gz`, decompress it and place `covtype.data` in `data/raw/`.
Check the file against the checksum of `data/README.md`:

```bash
sha256sum data/raw/covtype.data                  # Linux / macOS
Get-FileHash data\raw\covtype.data -Algorithm SHA256   # Windows PowerShell
```

Expected: `0a9371cef7c964b5475d6053cc3e0894a5aa6f65ad1ed3ecb01c45aa96217945`.

## 2. Run with Docker (recommended)

What each service and volume does, and the fixes for common errors, are in [DOCKER.md](DOCKER.md).

```bash
cp .env.example .env            # optional; the defaults already work
docker compose up --build -d
docker compose ps               # db and api healthy, app running
```

Open the Streamlit app at <http://localhost:8501>. It is still the M0
placeholder; the real interface belongs to M6.

`data/` and `models/` are mounted from your folder (the image does not contain
them), so the dataset of step 1 is visible inside the container.

**Train and export the model** (about two minutes). `models/model.joblib` is not
in Git, so this is needed once per clone:

```bash
docker compose exec app python src/export_model.py
```

It ends with the validation metrics (accuracy 0.9520, macro F1 0.9186 for
version `0.1.0`) and a self-check of the exported file.

**Load the model in the API.** Compose already started the API (`api` service on
port 8000), but without a model, and it loads the model only at startup. Restart
it and wait until it is healthy (20 to 40 seconds):

```bash
docker compose restart api
docker compose ps               # wait for api to show (healthy)
```

Then check it:

```bash
curl http://localhost:8000/health
```

PowerShell: `Invoke-RestMethod http://localhost:8000/health`. Expected:
`"status": "ok"`, `"model_loaded": true`, `"db_connected": true`. Swagger is at
<http://localhost:8000/docs>; a request example for `POST /predict` is in
[APP.md](APP.md).

Stop with `docker compose down`. The database
rows stay in the `db_data` volume; `docker compose down -v` deletes them.

## 3. Run locally without Docker

```bash
python3.11 -m venv .venv                 # Windows: py -3.11 -m venv .venv
source .venv/bin/activate                # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/check_imports.py          # every module imports
python src/export_model.py               # trains and writes models/model.joblib
uvicorn app.api:app --port 8000          # API
streamlit run app/main.py                # placeholder app (other terminal)
```

Without `DATABASE_URL` the API stores predictions in a local SQLite file
(`data/processed/multiclass.db`). To use the MySQL of Compose, start it with
`docker compose up -d db` and set
`DATABASE_URL=mysql+pymysql://app:app@localhost:3306/multiclass` (use the port of `MYSQL_PORT` if you changed it).

## 4. The pinned environment

`requirements.txt` pins every library the code uses with `==`, including
`pydantic` and `scipy`, which pip would otherwise choose freely. The other
packages that pip installs (for example `starlette` or `threadpoolctl`) come as
dependencies of the pinned ones, within the ranges those libraries allow.

To see the exact set that a clean build resolves:

```bash
docker build -t multiclass-ref .
docker run --rm multiclass-ref pip freeze
```

To change a pin: edit `requirements.txt`, run `docker compose up --build`, run
the checklist below and let CI confirm it on the pull request. A model saved
with `joblib` must be loaded with the same scikit-learn version that exported
it, so after changing `scikit-learn` or `numpy` re-run the export.

## 5. Clean-clone checklist

Run it in an empty folder with only `data/raw/covtype.data` copied in.

| # | Step | Expected |
|---|---|---|
| 1 | `docker compose up --build -d` | The images build; `docker compose ps` shows `db` and `api` healthy and `app` running |
| 2 | `docker compose exec app python scripts/check_imports.py` | Ends with `All ... modules import correctly.` |
| 3 | `docker compose exec app python src/export_model.py` | Validation accuracy 0.9520, macro F1 0.9186 |
| 4 | `docker compose exec app python src/database.py` | Read/write checks pass and the MySQL row counts print |
| 5 | `docker compose restart api`, wait for `(healthy)`, then `GET /health` | `model_loaded` and `db_connected` are `true` |
| 6 | `POST /predict` with the example of [APP.md](APP.md) | `cover_type` 2 (Lodgepole Pine) |
| 7 | <http://localhost:8501> | The Streamlit placeholder loads |

## 6. Known limits

- The dataset is a manual download (step 1); there is no download script.
- Compose publishes MySQL on host port 3306. If that port is taken (a local MySQL service, for example) set `MYSQL_PORT=3307` in `.env` or in the shell before `docker compose up`. The app reaches the database over the internal network, so it is not affected.
- The model is trained on your machine. Its file is not byte-identical across
  different library versions, so compare `model_sha256` in
  `models/model_metadata.json` only between identical environments.
- The Docker image does not contain `data/`, `models/` or `docs/`
  (`.dockerignore`); run it through Compose, which mounts the first two.
- On Windows, a security policy such as Application Control can block a
  scikit-learn DLL when you run locally. Use the Docker path in that case.
- The API loads the model only at startup: after a new export run `docker compose restart api`.
- The unit tests of #40 will need `pytest`, which is not pinned yet.