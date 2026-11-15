# Spec: feature/32-export-model-pipeline

| | |
|---|---|
| Issue | #32 - [M6] Export the model and pipeline (joblib/pickle) |
| Milestone | M6 |
| Branch | `feature/32-export-model-pipeline` (from `develop`) |
| Owner | @levifvy |
| Depends on | #29 (M5 tuning, **not merged yet**, see *Design*), #23 (shortlist, merged), #34 (serving contract, merged) |

## Goal

Export the final model and its preprocessing as one fitted scikit-learn
`Pipeline` in `models/model.joblib`, together with a metadata file (version,
label mapping, metrics), so the API of #34 can load it and serve predictions.

## Scope

- In scope: `src/export_model.py` (build, fit on the train set, serialize,
  write metadata, check the serving contract), the *Model export* section of
  `docs/APP.md`.
- Out of scope:
  - Hyperparameter tuning (#29) and imbalance handling (#17). The export uses
    the current configuration of the primary model and is re-run when they land.
  - Final metrics on the test set (#25) and the overfitting gap (#28). The
    test set is not read by this branch.
  - Any change to `app/serving.py` or the API (#34); this branch only produces
    the file that satisfies its contract.
  - Shipping the artifact inside the Docker image or to the cloud (M6
    Dockerization / deployment issues).

## Design

| File | Change |
|---|---|
| `src/export_model.py` | New. `build_pipeline`, `fit_pipeline`, `validation_metrics`, `label_mapping`, `build_metadata`, `export`, `check_contract`, `main`. |
| `docs/APP.md` | New *Model export* section with the reproduce command and the observed results. |

Decisions:

- **Model: the untuned primary model of the shortlist.** #29 is still open, so
  there is no tuned configuration. The export uses `random_forest.build_model()`
  (#21): `RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)`,
  the primary model agreed in `docs/MODELING.md` (*Shortlist*, macro F1
  0.9124 ± 0.0023 in CV). Reusing `build_model` means a tuned configuration
  merged there is picked up by re-running the export; `MODEL_VERSION` is bumped
  then.
- **Pipeline = Preprocessor + Estimator.** The preprocessor is a
  `ColumnTransformer` that selects the 54 `FEATURES` by name and passes them
  through unchanged. No scaling: a Random Forest splits on thresholds, so
  scaling has no effect (`docs/MODELING.md`, *Ensemble model: Random Forest*).
  The step is kept so that (a) the artifact has the ontology's pipeline shape
  and a later model that needs scaling or feature engineering only swaps the
  step, and (b) the pipeline exposes `feature_names_in_ == FEATURES`, which
  `app/serving.py` checks at load time.
- **Target: `Cover_Type` 1-7, not encoded.** Random Forest accepts any integer
  labels, so `classes_` is `[1..7]` and no decoding is needed. The serving
  contract accepts 1-7 or 0-6.
- **No data leakage.** `clean(load_raw())` then `split_train_val_test` (#16);
  the pipeline is fitted on the train set only. The validation set is only
  predicted, to record accuracy and macro F1 in the metadata. The test set is
  never touched.
- **Serialization.** `joblib.dump(pipeline, "models/model.joblib", compress=3)`.
  An unlimited-depth forest on 406,708 rows is large; compression keeps the
  file manageable for the API start-up and Docker (concern raised in #23).
  The observed size is recorded in the docs.
- **Label mapping and versioning.** `models/model_metadata.json` is written
  next to the model: `model_version`, creation time (UTC), SHA-256 and size of
  the model file, library versions (python, scikit-learn, joblib, numpy,
  pandas), estimator and hyperparameters, `random_state`, rows per partition
  used, `features`, validation metrics, and the label mapping (column index of
  `predict_proba` -> `Cover_Type` -> class name, from `CLASS_NAMES` of #15).
  The SHA-256 ties the metadata to one exact model file. `models/label_mapping.json`
  of #15 (encoded 0-6 mapping) is left as is.
- **Version scheme.** `MODEL_VERSION = "0.1.0"`: untuned primary model. Bump
  the minor version when the configuration changes (#29, #17) and the major
  version when the input contract changes.
- **Nothing under `models/` is committed** (`.gitignore`: `models/*`). The
  artifact is rebuilt with one command.
- **Self-check.** `main()` reloads the file through `app.serving.load_model`
  and fails if it is not ready, so a successful run means the artifact meets
  the serving contract.
- No new dependency (`joblib` is already pinned).

## Acceptance criteria

- [x] Bundle preprocessing + model into a pipeline
- [x] Serialize with joblib/pickle
- [x] Save label mapping
- [x] Version the artifact
- [x] Model artifact loadable and ready for inference
- [x] `app/serving.py` `load_model()` and `predict()` work on the exported file (added)
- [x] The pipeline is fitted on the train set only (added)

## Verification

```bash
python src/export_model.py
```

Expected: prints the partition sizes, validation accuracy and macro F1, the
path, size and SHA-256 of `models/model.joblib`, the path of
`models/model_metadata.json`, and `Serving contract check passed`.

Then, from the project root, load the file as the API does:

```bash
python -c "from types import SimpleNamespace as R; from app.serving import load_model, predict; m = load_model(); print(m.ready, m.error); print(predict(m, R(Elevation=2900, Aspect=150, Slope=12, Horizontal_Distance_To_Hydrology=250, Vertical_Distance_To_Hydrology=40, Horizontal_Distance_To_Roadways=2300, Hillshade_9am=215, Hillshade_Noon=225, Hillshade_3pm=140, Horizontal_Distance_To_Fire_Points=1900, Wilderness_Area=1, Soil_Type=29)))"
```

Expected: `True None` and a prediction with `cover_type` in 1-7, a
`class_name`, a `confidence` in (0, 1] and 7 probabilities that add up to 1.

`git status --short` must show no file under `models/` or `data/`.

Observed (2026-11-13, Python 3.12.10, scikit-learn 1.5.1, joblib 1.4.2):

- `python src/export_model.py` finished in about 2 minutes: fitted on 406,708
  training rows, validation accuracy 0.9520 and macro F1 0.9186 (87,152 rows),
  `models/model.joblib` 136.3 MB, SHA-256 `1ebf9fd4...9df51e`,
  `models/model_metadata.json` written with version `0.1.0` and the 7-entry
  label mapping, and `Serving contract check passed`.
- The `app.serving` command printed `True None`, then `cover_type` 2,
  `class_name` Lodgepole Pine, `confidence` 0.95 and 7 probabilities adding up
  to 1.0. Loading plus one prediction took about 10 s.
- `scripts/check_imports.py` reports `ok export_model`.
- `git status --short` showed only the spec, `src/export_model.py` and
  `docs/APP.md`; nothing under `models/` or `data/`.

Not verified:

- The HTTP endpoint (`uvicorn app.api:app`, `POST /predict`): `fastapi` is not
  installed in the local environment, so only `app/serving.py` was exercised.
- Loading the file under Python 3.11 (the project and Docker version); the
  export ran on Python 3.12.10 with the pinned scikit-learn 1.5.1.
- Train-only fitting is verified by reading the code (`fit_pipeline` receives
  only `X_train`, `y_train`), not by a test.
