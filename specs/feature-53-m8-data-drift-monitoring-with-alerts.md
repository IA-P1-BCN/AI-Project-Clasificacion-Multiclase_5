# Spec: Data drift monitoring with alerts (#53)

- **Issue:** #53 [M8] Data drift monitoring with alerts
- **Milestone:** M8 (optional stretch pool)
- **Branch:** `feature/53-m8-data-drift-monitoring-with-alerts`
- **Owner:** @Leandroletoile
- **Depends on:** #34, #35, #37 (backend, feedback, database), #32 (exported model)

## Goal

Detect when the inputs received by the API stop looking like the data the model
was trained on, and alert when that happens: define a drift metric, track the
input distribution over time and add alerting.

## Scope

In scope:

- A drift metric (PSI) per input feature against the training distribution.
- A reference profile built from the train split.
- Tracking over time with windows of consecutive predictions.
- Alerting: automatic check with a log warning and an optional webhook, the
  `GET /drift` endpoint and a command-line check with an exit code.
- A simulation on the validation set to measure false alarms and detection.
- Unit tests and documentation.

Out of scope: concept drift (changes in the relation between inputs and class,
which needs labels), automatic retraining on drift, a dashboard or UI, e-mail
delivery, persistence of alert history in a new table.

## Design

- **Monitored inputs.** The 12 inputs the API stores in `predictions`: the 10
  numeric features plus `Wilderness_Area` (1-4) and `Soil_Type` (1-40). The
  reference is built from the train split with the one-hot columns converted back
  to these two values, so both sides use the same representation.
- **Metric.** Population Stability Index,
  `PSI = sum((actual - expected) * ln(actual / expected))` over bins, with
  proportions floored at 1e-4. Numeric features use the decile edges of the
  reference as bins; values outside the reference range fall in the first or last
  bin. Categorical features use one bin per category, and categories with less
  than 1 % of the reference are merged into one "other" bin so rare categories do
  not create false alarms.
- **Levels.** PSI < 0.1 `ok`; 0.1 to < 0.25 `warning`; >= 0.25 `alert`. The status
  of a window is the worst level of its features. A window with fewer than 200
  rows is `insufficient_data`.
- **Reference.** `python src/drift_monitoring.py build` writes
  `models/drift_reference.json` (git-ignored): bin edges or categories, expected
  proportions, number of rows and creation time. The API reads it at startup; if
  it is missing, drift monitoring is off and `/health` says so.
- **Tracking over time.** `database.prediction_inputs` returns the stored inputs
  in order. Consecutive predictions are grouped in windows of `DRIFT_WINDOW`
  (default 500); each window reports its first and last prediction id and
  timestamps, its status and the PSI of every feature.
- **API.** `GET /drift?windows=N` returns the latest window with its per-feature
  PSI and alerts, and the summary of the previous N-1 windows.
- **Alerting.** Every `DRIFT_CHECK_EVERY` predictions (default 500, 0 = off) the
  API checks the latest window in a background task. A `warning` or `alert` is
  logged and, if `DRIFT_WEBHOOK_URL` is set, sent as a JSON POST (standard
  library, no new dependency; a failing webhook never breaks `/predict`).
  `python src/drift_monitoring.py check` runs the same check on the database and
  exits 1 on `alert`, so it can be scheduled.
- **Simulation.** `python src/drift_monitoring.py simulate` draws windows from the
  validation set: it counts false alarms over many windows with no drift and
  checks that shifted inputs (elevation +150 m and +300 m, a changed soil type
  mix) are detected. Results go to `docs/DRIFT_MONITORING.md`.

## Acceptance criteria

Copied from issue #53 (optional, only if time allows):

- [x] Drift metric defined
- [x] Input distribution tracked over time
- [x] Alerting added
- [x] Drift monitoring and alerts in place

## Verification / Result

- `python -m pytest`: 75 passed. The only test excluded locally is the one that loads
  the real exported model, because the local virtual environment has another
  scikit-learn version than the one that exported it (see guide D10.5); CI skips it
  (no model).
- `python src/drift_monitoring.py build` (Docker): reference profile built from the
  406,708 rows of the train split.
- `python src/drift_monitoring.py simulate` (Docker, validation split): no drift ->
  200 of 200 windows `ok` (typical highest PSI 0.04, p95 0.062); elevation +100 m is
  detected in every window and +150 m almost always reaches `alert`; changing the soil
  type of 30 % of the rows gives PSI 0.86. Full table in
  [docs/DRIFT_MONITORING.md](../docs/DRIFT_MONITORING.md).
- Docker with MySQL, `DRIFT_WINDOW=200`, `DRIFT_CHECK_EVERY=200`, 400 identical
  requests: `/health` reports `drift.enabled: true`; `GET /drift` answers `alert`
  (12 inputs, highest PSI 8.46) and the oldest window (45 rows) is
  `insufficient_data`; the automatic check wrote `Data drift ALERT` to the API log
  (ids 401-600); `check` exited with code 1.
- Webhook: with `DRIFT_WEBHOOK_URL` pointing to a local listener the API delivered the
  JSON message (`text`, `content`, `status`, `max_psi`, `alerts`).

Known limits (see the document): input drift only, the reference is not refreshed
after retraining, no alert history in the database, and it was tested with simulated
shifts, not real traffic or a real Slack/Discord webhook.