"""Classification-specific EDA (ticket #9): per-class histograms and boxplots,
correlation matrix and a ranking of the features that separate the classes."""
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from data_audit import COLUMNS, load_raw

FIG_DIR = Path(__file__).resolve().parents[1] / "docs" / "figures"
TARGET = "Cover_Type"
NUMERIC = COLUMNS[:10]  # the 10 quantitative features


def _title(col: str) -> str:
    return textwrap.fill(col.replace("_", " "), 22)


def separation_scores(df: pd.DataFrame) -> pd.Series:
    """Eta squared per feature: share of the variance explained by the class."""
    scores = {}
    for col in NUMERIC:
        grand_mean = df[col].mean()
        grp = df.groupby(TARGET)[col]
        ss_between = (grp.count() * (grp.mean() - grand_mean) ** 2).sum()
        ss_total = ((df[col] - grand_mean) ** 2).sum()
        scores[col] = ss_between / ss_total
    return pd.Series(scores, name="eta_squared").sort_values(ascending=False)


def top_correlations(corr: pd.DataFrame, n: int = 6) -> pd.Series:
    """Strongest feature pairs by absolute Pearson correlation."""
    upper = corr.where(np.triu(np.ones(corr.shape, dtype=bool), k=1)).stack()
    return upper.reindex(upper.abs().sort_values(ascending=False).index).head(n)


def plot_histograms(df: pd.DataFrame, path: Path) -> None:
    classes = sorted(df[TARGET].unique())
    colors = plt.cm.tab10(np.arange(len(classes)))
    fig, axes = plt.subplots(2, 5, figsize=(22, 8))
    for ax, col in zip(axes.ravel(), NUMERIC):
        bins = np.histogram_bin_edges(df[col], bins=40)
        for cls, color in zip(classes, colors):
            ax.hist(
                df.loc[df[TARGET] == cls, col],
                bins=bins,
                density=True,
                histtype="step",
                linewidth=1.3,
                color=color,
                label=f"Class {cls}",
            )
        ax.set_title(_title(col), fontsize=10)
        ax.set_yticks([])
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=len(classes))
    fig.suptitle("Feature distributions per class (density)", fontsize=14)
    fig.tight_layout(rect=(0, 0.05, 1, 0.96))
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_boxplots(df: pd.DataFrame, path: Path) -> None:
    classes = sorted(df[TARGET].unique())
    fig, axes = plt.subplots(2, 5, figsize=(22, 8))
    for ax, col in zip(axes.ravel(), NUMERIC):
        data = [df.loc[df[TARGET] == cls, col] for cls in classes]
        ax.boxplot(data, showfliers=False)
        ax.set_xticklabels(classes)
        ax.set_title(_title(col), fontsize=10)
        ax.set_xlabel("Cover_Type")
    fig.suptitle("Feature boxplots per class (outliers hidden)", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_correlation(corr: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 8.5))
    im = ax.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr)))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(corr)))
    ax.set_yticklabels(corr.columns)
    for i in range(len(corr)):
        for j in range(len(corr)):
            value = corr.iloc[i, j]
            ax.text(
                j, i, f"{value:.2f}", ha="center", va="center", fontsize=8,
                color="white" if abs(value) > 0.6 else "black",
            )
    fig.colorbar(im, ax=ax, label="Pearson r")
    ax.set_title("Correlation matrix - numeric features")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    df = load_raw()
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    scores = separation_scores(df)
    corr = df[NUMERIC].corr()

    print("== Class separation (eta squared, higher = better separation) ==")
    print(scores.round(4).to_string())
    print("\n== Strongest correlations between numeric features ==")
    print(top_correlations(corr).round(3).to_string())

    plot_histograms(df, FIG_DIR / "class_histograms.png")
    plot_boxplots(df, FIG_DIR / "class_boxplots.png")
    plot_correlation(corr, FIG_DIR / "correlation_matrix.png")
    print(f"\nFigures saved to: {FIG_DIR}")


if __name__ == "__main__":
    main()