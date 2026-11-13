"""Model export (ticket #32): fit the final pipeline on the train set and save it with its metadata."""
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.metrics import accuracy_score, f1_score
from sklearn.pipeline import Pipeline

from data_audit import load_raw
from data_cleaning import FEATURES, TARGET, clean
from data_split import RANDOM_STATE, split_train_val_test
from random_forest import build_model
from target_encoding import CLASS_NAMES

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "model.joblib"
METADATA_PATH = ROOT / "models" / "model_metadata.json"

# 0.1.0: untuned primary model of the shortlist (#23). Bump the minor version
# when the configuration changes (#29, #17), the major one when the input changes.
MODEL_VERSION = "0.1.0"
COMPRESSION = 3


def build_pipeline() -> Pipeline:
    """Unfitted pipeline: preprocessor + primary model of the shortlist.

    The preprocessor selects the 54 FEATURES by name and passes them through
    unchanged: a Random Forest needs no scaling (see docs/MODELING.md). It is
    kept as a step so the pipeline records `feature_names_in_` and a model that
    needs scaling or feature engineering only has to swap it.
    """
    preprocessor = ColumnTransformer(
        transformers=[("features", "passthrough", FEATURES)],
        remainder="drop",
        verbose_feature_names_out=False,
    ).set_output(transform="pandas")
    return Pipeline([("preprocessor", preprocessor), ("model", build_model())])


def fit_pipeline(X_train: pd.DataFrame, y_train: pd.Series) -> Pipeline:
    """Fit the pipeline on training rows only; the target stays Cover_Type (1-7)."""
    return build_pipeline().fit(X_train, y_train)


def validation_metrics(pipeline: Pipeline, X_val: pd.DataFrame, y_val: pd.Series) -> dict:
    """Accuracy and macro F1 of the fitted pipeline on rows it was not fitted on."""
    predictions = pipeline.predict(X_val)
    return {
        "accuracy": float(accuracy_score(y_val, predictions)),
        "macro_f1": float(f1_score(y_val, predictions, average="macro", zero_division=0)),
    }


def label_mapping(pipeline: Pipeline) -> list[dict]:
    """Column of `predict_proba` -> Cover_Type -> class name, in column order."""
    return [
        {"index": index, "cover_type": int(cover_type), "name": CLASS_NAMES[int(cover_type)]}
        for index, cover_type in enumerate(pipeline.classes_)
    ]


def sha256_of(path: Path) -> str:
    """SHA-256 of a file, read in chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_metadata(pipeline: Pipeline, model_path: Path, rows: dict, metrics: dict) -> dict:
    """Everything needed to identify and reproduce the exported model file."""
    estimator = pipeline.named_steps["model"]
    return {
        "model_version": MODEL_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model_file": model_path.name,
        "model_sha256": sha256_of(model_path),
        "model_size_bytes": model_path.stat().st_size,
        "estimator": type(estimator).__name__,
        "hyperparameters": estimator.get_params(),
        "tuned": False,  # #29 is not merged: default hyperparameters of #21
        "random_state": RANDOM_STATE,
        "pipeline_steps": [name for name, _ in pipeline.steps],
        "rows": rows,
        "validation_metrics": metrics,
        "features": list(pipeline.feature_names_in_),
        "target": TARGET,
        "label_mapping": label_mapping(pipeline),
        "versions": {
            "python": platform.python_version(),
            "scikit-learn": sklearn.__version__,
            "joblib": joblib.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "reproduce": "python src/export_model.py",
    }


def export(
    pipeline: Pipeline,
    rows: dict,
    metrics: dict,
    model_path: Path = MODEL_PATH,
    metadata_path: Path = METADATA_PATH,
) -> dict:
    """Serialize the fitted pipeline with joblib and write its metadata. Returns the metadata."""
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, model_path, compress=COMPRESSION)
    metadata = build_metadata(pipeline, model_path, rows, metrics)
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def check_contract(model_path: Path, X_sample: pd.DataFrame, expected: np.ndarray) -> None:
    """Raise AssertionError if the saved file does not meet the contract of app/serving.py.

    Loads the file exactly as the API does and compares its probabilities on
    `X_sample` with the ones of the in-memory pipeline (`expected`).
    """
    sys.path.insert(0, str(ROOT))
    from app.serving import load_model  # imported here: app/ is not on the path of src/ scripts

    loaded = load_model(model_path)
    assert loaded.ready, loaded.error
    assert list(loaded.model.feature_names_in_) == FEATURES, "feature names differ from FEATURES"
    assert sorted(loaded.cover_types) == sorted(CLASS_NAMES), "classes are not Cover_Type 1-7"
    probabilities = loaded.model.predict_proba(X_sample)
    assert probabilities.shape == (len(X_sample), len(CLASS_NAMES)), "unexpected predict_proba shape"
    assert np.allclose(probabilities.sum(axis=1), 1.0), "probabilities do not add up to 1"
    assert np.allclose(probabilities, expected), "reloaded model predicts differently"


def main() -> None:
    df = clean(load_raw())
    X_train, X_val, _, y_train, y_val, _ = split_train_val_test(df[FEATURES], df[TARGET])

    pipeline = fit_pipeline(X_train, y_train)
    metrics = validation_metrics(pipeline, X_val, y_val)
    rows = {"train": len(y_train), "validation": len(y_val)}
    metadata = export(pipeline, rows, metrics)

    sample = X_val.head(1000)
    check_contract(MODEL_PATH, sample, pipeline.predict_proba(sample))

    print(f"== Model export (version {MODEL_VERSION}) ==")
    print(f"Pipeline steps: {' -> '.join(metadata['pipeline_steps'])}")
    print(f"Estimator: {metadata['estimator']} (untuned, #29 pending)")
    print(f"Fitted on {rows['train']:,} training rows; test set not used")
    print(f"\n== Validation set ({rows['validation']:,} rows) ==")
    print(f"Accuracy: {metrics['accuracy']:.4f}")
    print(f"Macro F1: {metrics['macro_f1']:.4f}")
    print("\n== Label mapping (predict_proba column -> Cover_Type -> name) ==")
    print(pd.DataFrame(metadata["label_mapping"]).to_string(index=False))
    print("\n== Artifacts (git-ignored) ==")
    print(f"Model:    {MODEL_PATH} ({metadata['model_size_bytes'] / 1e6:.1f} MB)")
    print(f"SHA-256:  {metadata['model_sha256']}")
    print(f"Metadata: {METADATA_PATH}")
    print("\nServing contract check passed: app.serving.load_model() loads the file "
          "and it reproduces the in-memory predictions.")


if __name__ == "__main__":
    main()
