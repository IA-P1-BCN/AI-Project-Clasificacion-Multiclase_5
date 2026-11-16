# APP — Application Requirements

> Requirements and design of the prediction application.

## Functional requirements

- Accepts input data and returns a multiclass prediction.
- Streamlit (frontend) + FastAPI (backend) + model pipeline.
- Feedback collection system to monitor production performance.
- Pipeline to collect new data for future retraining.

## Architecture

```
Streamlit (frontend) ──► FastAPI (backend) ──► model pipeline ──► prediction
                              │
                              ▼
                        Database (MySQL/MongoDB)
```

## Backend API (FastAPI)

Issue #34. Run it from the project root:

```bash
uvicorn app.api:app --port 8000
```

Interactive documentation (Swagger): <http://localhost:8000/docs>.

| Endpoint | What it does |
|---|---|
| `GET /health` | Service status and whether a model is loaded. |
| `POST /predict` | Validates the input and returns the predicted cover type with its confidence. |

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
python src/database.py
```

### Database choice and configuration

The project uses **MySQL 8.0** (`mysql:8.0` in `docker-compose.yml`, connected
via `PyMySQL==1.1.1`) as the production relational database, with an automatic
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

## Dockerization

- `Dockerfile` + `docker-compose.yml`
- Services: app (backend + frontend), database (optional)

## Deployment

- Cloud target: Render / Vercel / AWS (to be decided in M6).

## Usage

```bash
docker compose up
```

_To be filled in M6._
