"""Shared test configuration and fixtures (ticket #40).

Puts ``src/`` and the repository root on ``sys.path`` so the flat training
modules (imported by bare name) and the ``app`` package both resolve, then
exposes small synthetic fixtures that stand in for the git-ignored raw dataset
and model artifact, so the core suite runs with no external files.
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
# Same order as scripts/check_imports.py: src/ first (bare-name imports), then root (app package).
for path in (ROOT / "src", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from data_audit import COLUMNS  # noqa: E402
from data_cleaning import FEATURES, NUMERIC_FEATURES, SOIL_FEATURES, WILDERNESS_FEATURES  # noqa: E402
from target_encoding import COVER_TYPES  # noqa: E402

RANDOM_STATE = 42

# Artifact locations (all git-ignored); gated tests skip when they are absent.
RAW_DATA_PATH = ROOT / "data" / "raw" / "covtype.data"
MODEL_PATH = ROOT / "models" / "model.joblib"
METADATA_PATH = ROOT / "models" / "model_metadata.json"


def _make_dataset(n_per_class: int = 60, seed: int = RANDOM_STATE) -> pd.DataFrame:
    """A small, learnable frame with the 54 FEATURES, valid one-hot blocks and Cover_Type 1-7.

    ``Elevation`` is shifted per class so a tree model can separate the classes;
    every other column is random but kept inside its physical range. Exactly one
    wilderness area and one soil type are active per row, as in the real file.
    """
    rng = np.random.default_rng(seed)
    frames = []
    for cover_type in COVER_TYPES:
        rows = pd.DataFrame(index=range(n_per_class))
        rows["Elevation"] = rng.normal(2000 + cover_type * 250, 40, n_per_class)
        rows["Aspect"] = rng.uniform(0, 360, n_per_class)
        rows["Slope"] = rng.uniform(0, 45, n_per_class)
        rows["Horizontal_Distance_To_Hydrology"] = rng.uniform(0, 1000, n_per_class)
        rows["Vertical_Distance_To_Hydrology"] = rng.uniform(-100, 300, n_per_class)
        rows["Horizontal_Distance_To_Roadways"] = rng.uniform(0, 5000, n_per_class)
        rows["Hillshade_9am"] = rng.uniform(100, 255, n_per_class)
        rows["Hillshade_Noon"] = rng.uniform(100, 255, n_per_class)
        rows["Hillshade_3pm"] = rng.uniform(50, 255, n_per_class)
        rows["Horizontal_Distance_To_Fire_Points"] = rng.uniform(0, 5000, n_per_class)

        for column in WILDERNESS_FEATURES:
            rows[column] = 0
        active_wilderness = rng.integers(0, len(WILDERNESS_FEATURES), n_per_class)
        for i, column in enumerate(WILDERNESS_FEATURES):
            rows.loc[active_wilderness == i, column] = 1

        for column in SOIL_FEATURES:
            rows[column] = 0
        active_soil = rng.integers(0, len(SOIL_FEATURES), n_per_class)
        for i, column in enumerate(SOIL_FEATURES):
            rows.loc[active_soil == i, column] = 1

        rows["Cover_Type"] = cover_type
        frames.append(rows)

    data = pd.concat(frames, ignore_index=True)
    return data.sample(frac=1.0, random_state=seed).reset_index(drop=True)


@pytest.fixture(scope="session")
def synthetic_dataset() -> pd.DataFrame:
    """Full synthetic frame (55 columns): the 54 FEATURES plus Cover_Type."""
    data = _make_dataset()
    assert list(data.columns) == COLUMNS
    return data


@pytest.fixture(scope="session")
def synthetic_xy(synthetic_dataset):
    """``(X, y)`` split of the synthetic frame: the 54 FEATURES and Cover_Type."""
    return synthetic_dataset[FEATURES], synthetic_dataset["Cover_Type"]


@pytest.fixture
def numeric_features() -> list:
    return list(NUMERIC_FEATURES)
