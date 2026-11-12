"""Train XGBoost and LightGBM gradient-boosted ensembles (ticket #22)."""
from collections import defaultdict

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedKFold, train_test_split
from xgboost import XGBClassifier

from data_audit import load_raw
from data_cleaning import FEATURES, TARGET, clean

RANDOM_STATE = 42
N_SPLITS = 5
TEST_SIZE = 0.3

CV = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)

CLASS_NAMES = {
    1: "Spruce/Fir",
    2: "Lodgepole Pine",
    3: "Ponderosa Pine",
    4: "Cottonwood/Willow",
    5: "Aspen",
    6: "Douglas-fir",
    7: "Krummholz",
}
CLASSES = list(CLASS_NAMES)
METRICS = ["accuracy", "precision_macro", "recall_macro", "f1_macro"]


def build_models() -> dict:
    """Return the two gradient-boosted models with default hyperparameters."""
    return {
        "XGBoost": XGBClassifier(random_state=RANDOM_STATE, n_jobs=-1),
        "LightGBM": LGBMClassifier(
            random_state=RANDOM_STATE, n_jobs=-1, verbosity=-1
        ),
    }


def cross_val_evaluate(model, X, y):
    """Evaluate a model with 5-fold stratified CV.

    Returns a dict with, per metric, the mean and std across folds, plus the
    F1 per class (mean and std). Fits the model once per fold.

    `y` is Cover_Type (1..7). XGBoost requires 0-indexed labels, so we fit on
    `y - 1` and shift predictions back to 1..7 for the metrics.
    """
    y_enc = y - 1
    fold_scores = defaultdict(list)

    for train_idx, val_idx in CV.split(X, y_enc):
        model.fit(X[train_idx], y_enc[train_idx])
        y_pred = model.predict(X[val_idx]) + 1  # back to Cover_Type 1..7
        y_val = y[val_idx]

        fold_scores["accuracy"].append(accuracy_score(y_val, y_pred))
        fold_scores["precision_macro"].append(
            precision_score(y_val, y_pred, average="macro", zero_division=0)
        )
        fold_scores["recall_macro"].append(
            recall_score(y_val, y_pred, average="macro", zero_division=0)
        )
        fold_scores["f1_macro"].append(
            f1_score(y_val, y_pred, average="macro", zero_division=0)
        )

        report = classification_report(
            y_val, y_pred, labels=CLASSES, output_dict=True, zero_division=0
        )
        for cls in CLASSES:
            fold_scores[f"f1_class_{cls}"].append(report[str(cls)]["f1-score"])

    summary = {}
    for metric in METRICS:
        values = fold_scores[metric]
        summary[metric] = {
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
        }
    summary["f1_per_class"] = {
        cls: {
            "mean": float(np.mean(fold_scores[f"f1_class_{cls}"])),
            "std": float(np.std(fold_scores[f"f1_class_{cls}"])),
        }
        for cls in CLASSES
    }
    return summary


def feature_importances(model, X, y):
    """Fit on the training rows and return importances sorted descending."""
    model.fit(X, y - 1)  # XGBoost requires 0-indexed labels
    return pd.Series(model.feature_importances_, index=FEATURES).sort_values(
        ascending=False
    )


def _metric_table(summary: dict) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "metric": METRICS,
            "mean": [f"{summary[m]['mean']:.4f}" for m in METRICS],
            "std": [f"{summary[m]['std']:.4f}" for m in METRICS],
        }
    )


def _per_class_table(summary: dict) -> pd.DataFrame:
    per_class = summary["f1_per_class"]
    return pd.DataFrame(
        {
            "class": CLASSES,
            "name": [CLASS_NAMES[cls] for cls in CLASSES],
            "f1_mean": [f"{per_class[cls]['mean']:.4f}" for cls in CLASSES],
            "f1_std": [f"{per_class[cls]['std']:.4f}" for cls in CLASSES],
        }
    )


def main() -> None:
    df = clean(load_raw())
    X = df[FEATURES].to_numpy()
    y = df[TARGET].to_numpy()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE
    )

    print("== Data ==")
    print(f"Rows after cleaning: {len(df):,}")
    print(f"Train rows ({1 - TEST_SIZE:.0%}): {len(X_train):,}")
    print(f"Test rows ({TEST_SIZE:.0%}, held out): {len(X_test):,}")

    for name, model in build_models().items():
        print(f"\n== {name}: {N_SPLITS}-fold stratified CV ==")
        summary = cross_val_evaluate(model, X_train, y_train)

        print(_metric_table(summary).to_string(index=False))

        print("\nF1 per class:")
        print(_per_class_table(summary).to_string(index=False))

        importances = feature_importances(model, X_train, y_train)
        print(f"\nTop 10 features ({name}):")
        print(importances.head(10).to_string())


if __name__ == "__main__":
    main()
