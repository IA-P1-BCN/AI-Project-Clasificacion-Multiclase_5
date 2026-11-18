# User stories

> The needs of the people who use, build, run and review this project, written as
> user stories with acceptance criteria. Each story points to the issues that
> implement it and to the document where the result is recorded.

Status as of 2026-11-18: ✅ done (merged into `develop`), 🟡 in progress or in
review, ⬜ pending. The delivery level (`Esencial`, `Medio`, `Avanzado`,
`Experto`) is the one of [DELIVERABLES.md](DELIVERABLES.md). Priorities
(`Must`, `Should`, `Could`) are the labels of each issue in the
[issue tracker](https://github.com/IA-P1-BCN/AI-Project-Clasificacion-Multiclase_5/issues).

## Contents

- [Users](#users)
- [Format](#format)
- [Summary](#summary)
- [A. Predicting forest cover](#a-predicting-forest-cover)
- [B. Building and evaluating the model](#b-building-and-evaluating-the-model)
- [C. Running and monitoring the system](#c-running-and-monitoring-the-system)
- [D. Reviewing and reproducing the project](#d-reviewing-and-reproducing-the-project)
- [Not covered](#not-covered)

## Users

| User | Who they are | What they need |
|---|---|---|
| **Forest analyst** | A person with the cartographic data of a 30 × 30 m forest cell (elevation, slope, distances, hillshade, wilderness area, soil type) | To know which of the 7 cover types the cell has, and how far to trust the answer |
| **Data scientist** | A member of the team that builds and evaluates the model | A clean, leak-free dataset, fair comparisons between models and honest metrics |
| **ML engineer** | The person who runs the system and keeps it healthy after release | To start it with one command, watch how it performs on real data and replace the model safely |
| **Reviewer** | An instructor, a teammate or a new contributor who reads the repository | To reproduce the results and follow how and why each decision was made |

## Format

```
As a <user>, I want <goal> so that <benefit>.
Acceptance criteria: Given <context>, when <action>, then <observable result>.
```

Every story lists its delivery level, the issues that implement it and its
status. The numbers quoted in the criteria come from the documents linked in each
story.

## Summary

| ID | Story | User | Level | Issues | Status |
|---|---|---|---|---|---|
| [US-01](#us-01--predict-the-cover-type-of-a-cell) | Predict the cover type of a cell | Forest analyst | Esencial | #32, #33, #34 | ✅ |
| [US-02](#us-02--see-how-confident-the-prediction-is) | See how confident the prediction is | Forest analyst | Esencial | #33 | ✅ |
| [US-03](#us-03--learn-about-the-predicted-species) | Learn about the predicted species | Forest analyst | Esencial | #33 | ✅ |
| [US-04](#us-04--be-told-when-the-input-is-wrong) | Be told when the input is wrong | Forest analyst | Esencial | #33, #34 | ✅ |
| [US-05](#us-05--report-the-real-cover-type) | Report the real cover type of a cell | Forest analyst | Medio | #35 | 🟡 |
| [US-06](#us-06--understand-the-dataset) | Understand the dataset | Data scientist | Esencial | #3 to #11 | ✅ |
| [US-07](#us-07--prepare-the-data-without-leakage) | Prepare the data without leakage | Data scientist | Esencial | #12 to #16 | ✅ |
| [US-08](#us-08--compare-models-fairly) | Compare models fairly | Data scientist | Medio | #17, #19 to #24 | ✅ |
| [US-09](#us-09--tune-the-best-models) | Tune the best models | Data scientist | Medio | #29 | ✅ |
| [US-10](#us-10--measure-the-final-model-honestly) | Measure the final model honestly | Data scientist | Esencial | #25, #28 | ✅ |
| [US-11](#us-11--understand-why-the-model-decides-and-fails) | Understand why the model decides and fails | Data scientist | Esencial | #18, #26, #27, #30 | ✅ |
| [US-12](#us-12--retrain-with-new-verified-data) | Retrain with new verified data | Data scientist | Medio | #36 | ✅ |
| [US-13](#us-13--export-one-reproducible-model-file) | Export one reproducible model file | ML engineer | Esencial | #32 | ✅ |
| [US-14](#us-14--start-the-whole-system-with-one-command) | Start the whole system with one command | ML engineer | Avanzado | #1, #37, #38, #47 | ✅ |
| [US-15](#us-15--keep-every-prediction-and-feedback) | Keep every prediction and feedback | ML engineer | Avanzado | #37 | ✅ |
| [US-16](#us-16--watch-the-live-accuracy) | Watch the live accuracy | ML engineer | Medio | #35 | ✅ |
| [US-17](#us-17--compare-two-models-in-production) | Compare two models in production | ML engineer | Experto | #52 | ✅ |
| [US-18](#us-18--be-alerted-when-the-inputs-drift) | Be alerted when the inputs drift | ML engineer | Experto | #53 | ✅ |
| [US-19](#us-19--run-it-in-the-cloud) | Run it in the cloud | ML engineer | Avanzado | #39 | 🟡 |
| [US-20](#us-20--catch-breakages-before-they-reach-develop) | Catch breakages before they reach `develop` | ML engineer | Avanzado | #40, #41, #42 | ✅ |
| [US-21](#us-21--reproduce-the-results-from-a-clean-clone) | Reproduce the results from a clean clone | Reviewer | Esencial | #46, #47 | ✅ |
| [US-22](#us-22--read-the-results-and-the-reasoning) | Read the results and the reasoning | Reviewer | Esencial | #31, #44, #48, #49 | 🟡 |
| [US-23](#us-23--follow-how-the-work-was-organised) | Follow how the work was organised | Reviewer | Esencial | #41, #50 | ✅ |

## A. Predicting forest cover

### US-01 · Predict the cover type of a cell

**As a** forest analyst, **I want** to enter the cartographic data of a 30 × 30 m
cell **so that** I get its predicted forest cover type.

- **Level:** Esencial · **Issues:** #32, #33, #34 · **Status:** ✅
- **Acceptance criteria**
  - Given the app is running and the model is loaded, when I fill in the 10
    quantitative features and choose the wilderness area (1 to 4) and the soil
    type (1 to 40) and press *Predecir cobertura forestal*, then I see the
    predicted cover type, one of the 7 species (Spruce/Fir, Lodgepole Pine,
    Ponderosa Pine, Cottonwood/Willow, Aspen, Douglas-fir, Krummholz).
  - Given the same inputs, when I ask again, then I get the same answer.
  - Given the backend is not reachable or has no model, when I press the button,
    then the app shows a message that says what to do instead of failing silently.
- **Where it is recorded:** [APP.md](APP.md).

### US-02 · See how confident the prediction is

**As a** forest analyst, **I want** to see how sure the model is **so that** I know
when to double-check the cell by other means.

- **Level:** Esencial · **Issues:** #33 · **Status:** ✅
- **Acceptance criteria**
  - Given a prediction, when it is shown, then it includes the confidence of the
    winning class and the probability of each of the 7 classes.
  - Given a confidence of 80 % or more, between 60 % and 80 %, or below 60 %,
    when it is shown, then it is labelled high, medium or low (*Confianza alta*,
    *media*, *baja*).
  - Given the model is unsure between two species, when the result is shown, then
    the two most probable classes are visible.
- **Why it matters:** the errors of the model concentrate in a few pairs of
  classes (for example Aspen and Lodgepole Pine), see [MODELING.md](MODELING.md#error-analysis).

### US-03 · Learn about the predicted species

**As a** forest analyst, **I want** a short description and a photo of the
predicted species **so that** I can recognise it and judge whether the answer
makes sense.

- **Level:** Esencial · **Issues:** #33 · **Status:** ✅
- **Acceptance criteria**
  - Given a prediction, when it is shown, then the species card includes
    botanical facts and a photo of that cover type.
  - The species names shown are the ones defined in `src/target_encoding.py`, the
    single source of truth of the project.

### US-04 · Be told when the input is wrong

**As a** forest analyst, **I want** impossible values to be rejected with a clear
message **so that** a typing mistake does not produce a confident wrong answer.

- **Level:** Esencial · **Issues:** #33, #34 · **Status:** ✅
- **Acceptance criteria**
  - Given a value outside the physical range of its feature (for example an
    `Elevation` above 5000 or a `Slope` above 90), when I send it, then the API
    answers `422` and no prediction is made.
  - Given a missing field or an unknown extra field, when I send the request,
    then the API answers `422`.
  - Given `Wilderness_Area` outside 1 to 4 or `Soil_Type` outside 1 to 40, when I
    send it, then the API answers `422`.
- **Where it is recorded:** [APP.md](APP.md#input-validation).

### US-05 · Report the real cover type

**As a** forest analyst, **I want** to tell the system the real cover type of a
cell once I have verified it in the field **so that** the system learns how often
it is right.

- **Level:** Medio · **Issues:** #35 · **Status:** 🟡 the API is done, the app has
  no form for it yet
- **Acceptance criteria**
  - Given a prediction with a `prediction_id`, when I send `POST /feedback` with the
    true cover type (1 to 7), then the system stores it linked to that prediction
    and tells me whether the prediction was correct.
  - Given a `prediction_id` that does not exist, when I send feedback, then the API
    answers `404`.
  - Given a true cover type outside 1 to 7, when I send feedback, then the API
    answers `422`.
  - ⬜ Given a prediction shown in the app, when I enter the real cover type, then
    it is sent to `POST /feedback` (not built yet: today feedback is sent to the
    API directly).
- **Where it is recorded:** [APP.md](APP.md#feedback-collection-and-monitoring).

## B. Building and evaluating the model

### US-06 · Understand the dataset

**As a** data scientist, **I want** an audit, a data dictionary and an exploratory
analysis of the dataset **so that** I know what the data contains before modelling.

- **Level:** Esencial · **Issues:** #3, #4, #5, #7, #8, #9, #10, #11 · **Status:** ✅
- **Acceptance criteria**
  - Given the raw file `covtype.data`, when I read the documentation, then I can
    find where it comes from, why this dataset was chosen and what each of the 54
    features and the target mean.
  - Given the class distribution, when I read the analysis, then the imbalance
    between the 7 classes is quantified and plotted.
  - Given the key features, when I read the analysis, then their distributions,
    skewness, outliers and a PCA projection are shown by class.
- **Where it is recorded:** [DATASET_SELECTION.md](DATASET_SELECTION.md),
  [DATA_DICTIONARY.md](DATA_DICTIONARY.md), [EDA.md](EDA.md).

### US-07 · Prepare the data without leakage

**As a** data scientist, **I want** cleaning, scaling and encoding fitted only on
the training data **so that** the validation and test results are not inflated.

- **Level:** Esencial · **Issues:** #12, #13, #14, #15, #16 · **Status:** ✅
- **Acceptance criteria**
  - Given the dataset, when it is split, then it is a stratified 70 / 15 / 15
    split (406,708 train, 87,152 validation and 87,152 test rows) that every
    later step reuses.
  - Given any preprocessing that learns from data (scaling, outlier limits), when
    it runs, then it is fitted on `train` only, inside a `Pipeline`.
  - Given the test set, when decisions are made, then it is not used: it is
    evaluated once, at the end.
- **Where it is recorded:** [PREPROCESSING.md](PREPROCESSING.md).

### US-08 · Compare models fairly

**As a** data scientist, **I want** every candidate model evaluated on the same
split and with the same protocol **so that** the ranking is trustworthy.

- **Level:** Medio · **Issues:** #17, #19, #20, #21, #22, #23, #24 · **Status:** ✅
- **Acceptance criteria**
  - Given the baselines, the logistic regression, the random forest, XGBoost,
    LightGBM and the neural network, when they are compared, then all use the
    canonical train split and 5-fold stratified cross-validation with macro F1
    as the main metric.
  - Given the comparison table, when I read it, then the Random Forest is first
    (macro F1 0.9124), ahead of the MLP (0.8557), XGBoost (0.8514), LightGBM
    (0.8261) and the logistic regression (0.5324).
  - Given class imbalance, when class weights are tried, then the result is
    recorded, including that they did not improve the cross-validated macro F1.
- **Where it is recorded:** [MODELING.md](MODELING.md).

### US-09 · Tune the best models

**As a** data scientist, **I want** the hyperparameters of the shortlisted models
searched on the training data only **so that** I improve them without touching the
validation or test sets.

- **Level:** Medio · **Issues:** #29 · **Status:** ✅
- **Acceptance criteria**
  - Given the Random Forest and XGBoost, when `RandomizedSearchCV` runs on `train`
    with 5-fold macro F1, then the Random Forest goes from 0.9123 to 0.9326 and
    XGBoost from 0.8489 to 0.9240.
  - Given those scores were chosen on the same folds, when they are reported,
    then they are flagged as slightly optimistic and the unbiased figures come
    from validation and test.
- **Where it is recorded:** [MODELING.md](MODELING.md#hyperparameter-optimization).

### US-10 · Measure the final model honestly

**As a** data scientist, **I want** the final metrics on validation and test,
per class, and a check of overfitting **so that** I can say how well the model
really generalises.

- **Level:** Esencial · **Issues:** #25, #28 · **Status:** ✅
- **Acceptance criteria**
  - Given the exported Random Forest, when it is evaluated, then validation gives
    accuracy 0.9520 and macro F1 0.9186, and test gives 0.9510 and 0.9199.
  - Given the per-class metrics and the 7 × 7 confusion matrices, when I read
    them, then the weakest classes are visible (Aspen and Cottonwood/Willow).
  - Given the train accuracy (1.0000) and the validation accuracy (0.9520), when
    the gap is computed, then it is +4.80 points, below the 5 % limit. The spec
    of #28 states that this is measured on accuracy, that the margin to the limit
    is thin (0.2 points) and that the gap on macro F1 is larger (8.1 points).
- **Where it is recorded:** [MODELING.md](MODELING.md), [TECHNICAL_REPORT.md](TECHNICAL_REPORT.md),
  [the spec of #28](../specs/feature-28-m5-verify-overfitting-5.md).

### US-11 · Understand why the model decides and fails

**As a** data scientist, **I want** feature importance, SHAP and an error analysis
**so that** I can check that the model relies on sensible variables and see where
it fails.

- **Level:** Esencial and Experto · **Issues:** #18, #26, #27, #30 · **Status:** ✅
- **Acceptance criteria**
  - Given the model, when I read the importance analysis, then `Elevation` and the
    distance features appear as the main drivers, confirmed by impurity-based
    importance, permutation importance and SHAP.
  - Given the validation errors, when I read the error analysis, then the most
    confused pairs of classes and the confidence of the errors are shown.
- **Where it is recorded:** [MODELING.md](MODELING.md), [PREPROCESSING.md](PREPROCESSING.md),
  figures in [docs/figures](figures/).

### US-12 · Retrain with new verified data

**As a** data scientist, **I want** to add newly verified observations and retrain
**so that** the model can improve with real data without risking a worse one in
production.

- **Level:** Medio · **Issues:** #36 · **Status:** ✅
- **Acceptance criteria**
  - Given new labelled observations, when they are ingested, then they are
    validated (physical ranges, one wilderness area and one soil type per row,
    class 1 to 7) and stored in `data/processed/new_samples.csv`, never in the raw
    file.
  - Given the new samples, when the pipeline is retrained, then they are added to
    the training set only, the validation and test sets stay fixed, and any row
    that also appears in them is discarded.
  - Given a retrained model, when it is promoted, then it replaces
    `models/model.joblib` only if its validation macro F1 is at least 0.90.
- **Where it is recorded:** [APP.md](APP.md#new-data-collection-and-retraining-pipeline).

## C. Running and monitoring the system

### US-13 · Export one reproducible model file

**As an** ML engineer, **I want** the whole pipeline (preprocessing and model)
exported as a single file with its metadata **so that** serving needs nothing else.

- **Level:** Esencial · **Issues:** #32 · **Status:** ✅
- **Acceptance criteria**
  - Given the raw dataset, when I run `python src/export_model.py`, then it
    creates `models/model.joblib` and `models/model_metadata.json`.
  - Given the exported file, when the API starts, then it loads it once and
    `GET /health` reports `model_loaded: true`.
- **Where it is recorded:** [APP.md](APP.md#model-export).

### US-14 · Start the whole system with one command

**As an** ML engineer, **I want** the frontend, the backend and the database to
start together **so that** I can run the project without manual setup.

- **Level:** Avanzado · **Issues:** #1, #37, #38, #47 · **Status:** ✅
- **Acceptance criteria**
  - Given Docker Compose, when I run `docker compose up --build`, then three
    services start in order: the MySQL database, the API on port 8000 and the
    Streamlit app on port 8501.
  - Given the services, when the database or the API is not ready, then the
    dependent service waits for its health check.
  - Given a restart of Docker, when the stack comes back, then the stored
    predictions are still there (persistent volume).
- **Where it is recorded:** [DOCKER.md](DOCKER.md).

### US-15 · Keep every prediction and feedback

**As an** ML engineer, **I want** every prediction and its feedback stored
**so that** I can audit the system and measure it later.

- **Level:** Avanzado · **Issues:** #37 · **Status:** ✅
- **Acceptance criteria**
  - Given a call to `POST /predict`, when it succeeds, then the inputs, the result
    and a `prediction_id` are stored.
  - Given the database is unreachable, when a prediction is requested, then the
    user still gets the prediction and the failure is only logged.
  - Given no `DATABASE_URL`, when the project runs locally, then it falls back to
    a SQLite file instead of failing.
- **Where it is recorded:** [APP.md](APP.md#database-integration).

### US-16 · Watch the live accuracy

**As an** ML engineer, **I want** to see how the model performs on real, labelled
feedback **so that** I notice when it degrades.

- **Level:** Medio · **Issues:** #35 · **Status:** ✅
- **Acceptance criteria**
  - Given no data yet, when I call `GET /metrics`, then it answers with zero
    counters and empty ratios instead of failing.
  - Given feedback, when I call `GET /metrics`, then I get the number of
    predictions, the feedback coverage, the live accuracy, the average confidence
    and the accuracy per class.
- **Where it is recorded:** [APP.md](APP.md#get-metrics).

### US-17 · Compare two models in production

**As an** ML engineer, **I want** to serve a challenger model to part of the
traffic **so that** I can decide with real feedback whether it should replace the
current one.

- **Level:** Experto · **Issues:** #52 · **Status:** ✅
- **Acceptance criteria**
  - Given `AB_TRAFFIC_B` between 0 and 1, when requests arrive, then that share is
    served by model B (version 0.2.0) and the rest by model A (0.1.0), and each
    prediction records its variant. With `0` the test is off.
  - Given feedback, when I call `GET /ab/results`, then I get the live accuracy of
    each variant and a decision.
  - Given fewer than 200 feedbacks per variant, or a difference that is not
    significant (p ≥ 0.05) or smaller than 0.5 points, when the decision is made,
    then no winner is declared.
- **Where it is recorded:** [AB_TESTING.md](AB_TESTING.md).

### US-18 · Be alerted when the inputs drift

**As an** ML engineer, **I want** to be warned when the data reaching the API
stops looking like the training data **so that** I can react before the model
degrades.

- **Level:** Experto · **Issues:** #53 · **Status:** ✅
- **Acceptance criteria**
  - Given the reference profile built from the training split, when I call
    `GET /drift`, then I get the PSI of each of the 12 inputs for the latest
    windows of predictions and a status (`ok`, `warning`, `alert` or
    `insufficient_data`).
  - Given a window whose highest PSI reaches 0.1 or 0.25, when the automatic check
    runs (every 500 predictions by default), then a warning or an alert is written
    to the log and, if a webhook is configured, sent to it.
  - Given the check or the webhook fails, when predictions keep arriving, then
    `POST /predict` is not affected.
- **Where it is recorded:** [DRIFT_MONITORING.md](DRIFT_MONITORING.md).

### US-19 · Run it in the cloud

**As an** ML engineer, **I want** a public deployment of the app and the API
**so that** the project can be used without running anything locally.

- **Level:** Avanzado · **Issues:** #39 · **Status:** 🟡 in progress
- **Acceptance criteria**
  - Given a free hosting plan, when the frontend and the API are deployed, then
    the public frontend returns a prediction made by the real model.
  - Given the memory limit of the free plan, when the model is loaded, then the
    service stays within it (the challenger model uses far less memory than the
    main one).

### US-20 · Catch breakages before they reach `develop`

**As an** ML engineer, **I want** automated tests and a CI pipeline **so that** a
change that breaks the data, the model or the API is caught in the pull request.

- **Level:** Avanzado · **Issues:** #40, #41, #42 · **Status:** ✅
- **Acceptance criteria**
  - Given a pull request to `develop` or `main`, when it is opened, then the CI
    installs the pinned dependencies, checks the imports and runs `pytest`.
  - Given the test suite, when it runs, then it covers data integrity, the model
    pipeline and its metrics, the A/B rules and the drift rules.
  - Given unseen data, when it is sent to the real `POST /predict` endpoint, then
    the predictions are correct (end-to-end test, #42). The part that needs the
    exported model and the raw dataset is skipped in the CI, where neither exists.
- **Where it is recorded:** [TESTING.md](TESTING.md).

## D. Reviewing and reproducing the project

### US-21 · Reproduce the results from a clean clone

**As a** reviewer, **I want** exact steps and pinned versions **so that** I can
run the project and get the same numbers.

- **Level:** Esencial · **Issues:** #46, #47 · **Status:** ✅
- **Acceptance criteria**
  - Given a fresh clone, when I follow the run steps, then I can start the app with
    Docker and export the model.
  - Given the pinned requirements, when I install them with Python 3.11, then the
    scripts of `src/` run and print the documented figures.
- **Where it is recorded:** [REPRODUCIBILITY.md](REPRODUCIBILITY.md), [DOCKER.md](DOCKER.md).

### US-22 · Read the results and the reasoning

**As a** reviewer, **I want** one technical report and the presentations
**so that** I can understand what was done, with which results and why.

- **Level:** Esencial · **Issues:** #31, #44, #48, #49 · **Status:** 🟡 the report and
  the modelling write-up are done, the presentations are pending
- **Acceptance criteria**
  - Given the technical report, when I read it, then it covers the methodology,
    the model comparison, the final metrics, the per-class results and the error
    analysis, and it can be exported to PDF or DOCX.
  - Given the project guide, when I read it, then each decision comes with its
    justification, its limits and a plain-language explanation.
  - ⬜ Given the business and the technical presentations, when they are ready,
    then they summarise the project for each audience (#48, #49).
- **Where it is recorded:** [TECHNICAL_REPORT.md](TECHNICAL_REPORT.md),
  [GUIA_PROYECTO_CLASIFICACION.md](GUIA_PROYECTO_CLASIFICACION.md).

### US-23 · Follow how the work was organised

**As a** reviewer, **I want** a clean Git history and a spec for every branch
**so that** I can trace each change to its issue and its intent.

- **Level:** Esencial · **Issues:** #41, #50 · **Status:** ✅
- **Acceptance criteria**
  - Given any merged branch, when I look for it, then there is a spec in `specs/`
    with the same name, written before the code.
  - Given the history, when I read it, then branches follow Git Flow
    (`main`, `develop`, `feature/<issue>-<slug>`) and commits follow Conventional
    Commits.
  - Given a pull request, when it is opened, then it targets `develop` and needs
    the CI to pass.
- **Where it is recorded:** [CONTRIBUTING.md](../CONTRIBUTING.md), [specs/](../specs/README.md).

## Not covered

- **Authentication and roles.** The app and the API are open: nobody logs in, and
  there is no difference between users beyond what each one does.
- **Batch predictions.** The app predicts one cell at a time; there is no upload
  of a file with many cells.
- **A feedback form in the app.** See US-05: today feedback is sent to the API.
- **Reading the data from a GIS system.** The inputs are typed by the user.