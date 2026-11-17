# Spec: feature/33-m6-basic-prediction-app-streamlit

| | |
|---|---|
| Issue | #33 - [M6] Basic prediction app (Streamlit) |
| Milestone | M6 |
| Branch | `feature/33-m6-basic-prediction-app-streamlit` (from `develop`) |
| Owner | @nagicome03 |
| Depends on | #32 (model export), #34 (FastAPI backend) |

## Goal

Replace the M0 placeholder in `app/main.py` with the Streamlit frontend of the
prediction application: a form that collects the 12 compact features of a
30×30 m forest cell and returns the predicted cover type through the FastAPI
backend.

## Scope

- In scope:
  - `app/main.py` — the Streamlit UI (form, example buttons, prediction display).
  - `.streamlit/config.toml` — forest-green theme.
  - `docker-compose.yml` — add a `backend` service so `docker compose up` runs
    FastAPI and Streamlit together.
  - `requirements.txt` — add `requests` (HTTP client; already a transitive
    dependency of Streamlit, now pinned explicitly).
- Out of scope:
  - Feedback collection ("was the prediction correct?") — #35.
  - Cloud deployment — #39.
  - Database persistence — already implemented in #37 and called by the
    backend; the frontend does not touch it.

## Design

- **Architecture (Option A, matches SPEC.md):** Streamlit calls the FastAPI
  backend at `POST /predict` over HTTP. The frontend never loads the model; the
  backend (#34) does. The backend URL is read from `BACKEND_URL` (default
  `http://localhost:8000`), set to `http://backend:8000` in Docker.
- **Form:** the 12 compact fields — the 10 numeric features plus
  `Wilderness_Area` (1–4) and `Soil_Type` (1–40) — matching `app/schemas.py`.
  Labels are in Spanish; the 7 species names come from
  `src/target_encoding.py` (`CLASS_NAMES`, single source of truth). The form
  lives in a collapsed `st.expander`: the demo fills it via the example buttons,
  not by hand.
- **Example buttons:** 7 buttons, one per cover type. Each fills the form with a
  correctly-classified training cell, spread across the confidence spectrum so
  the demo shows the model's full behaviour — high confidence (clear cells,
  ~85–95 %), medium (~70–75 %) and low (<60 %, borderline cells such as Aspen
  and Douglas-fir). The class median was rejected because, for overlapping
  classes, the median cell sits in the overlap and the model predicts the other
  class. Buttons set the widget state before the form widgets are instantiated,
  so Streamlit picks up the new values.
- **Result:** a species card with the botanical facts on the left (scientific
  name, height, habitat and a distinctive trait, from `SPECIES_INFO`) and a
  photo on the right, a color-coded confidence (green ≥80 %, amber 60–80 %, red
  <60 %), a "top-2" section showing both photos when the runner-up reaches
  ≥20 %, and the per-class probabilities as animated green bars (classes with
  0 % are hidden). Photos are hotlinked from Wikimedia Commons (CC licenses). A
  friendly message is shown when the backend is unreachable or the model is not
  loaded.
- **No data leakage:** the example cells are descriptive training rows, not
  learned parameters; they only pre-fill an input form.

## Acceptance criteria

- [x] App accepts data and returns a prediction.
- [x] Runs locally.

## Verification

1. Export the model once: `python src/export_model.py` (writes
   `models/model.joblib`).
2. Start the backend: `uvicorn app.api:app --port 8000`.
3. Start the frontend: `streamlit run app/main.py`, open http://localhost:8501.
4. Click a "Cargar un ejemplo" button and "Predecir cobertura forestal"; a
   species name, confidence and 7 probability bars appear.
5. Alternatively, `docker compose up` starts `app` (Streamlit) and `backend`
   (FastAPI) together.

Observed: the 7 example buttons each return their own species with the expected
confidence (high ~85–95 %, medium ~70–75 %, low ~54–58 %), and real test-set
cells (never seen by the model) are predicted correctly, matching the ~95 %
validation accuracy.
