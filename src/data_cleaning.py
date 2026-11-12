"""Missing values and duplicates (ticket #12): inspect, apply the strategy and verify."""
import pandas as pd

from data_audit import COLUMNS, load_raw

TARGET = "Cover_Type"
FEATURES = COLUMNS[:54]
NUMERIC_FEATURES = COLUMNS[:10]
WILDERNESS_FEATURES = COLUMNS[10:14]
SOIL_FEATURES = COLUMNS[14:54]


def missing_report(df: pd.DataFrame) -> dict:
    """Explicit nulls plus disguised missing values in the one-hot groups.

    A row whose Wilderness_Area or Soil_Type indicators do not sum to exactly 1
    has a missing (0) or contradictory (>1) category even though no cell is null.
    """
    return {
        "nulls_per_column": df.isnull().sum(),
        "nulls_total": int(df.isnull().sum().sum()),
        "rows_without_single_wilderness": int((df[WILDERNESS_FEATURES].sum(axis=1) != 1).sum()),
        "rows_without_single_soil": int((df[SOIL_FEATURES].sum(axis=1) != 1).sum()),
    }


def duplicate_report(df: pd.DataFrame) -> dict:
    """Exact duplicate rows, and rows with equal features but a different target."""
    full = int(df.duplicated().sum())
    same_features = int(df.duplicated(subset=FEATURES).sum())
    return {
        "duplicate_rows": full,
        "conflicting_rows": same_features - full,
    }


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the missing-value and duplicate strategy and return a new dataframe.

    Strategy (see docs/PREPROCESSING.md):
    - Missing values: none are expected, so no imputation is defined. If any
      appear, fail instead of silently imputing or dropping.
    - Duplicates: drop exact duplicate rows, keeping the first occurrence.
      Rows with equal features but different targets are kept.
    """
    missing = missing_report(df)
    if missing["nulls_total"] > 0:
        columns = missing["nulls_per_column"]
        raise ValueError(
            "Unexpected missing values found; no imputation strategy is defined. "
            f"Columns with nulls: {columns[columns > 0].to_dict()}"
        )
    return df.drop_duplicates(keep="first").reset_index(drop=True)


def main() -> None:
    df = load_raw()
    missing = missing_report(df)
    duplicates = duplicate_report(df)
    cleaned = clean(df)

    print("== Missing values ==")
    print(f"Explicit nulls: {missing['nulls_total']}")
    print(f"Rows without exactly one Wilderness_Area: {missing['rows_without_single_wilderness']}")
    print(f"Rows without exactly one Soil_Type: {missing['rows_without_single_soil']}")
    print("\n== Zero values in numeric features (not treated as missing) ==")
    print((df[NUMERIC_FEATURES] == 0).sum().to_string())
    print("\n== Duplicates ==")
    print(f"Exact duplicate rows: {duplicates['duplicate_rows']}")
    print(f"Rows with equal features but a different {TARGET}: {duplicates['conflicting_rows']}")
    print("\n== After cleaning ==")
    print(f"Rows before: {len(df):,}")
    print(f"Rows after:  {len(cleaned):,}")
    print(f"Rows removed: {len(df) - len(cleaned):,}")
    print(f"Nulls remaining: {int(cleaned.isnull().sum().sum())}")
    print(f"Duplicates remaining: {int(cleaned.duplicated().sum())}")


if __name__ == "__main__":
    main()
