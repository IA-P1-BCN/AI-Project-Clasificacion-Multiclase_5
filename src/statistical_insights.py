"""Deeper statistical insights (ticket #10): skewness/kurtosis, pairwise relationships, PCA."""
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from class_eda import NUMERIC, TARGET, separation_scores
from data_audit import load_raw

FIG_DIR = Path(__file__).resolve().parents[1] / "docs" / "figures"
SAMPLE_PER_CLASS = 1000
SEED = 42


def _label(col: str) -> str:
    return textwrap.fill(col.replace("_", " "), 18)


def distribution_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Skewness, excess kurtosis and share of values outside the 1.5*IQR fences."""
    q1 = df[NUMERIC].quantile(0.25)
    q3 = df[NUMERIC].quantile(0.75)
    iqr = q3 - q1
    outside = ((df[NUMERIC] < q1 - 1.5 * iqr) | (df[NUMERIC] > q3 + 1.5 * iqr)).mean() * 100
    return pd.DataFrame(
        {
            "skewness": df[NUMERIC].skew(),
            "excess_kurtosis": df[NUMERIC].kurt(),
            "pct_outside_iqr": outside,
        }
    ).round(3)


def balanced_sample(df: pd.DataFrame, n: int = SAMPLE_PER_CLASS) -> pd.DataFrame:
    """Same number of rows per class. For visualization only."""
    if df.empty:
        raise ValueError("Cannot build a balanced sample from an empty DataFrame.")
    n = min(n, int(df[TARGET].value_counts().min()))
    return df.groupby(TARGET, group_keys=False).sample(n=n, random_state=SEED)


def pca_projection(df: pd.DataFrame, sample: pd.DataFrame):
    """PCA on the standardized numeric features (numpy only)."""
    mean, std = df[NUMERIC].mean(), df[NUMERIC].std()
    z_all = (df[NUMERIC] - mean) / std
    eigvals, eigvecs = np.linalg.eigh(np.cov(z_all.values, rowvar=False))
    order = np.argsort(eigvals)[::-1]
    eigvals, eigvecs = eigvals[order], eigvecs[:, order]
    explained = eigvals / eigvals.sum()
    coords = ((sample[NUMERIC] - mean) / std).values @ eigvecs[:, :2]
    loadings = pd.DataFrame(eigvecs[:, :2], index=NUMERIC, columns=["PC1", "PC2"])
    return coords, explained, loadings


def plot_distributions(df: pd.DataFrame, stats: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(2, 5, figsize=(22, 8))
    for ax, col in zip(axes.ravel(), NUMERIC):
        ax.hist(df[col], bins=60, color="#4C72B0")
        ax.set_title(f"{_label(col)}\nskew = {stats.loc[col, 'skewness']:.2f}", fontsize=10)
        ax.set_yticks([])
    fig.suptitle("Feature distributions (all rows)", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_pairs(sample: pd.DataFrame, features: list, path: Path) -> None:
    classes = sorted(sample[TARGET].unique())
    colors = plt.cm.tab10(np.arange(len(classes)))
    k = len(features)
    fig, axes = plt.subplots(k, k, figsize=(3.2 * k, 3.2 * k))
    for i, fy in enumerate(features):
        for j, fx in enumerate(features):
            ax = axes[i, j]
            for cls, color in zip(classes, colors):
                sub = sample[sample[TARGET] == cls]
                if i == j:
                    ax.hist(sub[fx], bins=30, density=True, histtype="step", color=color)
                else:
                    ax.scatter(sub[fx], sub[fy], s=3, alpha=0.4, color=color, label=f"Class {cls}")
            if i == j:
                ax.set_yticks([])
            ax.tick_params(labelsize=7)
            if i == k - 1:
                ax.set_xlabel(_label(fx), fontsize=8)
            if j == 0:
                ax.set_ylabel(_label(fy), fontsize=8)
    handles, labels = axes[0, 1].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=len(classes), markerscale=4)
    fig.suptitle(f"Pairwise relationships - top {k} features (balanced sample)", fontsize=13)
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    fig.savefig(path, dpi=120)
    plt.close(fig)


def plot_pca(coords: np.ndarray, labels: pd.Series, explained: np.ndarray, path: Path) -> None:
    classes = sorted(labels.unique())
    colors = plt.cm.tab10(np.arange(len(classes)))
    fig, ax = plt.subplots(figsize=(9, 7))
    for cls, color in zip(classes, colors):
        mask = (labels == cls).values
        ax.scatter(coords[mask, 0], coords[mask, 1], s=5, alpha=0.5, color=color, label=f"Class {cls}")
    ax.set_xlabel(f"PC1 ({explained[0] * 100:.1f}% of variance)")
    ax.set_ylabel(f"PC2 ({explained[1] * 100:.1f}% of variance)")
    ax.set_title("PCA projection of the numeric features (balanced sample)")
    ax.legend(markerscale=3)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def main() -> None:
    df = load_raw()
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    stats = distribution_stats(df)
    print("== Distribution statistics (full dataset) ==")
    print(stats.to_string())

    sample = balanced_sample(df)
    top = list(separation_scores(df).index[:4])
    coords, explained, loadings = pca_projection(df, sample)

    print("\n== PCA explained variance ratio ==")
    for i, value in enumerate(explained, start=1):
        print(f"PC{i}: {value * 100:5.1f}%  (cumulative {explained[:i].sum() * 100:5.1f}%)")
    print("\n== PCA loadings (PC1, PC2) ==")
    print(loadings.round(3).to_string())
    print(f"\nPairplot features: {top}")

    plot_distributions(df, stats, FIG_DIR / "feature_distributions.png")
    plot_pairs(sample, top, FIG_DIR / "pairplot_top_features.png")
    plot_pca(coords, sample[TARGET], explained, FIG_DIR / "pca_projection.png")
    print(f"\nFigures saved to: {FIG_DIR}")


if __name__ == "__main__":
    main()
