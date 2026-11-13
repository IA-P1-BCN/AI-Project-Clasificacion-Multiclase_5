"""Compare all M4 models on one split and shortlist candidates (ticket #23).

Every model is re-evaluated on the canonical train split (`split_train_val_test`,
#16) with the shared protocol (`baseline.evaluate_model`,
`StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`, macro F1 as the
main metric), so the comparison is apples-to-apples. Each model reuses the exact
builder of its own ticket, so no hyperparameter is redefined here:

- LogisticRegression  -> `logistic_regression.build_pipeline` (#20)
- RandomForest        -> `random_forest.build_model` (#21)
- XGBoost / LightGBM  -> `gradient_boosting.build_models` (#22)
- MLP                 -> `neural_network.build_pipeline` (#24)
- Dummy baselines     -> `baseline.BASELINES` (#19)

Run every model (slow: the MLP CV takes about an hour):

    python src/model_comparison.py

Run a subset by name (XGBoost / LightGBM / the dummies are fast):

    python src/model_comparison.py XGBoost LightGBM DummyMostFrequent DummyStratified
"""
import sys

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin, clone
from sklearn.dummy import DummyClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import StratifiedKFold, cross_val_predict

import gradient_boosting
import logistic_regression
import neural_network
import random_forest
from baseline import N_SPLITS, RANDOM_STATE, evaluate_model
from data_audit import load_raw
from data_cleaning import FEATURES, TARGET, clean
from data_split import split_train_val_test
from gradient_boosting import CLASS_NAMES
from neural_network import HIDDEN_LAYER_SIZES
from random_forest import N_ESTIMATORS

CLASSES = list(CLASS_NAMES)


class LabelOffsetClassifier(BaseEstimator, ClassifierMixin):
    """Adapter for estimators that require 0-indexed labels (XGBoost).

    `Cover_Type` is 1..7, but modern XGBoost rejects labels that do not start at
    0. This wrapper maps `y` to 0-based for `fit` and shifts the predictions
    back, so the wrapped estimator runs under the shared protocol with the raw
    1..7 labels exactly like every other model. LightGBM encodes labels itself,
    so it does not need the wrapper.
    """

    def __init__(self, estimator):
        self.estimator = estimator

    def fit(self, X, y):
        y = np.asarray(y)
        self.offset_ = int(y.min())
        self.estimator_ = clone(self.estimator)
        self.estimator_.fit(X, y - self.offset_)
        self.classes_ = self.estimator_.classes_ + self.offset_
        return self

    def predict(self, X):
        return self.estimator_.predict(X) + self.offset_


def build_registry() -> dict:
    """Map a display name to the unfitted estimator built by its own ticket."""
    gb = gradient_boosting.build_models()
    return {
        "LogisticRegression": logistic_regression.build_pipeline(),
        f"RandomForest ({N_ESTIMATORS} trees)": random_forest.build_model(),
        "XGBoost": LabelOffsetClassifier(gb["XGBoost"]),
        "LightGBM": gb["LightGBM"],
        f"MLP {HIDDEN_LAYER_SIZES}": neural_network.build_pipeline(),
        "DummyClassifier (most_frequent)": DummyClassifier(strategy="most_frequent"),
        "DummyClassifier (stratified)": DummyClassifier(
            strategy="stratified", random_state=RANDOM_STATE
        ),
    }


def evaluate(model, X: pd.DataFrame, y: pd.Series) -> dict:
    """Headline scores plus per-class metrics for one model on the shared protocol.

    `accuracy` and `macro_f1` (mean ± std over the folds) come from
    `baseline.evaluate_model`. Macro precision / recall and the per-class F1
    come from pooled out-of-fold predictions over the same folds, so every row
    is predicted by a model that was not fitted on it.
    """
    scores = evaluate_model(model, X, y)

    cv = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    oof = cross_val_predict(model, X, y, cv=cv, n_jobs=-1)
    report = classification_report(y, oof, output_dict=True, zero_division=0)

    return {
        "accuracy_mean": scores["accuracy_mean"],
        "accuracy_std": scores["accuracy_std"],
        "macro_f1_mean": scores["macro_f1_mean"],
        "macro_f1_std": scores["macro_f1_std"],
        "precision_macro": report["macro avg"]["precision"],
        "recall_macro": report["macro avg"]["recall"],
        "f1_per_class": {cls: report[str(cls)]["f1-score"] for cls in CLASSES},
    }


def comparison_table(results: dict) -> pd.DataFrame:
    """One row per model, ranked by macro F1 (descending)."""
    rows = [
        {
            "Model": name,
            "Accuracy": r["accuracy_mean"],
            "Precision (macro)": r["precision_macro"],
            "Recall (macro)": r["recall_macro"],
            "F1 (macro)": r["macro_f1_mean"],
            "F1 std": r["macro_f1_std"],
        }
        for name, r in results.items()
    ]
    return (
        pd.DataFrame(rows)
        .sort_values("F1 (macro)", ascending=False)
        .reset_index(drop=True)
    )


def per_class_table(results: dict) -> pd.DataFrame:
    """Per-class F1 of every model, one column per model (ranked by macro F1)."""
    order = comparison_table(results)["Model"].tolist()
    data = {
        name: [results[name]["f1_per_class"][cls] for cls in CLASSES] for name in order
    }
    index = pd.Index([f"{cls} {CLASS_NAMES[cls]}" for cls in CLASSES], name=TARGET)
    return pd.DataFrame(data, index=index)


def main() -> None:
    df = clean(load_raw())
    X_train, _, _, y_train, _, _ = split_train_val_test(df[FEATURES], df[TARGET])

    registry = build_registry()
    requested = sys.argv[1:] or list(registry)
    unknown = [name for name in requested if name not in registry]
    if unknown:
        raise SystemExit(
            f"Unknown model(s): {unknown}. Choose from: {list(registry)}"
        )

    print(
        f"== Model comparison on the canonical train split "
        f"({len(y_train):,} rows, stratified {N_SPLITS}-fold CV) =="
    )
    print(f"Evaluating: {requested}\n")

    results = {}
    for name in requested:
        print(f"-- {name} ...", flush=True)
        results[name] = evaluate(registry[name], X_train, y_train)

    table = comparison_table(results)
    print("\n== Comparison table (ranked by macro F1) ==")
    print(table.round(4).to_string(index=False))

    print("\n== F1 per class (ranked by macro F1) ==")
    print(per_class_table(results).round(4).to_string())

    best = table.iloc[0]
    print(
        f"\nTop model: {best['Model']} "
        f"(macro F1 {best['F1 (macro)']:.4f}, accuracy {best['Accuracy']:.4f})"
    )


if __name__ == "__main__":
    main()
