"""Challenger export for the A/B test (ticket #52): the XGBoost tuned in #29 as a second model.

Same pipeline layout and serving contract as the main model (src/export_model.py):
the 54 raw FEATURES in, `predict_proba` and `classes_` (Cover_Type 1-7) out. It is
fitted on the train split only. Run it with the pinned versions, inside Docker:

    docker compose run --rm --no-deps app python src/export_challenger.py
"""
import json

import joblib
import pandas as pd
from sklearn.pipeline import Pipeline

from data_audit import load_raw
from data_cleaning import FEATURES, TARGET, clean
from data_split import split_train_val_test
from export_model import (
    COMPRESSION,
    ROOT,
    build_metadata,
    build_pipeline,
    check_contract,
    validation_metrics,
)
from gradient_boosting import build_models
from model_comparison import LabelOffsetClassifier

MODEL_B_PATH = ROOT / "models" / "model_b.joblib"
METADATA_B_PATH = ROOT / "models" / "model_b_metadata.json"
CHALLENGER_VERSION = "0.2.0"

# Best parameters of the XGBoost search of #29 (python src/hyperparameter_optimization.py).
XGB_PARAMS = {
    "learning_rate": 0.05,
    "n_estimators": 300,
    "max_depth": 12,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 3,
    "reg_lambda": 0.0,
    "reg_alpha": 1.0,
}


def build_challenger() -> Pipeline:
    """Unfitted pipeline: the preprocessor of the main model + the tuned XGBoost.

    XGBoost needs 0-indexed labels, so it is wrapped in `LabelOffsetClassifier`,
    which keeps `classes_` as Cover_Type 1-7 like the main model.
    """
    xgboost = build_models()["XGBoost"].set_params(**XGB_PARAMS)
    return build_pipeline().set_params(model=LabelOffsetClassifier(xgboost))


def main() -> None:
    df = clean(load_raw())
    X_train, X_val, _, y_train, y_val, _ = split_train_val_test(df[FEATURES], df[TARGET])

    pipeline = build_challenger().fit(X_train, y_train)
    metrics = validation_metrics(pipeline, X_val, y_val)
    rows = {"train": len(y_train), "validation": len(y_val)}

    MODEL_B_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_B_PATH, compress=COMPRESSION)
    metadata = build_metadata(pipeline, MODEL_B_PATH, rows, metrics)
    estimator = pipeline.named_steps["model"].estimator_
    metadata.update(
        model_version=CHALLENGER_VERSION,
        estimator=type(estimator).__name__,
        hyperparameters=estimator.get_params(),
        tuned=True,
        reproduce="python src/export_challenger.py",
    )
    METADATA_B_PATH.write_text(json.dumps(metadata, indent=2, default=str) + "\n", encoding="utf-8")

    sample = X_val.head(1000)
    check_contract(MODEL_B_PATH, sample, pipeline.predict_proba(sample))

    print(f"== Challenger export (version {CHALLENGER_VERSION}) ==")
    print(f"Pipeline steps: {' -> '.join(metadata['pipeline_steps'])}")
    print(f"Estimator: {metadata['estimator']} (tuned in #29)")
    print(f"Fitted on {rows['train']:,} training rows; test set not used")
    print(f"\n== Validation set ({rows['validation']:,} rows) ==")
    print(f"Accuracy: {metrics['accuracy']:.4f}")
    print(f"Macro F1: {metrics['macro_f1']:.4f}")
    print("\n== Label mapping (predict_proba column -> Cover_Type -> name) ==")
    print(pd.DataFrame(metadata["label_mapping"]).to_string(index=False))
    print("\n== Artifacts (git-ignored) ==")
    print(f"Model:    {MODEL_B_PATH} ({metadata['model_size_bytes'] / 1e6:.1f} MB)")
    print(f"SHA-256:  {metadata['model_sha256']}")
    print(f"Metadata: {METADATA_B_PATH}")
    print("\nServing contract check passed: app.serving.load_model() loads the file "
          "and it reproduces the in-memory predictions.")


if __name__ == "__main__":
    main()