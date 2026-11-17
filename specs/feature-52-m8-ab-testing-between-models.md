# Spec: A/B testing between models (#52)

- **Issue:** #52 [M8] A/B testing between models
- **Milestone:** M8 (optional stretch pool)
- **Branch:** `feature/52-m8-ab-testing-between-models`
- **Owner:** @Leandroletoile
- **Depends on:** #34, #35, #37 (backend, feedback, database), #29 (tuned models)

## Goal

Compare two models in production through an A/B test: serve both versions,
split traffic between them, collect per-variant metrics from the existing
feedback loop, and decide a winner with an explicit statistical rule.

## Scope

In scope:

- Serve a control model (A) and a challenger model (B) from the same API.
- Random traffic split controlled by configuration.
- Store the variant of every prediction and report metrics per variant.
- Winner decision rule (two-proportion z-test) exposed by the API.
- Offline simulation over the validation set to document results.
- Unit tests and documentation.

Out of scope: sticky assignment per user (requests carry no user id), more than
two variants, multi-armed bandits, UI for the results.

## Design

- **Variants.** A = `MODEL_PATH` (random forest 0.1.0, untuned). B =
  `MODEL_B_PATH` (default `models/model_b.joblib`), the XGBoost tuned in #29
  (`learning_rate=0.05, n_estimators=300, max_depth=12, subsample=0.8,
  colsample_bytree=0.8, min_child_weight=3, reg_lambda=0.0, reg_alpha=1.0`).
  B is exported by `src/export_challenger.py` with the same pipeline layout and
  serving contract as A. Version 0.2.0.
- **Traffic split.** `AB_TRAFFIC_B` in [0, 1] (default 0 = A/B disabled, every
  request goes to A). If B fails to load, every request goes to A and `/health`
  reports it. `POST /predict?variant=A|B` forces a variant (tests, simulation).
- **Storage.** `predictions.variant` (`'A'` / `'B'`, default `'A'`), added by an
  automatic migration of existing tables. `model_version` already stored per row.
- **Results.** `GET /ab/results`: per variant predictions, feedback, correct,
  live accuracy and average confidence; z-test of the accuracy difference;
  `decision` in `{winner_A, winner_B, inconclusive, insufficient_data}`.
- **Decision rule.** At least 200 feedback entries per variant, then a winner
  only if p < 0.05 (two-sided) and the accuracy difference is >= 0.5 points;
  otherwise `inconclusive`.
- **Simulation.** `src/ab_simulation.py` replays validation rows through the two
  exported models with a random split, uses the true label as feedback on a
  temporary SQLite database, and prints the same report as the endpoint.
  Results are recorded in `docs/AB_TESTING.md`.
- **Shared code.** `LabelOffsetClassifier` gets `predict_proba` (needed by the
  serving contract); no behavior change for existing uses.

## Acceptance criteria

Copied from issue #52 (optional, only if time allows):

- [x] Two model versions served
- [x] Traffic split and per-variant metrics collected
- [x] Winner decided with a documented rule
- [x] A/B test results documented

## Verification / Result

- `python -m pytest`: 44 passed (19 of them in `tests/test_ab_testing.py` plus the
  existing suite). The only test excluded locally is the one that loads the real
  exported model, because the local virtual environment has another scikit-learn
  version than the one that exported it (see guide D10.5); CI skips it (no model).
- `python src/export_challenger.py` (Docker): XGBoost 0.2.0, 19.6 MB, validation
  accuracy 0.9471 and macro F1 0.9244; the serving contract check passes.
- `python src/ab_simulation.py` (Docker, seed 42): offline McNemar p = 3.6e-16 in
  favour of A in accuracy; 10,000 requests -> `inconclusive` (p = 0.08); 60,000
  requests -> `winner_A` (-0.66 points, p = 0.0002); A/A control `inconclusive`
  in both runs. Full tables in [docs/AB_TESTING.md](../docs/AB_TESTING.md).
- Docker with `AB_TRAFFIC_B=0.5` and MySQL: `/health` reports `ab_test`, 40 requests
  split 24 A / 16 B, `/ab/results` counts per variant (`insufficient_data`),
  `?variant=B` serves B, `?variant=C` returns 422, and a row stored before the
  migration appears as variant A.

Known limits (see the document): accuracy is the criterion, while macro F1 is
the project metric and favours B; the simulation labels every request.