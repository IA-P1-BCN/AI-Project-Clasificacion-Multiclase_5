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
├── CONTRIBUTING.md        # Git workflow & commit convention
├── Dockerfile
├── docker-compose.yml
├── requirements.txt       # Pinned dependencies (reproducible)
├── .python-version        # 3.11
├── .env.example
├── docs/
│   ├── EDA.md
│   ├── PREPROCESSING.md
│   ├── MODELING.md
│   ├── APP.md
│   └── DELIVERABLES.md
├── data/
│   ├── raw/               # Original, immutable data (git-ignored)
│   └── processed/         # Cleaned/feature-engineered data (git-ignored)
├── models/                # Trained model artifacts (git-ignored)
├── src/                   # Library code (preprocessing, training, ...)
└── app/
    └── main.py            # Streamlit app
```

## Setup / Getting started

**Requirements:** [Docker](https://docs.docker.com/get-docker/) with Compose v2.

A clean clone runs with two commands:

```bash
git clone https://github.com/IA-P1-BCN/AI-Project-Clasificacion-Multiclase_5.git
cd AI-Project-Clasificacion-Multiclase_5
docker compose up
```

Then open the app at **http://localhost:8501**. To stop: `Ctrl+C` (or
`docker compose down`). After changing `requirements.txt` or the `Dockerfile`,
rebuild with `docker compose up --build`.

### Dataset

The dataset is **not** stored in the repository (`data/raw/` is git-ignored). After cloning, download it and place it locally:

1. Download the *Covertype* dataset from the UCI repository: https://archive.ics.uci.edu/dataset/31/covertype
2. Extract `covertype.zip`. It contains `covtype.data.gz`; decompress it to obtain `covtype.data` (no header, 581,012 rows x 55 columns).
3. Place `covtype.data` in `data/raw/`, so the final path is `data/raw/covtype.data`.

Check that everything is in place with `python src/data_audit.py`.

### Local development without Docker (optional)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app/main.py
```

> An optional PostgreSQL service is already defined (commented) in
> `docker-compose.yml` for later milestones. Copy `.env.example` to `.env`
> and uncomment the `db` block to enable it.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the branch model (`main` / `develop`
/ `feature/*`) and the Conventional Commits convention.

See [docs/APP.md](docs/APP.md) for the application requirements and [SPEC.md](SPEC.md) for the technical specification.
