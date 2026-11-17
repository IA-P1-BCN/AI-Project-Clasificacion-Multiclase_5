"""Feature importance (ticket #26): rank the features that drive the shortlist model."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: write the figure to a file, never open a window
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.inspection import permutation_importance

from baseline import RANDOM_STATE
from data_audit import load_raw
from data_cleaning import FEATURES, TARGET, clean
from data_split import split_train_val_test
from random_forest import build_model

FIGURE_PATH = Path(__file__).resolve().parents[1] / "docs" / "figures" / "feature_importance.png"
N_REPEATS = 5
TOP_N = 15


def mdi_importance(model, X_train: pd.DataFrame, y_train: pd.Series) -> pd.Series:
    """Mean decrease in impurity of a Random Forest fitted on the training rows.

    Fast but biased toward continuous, high-cardinality features, so it is
    reported alongside the permutation importance rather than on its own.
    """
    model.fit(X_train, y_train)
    return pd.Series(model.feature_importances_, index=FEATURES).sort_values(ascending=False)


def permutation_importance_val(model, X_train, y_train, X_val, y_val) -> pd.Series:
    """Permutation importance measured on the validation partition.

    The forest is fitted on the training partition only; each feature is then
    shuffled in the held-out validation partition and the drop in macro F1 is
    recorded. The model never saw these rows, so the result is a leakage-free,
    model-agnostic measure that does not share the MDI bias toward continuous
    features. Returns the mean importance per feature, descending.
    """
    model.fit(X_train, y_train)
    result = permutation_importance(
        model,
        X_val,
        y_val,
        scoring="f1_macro",
        n_repeats=N_REPEATS,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    return pd.Series(result.importances_mean, index=FEATURES).sort_values(ascending=False)


def plot_top_importances(mdi: pd.Series, perm: pd.Series, path: Path = FIGURE_PATH, top_n: int = TOP_N) -> None:
    """Save a two-panel bar chart ranking the top features by each measure."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    panels = [
        (axes[0], mdi.head(top_n), "Mean decrease in impurity (MDI)", "#4C72B0"),
        (axes[1], perm.head(top_n), "Permutation importance (macro F1 drop)", "#55A868"),
    ]
    for ax, data, title, color in panels:
        ax.barh(data.index[::-1], data.values[::-1], color=color)
        ax.set_title(title)
        ax.set_xlabel("importance")
        ax.tick_params(axis="y", labelsize=8)
    fig.suptitle(f"Random Forest feature importance (top {top_n})")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    df = clean(load_raw())
    X_train, X_val, _, y_train, y_val, _ = split_train_val_test(df[FEATURES], df[TARGET])

    mdi = mdi_importance(build_model(), X_train, y_train)
    perm = permutation_importance_val(build_model(), X_train, y_train, X_val, y_val)
    plot_top_importances(mdi, perm)

    print(f"== Random Forest feature importance (fit on {len(y_train):,} train rows) ==")
    print(f"\n== Top {TOP_N} by mean decrease in impurity — MDI (full train set) ==")
    print(mdi.head(TOP_N).round(4).to_string())
    print(f"\n== Top {TOP_N} by permutation importance (macro F1 drop on {len(y_val):,} validation rows, {N_REPEATS} repeats) ==")
    print(perm.head(TOP_N).round(4).to_string())
    print(f"\nFigure saved to: {FIGURE_PATH}")


if __name__ == "__main__":
    main()
