"""Simple supervised model (ticket #20): multiclass logistic regression under the CV protocol."""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import StratifiedKFold, cross_validate
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


def per_class_report(model, X: pd.DataFrame, y: pd.Series) -> tuple[pd.DataFrame, list[int]]:
    """Per-class metrics from out-of-fold predictions, and solver iterations per fold.

    Uses the same folds as the CV protocol, so every row is predicted by a
    model that was not fitted on it. The last row of the table holds the macro
    averages. The second value is the number of solver iterations of each
    fold's fit, which lets the caller check convergence on every fold: the
    folds are fitted in worker processes, where a `ConvergenceWarning` would
    not reach the parent process.
    """
    cv = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    folds = cross_validate(
        model, X, y, cv=cv, scoring="accuracy", n_jobs=-1, return_estimator=True, return_indices=True
    )
    predictions = np.empty(len(y), dtype=y.dtype)
    for estimator, test_index in zip(folds["estimator"], folds["indices"]["test"]):
        predictions[test_index] = estimator.predict(X.iloc[test_index])
    iterations = [int(estimator.named_steps["model"].n_iter_.max()) for estimator in folds["estimator"]]

    report = classification_report(y, predictions, output_dict=True, zero_division=0)
    rows = [str(label) for label in sorted(y.unique())] + ["macro avg"]
    table = pd.DataFrame(report).T.loc[rows]
    return table.astype({"support": int}).rename_axis(TARGET), iterations


def main() -> None:
    df = clean(load_raw())
    X_train, _, _, y_train, _, _ = split_train_val_test(df[FEATURES], df[TARGET])

    scores = evaluate_model(build_pipeline(), X_train, y_train)
    report, fold_iterations = per_class_report(build_pipeline(), X_train, y_train)

    fitted = build_pipeline().fit(X_train, y_train)
    full_iterations = int(fitted.named_steps["model"].n_iter_.max())
    converged = max(fold_iterations + [full_iterations]) < MAX_ITER

    print(f"== Logistic regression (stratified {N_SPLITS}-fold CV on {len(y_train):,} training rows) ==")
    print(f"Accuracy: {scores['accuracy_mean']:.4f} ± {scores['accuracy_std']:.4f}")
    print(f"Macro F1: {scores['macro_f1_mean']:.4f} ± {scores['macro_f1_std']:.4f}")
    print("\n== Per-class metrics (out-of-fold predictions) ==")
    print(report.round(4).to_string())
    print(f"\n== Convergence (max_iter={MAX_ITER}) ==")
    print(f"Iterations per CV fold: {fold_iterations}")
    print(f"Iterations on the full train set: {full_iterations}")
    print(f"Converged: {converged}")
    if not converged:
        raise RuntimeError(f"LogisticRegression reached max_iter={MAX_ITER} on at least one fit")


if __name__ == "__main__":
    main()
