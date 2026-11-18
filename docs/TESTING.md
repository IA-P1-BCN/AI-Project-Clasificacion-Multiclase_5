# TESTING — Test suite

> Automated tests for the project. They run with `pytest` and are executed by the
> CI (#41) on every pull request and push to `develop`/`main`.

## How to run

```bash
pytest                              # the whole suite
pytest tests/test_end_to_end.py -v  # one file
pytest -k "synthetic"               # tests whose name matches
```

Inside Docker (the pinned environment):

```bash
docker compose run --rm --no-deps app python -m pytest
```

## What is covered

| File | Issue | What it checks |
|---|---|---|
| `tests/test_data_integrity.py` | #40 | Dataset shape, columns, one-hot blocks, no nulls. |
| `tests/test_model.py` | #40 | The pipeline fits, predicts valid labels and normalised probabilities; the serving layer loads a model and returns a well-formed prediction. |
| `tests/test_metrics.py` | #40 | The final-metrics helpers produce consistent numbers. |
| `tests/test_ab_testing.py` | #52 | Variant assignment and the A/B winner rule. |
| `tests/test_drift_monitoring.py` | #53 | PSI, windows and the drift alert rules. |
| `tests/test_end_to_end.py` | #42 | The real `POST /predict` endpoint predicts unseen data correctly through FastAPI's `TestClient`. |

## End-to-end test (#42)

`tests/test_end_to_end.py` exercises the full request path — FastAPI validation,
serving layer, model and response — with data the model never saw:

- **Synthetic (always runs):** fits the pipeline on 70 % of the synthetic frame
  from `tests/conftest.py` and predicts the held-out 30 % (>= 85 % accuracy).
- **Real (skipped when the artifacts are absent):** predicts 20 random rows of
  the real test split (>= 70 % accuracy). Requires `models/model.joblib` and
  `data/raw/covtype.data`.

The test calls the API through FastAPI's `TestClient`, so it needs `httpx`
(pinned in `requirements.txt`). The database is isolated in a temporary SQLite
file, so the test never touches the real one.

> **Local vs Docker.** The real layer needs a model exported with the **pinned**
> scikit-learn (1.5.1, Python 3.11). A model exported with another version (e.g.
> local Python 3.13 + sklearn 1.9.1) does not load, and the test **skips**
> instead of failing. Run it in Docker, or deselect it locally:
> `pytest --deselect tests/test_end_to_end.py::test_predict_real_test_set`.
