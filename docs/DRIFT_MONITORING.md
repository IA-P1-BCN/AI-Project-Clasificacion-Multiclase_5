# Data drift monitoring

Issue #53 (optional, `Could`). Spec: [specs/feature-53-m8-data-drift-monitoring-with-alerts.md](../specs/feature-53-m8-data-drift-monitoring-with-alerts.md).

The API stores the inputs of every prediction (#34). This module compares the latest inputs with the data the model was trained on and raises an alert when they stop looking alike. It needs no labels, so it works from the first request, unlike the accuracy metrics of #35 that depend on feedback arriving later.

## Contents

- [Drift metric](#drift-metric)
- [How it works](#how-it-works)
- [Alerting](#alerting)
- [Running it](#running-it)
- [Configuration](#configuration)
- [Results](#results)
- [Limitations](#limitations)
- [Reproduction](#reproduction)

## Drift metric

The metric is the **Population Stability Index (PSI)**, computed for each of the 12 model inputs (10 numeric features plus `Wilderness_Area` and `Soil_Type`, which are decoded from the one-hot columns):

```
PSI = sum over bins of (actual - expected) * ln(actual / expected)
```

`expected` is the share of training rows in each bin and `actual` the share of the window being checked. Shares are floored at 1e-4 so an empty bin does not produce an infinite value.

| Input type | Bins |
|---|---|
| Numeric (10 features) | 10 decile bins of the train split |
| Categorical (`Wilderness_Area`, `Soil_Type`) | One bin per category; categories under 1 % of the train split are merged into one "other" bin |

| PSI | Level | Meaning |
|---|---|---|
| below 0.1 | `ok` | No relevant change |
| 0.1 to below 0.25 | `warning` | Moderate shift, worth watching |
| 0.25 or more | `alert` | Large shift |

The thresholds are the usual convention for PSI. A window is judged by its highest PSI. A window with fewer than 200 rows is `insufficient_data`.

The reference profile comes from the **train split only** (406,708 rows), never from validation or test. It is stored in `models/drift_reference.json` (git-ignored, like the model).

## How it works

- **Windows.** Consecutive predictions are grouped in windows of `DRIFT_WINDOW` rows (500 by default), counted back from the latest prediction. The oldest window can be partial.
- **Automatic check.** After every `DRIFT_CHECK_EVERY` predictions (500 by default, `0` turns it off) the API schedules a background check of the latest window. It never delays the response and never raises: a failing check is only logged.
- **On demand.** `GET /drift` reports the latest window with the PSI of every input and the previous windows.
- **Optional.** If the reference file does not exist the API serves predictions as usual, `/health` reports `drift.enabled: false` and `GET /drift` answers 503.

## Alerting

On a `warning` or an `alert` the check:

1. writes a warning line to the API log (`Data drift ALERT: max PSI 8.46 on ...`);
2. if `DRIFT_WEBHOOK_URL` is set, sends a JSON `POST` to it. The body has the keys `text` and `content` (so Slack and Discord incoming webhooks accept it) plus `status`, `max_psi`, `alerts`, `first_id` and `last_id`.

A webhook failure is logged and never reaches the caller.

## Running it

```bash
# Build the reference profile once, from the train split (needs data/raw/covtype.data).
docker compose exec app python src/drift_monitoring.py build
# The api service reads the profile at startup:
docker compose restart api

# Check the latest window of stored predictions (exit code 1 only on an alert):
docker compose exec api python src/drift_monitoring.py check

# Offline simulation on the validation split (no API needed):
docker compose exec app python src/drift_monitoring.py simulate
```

```
GET /drift?windows=5
```

Response fields: `status`, `window_size`, `thresholds`, `reference`, `latest` (with `features` and `alerts`) and `history`. See [APP.md](APP.md#backend-api-fastapi).

## Configuration

| Variable | Default | Description |
|---|---|---|
| `DRIFT_REFERENCE_PATH` | `models/drift_reference.json` | Reference profile written by `build` and read by the API |
| `DRIFT_WINDOW` | `500` | Predictions per window |
| `DRIFT_CHECK_EVERY` | `500` | Predictions between automatic checks; `0` turns them off |
| `DRIFT_WEBHOOK_URL` | empty | Optional webhook that receives warnings and alerts |

Restart `api` after changing them.

## Results

### Calibration on real data

`python src/drift_monitoring.py simulate` takes windows from the validation split, which has the same distribution as train, and shifts them in controlled ways.

| Scenario | Result |
|---|---|
| No drift (200 windows) | All 200 `ok`; the typical highest PSI is 0.04 and the 95th percentile 0.062, well under the 0.1 warning threshold. No false alarms |
| Elevation +50 m | Rarely flagged (8 % of the windows) |
| Elevation +100 m | Every window flagged |
| Elevation +150 m | Almost every window at `alert` |
| 30 % of the rows with another soil type | PSI 0.86, every window at `alert` |

Sanity check: the whole validation split against the reference gives PSI 0.0003. The thresholds were kept as they are.

### Check against the running API

Docker with MySQL, `DRIFT_WINDOW=200`, `DRIFT_CHECK_EVERY=200`, 400 identical requests (a fixed point, so obvious drift):

- `/health` reports `drift.enabled: true`.
- `GET /drift` answers `status: alert`, with the 12 inputs at `alert` (highest PSI 8.46 on `Vertical_Distance_To_Hydrology`). The oldest window has 45 rows and is `insufficient_data`.
- The automatic check at prediction 600 wrote `Data drift ALERT ... (ids 401-600)` to the API log.
- With `DRIFT_WEBHOOK_URL` pointing to a local listener on the host, the API delivered the JSON message (`User-Agent: covertype-drift-monitor/1.0`).
- `python src/drift_monitoring.py check` exited with code 1.

## Limitations

- **Input drift only.** The module detects changes in the inputs. A change in the relation between inputs and cover type (concept drift) is not detected; accuracy per variant from #35 and #52 is what shows it, and only when feedback arrives.
- **The reference is not refreshed.** After retraining (#36) the profile has to be rebuilt with `build`, otherwise the new model is compared with old data.
- **Windows end at the latest prediction.** The oldest window can be partial, and a short burst of unusual requests only shows in the window that contains it.
- **PSI depends on the binning.** Deciles are a common choice, but other binnings give other values; the thresholds are a convention, calibrated here only on this dataset.
- **No alert history.** Alerts go to the log and the webhook; they are not stored in the database, so `GET /drift` shows the windows as they are computed now.
- **Not tested with real traffic.** The checks use simulated shifts and identical requests; the webhook was tested against a local listener, not Slack or Discord.

## Reproduction

```bash
docker compose up -d --build
docker compose exec app python src/drift_monitoring.py build
docker compose restart api
docker compose exec app python src/drift_monitoring.py simulate
python -m pytest tests/test_drift_monitoring.py
```