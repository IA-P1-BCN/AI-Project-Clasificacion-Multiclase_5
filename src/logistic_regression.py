"""Simple supervised model (ticket #20): multiclass logistic regression under the CV protocol."""
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline

from baseline import N_SPLITS, RANDOM_STATE, evaluate_model
from data_audit import load_raw
from data_cleaning import FEATURES, TARGET, clean
from data_split import split_train_val_test
from feature_scaling import build_preprocessor

MAX_ITER = 1000


def build_pipeline() -> Pipeline:
    """Unfitted Pipeline: standard scaling of NUMERIC_FEATURES, then logistic regression.

    The preprocessor is a Pipeline step, so cross-validation refits it on each
    training fold and no validation row influences the scaling parameters.
    """
    return Pipeline(
        [
            ("preprocessor", build_preprocessor("standard")),
            ("model", LogisticRegression(max_iter=MAX_ITER, random_state=RANDOM_STATE)),
        ]
    )


def per_class_report(model, X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
    """Precision, recall, F1 and support per class from out-of-fold predictions.

    Uses the same folds as the CV protocol, so every row is predicted by a
    model that was not fitted on it. The last row holds the macro averages.
    """
    cv = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    predictions = cross_val_predict(model, X, y, cv=cv, n_jobs=-1)
    report = classification_report(y, predictions, output_dict=True, zero_division=0)
    rows = [str(label) for label in sorted(y.unique())] + ["macro avg"]
    table = pd.DataFrame(report).T.loc[rows]
    return table.astype({"support": int}).rename_axis(TARGET)


def main() -> None:
    df = clean(load_raw())
    X_train, _, _, y_train, _, _ = split_train_val_test(df[FEATURES], df[TARGET])

    scores = evaluate_model(build_pipeline(), X_train, y_train)
    report = per_class_report(build_pipeline(), X_train, y_train)

    fitted = build_pipeline().fit(X_train, y_train)
    iterations = int(fitted.named_steps["model"].n_iter_.max())

    print(f"== Logistic regression (stratified {N_SPLITS}-fold CV on {len(y_train):,} training rows) ==")
    print(f"Accuracy: {scores['accuracy_mean']:.4f} ± {scores['accuracy_std']:.4f}")
    print(f"Macro F1: {scores['macro_f1_mean']:.4f} ± {scores['macro_f1_std']:.4f}")
    print("\n== Per-class metrics (out-of-fold predictions) ==")
    print(report.round(4).to_string())
    print(f"\n== Convergence (fit on the full train set, max_iter={MAX_ITER}) ==")
    print(f"Iterations: {iterations}")
    print(f"Converged: {iterations < MAX_ITER}")


if __name__ == "__main__":
    main()
