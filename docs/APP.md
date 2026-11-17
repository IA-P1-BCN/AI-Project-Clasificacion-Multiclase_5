# APP — Application Requirements

> Requirements, architecture and usage of the prediction application. See
> [SPEC.md](../SPEC.md) for the functional and technical specification and
> [DELIVERABLES.md](DELIVERABLES.md) for delivery-level status.

## Contents

- [Functional requirements](#functional-requirements)
- [Architecture](#architecture)
- [Backend API (FastAPI)](#backend-api-fastapi)
- [Model export](#model-export)
- [Database integration](#database-integration)
- [New data collection and retraining pipeline](#new-data-collection-and-retraining-pipeline)
- [Dockerization](#dockerization)
- [Deployment](#deployment)
- [Usage](#usage)

## Functional requirements

1. **Multiclass prediction from cartographic inputs.** Accepts the 10
   quantitative cartographic features (`NUMERIC_FEATURES`), `Wilderness_Area`
   (`1–4`) and `Soil_Type` (`1–40`) defined in
   [DATA_DICTIONARY.md](DATA_DICTIONARY.md), expands the categorical selectors
   into the 44 binary indicators (`BINARY_FEATURES`), and returns the predicted
   `Cover_Type` (`1–7`), its species name (`class_name`), the winning class
   probability (`confidence`), and the 7-class probability distribution
   (`probabilities`).
2. **Decoupled frontend, backend and model pipeline.**
   - **Frontend (`Streamlit`):** [app/main.py](../app/main.py) provides the
     user interface (M0 base environment merged; interactive prediction form
     tracked in #33).
   - **Backend (`FastAPI`):** [app/api.py](../app/api.py),
     [app/serving.py](../app/serving.py) and
     [app/schemas.py](../app/schemas.py) validate inputs and serve `/health`
     and `/predict` (#34).
   - **Exported pipeline (`joblib`):** [src/export_model.py](../src/export_model.py)
     bundles the 54-feature `ColumnTransformer` and the fitted primary
     `RandomForestClassifier` into `models/model.joblib` with versioned metadata
     in `models/model_metadata.json` (#32).
3. **Prediction logging and feedback collection.** Every `POST /predict` call is
   logged on a best-effort basis to the `predictions` table (`prediction_id`),
   and verified ground-truth labels are stored in the `feedback` table via
   [src/database.py](../src/database.py) (#37; feedback endpoint and monitoring
   UI tracked in #35).
4. **New data ingestion and retraining pipeline.** Validated labeled observations
   are stored in `data/processed/new_samples.csv` and used by
   [src/retraining.py](../src/retraining.py) to retrain the pipeline on the
   training partition only (#36).

## Architecture

```
Streamlit (frontend, app/main.py)
        │
        ▼
FastAPI (backend, app/api.py + app/schemas.py)
        ├──► Serving layer (app/serving.py) ──► Pipeline (models/model.joblib, #32)
        │                                                │
        │                                                ▼
        │                                     Multiclass prediction (1–7)
        ▼
Database (src/database.py: MySQL 8.0 in Docker / SQLite local fallback, #37)
        │
        ▼
Retraining pipeline (src/retraining.py: train-only augmentation, #36)
```

| Component | Module | Responsibility |
|---|---|---|
| Frontend UI | [app/main.py](../app/main.py) | Streamlit web interface on port `8501` (#1 base, #33 prediction form). |
| HTTP API | [app/api.py](../app/api.py), [app/schemas.py](../app/schemas.py) | Pydantic input validation, `GET /health` and `POST /predict` on port `8000` (#34). |
| Model serving | [app/serving.py](../app/serving.py) | Loads `models/model.joblib`, expands 12 compact fields into 54 `FEATURES`, computes 7-class probabilities (#34). |
| Pipeline export | [src/export_model.py](../src/export_model.py) | Fits the `ColumnTransformer` + `RandomForestClassifier` pipeline on `X_train, y_train` only and writes `models/model.joblib` + `models/model_metadata.json` (#32). |
| Persistence | [src/database.py](../src/database.py) | Creates and queries the `predictions` and `feedback` tables in MySQL 8.0 or local SQLite (#37). |
| Retraining | [src/retraining.py](../src/retraining.py) | Validates and deduplicates new labeled rows in `data/processed/new_samples.csv` and retrains without data leakage (#36). |

## Backend API (FastAPI)

Issue #34. Run it from the project root:

```bash
uvicorn app.api:app --port 8000
```

Interactive documentation (Swagger): <http://localhost:8000/docs>.

| Endpoint | What it does |
|---|---|
| `GET /health` | Service status, whether a model is loaded and whether the database is reachable (`db_connected`, `db_detail`). |
| `POST /predict` | Validates the input and returns the predicted cover type with its confidence. |
| `POST /feedback` | Stores the observed true cover type for a past prediction (#35). |
| `GET /metrics` | Returns basic production-monitoring metrics from the collected feedback (#35). |

Example request body (`POST /predict`):

```json
{
  "Elevation": 2900, "Aspect": 150, "Slope": 12,
  "Horizontal_Distance_To_Hydrology": 250,
  "Vertical_Distance_To_Hydrology": 40,
  "Horizontal_Distance_To_Roadways": 2300,
  "Hillshade_9am": 215, "Hillshade_Noon": 225, "Hillshade_3pm": 140,
  "Horizontal_Distance_To_Fire_Points": 1900,
  "Wilderness_Area": 1, "Soil_Type": 29
}
```

Example response (illustrative values):

```json
{
  "cover_type": 2,
  "class_name": "Lodgepole Pine",
  "confidence": 0.81,
  "probabilities": {
    "Spruce/Fir": 0.12, "Lodgepole Pine": 0.81, "Ponderosa Pine": 0.03,
    "Cottonwood/Willow": 0.0, "Aspen": 0.02, "Douglas-fir": 0.01, "Krummholz": 0.01
  }
}
```

### Input validation

The numeric fields use the dataset column names. The bounds are physical
limits, not the observed min/max, so a valid new observation is not rejected.

| Field | Allowed values |
|---|---|
| `Elevation` | 0 to 5000 (m) |
| `Aspect` | 0 to 360 (degrees) |
| `Slope` | 0 to 90 (degrees) |
| `Horizontal_Distance_To_Hydrology`, `Horizontal_Distance_To_Roadways`, `Horizontal_Distance_To_Fire_Points` | 0 to 10000 (m) |
| `Vertical_Distance_To_Hydrology` | -500 to 1000 (m) |
| `Hillshade_9am`, `Hillshade_Noon`, `Hillshade_3pm` | 0 to 255 |
| `Wilderness_Area` | integer 1 to 4 |
| `Soil_Type` | integer 1 to 40 |

A missing, extra or out-of-range field returns HTTP 422 with the failing field.
The API expands `Wilderness_Area` and `Soil_Type` into the 44 one-hot columns,
so exactly one of each is active, as in the dataset.

### Model file

The model is loaded once at startup from `MODEL_PATH` (default
`models/model.joblib`). It must take a DataFrame with the 54 original features
in the training order and expose `predict_proba` and `classes_`; any feature
engineering or scaling lives inside the exported pipeline (#32). Classes can be
Cover_Type (1-7) or the encoded labels (0-6) of #15.

If the file is missing or invalid the API still starts: `/health` returns
`model_loaded: false` with the reason, and `/predict` returns HTTP 503.

## Feedback collection and monitoring

Issue #35. The system closes the loop between a prediction and its observed
outcome, and exposes how the deployed model is doing on real data. Feedback is
stored in the `feedback` table (#37), linked to the `predictions` row it refers
to.

### `POST /feedback`

Records the true cover type for a prediction returned earlier by `POST /predict`
(the response of which includes a `prediction_id`). The stored row keeps a UTC
timestamp, the true class and whether the original prediction was correct.

Request body:

```json
{ "prediction_id": 1, "true_cover_type": 2, "comment": "Verified in the field." }
```

| Field | Allowed values |
|---|---|
| `prediction_id` | integer ≥ 1 — the id returned by `POST /predict` |
| `true_cover_type` | integer 1 to 7 |
| `comment` | optional free text, up to 1000 characters |

Response:

```json
{
  "feedback_id": 1, "prediction_id": 1,
  "true_cover_type": 2, "true_class_name": "Lodgepole Pine",
  "predicted_cover_type": 2, "is_correct": true
}
```

| Status | When |
|---|---|
| `200` | Feedback stored. |
| `404` | `prediction_id` does not exist. |
| `422` | Missing, extra or out-of-range field (e.g. `true_cover_type` outside 1-7). |
| `503` | Database unreachable; the feedback was not stored. |

### `GET /metrics`

Aggregates the collected feedback into basic production metrics. Counters start
at zero and ratios are `null` until there is data, so the endpoint works from
the first request.

```json
{
  "predictions_total": 2, "feedback_total": 2, "feedback_coverage": 1.0,
  "correct_total": 1, "live_accuracy": 0.5, "average_confidence": 0.9,
  "per_class": [
    { "cover_type": 1, "class_name": "Spruce/Fir", "feedback_count": 1, "correct": 0, "accuracy": 0.0 },
    { "cover_type": 2, "class_name": "Lodgepole Pine", "feedback_count": 1, "correct": 1, "accuracy": 1.0 }
  ]
}
```

- **`live_accuracy`** — accuracy measured on labelled feedback (`correct_total /
  feedback_total`); the production counterpart of the offline accuracy in
  `docs/MODELING.md`.
- **`feedback_coverage`** — share of predictions that received feedback.
- **`average_confidence`** — mean model confidence of the predictions that were
  given feedback.
- **`per_class`** — feedback count and accuracy per true `Cover_Type` (1-7), to
  spot which classes degrade in production.

Reproduce the storage and metrics checks without the server:

```bash
python src/database.py
```

## Model export

Issue #32. Reproduce from the project root (about two minutes on 8 CPU cores):

```bash
python src/export_model.py
```

It writes two git-ignored files under `models/`; nothing there is committed,
so every environment that serves the model runs the command once.

| File | Content |
|---|---|
| `models/model.joblib` | The fitted scikit-learn `Pipeline` (`joblib`, `compress=3`), loaded by the API. |
| `models/model_metadata.json` | Model version, creation time, SHA-256 and size of the model file, library versions, hyperparameters, rows used, validation metrics, the 54 feature names and the label mapping. |

- **Pipeline:** `preprocessor` -> `model`. The preprocessor selects the 54
  `FEATURES` by name and passes them through unchanged (a Random Forest needs no
  scaling); the model is the primary model of the shortlist (#23),
  `RandomForestClassifier(n_estimators=100, random_state=42)`, built by
  `random_forest.build_model()`.
- **Untuned.** Tuning (#29) is not merged yet, so version `0.1.0` uses the
  default hyperparameters of #21. Once #29 or #17 change the configuration,
  bump `MODEL_VERSION` in `src/export_model.py` and re-run the export.
- **No leakage:** fitted on the train set of the canonical split
  (`split_train_val_test`, #16; 406,708 rows) only. The validation set is only
  predicted; the test set is not used (final metrics belong to #25).
- **Label mapping:** the model is trained on `Cover_Type` (1-7), so column `i`
  of `predict_proba` is `Cover_Type` `i + 1`. The mapping with the class names
  is stored in `label_mapping` of the metadata file.
- **Versioning:** `model_version` plus `model_sha256` in the metadata identify
  one exact model file; compare the hash to check which model is deployed.
- **Self-check:** the script reloads the file through
  `app.serving.load_model()` and fails unless it loads and reproduces the
  in-memory probabilities on 1,000 validation rows.

Observed (version `0.1.0`, Python 3.12.10, scikit-learn 1.5.1):

| Measure | Value |
|---|---|
| Validation accuracy (87,152 rows) | 0.9520 |
| Validation macro F1 | 0.9186 |
| Size of `models/model.joblib` | 136.3 MB |
| Time for `load_model()` plus one prediction | about 10 s |

The example request of the *Backend API* section, passed to
`app.serving.predict()`, returns `cover_type` 2 (Lodgepole Pine) with
`confidence` 0.95.

Load the file with the same scikit-learn version it was exported with
(`requirements.txt` pins 1.5.1; the metadata records the versions used).


## Database integration

Issue #37. Verify the schema, read/write operations and constraints from the
project root:

```bash
docker compose up -d --build
docker compose exec app python src/database.py
```

The script runs its read/write checks on a temporary SQLite file and, when
`DATABASE_URL` is set (as in the `app` container), also connects to that
database and prints its row counts; it exits with an error if it cannot
connect.

### Database choice and configuration

The project uses **MySQL 8.0** (`mysql:8.0` in `docker-compose.yml`, connected
via `PyMySQL==1.1.1`, which needs `cryptography==43.0.1` for the MySQL 8
login) as the production relational database, with an automatic
**SQLite** fallback (`sqlite:///data/processed/multiclass.db`) when
`DATABASE_URL` is unset or points to a `sqlite:///` URL during local script
execution.

Environment variables (see `.env.example`):

| Variable | Default in `docker-compose.yml` | Purpose |
|---|---|---|
| `MYSQL_DATABASE` | `multiclass` | Database created on container startup |
| `MYSQL_USER` | `app` | Application database user |
| `MYSQL_PASSWORD` | `app` | Application database password |
| `MYSQL_ROOT_PASSWORD` | `root` | MySQL root password (used by healthcheck) |
| `MYSQL_PORT` | `3306` | Host port published for MySQL; set it (e.g. `3307`) if 3306 is taken |
| `DATABASE_URL` | `mysql+pymysql://app:app@db:3306/multiclass` | Connection URL read by `src/database.py` |

### Schema

`init_db()` creates two relational tables:

1. **`predictions`** — one row per `POST /predict` call:
   - `id` (`INT AUTO_INCREMENT PRIMARY KEY` / `INTEGER PRIMARY KEY AUTOINCREMENT`)
   - `created_at_utc` (`VARCHAR(32) NOT NULL`) — ISO-8601 UTC timestamp
   - `model_version` (`VARCHAR(32) NOT NULL`) — version string (e.g. `0.1.0`)
   - `Elevation`, `Aspect`, `Slope`, `Horizontal_Distance_To_Hydrology`,
     `Vertical_Distance_To_Hydrology`, `Horizontal_Distance_To_Roadways`,
     `Hillshade_9am`, `Hillshade_Noon`, `Hillshade_3pm`,
     `Horizontal_Distance_To_Fire_Points` (`DOUBLE NOT NULL`)
   - `Wilderness_Area` (`INT NOT NULL`, 1–4)
   - `Soil_Type` (`INT NOT NULL`, 1–40)
   - `predicted_cover_type` (`INT NOT NULL`, 1–7)
   - `predicted_class_name` (`VARCHAR(64) NOT NULL`)
   - `confidence` (`DOUBLE NOT NULL`)
   - `probabilities_json` (`TEXT NOT NULL`) — JSON object of the 7 class probabilities
2. **`feedback`** — user-verified ground truth linked to a prediction:
   - `id` (`INT AUTO_INCREMENT PRIMARY KEY` / `INTEGER PRIMARY KEY AUTOINCREMENT`)
   - `prediction_id` (`INT NOT NULL`, `FOREIGN KEY REFERENCES predictions(id)`)
   - `created_at_utc` (`VARCHAR(32) NOT NULL`)
   - `true_cover_type` (`INT NOT NULL`, 1–7)
   - `true_class_name` (`VARCHAR(64) NOT NULL`)
   - `is_correct` (`INT NOT NULL`, `1` when `true_cover_type == predicted_cover_type`, `0` otherwise)
   - `comment` (`TEXT`)

### Read / write API (`src/database.py`)

| Function | Purpose |
|---|---|
| `init_db(db_url=None)` | Create the `predictions` and `feedback` tables if missing. |
| `save_prediction(request, prediction, model_version="0.1.0", db_url=None) -> int` | Insert a prediction row and return `prediction_id`. Called automatically by `POST /predict`. |
| `get_prediction(prediction_id, db_url=None) -> dict \| None` | Fetch one prediction by ID (deserializing `probabilities`). |
| `list_predictions(limit=100, db_url=None) -> list[dict]` | List the most recent predictions. |
| `save_feedback(prediction_id, true_cover_type, comment=None, db_url=None) -> int` | Validate `true_cover_type` (`1..7`) and `prediction_id`, compute `is_correct`, and insert a feedback row. |
| `list_feedback(limit=100, db_url=None) -> list[dict]` | Join `feedback` with `predictions` so monitoring (#35) and retraining (#36) have full feature + label rows. |
| `db_status(db_url=None) -> dict` | Report connectivity and row counts (used by `GET /health`). |

If the database is unreachable, `POST /predict` still answers, with
`prediction_id: null`; the reason is logged and shown in `/health` as
`db_detail`. Rows survive `docker compose down` in the `db_data` volume
(`docker compose down -v` deletes them).

## New data collection and retraining pipeline

Issue #36. Verify and reproduce from the project root:

```bash
docker compose exec app python src/retraining.py
```

Run a full retraining evaluation against the canonical dataset and any samples
stored in `data/processed/new_samples.csv` (about 2 minutes; it reports the
validation metrics and does not replace `models/model.joblib`):

```bash
docker compose exec app python src/retraining.py --full
```

With 2 new samples (2026-11-16): `train_total=406,710`, validation accuracy
`0.9520`, macro F1 `0.9183`.

### Storage format

Newly collected labeled observations are stored in
`data/processed/new_samples.csv` (git-ignored; `data/raw/covtype.data` remains
immutable). The CSV uses a header with the 55 canonical `COLUMNS` (`FEATURES` +
`Cover_Type` in `1..7`), all stored as `int64`.

### Ingestion path (`src/retraining.py`)

`ingest_samples(samples, path=NEW_DATA_PATH)` accepts:

1. **Compact 13-field records** (`dict`, `list[dict]`, or `DataFrame` with the
   10 `NUMERIC_FEATURES`, `Wilderness_Area` in `1..4`, `Soil_Type` in `1..40`
   and `Cover_Type` in `1..7`, matching the API payload of `#34`), which
   `expand_compact_sample()` converts into the 55 one-hot-expanded columns.
2. **Full 55-column records** (`COLUMNS` in order).

Before writing to disk, `validate_samples()` enforces:

- All 55 `COLUMNS` present with zero nulls (`NaN`) and integer values only
  (the numeric features of a compact record are rounded to whole units).
- Physical bounds on the 10 numeric features matching `app/schemas.py`
  (`Elevation` 0–5000, `Aspect` 0–360, `Slope` 0–90, horizontal distances
  0–10000, `Vertical_Distance_To_Hydrology` -500 to 1000, `Hillshade_*` 0–255).
- Binary values `{0, 1}` on the 44 indicators, with **exactly one active
  `Wilderness_Area` and one active `Soil_Type` per row** (#12).
- `Cover_Type` in `1..7` (#15).

Valid incoming rows are concatenated with existing stored rows and passed
through `data_cleaning.clean()` (#12) to drop exact duplicates before saving.

```python
from retraining import ingest_samples, load_new_samples

ingest_samples({
    "Elevation": 2950, "Aspect": 160, "Slope": 14,
    "Horizontal_Distance_To_Hydrology": 240,
    "Vertical_Distance_To_Hydrology": 35,
    "Horizontal_Distance_To_Roadways": 2100,
    "Hillshade_9am": 218, "Hillshade_Noon": 228, "Hillshade_3pm": 142,
    "Horizontal_Distance_To_Fire_Points": 1850,
    "Wilderness_Area": 1, "Soil_Type": 29,
    "Cover_Type": 2,
})
stored_df = load_new_samples()
```

### Retraining procedure (no data leakage)

1. **Fixed evaluation splits:** `prepare_retraining_splits(raw_df, new_samples_df)`
   splits the original cleaned dataset with `split_train_val_test` (#16,
   `random_state=42`) **first**, keeping `validation` (87,152 rows) and `test`
   (87,152 rows) fixed across retraining runs.
2. **Held-out leakage guard:** any incoming row whose 54 features match an
   existing `validation` or `test` row is filtered out before training, and
   exact duplicates are removed via `clean()`.
3. **Train-only augmentation & quality gate:** `retrain_pipeline(...)` appends
   the remaining new samples exclusively to `(X_train, y_train)`, fits the
   pipeline (`export_model.fit_pipeline`), and evaluates on the fixed
   `validation` set. When `promote=True` and validation `macro_f1 >= min_macro_f1`
   (default `0.90`), it exports the updated `models/model.joblib` and
   `models/model_metadata.json` (recording `train_base`, `new_samples_added`,
   `train_total` and `validation` row counts).


## Dockerization

The containerized environment is defined in [Dockerfile](../Dockerfile) and
[docker-compose.yml](../docker-compose.yml) (#1, #37; multi-service frontend +
backend process orchestration and detailed Docker guide tracked in #38 and
#47):

| Service | Container | Image / Build | Port | Purpose |
|---|---|---|---|---|
| `app` | `multiclass_app` | Built from [Dockerfile](../Dockerfile) (`python:3.11-slim` + `libgomp1` + [requirements.txt](../requirements.txt)) | `8501:8501` | Application runtime with mounted `./app`, `./src`, `./data` and `./models` volumes |
| `db` | `multiclass_db` | `mysql:8.0` | `${MYSQL_PORT:-3306}:3306` (host port configurable) | Relational database for `predictions` and `feedback`, backed by persistent volume `db_data` |

The `app` service waits for `db` to pass its `mysqladmin ping` TCP healthcheck
(`condition: service_healthy`) before starting.

## Deployment

Issue #39. The application is deployed to **Hugging Face Spaces** (Docker SDK).
Verify the cloud entrypoint, model provisioning (including the `MODEL_URL`
download path), database initialization, FastAPI endpoints and Streamlit
readiness from the project root:

```bash
docker run --rm -v "$PWD:/app" -w /app -e DATABASE_URL= \
  ai-project-clasificacion-multiclase_5-app python scripts/start_cloud.py --check
```

### Cloud provider choice: Hugging Face Spaces

The exported model ([Model export](#model-export)) is a 100-tree
`RandomForestClassifier` with `max_depth=None`: 136.3 MB on disk and
**~1.17 GiB of RAM** once FastAPI + Streamlit are running (measured with
`docker stats` on 2026-11-17). That rules out every free tier with 512 MB.

| Provider | Free RAM | Real model fits | Decision |
|---|---|---|---|
| **Hugging Face Spaces** (Docker SDK) | 16 GB, 2 vCPU | Yes | **Chosen** |
| Render (Docker web service, [render.yaml](../render.yaml)) | 512 MB | No (would need the synthetic bootstrap model or a smaller model) | Kept as alternative |
| Streamlit Community Cloud | ~1 GB | Borderline; no FastAPI process, 100 MB GitHub file limit | Discarded |
| Vercel | Serverless (250 MB bundle) | No; no long-running Streamlit/WebSocket server | Discarded |

Free Spaces sleep after ~48 h without traffic and their disk is ephemeral:
the SQLite database (predictions and feedback) is reset on every restart or
rebuild. Point `DATABASE_URL` to an external MySQL 8.0 server to persist it.

### Cloud architecture

The Space repository holds only two files, kept in this repository under
[deploy/huggingface/](../deploy/huggingface/):

- [deploy/huggingface/README.md](../deploy/huggingface/README.md): Space card
  with the configuration front matter (`sdk: docker`, `app_port: 7860`).
- [deploy/huggingface/Dockerfile](../deploy/huggingface/Dockerfile): builds on
  `python:3.11-slim`, runs as UID 1000 (required by Spaces), clones this
  public GitHub repository at `REPO_REF` (default `develop`), installs
  [requirements.txt](../requirements.txt) and starts
  [scripts/start_cloud.py](../scripts/start_cloud.py).

This keeps binary files (`docs/figures/*.png`, `*.joblib`) out of the Space
git repository and leaves the project [Dockerfile](../Dockerfile) (#38)
untouched. At startup, `scripts/start_cloud.py`:

1. **Provisions the model (`ensure_cloud_model`).** An existing `MODEL_PATH`
   is used as-is. Otherwise, if `MODEL_URL` is set, the exported model is
   downloaded to `MODEL_PATH`, checked against `MODEL_SHA256` (written to a
   temporary file and renamed only if the checksum matches) and validated with
   `app.serving.load_model`; any failure stops the container. Only when
   `MODEL_URL` is unset does it fit a synthetic 30-tree bootstrap model
   (`model_version = "0.1.0-cloud-bootstrap"`) and log a warning: its
   predictions are **not** those of the project model.
2. **Initializes the database** (`src/database.py::init_db`).
3. **Starts FastAPI** (`uvicorn app.api:app`) on `127.0.0.1:$API_PORT`, waits
   for `GET /health`, then runs **Streamlit** in the foreground on
   `0.0.0.0:$PORT` (`SERVICE_ROLE=all`). `SERVICE_ROLE=api` / `app` runs a
   single service.

The model is hosted in a Hugging Face **model** repository, which stores large
files natively and serves them at
`https://huggingface.co/<owner>/<model-repo>/resolve/main/model.joblib`.

### Configuration and environment variables

Runtime settings are read from the environment. [.env.example](../.env.example)
lists the local Compose variables; the Space
[Dockerfile](../deploy/huggingface/Dockerfile) sets the cloud defaults and
the Space settings add the model variables:

| Variable | Default | Used by | Description |
|---|---|---|---|
| `SERVICE_ROLE` | `all` | [scripts/start_cloud.py](../scripts/start_cloud.py) | `all` (FastAPI + Streamlit in one container), `api` (FastAPI only), or `app` (Streamlit only). |
| `PORT` | `7860` (Space) / `8501` (`8000` when `SERVICE_ROLE=api`) | [scripts/start_cloud.py](../scripts/start_cloud.py) | Public HTTP port; must match `app_port` in the Space card. Render injects it. |
| `API_PORT` | `8000` | [scripts/start_cloud.py](../scripts/start_cloud.py) | Loopback port of FastAPI in `SERVICE_ROLE=all`. |
| `API_URL` | `http://127.0.0.1:8000` (cloud) / `http://api:8000` (Compose) | [app/main.py](../app/main.py) | Base URL of the FastAPI backend consumed by the Streamlit UI. |
| `MODEL_PATH` | `models/model.joblib` | [app/serving.py](../app/serving.py) | Path to the serialized scikit-learn `Pipeline` (#32). |
| `MODEL_URL` | unset | [scripts/start_cloud.py](../scripts/start_cloud.py) | URL of the exported `model.joblib`, downloaded when `MODEL_PATH` is missing. |
| `MODEL_SHA256` | unset | [scripts/start_cloud.py](../scripts/start_cloud.py) | Expected SHA-256 of the download (`model_sha256` in `models/model_metadata.json`). Recommended. |
| `MODEL_METADATA_URL` | unset | [scripts/start_cloud.py](../scripts/start_cloud.py) | Optional URL of `model_metadata.json`, saved next to the model. |
| `HF_TOKEN` | unset | [scripts/start_cloud.py](../scripts/start_cloud.py) | Optional Bearer token, only if the model repository is private. Set it as a Space **secret**. |
| `REPO_REF` | `develop` | [deploy/huggingface/Dockerfile](../deploy/huggingface/Dockerfile) (build arg) | Git branch or tag of this repository cloned into the Space. |
| `DATABASE_URL` | `mysql+pymysql://app:app@db:3306/multiclass` (Docker) / `sqlite:///data/processed/multiclass.db` (local & cloud) | [src/database.py](../src/database.py) | Database connection string (#37). |
| `MYSQL_DATABASE` | `multiclass` | `db` container | MySQL database created on startup. |
| `MYSQL_USER` | `app` | `db` container | MySQL application user. |
| `MYSQL_PASSWORD` | `app` | `db` container | MySQL application password. |
| `MYSQL_ROOT_PASSWORD` | `root` | `db` container | MySQL root password for healthchecks. |
| `MYSQL_PORT` | `3306` | `docker-compose.yml` | Host port published for the `db` service (`${MYSQL_PORT:-3306}:3306`); change it if 3306 is taken locally. |

### Readiness and health checks

- **Streamlit UI health check (`GET /_stcore/health`):** returns `ok` (HTTP 200).
  Spaces mark the app as *Running* once `app_port` answers.
- **FastAPI health check (`GET /health`):** returns HTTP 200 with `status`
  (`"ok"`), `model_loaded` (`bool`), `db_connected` (`bool`), `detail` and
  `db_detail`. In `SERVICE_ROLE=all` it is only reachable inside the container.

### Step-by-step deployment on Hugging Face Spaces

1. **Upload the model.** Sign in to <https://huggingface.co>, click
   **New** → **Model**, create a public repository (e.g.
   `<owner>/covertype-random-forest`) and, in **Files** → **Add file** →
   **Upload files**, upload `models/model.joblib` and
   `models/model_metadata.json` produced by `python src/export_model.py`.
2. **Create the Space.** **New** → **Space**, SDK **Docker** → **Blank**,
   hardware **CPU basic (free)**, visibility public.
3. **Add the Space files.** In the Space **Files** tab, upload
   [deploy/huggingface/README.md](../deploy/huggingface/README.md) and
   [deploy/huggingface/Dockerfile](../deploy/huggingface/Dockerfile) to the
   root, replacing the generated `README.md`.
4. **Configure variables** in **Settings** → **Variables and secrets**:
   - `MODEL_URL` = `https://huggingface.co/<owner>/covertype-random-forest/resolve/main/model.joblib`
   - `MODEL_METADATA_URL` = `https://huggingface.co/<owner>/covertype-random-forest/resolve/main/model_metadata.json`
   - `MODEL_SHA256` = value of `model_sha256` in `models/model_metadata.json`
   - (optional) `REPO_REF` = branch to deploy, e.g. `feature/39-cloud-deployment`
     before the merge into `develop`.
5. **Build.** The Space builds automatically; the logs must show
   `[start_cloud] model status: downloaded` and
   `[start_cloud] FastAPI healthy at http://127.0.0.1:8000`. The app is public at
   `https://huggingface.co/spaces/<owner>/<space>` (direct URL
   `https://<owner>-<space>.hf.space`).
6. **Redeploy after a merge.** The Space does not watch GitHub: use
   **Settings** → **Factory rebuild** to clone the latest `REPO_REF`.

### Alternative: Render

[render.yaml](../render.yaml) remains available (**New +** → **Blueprint** on
<https://dashboard.render.com>). On the free plan (512 MB) the real model does
not fit, so the container serves the synthetic bootstrap model unless a paid
instance with more memory is used together with `MODEL_URL` and `MODEL_SHA256`.

## Usage

This section is the quick start. The pinned environment, the full run steps
and the clean-clone checklist are in [REPRODUCIBILITY.md](REPRODUCIBILITY.md),
which is the reference if the two ever differ.

### 1. Prerequisite: raw dataset and exported model

Place `covtype.data` under `data/raw/covtype.data` (see
[data/README.md](../data/README.md)) and generate the model artifact once (about
2 minutes):

```bash
# With Docker Compose:
docker compose up -d --build
docker compose exec app python src/export_model.py

# Or locally in a Python 3.11 virtual environment:
python src/export_model.py
```

This creates `models/model.joblib` and `models/model_metadata.json` (both
git-ignored).

### 2. Run with Docker Compose

```bash
docker compose up --build
```

- Streamlit UI: <http://localhost:8501>
- Stop containers (keeping MySQL data in `db_data`): `docker compose down`
- Run the FastAPI backend: `docker-compose.yml` only publishes port `8501`, so
  start the API in a one-off container that publishes port `8000` to the host
  (it reuses the `db` service and the mounted `models/`):

```bash
docker compose run --rm -p 8000:8000 app uvicorn app.api:app --host 0.0.0.0 --port 8000
```

The API is then reachable at <http://localhost:8000> (Swagger UI at `/docs`)
and the requests of [4. Query the API](#4-query-the-api) work from the host.
A permanent `api` service in Compose is tracked in #38.

### 3. Run locally without Docker

Requires **Python 3.11** (the reference version; with 3.13 the pinned
dependencies do not install).

```bash
python3.11 -m venv .venv           # Windows: py -3.11 -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Export the model artifact (if models/model.joblib is not present yet)
python src/export_model.py

# Start the FastAPI backend (http://localhost:8000, Swagger UI at /docs)
uvicorn app.api:app --port 8000

# In a second terminal, start the Streamlit frontend (http://localhost:8501)
streamlit run app/main.py
```

When `DATABASE_URL` is not set locally, [src/database.py](../src/database.py)
automatically persists predictions and feedback in
`data/processed/multiclass.db` (SQLite).

### 4. Query the API

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "Elevation": 2900, "Aspect": 150, "Slope": 12,
    "Horizontal_Distance_To_Hydrology": 250,
    "Vertical_Distance_To_Hydrology": 40,
    "Horizontal_Distance_To_Roadways": 2300,
    "Hillshade_9am": 215, "Hillshade_Noon": 225, "Hillshade_3pm": 140,
    "Horizontal_Distance_To_Fire_Points": 1900,
    "Wilderness_Area": 1, "Soil_Type": 29
  }'
```
