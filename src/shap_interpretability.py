"""Model interpretability with SHAP (ticket #30): explain the chosen model's predictions.

Builds a TreeExplainer for the exported Random Forest (fitted on the training
partition only) and computes SHAP values on a held-out validation sample. Saves
a multiclass summary bar, a per-class beeswarm and a dependence plot for the
most important feature, and reports the signed, per-prediction attribution that
complements the impurity/permutation importances of #26. Optional Could task.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: write the figures to files, never open a window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

from data_audit import load_raw
from data_cleaning import FEATURES, TARGET, clean
from data_split import RANDOM_STATE, split_train_val_test
from export_model import fit_pipeline
from target_encoding import CLASS_NAMES, COVER_TYPES

FIGURE_DIR = Path(__file__).resolve().parents[1] / "docs" / "figures"
SUMMARY_PATH = FIGURE_DIR / "shap_summary_bar.png"
BEESWARM_PATH = FIGURE_DIR / "shap_beeswarm.png"
DEPENDENCE_PATH = FIGURE_DIR / "shap_dependence_elevation.png"

SAMPLE_SIZE = 2000  # validation rows SHAP is computed on (approximate SHAP is O(sample))
DRIVER_FEATURE = "Elevation"  # most discriminative feature (eta^2 0.616; top of #26)
BEESWARM_CLASS = 2  # Lodgepole Pine, the majority class, for the per-class beeswarm
TOP_N = 15


def build_explainer(pipeline) -> shap.TreeExplainer:
    """TreeExplainer for the Random Forest inside the fitted pipeline.

    Uses the default ``feature_perturbation="tree_path_dependent"``: exact for a
    tree ensemble and needs no background dataset, so nothing extra is fitted.
    """
    return shap.TreeExplainer(pipeline.named_steps["model"])


def shap_sample(pipeline, X: pd.DataFrame, n: int = SAMPLE_SIZE) -> pd.DataFrame:
    """A reproducible validation sample, passed through the pipeline preprocessor.

    The passthrough preprocessor keeps the exact 54 feature names the forest saw,
    so the returned frame lines up with the explainer and the plots.
    """
    sample = X.sample(n=min(n, len(X)), random_state=RANDOM_STATE)
    return pipeline.named_steps["preprocessor"].transform(sample)


def shap_values(explainer: shap.TreeExplainer, X: pd.DataFrame) -> shap.Explanation:
    """Approximate SHAP values; Explanation with values (n_samples, n_features, n_classes).

    Exact TreeSHAP costs ~3 s/row on this forest (max depth 64, ~80k nodes per
    tree), i.e. hours for a useful sample. The fast approximate (Saabas)
    attribution is near-instant and gives the same qualitative feature ranking,
    which is what the summary and dependence plots need. Additivity is not exact
    under the approximation, so that check is disabled.
    """
    return explainer(X, approximate=True, check_additivity=False)


def mean_abs_importance(explanation: shap.Explanation) -> pd.DataFrame:
    """Mean |SHAP| per feature, per class and aggregated, sorted by the aggregate.

    Columns: one per Cover_Type class plus ``All classes`` (the mean over
    classes). Rows are features, descending by the aggregate magnitude.
    """
    values = np.abs(np.asarray(explanation.values))  # (n_samples, n_features, n_classes)
    per_class = values.mean(axis=0)  # (n_features, n_classes)
    table = pd.DataFrame(
        per_class,
        index=explanation.feature_names,
        columns=[f"{cls} {CLASS_NAMES[cls]}" for cls in COVER_TYPES],
    )
    table["All classes"] = per_class.mean(axis=1)
    return table.sort_values("All classes", ascending=False)


def plot_summary_bar(importance: pd.DataFrame, path: Path = SUMMARY_PATH, top_n: int = TOP_N) -> None:
    """Stacked bar of mean |SHAP| for the top features, one segment per class."""
    path.parent.mkdir(parents=True, exist_ok=True)
    class_cols = [c for c in importance.columns if c != "All classes"]
    top = importance.head(top_n).iloc[::-1]  # smallest at the bottom for a horizontal bar

    fig, ax = plt.subplots(figsize=(10, 7))
    left = np.zeros(len(top))
    colors = plt.cm.tab10(np.linspace(0, 1, len(class_cols)))
    for color, col in zip(colors, class_cols):
        ax.barh(top.index, top[col].to_numpy(), left=left, color=color, label=col)
        left += top[col].to_numpy()
    ax.set_title(f"SHAP feature importance (mean |SHAP|, top {top_n}, validation sample)")
    ax.set_xlabel("mean |SHAP value| (summed across classes)")
    ax.tick_params(axis="y", labelsize=8)
    ax.legend(title="Cover_Type", fontsize=7, title_fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_beeswarm(
    explanation: shap.Explanation, cover_type: int = BEESWARM_CLASS,
    path: Path = BEESWARM_PATH, top_n: int = TOP_N,
) -> None:
    """Beeswarm (classic SHAP summary) for one class: effect size and direction per feature."""
    path.parent.mkdir(parents=True, exist_ok=True)
    class_index = COVER_TYPES.index(cover_type)
    fig = plt.figure()
    shap.plots.beeswarm(explanation[:, :, class_index], max_display=top_n, show=False)
    plt.title(f"SHAP beeswarm — Cover_Type {cover_type} {CLASS_NAMES[cover_type]} (validation sample)")
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_dependence(
    explanation: shap.Explanation, feature: str = DRIVER_FEATURE,
    cover_type: int = BEESWARM_CLASS, path: Path = DEPENDENCE_PATH,
) -> None:
    """Dependence plot: the feature value vs its SHAP value for one class."""
    path.parent.mkdir(parents=True, exist_ok=True)
    class_index = COVER_TYPES.index(cover_type)
    feature_index = list(explanation.feature_names).index(feature)
    fig = plt.figure()
    shap.plots.scatter(explanation[:, feature_index, class_index], show=False)
    plt.title(
        f"SHAP dependence — {feature} on Cover_Type {cover_type} "
        f"{CLASS_NAMES[cover_type]} (validation sample)"
    )
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    df = clean(load_raw())
    X_train, X_val, _, y_train, _, _ = split_train_val_test(df[FEATURES], df[TARGET])

    pipeline = fit_pipeline(X_train, y_train)
    explainer = build_explainer(pipeline)
    sample = shap_sample(pipeline, X_val)
    explanation = shap_values(explainer, sample)

    importance = mean_abs_importance(explanation)

    print("== SHAP interpretability: RandomForest (100 trees), fitted on "
          f"{len(y_train):,} train rows (ticket #30) ==")
    print(f"Approximate TreeSHAP (Saabas) on {len(sample):,} held-out "
          f"validation rows; values shape {np.asarray(explanation.values).shape} "
          "(samples, features, classes).")

    print(f"\n== Top {TOP_N} features by mean |SHAP| (aggregated across classes) ==")
    print(importance["All classes"].head(TOP_N).round(4).to_string())

    print(f"\n== Top {TOP_N} features by mean |SHAP| (per class) ==")
    print(importance.drop(columns="All classes").head(TOP_N).round(4).to_string())

    plot_summary_bar(importance)
    plot_beeswarm(explanation)
    plot_dependence(explanation)

    print("\n== Figures ==")
    print(f"Summary bar:  {SUMMARY_PATH}")
    print(f"Beeswarm:     {BEESWARM_PATH}")
    print(f"Dependence:   {DEPENDENCE_PATH}")


if __name__ == "__main__":
    main()
