"""Final evaluation metrics (ticket #25): accuracy (train vs validation), per-class precision/recall/F1, and confusion matrix for the chosen model."""
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.pipeline import Pipeline

from data_audit import load_raw
from data_cleaning import FEATURES, TARGET, clean
from data_split import split_train_val_test
from export_model import build_pipeline, fit_pipeline
from random_forest import N_ESTIMATORS
from target_encoding import CLASS_NAMES, COVER_TYPES

MODEL_NAME = f"RandomForest ({N_ESTIMATORS} trees)"


def partition_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict:
    """Headline multiclass metrics (accuracy and macro precision/recall/F1) on one partition."""
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(
            precision_score(y_true, y_pred, average="macro", zero_division=0)
        ),
        "recall_macro": float(
            recall_score(y_true, y_pred, average="macro", zero_division=0)
        ),
        "macro_f1": float(
            f1_score(y_true, y_pred, average="macro", zero_division=0)
        ),
    }


def headline_table(
    pipeline: Pipeline, partitions: dict[str, tuple[pd.DataFrame, pd.Series]]
) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    """Predict each partition and return (summary_table, predictions_by_partition)."""
    rows = []
    predictions = {}
    for name, (X_part, y_part) in partitions.items():
        y_pred = np.asarray(pipeline.predict(X_part))
        predictions[name] = y_pred
        metrics = partition_metrics(y_part, y_pred)
        rows.append(
            {
                "Partition": name,
                "Rows": int(len(y_part)),
                "Accuracy": metrics["accuracy"],
                "Precision (macro)": metrics["precision_macro"],
                "Recall (macro)": metrics["recall_macro"],
                "F1 (macro)": metrics["macro_f1"],
            }
        )
    return pd.DataFrame(rows), predictions


def per_class_table(y_true: pd.Series, y_pred: np.ndarray) -> pd.DataFrame:
    """Precision, recall, F1 and support per class (1..7), plus macro and weighted averages."""
    report = classification_report(
        y_true, y_pred, labels=COVER_TYPES, output_dict=True, zero_division=0
    )
    rows = []
    for cls in COVER_TYPES:
        entry = report[str(cls)]
        rows.append(
            {
                TARGET: str(cls),
                "Name": CLASS_NAMES[cls],
                "Precision": float(entry["precision"]),
                "Recall": float(entry["recall"]),
                "F1": float(entry["f1-score"]),
                "Support": int(entry["support"]),
            }
        )
    for avg_key, avg_label in [
        ("macro avg", "Macro average"),
        ("weighted avg", "Weighted average"),
    ]:
        entry = report[avg_key]
        rows.append(
            {
                TARGET: "",
                "Name": avg_label,
                "Precision": float(entry["precision"]),
                "Recall": float(entry["recall"]),
                "F1": float(entry["f1-score"]),
                "Support": int(entry["support"]),
            }
        )
    return pd.DataFrame(rows)


def confusion_matrix_tables(
    y_true: pd.Series, y_pred: np.ndarray
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return 7x7 confusion matrices: (raw counts, row-normalized recall percentages)."""
    counts = confusion_matrix(y_true, y_pred, labels=COVER_TYPES)
    row_pct = (
        confusion_matrix(y_true, y_pred, labels=COVER_TYPES, normalize="true") * 100.0
    )
    index = pd.Index(
        [f"{cls} {CLASS_NAMES[cls]}" for cls in COVER_TYPES], name="True \\ Pred"
    )
    columns = [f"Pred {cls}" for cls in COVER_TYPES]
    return (
        pd.DataFrame(counts, index=index, columns=columns),
        pd.DataFrame(row_pct, index=index, columns=columns),
    )


def evaluate_final_model(
    X_train: pd.DataFrame,
    X_val: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_val: pd.Series,
    y_test: pd.Series,
) -> dict:
    """Fit the chosen pipeline on (X_train, y_train) only and compute all M5 metrics."""
    pipeline = fit_pipeline(X_train, y_train)
    partitions = {
        "train": (X_train, y_train),
        "validation": (X_val, y_val),
        "test": (X_test, y_test),
    }
    headline, preds = headline_table(pipeline, partitions)
    acc_by_part = dict(zip(headline["Partition"], headline["Accuracy"]))
    overfitting_gap = float(acc_by_part["train"] - acc_by_part["validation"])

    val_counts, val_pct = confusion_matrix_tables(y_val, preds["validation"])
    test_counts, test_pct = confusion_matrix_tables(y_test, preds["test"])

    return {
        "model": MODEL_NAME,
        "pipeline_steps": [name for name, _ in build_pipeline().steps],
        "headline": headline,
        "overfitting_gap": overfitting_gap,
        "per_class": {
            "validation": per_class_table(y_val, preds["validation"]),
            "test": per_class_table(y_test, preds["test"]),
        },
        "confusion_matrix": {
            "validation": {"counts": val_counts, "row_pct": val_pct},
            "test": {"counts": test_counts, "row_pct": test_pct},
        },
    }


def main() -> None:
    df = clean(load_raw())
    X_train, X_val, X_test, y_train, y_val, y_test = split_train_val_test(
        df[FEATURES], df[TARGET]
    )

    results = evaluate_final_model(X_train, X_val, X_test, y_train, y_val, y_test)

    print(f"== Final metrics: {results['model']} (ticket #25) ==")
    print(f"Pipeline steps: {' -> '.join(results['pipeline_steps'])}")
    print(
        f"Rows: train={len(y_train):,} (fitted here)  "
        f"validation={len(y_val):,}  test={len(y_test):,}"
    )

    print("\n== Headline metrics by partition ==")
    print(results["headline"].round(4).to_string(index=False))

    gap = results["overfitting_gap"]
    print(
        f"\n== Train vs validation accuracy gap ==\n"
        f"train - validation = {gap:+.4f} ({gap * 100:+.2f} percentage points)"
    )

    for part in ("validation", "test"):
        print(f"\n== Per-class metrics ({part} set, {len(y_val if part == 'validation' else y_test):,} rows) ==")
        print(results["per_class"][part].round(4).to_string(index=False))

        print(f"\n== Confusion matrix: raw counts ({part} set) ==")
        print(results["confusion_matrix"][part]["counts"].to_string())

        print(f"\n== Confusion matrix: row-normalized recall % ({part} set) ==")
        print(results["confusion_matrix"][part]["row_pct"].round(2).to_string())


if __name__ == "__main__":
    main()
