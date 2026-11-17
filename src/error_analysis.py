"""Error analysis (ticket #27): where the chosen model fails per class and why.

Ranks the most confused class pairs, contrasts the model's confidence on correct
vs misclassified predictions, explains the dominant confusion with the most
discriminative feature (Elevation), and lists the most confident errors. The
pipeline is the exported Random Forest of #32, fitted on the training partition
only, so the analysis runs leakage-free on held-out rows.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: write the figure to a file, never open a window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix

from data_audit import load_raw
from data_cleaning import FEATURES, TARGET, clean
from data_split import split_train_val_test
from export_model import fit_pipeline
from target_encoding import CLASS_NAMES, COVER_TYPES

FIGURE_PATH = Path(__file__).resolve().parents[1] / "docs" / "figures" / "error_analysis.png"
DRIVER_FEATURE = "Elevation"  # most discriminative feature (eta^2 0.616; top of #26)
TOP_PAIRS = 10
TOP_ERRORS = 10


def _label(cls: int) -> str:
    """`'2 Lodgepole Pine'` for a Cover_Type label."""
    return f"{cls} {CLASS_NAMES[cls]}"


def confused_pairs(y_true: pd.Series, y_pred: np.ndarray) -> pd.DataFrame:
    """Directed confused pairs (True -> Pred) ranked by count, descending.

    Each off-diagonal confusion-matrix cell becomes one row with its raw count,
    its share of the true class's own errors (``% of class errors``) and its
    share of every misclassified row (``% of all errors``). Reporting both the
    count and the per-class share surfaces the high-volume majority confusions
    and the high-rate minority confusions at once.
    """
    cm = confusion_matrix(y_true, y_pred, labels=COVER_TYPES)
    class_errors = cm.sum(axis=1) - np.diag(cm)  # misclassified rows per true class
    total_errors = int(class_errors.sum())
    rows = []
    for i, true_cls in enumerate(COVER_TYPES):
        for j, pred_cls in enumerate(COVER_TYPES):
            if i == j or cm[i, j] == 0:
                continue
            count = int(cm[i, j])
            rows.append(
                {
                    "True": _label(true_cls),
                    "Pred": _label(pred_cls),
                    "Count": count,
                    "% of class errors": count / class_errors[i] * 100.0,
                    "% of all errors": count / total_errors * 100.0,
                }
            )
    return (
        pd.DataFrame(rows)
        .sort_values("Count", ascending=False)
        .reset_index(drop=True)
    )


def confidence_contrast(y_true: pd.Series, y_pred: np.ndarray, proba: np.ndarray) -> pd.DataFrame:
    """Top predicted probability on correct vs misclassified rows.

    The top ``predict_proba`` value is the model's confidence in the class it
    returned. If errors sit at lower confidence than correct predictions, they
    concentrate near the decision boundary rather than being confident mistakes.
    """
    confidence = proba.max(axis=1)
    correct = np.asarray(y_true) == y_pred
    rows = []
    for name, mask in [("Correct", correct), ("Misclassified", ~correct)]:
        subset = confidence[mask]
        rows.append(
            {
                "Prediction": name,
                "Rows": int(mask.sum()),
                "Mean confidence": float(subset.mean()),
                "Median confidence": float(np.median(subset)),
                "Share below 0.5": float((subset < 0.5).mean()),
            }
        )
    return pd.DataFrame(rows)


def feature_contrast(
    X: pd.DataFrame,
    y_true: pd.Series,
    y_pred: np.ndarray,
    true_cls: int,
    pred_cls: int,
    feature: str = DRIVER_FEATURE,
) -> pd.DataFrame:
    """Explain the ``true_cls -> pred_cls`` confusion through one feature.

    Compares the feature on three groups: rows of ``true_cls`` the model got
    right, rows of ``true_cls`` it mislabeled as ``pred_cls``, and the reference
    rows that truly are ``pred_cls``. When the mislabeled group sits between the
    two class centers, the classes overlap on that feature and the confusion is
    expected rather than a model defect.
    """
    y_true = y_true.reset_index(drop=True)
    values = X[feature].reset_index(drop=True)
    pred = pd.Series(y_pred).reset_index(drop=True)

    is_true_a = y_true == true_cls
    groups = {
        f"True {true_cls}, pred {true_cls} (correct)": is_true_a & (pred == true_cls),
        f"True {true_cls}, pred {pred_cls} (confused)": is_true_a & (pred == pred_cls),
        f"True {pred_cls} (reference)": y_true == pred_cls,
    }
    rows = []
    for name, mask in groups.items():
        subset = values[mask]
        rows.append(
            {
                "Group": name,
                "Rows": int(mask.sum()),
                f"{feature} mean": float(subset.mean()),
                f"{feature} std": float(subset.std()),
            }
        )
    return pd.DataFrame(rows)


def top_confident_errors(
    X: pd.DataFrame,
    y_true: pd.Series,
    y_pred: np.ndarray,
    proba: np.ndarray,
    n: int = TOP_ERRORS,
    feature: str = DRIVER_FEATURE,
) -> pd.DataFrame:
    """The ``n`` misclassified rows the model was most confident about.

    Confident errors are the costliest and the most informative examples to
    inspect: the model was sure yet wrong. Shows the true and predicted class,
    the confidence and the driving feature for each.
    """
    y_true = y_true.reset_index(drop=True)
    values = X[feature].reset_index(drop=True)
    confidence = proba.max(axis=1)
    wrong = np.asarray(y_true) != y_pred
    table = pd.DataFrame(
        {
            "True": [_label(c) for c in y_true[wrong]],
            "Pred": [_label(c) for c in y_pred[wrong]],
            "Confidence": confidence[wrong],
            feature: values[wrong].to_numpy(),
        }
    )
    return (
        table.sort_values("Confidence", ascending=False)
        .head(n)
        .reset_index(drop=True)
    )


def plot_error_analysis(
    pairs: pd.DataFrame,
    y_true: pd.Series,
    y_pred: np.ndarray,
    proba: np.ndarray,
    path: Path = FIGURE_PATH,
    top_pairs: int = TOP_PAIRS,
) -> None:
    """Two-panel figure: top confused pairs and the confidence distributions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(13, 6))

    top = pairs.head(top_pairs)
    labels = [f"{t} -> {p}" for t, p in zip(top["True"], top["Pred"])]
    axes[0].barh(labels[::-1], top["Count"].to_numpy()[::-1], color="#C44E52")
    axes[0].set_title(f"Top {top_pairs} confused pairs (True -> Pred)")
    axes[0].set_xlabel("misclassified rows")
    axes[0].tick_params(axis="y", labelsize=8)

    confidence = proba.max(axis=1)
    correct = np.asarray(y_true) == y_pred
    bins = np.linspace(0, 1, 21)
    axes[1].hist(confidence[correct], bins=bins, density=True, alpha=0.6,
                 color="#55A868", label="Correct")
    axes[1].hist(confidence[~correct], bins=bins, density=True, alpha=0.6,
                 color="#C44E52", label="Misclassified")
    axes[1].set_title("Model confidence: correct vs misclassified")
    axes[1].set_xlabel("top predicted probability")
    axes[1].set_ylabel("density")
    axes[1].legend()

    fig.suptitle("Random Forest error analysis (validation partition)")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def analyze_partition(
    name: str, X: pd.DataFrame, y_true: pd.Series, y_pred: np.ndarray, proba: np.ndarray
) -> dict:
    """All error-analysis tables for one partition; the dominant pair drives the feature contrast."""
    pairs = confused_pairs(y_true, y_pred)
    dominant = pairs.iloc[0]
    true_cls = int(dominant["True"].split()[0])
    pred_cls = int(dominant["Pred"].split()[0])
    return {
        "name": name,
        "pairs": pairs,
        "confidence": confidence_contrast(y_true, y_pred, proba),
        "dominant_pair": (true_cls, pred_cls),
        "feature_contrast": feature_contrast(X, y_true, y_pred, true_cls, pred_cls),
        "confident_errors": top_confident_errors(X, y_true, y_pred, proba),
    }


