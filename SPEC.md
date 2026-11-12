# SPEC — Functional and Technical Specification

## 1. Overview

Multiclass classification model that receives input data and returns a single predicted class among three or more mutually exclusive categories.

## 2. Problem definition

- **Type of task:** supervised multiclass classification (≥ 3 classes).
- **Target variable:** to be defined (see M1).
- **Success criteria:** overfitting below 5% (difference between training and validation accuracy); accuracy, precision, recall and F1 per class.

## 3. Dataset

- **Candidates:** Dry Bean, Wine, Forest Cover Type (suggested).
- **Source & version:** to be documented (see M1).

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
