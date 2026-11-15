"""Imbalance handling (ticket #17): inverse-frequency class weights for the
shortlisted models.

Strategy (see docs/PREPROCESSING.md): "balanced" (inverse-frequency) class
weights, applied only at fit time on the training fold. The comparison runs
under the shared protocol (StratifiedKFold 5, macro F1 as the main metric) for
the two shortlisted models (#23): Random Forest and XGBoost.
"""
from collections import defaultdict

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.utils.class_weight import compute_class_weight

from baseline import N_SPLITS, RANDOM_STATE
from data_audit import load_raw
from data_cleaning import FEATURES, TARGET, clean
from data_split import class_shares, split_train_val_test
from gradient_boosting import build_models
from model_comparison import CLASSES, CLASS_NAMES, LabelOffsetClassifier
from random_forest import build_model

CV = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
METRICS = ["accuracy", "precision_macro", "recall_macro", "f1_macro"]
MINORITY_CLASSES = [4, 5, 6, 7]


def build_shortlist() -> dict:
    """Return the two shortlisted models (#23), each from its own builder."""
    return {
        "RandomForest": build_model(),
        "XGBoost": LabelOffsetClassifier(build_models()["XGBoost"]),
    }


def balanced_class_weights(y) -> dict:
    """Inverse-frequency ("balanced") weight per class, as {class: weight}."""
    classes = np.unique(y)
    weights = compute_class_weight(class_weight="balanced", classes=classes, y=y)
    return {int(cls): float(w) for cls, w in zip(classes, weights)}


def to_sample_weight(y, class_weights: dict) -> np.ndarray:
    """Per-row weight array for `fit(sample_weight=...)` from a class->weight map."""
    return np.asarray([class_weights[int(cls)] for cls in y])


def cross_val_evaluate(model, X, y, class_weights=None) -> dict:
    """Evaluate a model with 5-fold stratified CV, optionally with class weights.

    Mirrors `baseline.evaluate_model` / `model_comparison.evaluate` but supports
    a per-row `sample_weight` at fit time. Weights are computed from each
    training fold's `y` only (leakage-safe); validation folds are scored
    unweighted. Returns mean ± std for the headline metrics and the per-class F1.
    """
    fold_scores = defaultdict(list)

    for train_idx, val_idx in CV.split(X, y):
        X_train, y_train = X[train_idx], y[train_idx]
        X_val, y_val = X[val_idx], y[val_idx]

        sample_weight = (
            to_sample_weight(y_train, class_weights) if class_weights else None
        )
        model.fit(X_train, y_train, sample_weight=sample_weight)
        y_pred = model.predict(X_val)

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

    summary = {
        metric: {
            "mean": float(np.mean(fold_scores[metric])),
            "std": float(np.std(fold_scores[metric])),
        }
        for metric in METRICS
    }
    summary["f1_per_class"] = {
        cls: float(np.mean(fold_scores[f"f1_class_{cls}"])) for cls in CLASSES
    }
    return summary


def _comparison_table(default: dict, weighted: dict) -> pd.DataFrame:
    rows = []
    for metric in METRICS:
        rows.append(
            {
                "Metric": metric,
                "Default": f"{default[metric]['mean']:.4f} ± {default[metric]['std']:.4f}",
                "Weighted": f"{weighted[metric]['mean']:.4f} ± {weighted[metric]['std']:.4f}",
            }
        )
    for cls in MINORITY_CLASSES:
        rows.append(
            {
                "Metric": f"F1 class {cls} ({CLASS_NAMES[cls]})",
                "Default": f"{default['f1_per_class'][cls]:.4f}",
                "Weighted": f"{weighted['f1_per_class'][cls]:.4f}",
            }
        )
    return pd.DataFrame(rows)


def compare_with_without(X_train, y_train) -> tuple:
    """Default vs class-weighted for each shortlisted model on the same folds."""
    class_weights = balanced_class_weights(y_train)
    results = {}
    for name, model in build_shortlist().items():
        results[name] = {
            "default": cross_val_evaluate(model, X_train, y_train),
            "weighted": cross_val_evaluate(model, X_train, y_train, class_weights),
        }
    return class_weights, results


def main() -> None:
    df = clean(load_raw())
    X = df[FEATURES].to_numpy()
    y = df[TARGET].to_numpy()

    X_train, _, _, y_train, _, _ = split_train_val_test(X, y)

    print("== Data ==")
    print(f"Rows after cleaning: {len(df):,}")
    print(f"Train rows: {len(X_train):,}")

    print("\n== Class shares on the training partition (%) ==")
    print(class_shares(pd.Series(y_train)).round(3).to_string())

    class_weights, results = compare_with_without(X_train, y_train)

    print("\n== Inverse-frequency class weights (balanced) ==")
    print(pd.Series(class_weights, name="weight").round(4).to_string())

    for name in results:
        print(f"\n== {name}: default vs class-weighted ({N_SPLITS}-fold CV) ==")
        print(_comparison_table(results[name]["default"], results[name]["weighted"]).to_string(index=False))


if __name__ == "__main__":
    main()
