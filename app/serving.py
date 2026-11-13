"""Model loading and prediction for the API (ticket #34), independent of FastAPI.

The model file comes from the export of ticket #32. Contract: a scikit-learn
compatible object that takes a DataFrame with the 54 original FEATURES in the
training order and exposes `predict_proba` and `classes_`. Any feature
engineering or scaling lives inside the exported pipeline, so this module
always passes the raw features.
"""
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # the training modules are plain scripts

from data_cleaning import (  # noqa: E402
    FEATURES,
    NUMERIC_FEATURES,
    SOIL_FEATURES,
    WILDERNESS_FEATURES,
)
from target_encoding import CLASS_NAMES, DECODE  # noqa: E402

MODEL_PATH = Path(os.getenv("MODEL_PATH", ROOT / "models" / "model.joblib"))


@dataclass
class LoadedModel:
    """A model ready to serve, or the reason why there is none."""

    model: object = None
    cover_types: list = None  # Cover_Type (1-7) of each column of predict_proba
    error: str | None = None

    @property
    def ready(self) -> bool:
        return self.model is not None


def cover_types_of(classes) -> list:
    """Cover_Type (1-7) of each model class.

    The model may have been trained on Cover_Type (1-7) or on the encoded
    labels (0-6) of ticket #15; both are accepted.
    """
    classes = [int(c) for c in classes]
    if set(classes) == set(CLASS_NAMES):
        return classes
    if set(classes) == set(DECODE):
        return [DECODE[c] for c in classes]
    raise ValueError(
        f"Model classes {sorted(classes)} are neither Cover_Type 1-7 nor encoded labels 0-6."
    )


def load_model(path: Path = MODEL_PATH) -> LoadedModel:
    """Load the model; never raises, so the API can start without it."""
    path = Path(path)
    if not path.exists():
        return LoadedModel(error=f"Model file not found at {path}. Export the pipeline first (#32).")
    try:
        model = joblib.load(path)
        for attribute in ("predict_proba", "classes_"):
            if not hasattr(model, attribute):
                raise AttributeError(f"the model has no '{attribute}'")
        trained_on = getattr(model, "feature_names_in_", None)
        if trained_on is not None and list(trained_on) != FEATURES:
            raise ValueError("the model was trained on columns other than the 54 original FEATURES")
        return LoadedModel(model=model, cover_types=cover_types_of(model.classes_))
    except Exception as exc:  # a broken file must not stop the API from starting
        return LoadedModel(error=f"Could not load the model at {path}: {exc}")


def to_frame(request) -> pd.DataFrame:
    """One-row DataFrame with the 54 FEATURES, in the training order."""
    row = {name: float(getattr(request, name)) for name in NUMERIC_FEATURES}
    for index, column in enumerate(WILDERNESS_FEATURES, start=1):
        row[column] = int(request.Wilderness_Area == index)
    for index, column in enumerate(SOIL_FEATURES, start=1):
        row[column] = int(request.Soil_Type == index)
    return pd.DataFrame([row], columns=FEATURES)


def predict(loaded: LoadedModel, request) -> dict:
    """Predicted Cover_Type with its confidence and the probability of every class."""
    probabilities = loaded.model.predict_proba(to_frame(request))[0]
    best = int(probabilities.argmax())
    cover_type = loaded.cover_types[best]
    return {
        "cover_type": cover_type,
        "class_name": CLASS_NAMES[cover_type],
        "confidence": float(probabilities[best]),
        "probabilities": {
            CLASS_NAMES[ct]: float(p) for ct, p in zip(loaded.cover_types, probabilities)
        },
    }