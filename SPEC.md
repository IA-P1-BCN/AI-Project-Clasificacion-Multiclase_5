# SPEC — Functional and Technical Specification

## 1. Overview

Multiclass classification model that receives input data and returns a single predicted class among three or more mutually exclusive categories.

## 2. Problem definition

### Objective
Predict the **forest cover type** (the dominant tree species) of a 30×30 m cell in the Roosevelt National Forest (Colorado, USA), using cartographic and environmental features. This supports forest management, ecological mapping and resource planning.

### Type of task
Supervised **multiclass classification** — each instance is assigned to exactly one of **7 mutually exclusive classes** (tree cover types).

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
- **Source & version:** to be documented on download (see M1).

## 4. Functional requirements

1. Application that receives data as input and returns a multiclass prediction.
2. Technical report with metrics and model analysis.
3. Business presentation + technical code presentation.
4. Project organization tool (GitHub Projects).

## 5. Technical requirements

- Preprocessing pipeline (cleaning, scaling, encoding).
- Stratified train/validation/test split (StratifiedKFold).
- Ensemble models (Random Forest, XGBoost, LightGBM).
- Hyperparameter optimization (GridSearchCV / RandomizedSearch / Optuna).
- Metrics: accuracy, precision/recall/F1 per class, confusion matrix, feature importance, error analysis.
- Dockerized application, DB integration, cloud deployment, unit tests.
- Feedback collection system + retraining pipeline.

## 6. Architecture

```
Streamlit (frontend) ──► FastAPI (backend) ──► model pipeline ──► prediction
                              │
                              ▼
                        Database (MySQL/MongoDB)
```

## 7. Quality gates

- Overfitting < 5%.
- Unit tests: data integrity, model works, minimum metrics.
- CI/CD pipeline.
