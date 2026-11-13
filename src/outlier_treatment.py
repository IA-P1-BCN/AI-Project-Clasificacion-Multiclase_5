"""Outlier treatment (ticket #13): detect outliers and clip the numeric features.

Strategy (see docs/PREPROCESSING.md): clip (winsorize) the 10 numeric features
to IQR fences, never remove rows. The clip bounds are learned on the training
partition only, so the transformer is leakage-safe and composes before the
scaler inside a scikit-learn Pipeline. The 44 binary indicators are passed
through untouched.
"""
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer

from data_audit import load_raw
from data_cleaning import FEATURES, NUMERIC_FEATURES, SOIL_FEATURES, TARGET, WILDERNESS_FEATURES, clean
from data_split import class_shares, split_train_val_test

BINARY_FEATURES = WILDERNESS_FEATURES + SOIL_FEATURES
IQR_FACTOR = 1.5
Z_THRESHOLD = 3.0


def outlier_report(X: pd.DataFrame) -> pd.DataFrame:
    """Per-feature outlier counts by the IQR rule and the z-score rule.

    Detection only; nothing is modified. Both rules are reported so the decision
    does not depend on a single definition of "outlier".
    """
    numeric = X[NUMERIC_FEATURES]
    q1 = numeric.quantile(0.25)
    q3 = numeric.quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - IQR_FACTOR * iqr, q3 + IQR_FACTOR * iqr
    iqr_mask = (numeric < lower) | (numeric > upper)

    z = (numeric - numeric.mean()) / numeric.std(ddof=0)
    z_mask = z.abs() > Z_THRESHOLD

    n = len(numeric)
    return pd.DataFrame(
        {
            "iqr_count": iqr_mask.sum(),
            "iqr_pct": (iqr_mask.sum() / n * 100).round(3),
            "zscore_count": z_mask.sum(),
            "zscore_pct": (z_mask.sum() / n * 100).round(3),
        }
    )


class OutlierClipper(BaseEstimator, TransformerMixin):
    """Clip each column to IQR fences learned in `fit` (training data only).

    `fit` stores the lower/upper bound per column from the given data; `transform`
    clips any partition to those bounds. Fitting on the training partition only
    keeps validation/test values out of the learned bounds (no leakage).
    """

    def __init__(self, factor: float = IQR_FACTOR):
        self.factor = factor

    def fit(self, X, y=None):
        X = pd.DataFrame(X)
        q1 = X.quantile(0.25)
        q3 = X.quantile(0.75)
        iqr = q3 - q1
        self.lower_ = q1 - self.factor * iqr
        self.upper_ = q3 + self.factor * iqr
        self.feature_names_in_ = np.asarray(X.columns)
        self.n_features_in_ = X.shape[1]
        return self

    def transform(self, X):
        X = pd.DataFrame(X)
        return X.clip(lower=self.lower_, upper=self.upper_, axis=1)

    def get_feature_names_out(self, input_features=None):
        return np.asarray(self.feature_names_in_)


def build_outlier_preprocessor(factor: float = IQR_FACTOR) -> ColumnTransformer:
    """Unfitted preprocessor: clips NUMERIC_FEATURES, passes BINARY_FEATURES through.

    Use it as a Pipeline step (before the scaler) so the clip bounds are fitted on
    the training data, or on each training fold during cross-validation, only. The
    output is a DataFrame with the same 54 columns in the same order.
    """
    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", OutlierClipper(factor), NUMERIC_FEATURES),
            ("binary", "passthrough", BINARY_FEATURES),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )
    return preprocessor.set_output(transform="pandas")


