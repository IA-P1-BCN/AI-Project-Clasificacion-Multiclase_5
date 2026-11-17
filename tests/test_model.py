"""Model behavior tests (ticket #40): the pipeline fits and predicts validly,
and the serving layer loads a model and returns a well-formed prediction.

The synthetic tests always run. ``test_real_model_*`` runs only when
``models/model.joblib`` is present (git-ignored), so CI skips it.
"""
import joblib
import numpy as np
import pytest

from conftest import MODEL_PATH
from app.schemas import PredictionRequest
from app.serving import load_model, predict, to_frame
from data_cleaning import FEATURES
from export_model import build_pipeline, fit_pipeline
from target_encoding import CLASS_NAMES, COVER_TYPES

requires_model = pytest.mark.skipif(
    not MODEL_PATH.exists(), reason="model artifact models/model.joblib not present"
)

SAMPLE_REQUEST = PredictionRequest(
    Elevation=2900,
    Aspect=150,
    Slope=12,
    Horizontal_Distance_To_Hydrology=250,
    Vertical_Distance_To_Hydrology=40,
    Horizontal_Distance_To_Roadways=2300,
    Hillshade_9am=215,
    Hillshade_Noon=225,
    Hillshade_3pm=140,
    Horizontal_Distance_To_Fire_Points=1900,
    Wilderness_Area=1,
    Soil_Type=29,
)


@pytest.fixture(scope="module")
def fitted_pipeline(synthetic_xy):
    """The real project pipeline, fitted on the synthetic data."""
    X, y = synthetic_xy
    return fit_pipeline(X, y)


# --- Pipeline contract (always run) ----------------------------------------


def test_pipeline_records_the_54_features(fitted_pipeline):
    assert list(fitted_pipeline.feature_names_in_) == FEATURES


def test_pipeline_classes_are_cover_types(fitted_pipeline):
    assert set(int(c) for c in fitted_pipeline.classes_) <= set(COVER_TYPES)


def test_pipeline_predict_returns_valid_labels(fitted_pipeline, synthetic_xy):
    X, _ = synthetic_xy
    predictions = fitted_pipeline.predict(X)
    assert len(predictions) == len(X)
    assert set(int(p) for p in predictions) <= set(COVER_TYPES)


def test_pipeline_predict_proba_is_a_distribution(fitted_pipeline, synthetic_xy):
    X, _ = synthetic_xy
    proba = fitted_pipeline.predict_proba(X)
    assert proba.shape == (len(X), len(fitted_pipeline.classes_))
    assert np.allclose(proba.sum(axis=1), 1.0)
    assert (proba >= 0).all() and (proba <= 1).all()


# --- Serving layer (always run) --------------------------------------------


def test_to_frame_builds_the_54_feature_row():
    frame = to_frame(SAMPLE_REQUEST)
    assert list(frame.columns) == FEATURES
    assert frame.shape == (1, 54)
    # Compact input expands to exactly one active wilderness area and one soil type.
    assert int(frame["Wilderness_Area1"].iloc[0]) == 1
    assert int(frame["Soil_Type29"].iloc[0]) == 1
    assert frame[[f"Wilderness_Area{i}" for i in range(1, 5)]].sum(axis=1).iloc[0] == 1
    assert frame[[f"Soil_Type{i}" for i in range(1, 41)]].sum(axis=1).iloc[0] == 1


def test_load_model_missing_file_is_not_ready(tmp_path):
    loaded = load_model(tmp_path / "missing.joblib")
    assert not loaded.ready
    assert loaded.error is not None


def test_load_model_roundtrip_and_predict(fitted_pipeline, tmp_path):
    path = tmp_path / "model.joblib"
    joblib.dump(fitted_pipeline, path)

    loaded = load_model(path)
    assert loaded.ready
    # The reloaded model decodes to the same Cover_Types the pipeline was trained on.
    assert sorted(loaded.cover_types) == sorted(int(c) for c in fitted_pipeline.classes_)

    result = predict(loaded, SAMPLE_REQUEST)
    assert result["cover_type"] in COVER_TYPES
    assert result["class_name"] == CLASS_NAMES[result["cover_type"]]
    assert 0.0 <= result["confidence"] <= 1.0
    assert set(result["probabilities"]) == set(CLASS_NAMES.values())
    assert np.isclose(sum(result["probabilities"].values()), 1.0)


def test_build_pipeline_is_unfitted():
    pipeline = build_pipeline()
    # An unfitted pipeline has not learned classes yet.
    assert not hasattr(pipeline, "classes_")


# --- Gated on the real exported model --------------------------------------


@requires_model
def test_real_model_loads_and_predicts():
    loaded = load_model(MODEL_PATH)
    assert loaded.ready, loaded.error
    assert list(loaded.model.feature_names_in_) == FEATURES
    assert sorted(loaded.cover_types) == sorted(COVER_TYPES)

    result = predict(loaded, SAMPLE_REQUEST)
    assert result["cover_type"] in COVER_TYPES
    assert 0.0 <= result["confidence"] <= 1.0
    assert np.isclose(sum(result["probabilities"].values()), 1.0)
