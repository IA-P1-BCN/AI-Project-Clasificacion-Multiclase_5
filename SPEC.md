# SPEC — Functional and Technical Specification

## 1. Overview

Multiclass classification model that receives the 54 cartographic features of a 30×30 m forest cell and returns a single predicted cover type among 7 mutually exclusive tree species.

## 2. Problem definition

### Objective
Predict the **forest cover type** (the dominant tree species) of a 30×30 m cell in the Roosevelt National Forest (Colorado, USA), using cartographic and environmental features. This supports forest management, ecological mapping and resource planning.

### Type of task
Supervised **multiclass classification** — each instance is assigned to exactly one of **7 mutually exclusive classes** (`Cover_Type` 1-7, tree cover types).

### Target variable — 7 classes
1. Spruce/Fir
2. Lodgepole Pine
3. Ponderosa Pine
4. Cottonwood/Willow
5. Aspen
6. Douglas-fir
7. Krummholz

### Features (54)
- **10 quantitative:** Elevation, Aspect, Slope, Horizontal_Distance_To_Hydrology, Vertical_Distance_To_Hydrology, Horizontal_Distance_To_Roadways, Hillshade_9am, Hillshade_Noon, Hillshade_3pm, Horizontal_Distance_To_Fire_Points.
- **4 binary (wilderness areas):** Rawah, Neota, Comanche Peak, Cache la Poudre.
- **40 binary (soil types):** USFS soil-type indicators.

### Success criteria
- Overfitting below **5%** (gap between training and validation).
- Report accuracy plus precision / recall / F1 **per class** and the confusion matrix.

## 3. Dataset

- **Dataset:** Forest Cover Type (Covertype) — Roosevelt National Forest, Colorado, USA (US Forest Service / UCI Machine Learning Repository).
- **Selection:** chosen over Wine and Dry Bean for its size, class imbalance and mixed feature types; see [docs/DATASET_SELECTION.md](docs/DATASET_SELECTION.md).
- **Data dictionary:** every column (type, unit, range, meaning) and the target classes are documented in [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md).
- **Source & version:** download URL, file size and checksum are documented in [data/README.md](data/README.md).

## 4. Functional requirements

1. **Prediction application.** The user enters the 54 cartographic features of a 30×30 m cell and receives the predicted cover type. The Streamlit frontend (`app/main.py`) talks to the FastAPI backend (`app/api.py`), which loads the exported model pipeline and serves `/health` and `/predict`; see [docs/APP.md](docs/APP.md).
2. **Feedback collection.** Predictions and user feedback are stored in MySQL (`src/database.py`, called from `app/api.py`) so the model can be retrained with new data later.
3. **Technical report** with the metrics and the model analysis; see [docs/MODELING.md](docs/MODELING.md).
4. **Presentations.** A business presentation and a technical code presentation.
5. **Project organization** with GitHub Projects (milestones and issues).

## 5. Technical requirements

- **Runtime:** Python 3.11 (`.python-version`), dependencies pinned in `requirements.txt` (scikit-learn, XGBoost, LightGBM, Streamlit, FastAPI).
- **Data pipeline:** cleaning (`src/data_cleaning.py`), feature engineering (`src/feature_engineering.py`), canonical stratified train/validation/test split (`src/data_split.py`, `split_train_val_test`).
- **Scaling:** `src/feature_scaling.py` (`StandardScaler` on `NUMERIC_FEATURES`, binary features passed through) is used by scale-sensitive models such as Logistic Regression; the exported Random Forest pipeline passes the 54 features through unchanged.
- **Models:** Random Forest (primary, `src/random_forest.py`) and XGBoost / LightGBM (`src/gradient_boosting.py`) from the M4 shortlist, with Logistic Regression (`src/logistic_regression.py`) and an MLP (`src/neural_network.py`) as references.
- **Evaluation protocol:** shared `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)` with macro F1 as the main metric (`src/baseline.py`). The current model runs untuned with its default hyperparameters. Hyperparameter search is tracked as issue #29 and is not part of this version.
- **Metrics:** macro F1 (main metric), accuracy, precision / recall / F1 per class, confusion matrix, feature importance, and the overfitting gap (< 5%), computed in `src/final_metrics.py`.
- **Serving:** the fitted pipeline is serialized with `joblib` (`src/export_model.py`, `models/model.joblib` plus `models/model_metadata.json`) and loaded by the backend.
- **Infrastructure:** Docker (`Dockerfile`, `docker-compose.yml`), MySQL 8.0 database with a local SQLite fallback, GitHub Actions CI (`.github/workflows/ci.yml`: import check, unit tests once `tests/` exists via #40, Docker build) and unit tests.

## 6. Architecture

```
Streamlit (frontend) ──► FastAPI (backend) ──► model pipeline ──► prediction
                              │
                              ▼
                        MySQL (feedback)
```

1. **Streamlit** (`app/main.py`) collects the 54 features from the user.
2. **FastAPI** (`app/api.py`) exposes `/health` and `/predict`; it loads the exported pipeline (`models/model.joblib`, built by `src/export_model.py`) and returns the predicted cover type.
3. **Model pipeline** bundles the preprocessing and the fitted Random Forest into a single scikit-learn `Pipeline`.
4. **MySQL** (`src/database.py`) persists predictions and feedback; the API still returns the prediction when the database is unavailable.
5. **Retraining** (`src/retraining.py`) ingests new labeled data and retrains the pipeline, closing the feedback loop (an offline process, outside the live request path).

## 7. Delivery levels

Requirements are organized in four levels, as in [README.md](README.md):

| Level | Scope in this project |
|---|---|
| 🟢 Essential | Functional multiclass model, EDA, overfitting < 5%, basic app, metrics report |
| 🟡 Medium | Ensemble models (Random Forest, XGBoost), stratified cross-validation, hyperparameter tuning, feedback system, retraining pipeline |
| 🟠 Advanced | Full Dockerization, DB integration (MySQL), cloud deployment, unit tests |
| 🔴 Expert | Neural networks (MLP), MLOps (A/B testing, data drift monitoring) |

## 8. Quality gates

- Overfitting < 5%.
- Unit tests: data integrity, model works, minimum metrics.
- CI/CD pipeline.
