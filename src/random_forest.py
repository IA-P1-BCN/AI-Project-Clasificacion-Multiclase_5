"""Ensemble model (ticket #21): Random Forest under the CV protocol."""
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import StratifiedKFold, cross_val_predict

from baseline import N_SPLITS, RANDOM_STATE, evaluate_model
from data_audit import load_raw
from data_cleaning import FEATURES, TARGET, clean
from data_split import split_train_val_test

N_ESTIMATORS = 100


def build_model() -> RandomForestClassifier:
    """Unfitted Random Forest with default hyperparameters.

    No preprocessor: a Random Forest splits on thresholds, so rescaling the
    numeric features has no effect and the model trains on the raw (cleaned)
    FEATURES. The forest is the only thing learned from data, and
    cross-validation refits it on each training fold, so there is no leakage.
    """
    return RandomForestClassifier(
        n_estimators=N_ESTIMATORS, random_state=RANDOM_STATE, n_jobs=-1
    )


def per_class_report(model, X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
    """Precision, recall, F1 and support per class from out-of-fold predictions.

    Uses the same folds as the CV protocol, so every row is predicted by a
    forest that was not fitted on it. The last row holds the macro averages.
    """
    cv = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    predictions = cross_val_predict(model, X, y, cv=cv, n_jobs=-1)
    report = classification_report(y, predictions, output_dict=True, zero_division=0)
    rows = [str(label) for label in sorted(y.unique())] + ["macro avg"]
    table = pd.DataFrame(report).T.loc[rows]
    return table.astype({"support": int}).rename_axis(TARGET)


def feature_importances(model, X: pd.DataFrame, y: pd.Series) -> pd.Series:
    """Fit on the training rows and return the impurity importances, descending."""
    model.fit(X, y)
    return pd.Series(model.feature_importances_, index=FEATURES).sort_values(
        ascending=False
    )


def main() -> None:
    df = clean(load_raw())
    X_train, _, _, y_train, _, _ = split_train_val_test(df[FEATURES], df[TARGET])

    scores = evaluate_model(build_model(), X_train, y_train)
    report = per_class_report(build_model(), X_train, y_train)
    importances = feature_importances(build_model(), X_train, y_train)

    print(f"== Random Forest ({N_ESTIMATORS} trees, stratified {N_SPLITS}-fold CV on {len(y_train):,} training rows) ==")
    print(f"Accuracy: {scores['accuracy_mean']:.4f} ± {scores['accuracy_std']:.4f}")
    print(f"Macro F1: {scores['macro_f1_mean']:.4f} ± {scores['macro_f1_std']:.4f}")
    print("\n== Per-class metrics (out-of-fold predictions) ==")
    print(report.round(4).to_string())
    print("\n== Top 10 feature importances (mean decrease in impurity, full train set) ==")
    print(importances.head(10).round(4).to_string())


if __name__ == "__main__":
    main()
