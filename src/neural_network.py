"""Neural network (ticket #24): multilayer perceptron with early stopping under the CV protocol."""
import pandas as pd
from sklearn.metrics import classification_report
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline

from baseline import N_SPLITS, RANDOM_STATE, evaluate_model
from data_audit import load_raw
from data_cleaning import FEATURES, TARGET, clean
from data_split import split_train_val_test
from feature_scaling import build_preprocessor

HIDDEN_LAYER_SIZES = (128, 64)
BATCH_SIZE = 512
MAX_ITER = 200
VALIDATION_FRACTION = 0.1
N_ITER_NO_CHANGE = 10


def build_pipeline() -> Pipeline:
    """Unfitted Pipeline: standard scaling of NUMERIC_FEATURES, then an MLP.

    Early stopping holds out VALIDATION_FRACTION of the rows passed to `fit`
    (training rows only) and stops after N_ITER_NO_CHANGE epochs without
    improvement on that hold-out. The preprocessor is a Pipeline step, so
    cross-validation refits it on each training fold.
    """
    model = MLPClassifier(
        hidden_layer_sizes=HIDDEN_LAYER_SIZES,
        batch_size=BATCH_SIZE,
        max_iter=MAX_ITER,
        early_stopping=True,
        validation_fraction=VALIDATION_FRACTION,
        n_iter_no_change=N_ITER_NO_CHANGE,
        random_state=RANDOM_STATE,
    )
    return Pipeline([("preprocessor", build_preprocessor("standard")), ("model", model)])


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

    fitted = build_pipeline().fit(X_train, y_train).named_steps["model"]

    print(f"== MLP {HIDDEN_LAYER_SIZES} (stratified {N_SPLITS}-fold CV on {len(y_train):,} training rows) ==")
    print(f"Accuracy: {scores['accuracy_mean']:.4f} ± {scores['accuracy_std']:.4f}")
    print(f"Macro F1: {scores['macro_f1_mean']:.4f} ± {scores['macro_f1_std']:.4f}")
    print("\n== Per-class metrics (out-of-fold predictions) ==")
    print(report.round(4).to_string())
    print(f"\n== Early stopping (fit on the full train set, max_iter={MAX_ITER}) ==")
    print(f"Epochs: {fitted.n_iter_}")
    print(f"Best internal hold-out accuracy: {fitted.best_validation_score_:.4f}")
    print(f"Stopped early: {fitted.n_iter_ < MAX_ITER}")


if __name__ == "__main__":
    main()
