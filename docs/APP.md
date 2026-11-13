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