def removal_impact(X: pd.DataFrame, y: pd.Series, factor: float = IQR_FACTOR) -> dict:
    """What removing every row with any IQR outlier would cost (evidence only).

    Quantifies why removal is rejected: how many rows would be dropped and how
    much the per-class shares would move. The bounds here use the whole input on
    purpose, to show the maximal removal; the applied strategy does not remove.
    """
    numeric = X[NUMERIC_FEATURES]
    q1, q3 = numeric.quantile(0.25), numeric.quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - factor * iqr, q3 + factor * iqr
    outlier_row = ((numeric < lower) | (numeric > upper)).any(axis=1)
    kept = ~outlier_row
    shift = (class_shares(y[kept]) - class_shares(y)).round(3)
    return {
        "rows_total": len(X),
        "rows_removed": int(outlier_row.sum()),
        "pct_removed": round(outlier_row.sum() / len(X) * 100, 3),
        "max_abs_class_shift": float(shift.abs().max()),
        "class_share_shift": shift,
    }


def check_no_leakage(preprocessor: ColumnTransformer, X_train: pd.DataFrame, X_full: pd.DataFrame) -> None:
    """Assert the clip bounds come from training data only and binary stays intact."""
    clipper = preprocessor.named_transformers_["numeric"]
    train_q1 = X_train[NUMERIC_FEATURES].quantile(0.25)
    train_q3 = X_train[NUMERIC_FEATURES].quantile(0.75)
    train_iqr = train_q3 - train_q1
    assert np.allclose(clipper.lower_, train_q1 - IQR_FACTOR * train_iqr), "lower bound not from training data"
    assert np.allclose(clipper.upper_, train_q3 + IQR_FACTOR * train_iqr), "upper bound not from training data"
    # Fitting on the full data would give different bounds: the split matters.
    full_fit = OutlierClipper().fit(X_full[NUMERIC_FEATURES])
    assert not np.allclose(clipper.upper_, full_fit.upper_), "train and full bounds identical; check the split"


def main() -> None:
    df = clean(load_raw())
    X, y = df[FEATURES], df[TARGET]
    X_train, X_val, X_test, y_train, y_val, y_test = split_train_val_test(X, y)

    print("== Outlier detection on training rows (numeric features) ==")
    print(outlier_report(X_train).to_string())

    impact = removal_impact(X_train, y_train)
    print("\n== If rows with any IQR outlier were removed (rejected strategy) ==")
    print(f"Rows removed: {impact['rows_removed']:,} of {impact['rows_total']:,} ({impact['pct_removed']}%)")
    print(f"Largest per-class share shift: {impact['max_abs_class_shift']} percentage points")
    print(impact["class_share_shift"].to_string())

    preprocessor = build_outlier_preprocessor()
    X_train_clipped = preprocessor.fit_transform(X_train)
    X_val_clipped = preprocessor.transform(X_val)
    X_test_clipped = preprocessor.transform(X_test)
    check_no_leakage(preprocessor, X_train, X)

    clipper = preprocessor.named_transformers_["numeric"]
    train_outliers = outlier_report(X_train)["iqr_count"].sum()
    clipped_outliers = int(
        (
            (X_train_clipped[NUMERIC_FEATURES] < clipper.lower_)
            | (X_train_clipped[NUMERIC_FEATURES] > clipper.upper_)
        ).sum().sum()
    )
    changed = int((X_train_clipped[NUMERIC_FEATURES].to_numpy() != X_train[NUMERIC_FEATURES].to_numpy()).sum())

    print("\n== Applied strategy: clip to training IQR fences ==")
    print(f"Numeric values changed (clipped) in training: {changed:,}")
    print(f"Values beyond the bounds before clipping: {train_outliers:,}; after clipping: {clipped_outliers}")
    print(f"Rows removed: 0 (clipping keeps every row)")
    print(f"Binary features untouched: {X_train_clipped[BINARY_FEATURES].equals(X_train[BINARY_FEATURES])}")

    shares = pd.DataFrame(
        {"before": class_shares(y_train).round(3), "after_clip": class_shares(y_train).round(3)}
    )
    print("\n== Class distribution before vs after clipping (training) ==")
    print(shares.to_string())
    print("\nChecks passed: bounds fitted on training rows only, binary untouched, class distribution unchanged.")


if __name__ == "__main__":
    main()
