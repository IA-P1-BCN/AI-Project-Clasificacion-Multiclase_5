"""Baseline models and the cross-validation protocol (ticket #19)."""
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.metrics import f1_score, make_scorer
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split

from data_audit import load_raw
from data_cleaning import FEATURES, TARGET, clean

N_SPLITS = 5
RANDOM_STATE = 42
MACRO_F1 = make_scorer(f1_score, average="macro", zero_division=0)

BASELINES = {
    "most_frequent": DummyClassifier(strategy="most_frequent"),
    "stratified": DummyClassifier(strategy="stratified"),
}


def evaluate_model(model, X, y, n_splits=N_SPLITS, random_state=RANDOM_STATE):
    """Run stratified k-fold cross-validation and return accuracy and macro F1.

    Returns the mean and standard deviation of both metrics across the folds.
    Reuse this function for every model so they are all compared on the same
    protocol (StratifiedKFold, macro F1 as the main metric).
    """
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    scores = cross_validate(
        model,
        X,
        y,
        cv=cv,
        scoring={"accuracy": "accuracy", "macro_f1": MACRO_F1},
        n_jobs=-1,
    )
    return {
        "accuracy_mean": float(scores["test_accuracy"].mean()),
        "accuracy_std": float(scores["test_accuracy"].std()),
        "macro_f1_mean": float(scores["test_macro_f1"].mean()),
        "macro_f1_std": float(scores["test_macro_f1"].std()),
    }


def main():
    df = clean(load_raw())
    X, y = df[FEATURES], df[TARGET]

    # Demonstration split: the canonical 70/15/15 split belongs to #16.
    # Once #16 is merged, replace this with
    # `from data_split import split_train_val_test`.
    X_train, _, y_train, _ = train_test_split(
        X, y, test_size=0.3, stratify=y, random_state=RANDOM_STATE
    )

    rows = []
    for name, model in BASELINES.items():
        result = evaluate_model(model, X_train, y_train)
        rows.append(
            {
                "Model": f"DummyClassifier({name})",
                "Accuracy": f"{result['accuracy_mean']:.4f} ± {result['accuracy_std']:.4f}",
                "Macro F1": f"{result['macro_f1_mean']:.4f} ± {result['macro_f1_std']:.4f}",
            }
        )

    print(f"== Baselines (stratified {N_SPLITS}-fold CV on {len(y_train):,} training rows) ==")
    print(pd.DataFrame(rows).to_string(index=False))
    print("\nEvery model must beat these scores, especially macro F1.")


if __name__ == "__main__":
    main()
