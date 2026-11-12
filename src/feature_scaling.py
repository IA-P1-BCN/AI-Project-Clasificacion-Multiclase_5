"""Feature scaling (ticket #14): scale the 10 numeric features, leave the 44 binary ones untouched."""
import warnings

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler, RobustScaler, StandardScaler

from data_audit import load_raw
from data_cleaning import (
    FEATURES,
    NUMERIC_FEATURES,
    SOIL_FEATURES,
    TARGET,
    WILDERNESS_FEATURES,
    clean,
)

BINARY_FEATURES = WILDERNESS_FEATURES + SOIL_FEATURES
SCALERS = {
    "standard": StandardScaler,
    "robust": RobustScaler,
    "minmax": MinMaxScaler,
}
DEFAULT_SCALER = "standard"
RANDOM_STATE = 42
COMPARISON_SAMPLE_SIZE = 60_000


def build_preprocessor(scaler: str = DEFAULT_SCALER) -> ColumnTransformer:
    """Unfitted preprocessor: scales NUMERIC_FEATURES, passes BINARY_FEATURES through.

    Use it as the first step of a scikit-learn Pipeline so that it is fitted on
    the training data (or on each training fold during cross-validation) only.
    The output is a DataFrame with the same 54 columns in the same order.
    """
    if scaler not in SCALERS:
        raise ValueError(f"Unknown scaler '{scaler}'. Choose one of {sorted(SCALERS)}.")
    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", SCALERS[scaler](), NUMERIC_FEATURES),
            ("binary", "passthrough", BINARY_FEATURES),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )
    return preprocessor.set_output(transform="pandas")


def scale_train_test(
    X_train: pd.DataFrame, X_test: pd.DataFrame, scaler: str = DEFAULT_SCALER
) -> tuple[pd.DataFrame, pd.DataFrame, ColumnTransformer]:
    """Fit the preprocessor on X_train only, then transform both partitions."""
    preprocessor = build_preprocessor(scaler)
    X_train_scaled = preprocessor.fit_transform(X_train)
    X_test_scaled = preprocessor.transform(X_test)
    return X_train_scaled, X_test_scaled, preprocessor


def check_scaling(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    X_train_scaled: pd.DataFrame,
    X_test_scaled: pd.DataFrame,
    preprocessor: ColumnTransformer,
) -> None:
    """Raise AssertionError if the StandardScaler output leaks or touches binary features."""
    fitted = preprocessor.named_transformers_["numeric"]
    assert isinstance(fitted, StandardScaler), "check_scaling expects the standard scaler"
    assert list(X_train_scaled.columns) == FEATURES, "column order changed"
    # Parameters come from the training partition only.
    assert np.allclose(fitted.mean_, X_train[NUMERIC_FEATURES].mean().to_numpy())
    assert np.allclose(fitted.scale_, X_train[NUMERIC_FEATURES].std(ddof=0).to_numpy())
    assert np.allclose(X_train_scaled[NUMERIC_FEATURES].mean(), 0, atol=1e-8)
    assert np.allclose(X_train_scaled[NUMERIC_FEATURES].std(ddof=0), 1, atol=1e-8)
    # Binary features are identical before and after.
    assert X_train_scaled[BINARY_FEATURES].equals(X_train[BINARY_FEATURES])
    assert X_test_scaled[BINARY_FEATURES].equals(X_test[BINARY_FEATURES])


def compare_scalers(
    X: pd.DataFrame, y: pd.Series, sample_size: int = COMPARISON_SAMPLE_SIZE
) -> pd.DataFrame:
    """Logistic regression on a stratified sample, once per scaler (and unscaled).

    Evidence for the scaler choice only: it uses a sample, a single split and
    default hyperparameters, so the scores are not final model results.
    """
    X_sample, _, y_sample, _ = train_test_split(
        X, y, train_size=sample_size, stratify=y, random_state=RANDOM_STATE
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_sample, y_sample, test_size=0.25, stratify=y_sample, random_state=RANDOM_STATE
    )
    rows = []
    for name in ["none", *SCALERS]:
        model = LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)
        steps = [("model", model)]
        if name != "none":
            steps.insert(0, ("preprocessor", build_preprocessor(name)))
        with warnings.catch_warnings():
            # Non-convergence is expected without scaling; it is reported in the table.
            warnings.simplefilter("ignore", ConvergenceWarning)
            pipeline = Pipeline(steps).fit(X_train, y_train)
        predictions = pipeline.predict(X_val)
        rows.append(
            {
                "Scaler": name,
                "Accuracy": accuracy_score(y_val, predictions),
                "Macro F1": f1_score(y_val, predictions, average="macro"),
                "Iterations": int(pipeline.named_steps["model"].n_iter_.max()),
                "Converged": bool(pipeline.named_steps["model"].n_iter_.max() < model.max_iter),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    df = clean(load_raw())
    X, y = df[FEATURES], df[TARGET]

    # Demonstration split only; the project split protocol belongs to ticket #16.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE
    )
    X_train_scaled, X_test_scaled, preprocessor = scale_train_test(X_train, X_test)
    check_scaling(X_train, X_test, X_train_scaled, X_test_scaled, preprocessor)

    summary = pd.DataFrame(
        {
            "train_mean_raw": X_train[NUMERIC_FEATURES].mean(),
            "train_std_raw": X_train[NUMERIC_FEATURES].std(ddof=0),
            "train_mean": X_train_scaled[NUMERIC_FEATURES].mean(),
            "train_std": X_train_scaled[NUMERIC_FEATURES].std(ddof=0),
            "test_mean": X_test_scaled[NUMERIC_FEATURES].mean(),
            "test_std": X_test_scaled[NUMERIC_FEATURES].std(ddof=0),
        }
    )
    print(f"== Scaling summary ({DEFAULT_SCALER}, fitted on {len(X_train):,} training rows) ==")
    print(summary.round(4).to_string())
    print(f"\nScaled features: {len(NUMERIC_FEATURES)}")
    print(f"Binary features passed through unchanged: {len(BINARY_FEATURES)}")
    print("Checks passed: parameters fitted on training rows only, binary features untouched.")

    print(f"\n== Scaler comparison (logistic regression, {COMPARISON_SAMPLE_SIZE:,}-row sample) ==")
    print(compare_scalers(X, y).round(4).to_string(index=False))


if __name__ == "__main__":
    main()
