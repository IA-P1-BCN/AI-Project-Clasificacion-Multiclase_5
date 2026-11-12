# Multiclass Classification Project

Machine learning project that solves a real problem using **multiclass classification** algorithms.

## Description

The goal of this project is to develop a machine learning model capable of solving a real problem using multiclass classification algorithms. It applies the knowledge acquired on data analysis, visualization, preprocessing, supervised model construction, and evaluation of results.

Multiclass classification is a supervised learning task in which each input instance is assigned to a single class among three or more possible ones. Unlike binary classification (two classes), the model must learn to distinguish between multiple mutually exclusive categories.

**Suggested dataset (optional):** *Forest Cover Type Dataset*. Other candidates under evaluation: Dry Bean and Wine. Authenticity of the chosen dataset is encouraged.

## Team

| Member | GitHub | Focus |
|---|---|---|
| Caro | — | Dataset, EDA, ensembles, evaluation |
| Levi | — | Cleaning, simple models, metrics, presentation |
| Leandro | — | Backend, Docker, DB, cloud, CI/CD |
| Nayeli | — | Problem definition, modeling, app, docs |

## Tech stack

- Scikit-learn, XGBoost, LightGBM
- Pandas / NumPy
- Matplotlib / Seaborn
- Streamlit
- FastAPI
- Docker
- Git / GitHub

## Delivery levels

- 🟢 **Esencial** — functional multiclass model, EDA, overfitting < 5%, basic app, metrics report.
- 🟡 **Medio** — ensemble models, stratified cross-validation, hyperparameter tuning, feedback system, retraining pipeline.
- 🟠 **Avanzado** — full Dockerization, DB integration, cloud deployment, unit tests.
- 🔴 **Experto** — neural networks, MLOps (A/B testing, data drift monitoring).

## Milestones

- **M0** — Environment & infrastructure (Sprint 0)
- **M1** — Problem definition & dataset
- **M2** — Audit & EDA
- **M3** — Cleaning & preprocessing
- **M4** — Model training & comparison
- **M5** — Evaluation & error analysis
- **M6** — Application & production
- **M7** — Documentation & deliverables
- **M8** — Final presentation & review

## Repository structure

```
.
├── README.md
├── SPEC.md
├── docs/
│   ├── EDA.md
│   ├── MODELING.md
│   ├── APP.md
│   └── DELIVERABLES.md
├── data/
├── models/
├── src/
└── app/
```

## Setup

```bash
docker compose up
```

See [docs/APP.md](docs/APP.md) for the application requirements and [SPEC.md](SPEC.md) for the technical specification.
