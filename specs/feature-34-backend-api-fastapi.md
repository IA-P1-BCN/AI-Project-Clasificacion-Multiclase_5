# Spec: feature/34-backend-api-fastapi

| | |
|---|---|
| Issue | #34 - [M6] Backend API (FastAPI) |
| Milestone | M6 |
| Branch | `feature/34-backend-api-fastapi` (from `develop`) |
| Owner | @Leandroletoile |
| Depends on | #32 (pipeline export, not merged yet: this branch builds against its contract), M0 environment (merged) |

## Goal

Expose the trained model through a FastAPI backend: an HTTP endpoint that
validates the input and returns the predicted `Cover_Type` with its confidence,
so the frontend and the feedback system of M6 have a service to call.

## Scope

- In scope: `GET /health`, `POST /predict`, Pydantic input and output schemas,
  loading the model and the label mapping at startup, documentation in
  `docs/APP.md`.
- Out of scope:
  - Exporting the fitted pipeline (#32). The API only loads a file with the
    contract below.
  - The Streamlit frontend, the feedback endpoint and the database.
  - A Docker service or published port for the API; it is run with `uvicorn`.
  - Automated tests (`pytest` and `httpx` are not in `requirements.txt`).
  - Choosing the final model (#23), tuning (#29) and final metrics (#25).

## Design

| File | Change |
|---|---|
| `app/schemas.py` | New. `PredictionRequest`, `PredictionResponse` (Pydantic). |
| `app/serving.py` | New. Model loading, one-hot expansion and prediction, with no FastAPI import so it can be checked without a server. |
| `docs/APP.md` | Fill the API section: endpoints, example request and response, how to run it. |

Decisions:

- **Contract with #32.** The model file is loaded with `joblib` from
  `MODEL_PATH` (default `models/model.joblib`). It must take a DataFrame with
  the 54 original `FEATURES` in the training order and expose `predict_proba`
  and `classes_`. Any feature engineering or scaling lives inside the exported
  pipeline, so the API always receives raw features. `classes_` can be
  Cover_Type (1-7) or encoded labels (0-6); the API detects which and decodes
  with `CLASS_NAMES` and `DECODE` of `src/target_encoding.py` (#15), imported
- **No model, no crash.** If the file is missing the app still starts:
  `/health` reports `model_loaded: false` and `/predict` returns 503 with a
  message, so the container is usable before #32 is merged.
- **Compact input.** The 10 numeric features (named as in the dataset) plus `Wilderness_Area` (1-4) and
  `Soil_Type` (1-40). The API builds the 54 columns, so exactly one wilderness
  area and one soil type are active, as in the dataset
  (`docs/DATA_DICTIONARY.md`).
- **Bounds are physical limits, not observed min/max**, so a valid new
  observation is not rejected: Elevation 0-5000 m, Aspect 0-360, Slope 0-90,
  horizontal distances 0-10000 m, Vertical_Distance_To_Hydrology -500 to 1000 m,
  Hillshade 0-255.
- **Response.** `cover_type` (1-7), `class_name`, `confidence` (the highest
  class probability) and `probabilities` per class name.
- **Validation errors.** Pydantic returns HTTP 422 with the failing field.
- No new dependency.

## Acceptance criteria

- [x] Create /predict endpoint
- [x] Load model/pipeline on startup
- [x] Add input validation (Pydantic)
- [x] Return prediction + confidence
- [x] API returns predictions via HTTP
- [x] Input validation in place
- [x] The app starts and reports a clear 503 when the model file is missing

## Verification

```bash
uvicorn app.api:app --port 8000
```

1. Without `models/model.joblib`: `GET /health` returns `model_loaded: false`
   and `POST /predict` returns 503.
2. With a stand-in pipeline saved at `MODEL_PATH`: a valid `POST /predict`
   returns 200 with `cover_type`, `class_name`, `confidence` and 7
   probabilities that add up to 1.
3. Invalid input (Aspect 400, Soil_Type 41, a missing field) returns 422.

Observed: without a model file, `GET /health` returned `model_loaded: false` with the reason and `POST /predict` returned 503. With a stand-in XGBoost model (random data, labels 0-6, saved at `models/model.joblib`), `GET /health` returned `model_loaded: true`, `POST /predict` returned 200 with `cover_type` 5, `class_name` Aspen, `confidence` 0.2644 and 7 probabilities that add up to 1, and a request with Aspect 400 returned 422. The stand-in predictions have no meaning; the run only checks the API, including the decoding of the encoded labels (0-6). Run locally with fastapi 0.162.5 (`requirements.txt` pins 0.112.2).
