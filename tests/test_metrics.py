"""Minimum-metrics tests (ticket #40).

The synthetic test proves the metric plumbing works and the pipeline beats a
trivial floor on separable data (always runs). ``test_recorded_metrics_*`` reads
the thresholds the real model actually reached from ``models/model_metadata.json``
(git-ignored), so CI, which has no artifact, skips it.
"""
import json

import pytest
from sklearn.model_selection import train_test_split

from conftest import METADATA_PATH, RANDOM_STATE
from export_model import fit_pipeline, validation_metrics
from final_metrics import partition_metrics

# Minimum thresholds for the exported model. Well below the recorded values
# (accuracy ~0.952, macro_f1 ~0.919 for the untuned RandomForest) so a normal
# re-export never makes the test flaky, while a real regression still trips it.
MIN_ACCURACY = 0.90
MIN_MACRO_F1 = 0.85

# The synthetic data is deliberately separable, but keep a conservative floor.
SYNTHETIC_MIN_MACRO_F1 = 0.80

requires_metadata = pytest.mark.skipif(
    not METADATA_PATH.exists(),
    reason="model metadata models/model_metadata.json not present",
)


# --- Metric plumbing on synthetic data (always run) ------------------------


def test_partition_metrics_keys_and_ranges(synthetic_xy):
    X, y = synthetic_xy
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.3, stratify=y, random_state=RANDOM_STATE
    )
    pipeline = fit_pipeline(X_train, y_train)
    metrics = partition_metrics(y_val, pipeline.predict(X_val))

    assert set(metrics) == {"accuracy", "precision_macro", "recall_macro", "macro_f1"}
    for value in metrics.values():
        assert 0.0 <= value <= 1.0


def test_pipeline_beats_floor_on_separable_data(synthetic_xy):
    X, y = synthetic_xy
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.3, stratify=y, random_state=RANDOM_STATE
    )
    pipeline = fit_pipeline(X_train, y_train)
    metrics = validation_metrics(pipeline, X_val, y_val)
    assert metrics["macro_f1"] >= SYNTHETIC_MIN_MACRO_F1
    assert metrics["accuracy"] >= SYNTHETIC_MIN_MACRO_F1


# --- Gated on the recorded metrics of the real export ----------------------


@requires_metadata
def test_recorded_metrics_meet_minimum_thresholds():
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    metrics = metadata["validation_metrics"]
    assert metrics["accuracy"] >= MIN_ACCURACY, metrics
    assert metrics["macro_f1"] >= MIN_MACRO_F1, metrics
