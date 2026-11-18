"""End-to-end test of the prediction API (ticket #42).

Exercises the full request path — FastAPI validation (Pydantic) -> serving
layer -> model -> response — with data the model never saw:

- ``test_predict_synthetic_unseen`` always runs: it fits the real project
  pipeline on synthetic rows and serves it through the real FastAPI app, then
  calls ``POST /predict`` with held-out rows.
- ``test_predict_real_test_set`` is gated on the git-ignored artifacts
  (``models/model.joblib`` and ``data/raw/covtype.data``): it predicts rows of
  the real test split, which the model was never trained on, and checks the
  predicted cover type against the true label.

The Streamlit UI is a thin client on top of this API, so the API path is the
end-to-end contract that can be automated (the manual UI check is out of scope).
"""
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.serving import LoadedModel, cover_types_of, load_model
from conftest import MODEL_PATH, RAW_DATA_PATH
from data_audit import load_raw
from data_cleaning import (
    FEATURES,
    NUMERIC_FEATURES,
    SOIL_FEATURES,
    TARGET,
    WILDERNESS_FEATURES,
    clean,
)
from data_split import split_train_val_test
from export_model import fit_pipeline
from target_encoding import CLASS_NAMES

requires_real_artifacts = pytest.mark.skipif(
    not (MODEL_PATH.exists() and RAW_DATA_PATH.exists()),
    reason="needs models/model.joblib and data/raw/covtype.data",
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A TestClient backed by an isolated SQLite database and no A/B routing."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/e2e.db")
    monkeypatch.setenv("AB_TRAFFIC_B", "0")  # keep /predict on model A (#52)
    with TestClient(app) as test_client:
        yield test_client


def _compact_request(row) -> dict:
    """Turn one 54-feature row into the 12-field compact request the API expects."""
    payload = {name: float(row[name]) for name in NUMERIC_FEATURES}
    payload["Wilderness_Area"] = int(np.argmax([row[c] for c in WILDERNESS_FEATURES])) + 1
    payload["Soil_Type"] = int(np.argmax([row[c] for c in SOIL_FEATURES])) + 1
    return payload


def _assert_well_formed(body: dict) -> None:
    """The response obeys the PredictionResponse contract."""
    assert body["cover_type"] in CLASS_NAMES
    assert body["class_name"] == CLASS_NAMES[body["cover_type"]]
    assert 0.0 <= body["confidence"] <= 1.0
    assert set(body["probabilities"]) == set(CLASS_NAMES.values())
    assert np.isclose(sum(body["probabilities"].values()), 1.0)


def _serve(monkeypatch, pipeline) -> None:
    """Make the API serve this fitted pipeline; monkeypatch restores it afterwards."""
    monkeypatch.setattr(
        app.state,
        "loaded",
        LoadedModel(model=pipeline, cover_types=cover_types_of(pipeline.classes_)),
    )


def test_predict_synthetic_unseen(client, monkeypatch, synthetic_xy):
    """The API predicts unseen synthetic rows correctly through the full path."""
    X, y = synthetic_xy
    split = int(len(X) * 0.7)
    pipeline = fit_pipeline(X.iloc[:split], y.iloc[:split])
    _serve(monkeypatch, pipeline)

    X_unseen = X.iloc[split:]
    y_unseen = y.iloc[split:]
    correct = 0
    for row, true_label in zip(X_unseen.to_dict("records"), y_unseen):
        response = client.post("/predict", json=_compact_request(row))
        assert response.status_code == 200, response.text
        body = response.json()
        _assert_well_formed(body)
        correct += int(body["cover_type"] == int(true_label))

    accuracy = correct / len(X_unseen)
    print(f"synthetic unseen accuracy: {accuracy:.0%} on {len(X_unseen)} rows")
    assert accuracy >= 0.85, f"synthetic unseen accuracy {accuracy:.0%} is too low"


@requires_real_artifacts
def test_predict_real_test_set(client, monkeypatch):
    """The exported model predicts real test-set rows (never seen) correctly."""
    loaded = load_model(MODEL_PATH)
    if not loaded.ready:
        # A model exported with another scikit-learn version (e.g. local Python
        # 3.13 + sklearn 1.9.1) does not load here; skip instead of failing, like
        # the other gated tests. In Docker/CI the pinned version loads it.
        pytest.skip(f"model artifact does not load in this environment: {loaded.error}")
    monkeypatch.setattr(app.state, "loaded", loaded)

    df = clean(load_raw())
    _, _, X_test, _, _, y_test = split_train_val_test(df[FEATURES], df[TARGET])

    rng = np.random.RandomState(42)
    indices = rng.choice(len(X_test), size=300, replace=False)

    correct = 0
    for index in indices:
        response = client.post("/predict", json=_compact_request(X_test.iloc[index]))
        assert response.status_code == 200, response.text
        body = response.json()
        _assert_well_formed(body)
        correct += int(body["cover_type"] == int(y_test.iloc[index]))

    accuracy = correct / len(indices)
    print(f"real test-set accuracy: {accuracy:.0%} on {len(indices)} rows")
    assert accuracy >= 0.85, f"real test-set accuracy {accuracy:.0%} is too low"