def main() -> None:
    df = clean(load_raw())
    X_train, X_val, X_test, y_train, y_val, y_test = split_train_val_test(
        df[FEATURES], df[TARGET]
    )

    pipeline = fit_pipeline(X_train, y_train)

    partitions = {
        "validation": (X_val, y_val),
        "test": (X_test, y_test),
    }
    results = {}
    for name, (X_part, y_part) in partitions.items():
        y_pred = np.asarray(pipeline.predict(X_part))
        proba = pipeline.predict_proba(X_part)
        results[name] = analyze_partition(name, X_part, y_part, y_pred, proba)

    val = results["validation"]
    plot_error_analysis(
        val["pairs"],
        y_val,
        np.asarray(pipeline.predict(X_val)),
        pipeline.predict_proba(X_val),
    )

    print("== Error analysis: RandomForest (100 trees), fitted on "
          f"{len(y_train):,} train rows (ticket #27) ==")
    print("Pipeline fitted on train only; analysis on held-out partitions.")

    for name in ("validation", "test"):
        res = results[name]
        rows = len(partitions[name][1])
        print(f"\n################  {name.upper()} set ({rows:,} rows)  ################")

        print(f"\n== Top {TOP_PAIRS} confused class pairs (True -> Pred) ==")
        print(res["pairs"].head(TOP_PAIRS).round(2).to_string(index=False))

        print("\n== Model confidence: correct vs misclassified ==")
        print(res["confidence"].round(4).to_string(index=False))

        true_cls, pred_cls = res["dominant_pair"]
        print(f"\n== {DRIVER_FEATURE} contrast for the dominant pair "
              f"({_label(true_cls)} -> {_label(pred_cls)}) ==")
        print(res["feature_contrast"].round(1).to_string(index=False))

        print(f"\n== {TOP_ERRORS} most confident errors ==")
        print(res["confident_errors"].round(4).to_string(index=False))

    print(f"\nFigure saved to: {FIGURE_PATH}")


if __name__ == "__main__":
    main()
