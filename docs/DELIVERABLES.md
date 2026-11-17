# DELIVERABLES — List of deliverables

> Project deliverables, quality gates and verification status across the four
> delivery levels (`Esencial`, `Medio`, `Avanzado`, `Experto`). See
> [SPEC.md](../SPEC.md) for the functional and technical specification and
> [project-briefing.md](project-briefing.md) for the original assignment brief.

## Contents

- [Required deliverables](#required-deliverables)
- [Technical requirements](#technical-requirements)
- [Final checklist](#final-checklist)

## Required deliverables

- [ ] **Application that receives data and returns a multiclass prediction.**
  - Backend API (`GET /health`, `POST /predict`) and serving contract are
    implemented and merged (#34: [app/api.py](../app/api.py),
    [app/serving.py](../app/serving.py), [app/schemas.py](../app/schemas.py)),
    backed by the exported Random Forest `Pipeline` (#32:
    [src/export_model.py](../src/export_model.py)) and MySQL/SQLite persistence
    (#37: [src/database.py](../src/database.py)). See [APP.md](APP.md).
  - The interactive Streamlit frontend ([app/main.py](../app/main.py)) and
    end-to-end new-data verification are tracked in #33 and #42.
- [x] **GitHub repository with well-managed branches and clean commits.**
  - Git Flow (`main` / `develop` / `feature/<issue>-<slug>`), Conventional
    Commits, one spec per branch under [specs/](../specs/README.md), and
    automated GitHub Actions CI (#41:
    [.github/workflows/ci.yml](../.github/workflows/ci.yml)). Workflow and rules
    are documented in [CONTRIBUTING.md](../CONTRIBUTING.md) and
    [AGENTS.md](../AGENTS.md) (final M8 audit tracked in #50).
- [x] **Technical report with metrics and model analysis.**
  - The consolidated report is [TECHNICAL_REPORT.md](TECHNICAL_REPORT.md) (#44):
    methodology and decisions, model comparison and selection, final metrics on
    `validation`/`test`, per-class precision/recall/F1, 7×7 confusion matrices,
    feature importance (MDI + permutation + SHAP) and error analysis, with a
    documented `pandoc` export to PDF/DOCX.
  - It consolidates the per-stage records [EDA.md](EDA.md) (#7–#11),
    [PREPROCESSING.md](PREPROCESSING.md) (#12–#18) and
    [MODELING.md](MODELING.md) (#19–#27, #29). The final write-up of the modeling
    results (#31) remains open.
- [ ] **Business presentation (PowerPoint, Canva, etc.).**
  - Tracked in M8 (#48).
- [ ] **Technical code presentation.**
  - Tracked in M8 (#49).
- [x] **Link to a project organization tool (GitHub Projects).**
  - Work is organized in milestones M0–M8 and 54 issues with MoSCoW (`Must`,
    `Should`, `Could`) and delivery-level (`nivel-esencial`, `nivel-medio`,
    `nivel-avanzado`, `nivel-experto`) labels:
    - Repository issues & milestones:
      <https://github.com/IA-P1-BCN/AI-Project-Clasificacion-Multiclase_5/milestones>
    - Issue tracker:
      <https://github.com/IA-P1-BCN/AI-Project-Clasificacion-Multiclase_5/issues>
    - Team 5 Scrumban board (GitHub Projects, private: visible to
      `IA-P1-BCN` organization members):
      <https://github.com/orgs/IA-P1-BCN/projects/61>

## Technical requirements

- [x] **Overfitting < 5%.**
  - On the canonical 70 / 15 / 15 stratified split (#16: 406,708 `train` /
    87,152 `validation` / 87,152 `test` rows), the primary Random Forest
    pipeline achieves `train` accuracy `1.0000` and `validation` accuracy
    `0.9520` (`macro F1 = 0.9186`), giving an `overfitting_gap` of **`+0.0480`
    (`+4.80` percentage points, `< 5%`)**, and generalizes to `test` with
    accuracy `0.9510` and `macro F1 = 0.9199` (#25:
    [src/final_metrics.py](../src/final_metrics.py),
    [MODELING.md](MODELING.md)). Formal M5 sign-off is tracked in #28.
- [ ] **Unit tests (data integrity, model works, minimum metrics).**
  - The CI workflow ([.github/workflows/ci.yml](../.github/workflows/ci.yml),
    #41) already runs [scripts/check_imports.py](../scripts/check_imports.py) on
    every push and pull request and executes `pytest` as soon as `tests/` is
    added (#40).
- [x] **Dockerized project.**
  - Multi-service setup with [Dockerfile](../Dockerfile) (`python:3.11-slim`,
    `libgomp1`, pinned dependencies) and
    [docker-compose.yml](../docker-compose.yml) (`api` + `app` + `db` `mysql:8.0` with
    healthcheck and persistent `db_data` volume), verified in CI (#1, #37, #41).
    Frontend and backend run as separate services since #38; usage guide:
    [DOCKER.md](DOCKER.md) (#47).
- [ ] **Documentation (`README`, `SPEC`, `docs/`).** *(in progress)*
  - The final `README.md` is still open (#43); the `docs/` set below is in
    place and kept in sync with each merged issue.
  - Entry point and setup: [README.md](../README.md),
    [CONTRIBUTING.md](../CONTRIBUTING.md), [SPEC.md](../SPEC.md) (#2, #6).
  - Dataset and provenance: [data/README.md](../data/README.md) (#4),
    [DATASET_SELECTION.md](DATASET_SELECTION.md) (#3),
    [DATA_DICTIONARY.md](DATA_DICTIONARY.md) (#5).
  - Analysis, preprocessing, modeling and application: [EDA.md](EDA.md)
    (#7–#11), [PREPROCESSING.md](PREPROCESSING.md) (#12–#18),
    [MODELING.md](MODELING.md) (#19–#27, #29), [APP.md](APP.md) (#32, #34, #36, #37,
    #45), [REPRODUCIBILITY.md](REPRODUCIBILITY.md) (#46), [GUIA_PROYECTO_CLASIFICACION.md](GUIA_PROYECTO_CLASIFICACION.md), and
    branch specs in [specs/](../specs/README.md).

## Final checklist

Status across the four delivery levels defined in [README.md](../README.md) and
[SPEC.md](../SPEC.md):

### 🟢 Essential level (`nivel-esencial`)

| Requirement | Status | Evidence & reproduction |
|---|---|---|
| Functional multiclass model (7 classes) | ✅ Done | [src/logistic_regression.py](../src/logistic_regression.py) (#20), [src/random_forest.py](../src/random_forest.py) (#21), [src/export_model.py](../src/export_model.py) (#32) — `python src/export_model.py` |
| Exploratory data analysis (EDA) with classification plots | ✅ Done | [EDA.md](EDA.md), [src/data_audit.py](../src/data_audit.py) (#7), [src/class_distribution.py](../src/class_distribution.py) (#8), [src/class_eda.py](../src/class_eda.py) (#9) |
| Data cleaning, outlier clipping, scaling & target encoding (no leakage) | ✅ Done | [PREPROCESSING.md](PREPROCESSING.md), [src/data_cleaning.py](../src/data_cleaning.py) (#12), [src/outlier_treatment.py](../src/outlier_treatment.py) (#13), [src/feature_scaling.py](../src/feature_scaling.py) (#14), [src/target_encoding.py](../src/target_encoding.py) (#15) |
| Overfitting controlled (`< 5%` train vs validation gap) | ✅ Verified (`+4.80` pp) | [MODELING.md](MODELING.md), [src/final_metrics.py](../src/final_metrics.py) (#25; formal check in #28) — `python src/final_metrics.py` |
| Basic application serving multiclass predictions | 🟡 In progress | FastAPI backend (#34: [app/api.py](../app/api.py)) & exported pipeline (#32) merged; Streamlit UI tracked in #33 ([app/main.py](../app/main.py)) and end-to-end check in #42 |
| Metrics report: accuracy, per-class precision/recall/F1, confusion matrix | ✅ Done | [MODELING.md](MODELING.md) (*Results*), [src/final_metrics.py](../src/final_metrics.py) (#25) |
| Feature importance & error analysis | ✅ Done | MDI and validation-set permutation importance in [MODELING.md](MODELING.md) (#21, #26: [src/feature_importance.py](../src/feature_importance.py) — `python src/feature_importance.py`) and gain importance in [PREPROCESSING.md](PREPROCESSING.md) (#18); error analysis (confused pairs, Elevation overlap, confidence of errors) in [MODELING.md](MODELING.md#error-analysis) (#27: [src/error_analysis.py](../src/error_analysis.py), figure [docs/figures/error_analysis.png](figures/error_analysis.png) — `python src/error_analysis.py`) |
| Business & technical presentations | ⬜ Pending (M8) | Tracked in #48, #49 and #51 |

### 🟡 Medium level (`nivel-medio`)

| Requirement | Status | Evidence & reproduction |
|---|---|---|
| Ensemble models (`RandomForest`, `XGBoost`, `LightGBM`) | ✅ Done | [src/random_forest.py](../src/random_forest.py) (#21), [src/gradient_boosting.py](../src/gradient_boosting.py) (#22), [src/model_comparison.py](../src/model_comparison.py) (#23) |
| Stratified split & 5-fold `StratifiedKFold` cross-validation | ✅ Done | [src/data_split.py](../src/data_split.py) (#16), [src/baseline.py](../src/baseline.py) (#19), [src/imbalance_handling.py](../src/imbalance_handling.py) (#17) |
| Hyperparameter optimization (`GridSearchCV` / `RandomizedSearch` / `Optuna`) | ✅ Done | `RandomizedSearchCV` on train only, 5-fold macro F1: Random Forest `0.9123 → 0.9326`, XGBoost `0.8489 → 0.9240`. These tuned scores are CV on `train` with the parameters selected on those same folds, so they are slightly optimistic; the unbiased measure comes from #28 (validation) and #25 (test) ([MODELING.md](MODELING.md), [src/hyperparameter_optimization.py](../src/hyperparameter_optimization.py), #29) — `python src/hyperparameter_optimization.py`. The exported pipeline (#32) still uses the default Random Forest; re-exporting with the tuned parameters is pending |
| Feedback collection system (production metrics) | 🟡 In progress | Database table `feedback` and `save_feedback` / `list_feedback` merged (#37: [src/database.py](../src/database.py)); endpoint/UI tracked in #35 |
| New data collection & retraining pipeline | ✅ Done | [APP.md](APP.md), [src/retraining.py](../src/retraining.py) (#36) — `python src/retraining.py` |

### 🟠 Advanced level (`nivel-avanzado`)

| Requirement | Status | Evidence & reproduction |
|---|---|---|
| Dockerization (`Dockerfile` + `docker-compose.yml`) | ✅ Done | [Dockerfile](../Dockerfile) (#1), [docker-compose.yml](../docker-compose.yml) (#1, #37, #38), CI build (#41), [DOCKER.md](DOCKER.md) (#47) |
| Database integration (MySQL 8.0 + SQLite fallback) | ✅ Done | [APP.md](APP.md), [src/database.py](../src/database.py) (#37) — `docker compose exec app python src/database.py` |
| Cloud deployment | ⬜ Pending | Tracked in #39 |
| Unit tests (data integrity, model works, minimum metrics) | ⬜ Pending | CI test runner wired in [.github/workflows/ci.yml](../.github/workflows/ci.yml) (#41); test suite tracked in #40 |

### 🔴 Expert level (`nivel-experto`)

| Requirement | Status | Evidence & reproduction |
|---|---|---|
| Deeper statistical insights (skewness, kurtosis, IQR, PCA) | ✅ Done | [EDA.md](EDA.md), [src/statistical_insights.py](../src/statistical_insights.py) (#10) |
| Feature engineering & selection | ✅ Done | [PREPROCESSING.md](PREPROCESSING.md), [src/feature_engineering.py](../src/feature_engineering.py) (#18) |
| Neural network with multiclass support (`MLPClassifier`) | ✅ Done | [MODELING.md](MODELING.md), [src/neural_network.py](../src/neural_network.py) (#24) — `python src/neural_network.py` |
| Quality-gated model promotion on retraining | ✅ Done | `retrain_pipeline(..., promote=True, min_macro_f1=0.90)` in [src/retraining.py](../src/retraining.py) (#36) |
| Model interpretability (`SHAP`), A/B testing, data drift monitoring | ⬜ Optional (`Could`) | Tracked in #30, #52 and #53 |
