"""Class distribution analysis (ticket #8): frequencies, percentages, imbalance ratio, bar chart."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from data_audit import load_raw

FIGURE_PATH = Path(__file__).resolve().parents[1] / "docs" / "figures" / "class_distribution.png"
TARGET = "Cover_Type"


def class_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Frequency and percentage per class, sorted by class label."""
    counts = df[TARGET].value_counts().sort_index()
    return pd.DataFrame(
        {
            "Class": counts.index,
            "Count": counts.values,
            "Percentage": (counts / counts.sum() * 100).round(2).values,
        }
    )


def imbalance_ratio(dist: pd.DataFrame) -> dict:
    """Min/max ratio between the least and most frequent classes."""
    min_row = dist.loc[dist["Count"].idxmin()]
    max_row = dist.loc[dist["Count"].idxmax()]
    return {
        "min_class": int(min_row["Class"]),
        "min_count": int(min_row["Count"]),
        "max_class": int(max_row["Class"]),
        "max_count": int(max_row["Count"]),
        "ratio": min_row["Count"] / max_row["Count"],
    }


def plot_distribution(dist: pd.DataFrame, path: Path = FIGURE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(dist["Class"].astype(str), dist["Count"], color="#4C72B0")
    ax.bar_label(bars, labels=[f"{c:,}" for c in dist["Count"]], padding=3, fontsize=9)
    ax.set_xlabel("Cover_Type (class)")
    ax.set_ylabel("Number of samples")
    ax.set_title("Class distribution - Covertype")
    ax.set_ylim(0, dist["Count"].max() * 1.12)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    df = load_raw()
    dist = class_distribution(df)
    imb = imbalance_ratio(dist)

    print("== Class frequencies ==")
    print(dist.to_string(index=False))
    print("\n== Imbalance ==")
    print(f"Least frequent: class {imb['min_class']} ({imb['min_count']:,})")
    print(f"Most frequent:  class {imb['max_class']} ({imb['max_count']:,})")
    print(f"Min/max ratio:  {imb['ratio']:.4f} (about 1:{1 / imb['ratio']:.0f})")

    plot_distribution(dist)
    print(f"\nChart saved to: {FIGURE_PATH}")


if __name__ == "__main__":
    main()