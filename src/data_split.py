"""Stratified train/validation/test split (ticket #16): split preserving class proportions."""
import pandas as pd
from sklearn.model_selection import train_test_split

from data_audit import load_raw
from data_cleaning import FEATURES, TARGET, clean

TEST_SIZE = 0.15
VAL_SIZE = 0.15
RANDOM_STATE = 42


def split_train_val_test(X, y, test_size=TEST_SIZE, val_size=VAL_SIZE, random_state=RANDOM_STATE):
    """Split X and y into train / validation / test, stratified on y.

    The test split is taken first, then validation is taken from the remaining
    rows, so the three partitions never overlap. Stratification on `y` preserves
    the class proportions of `Cover_Type` in every partition.
    """
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=test_size, stratify=y, random_state=random_state
    )
    val_frac_of_remaining = val_size / (1 - test_size)
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val,
        y_train_val,
        test_size=val_frac_of_remaining,
        stratify=y_train_val,
        random_state=random_state,
    )
    return X_train, X_val, X_test, y_train, y_val, y_test


def class_shares(y):
    """Class proportions of a target vector as percentages, sorted by class label."""
    return (y.value_counts(normalize=True).sort_index() * 100).rename("share")


def check_stratification(y, y_train, y_val, y_test, atol=0.05):
    """Raise AssertionError if a partition deviates from the full class shares."""
    full = class_shares(y)
    for name, part in [("train", y_train), ("validation", y_val), ("test", y_test)]:
        deviation = (class_shares(part) - full).abs()
        assert (deviation <= atol).all(), (
            f"{name} class shares deviate from the full data by more than {atol} "
            f"percentage points:\n{deviation.round(4).to_string()}"
        )


def main():
    df = clean(load_raw())
    X, y = df[FEATURES], df[TARGET]

    X_train, X_val, X_test, y_train, y_val, y_test = split_train_val_test(X, y)
    check_stratification(y, y_train, y_val, y_test)

    shares = pd.DataFrame(
        {
            "full": class_shares(y).round(3),
            "train": class_shares(y_train).round(3),
            "validation": class_shares(y_val).round(3),
            "test": class_shares(y_test).round(3),
        }
    )

    print("== Stratified train/validation/test split ==")
    print(f"Rows  train={len(y_train):,}  validation={len(y_val):,}  test={len(y_test):,}")
    print(
        f"Ratio train={len(y_train) / len(y):.1%}  "
        f"validation={len(y_val) / len(y):.1%}  test={len(y_test) / len(y):.1%}"
    )
    print("\n== Class shares per partition (%) ==")
    print(shares.to_string())
    print("\nStratification check passed: every partition matches the full class shares.")


if __name__ == "__main__":
    main()
