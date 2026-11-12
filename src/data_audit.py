"""Dataset audit for Covertype (ticket #7): rows, columns, dtypes, nulls, duplicates."""
from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "covtype.data"

COLUMNS = (
    [
        "Elevation",
        "Aspect",
        "Slope",
        "Horizontal_Distance_To_Hydrology",
        "Vertical_Distance_To_Hydrology",
        "Horizontal_Distance_To_Roadways",
        "Hillshade_9am",
        "Hillshade_Noon",
        "Hillshade_3pm",
        "Horizontal_Distance_To_Fire_Points",
    ]
    + [f"Wilderness_Area{i}" for i in range(1, 5)]
    + [f"Soil_Type{i}" for i in range(1, 41)]
    + ["Cover_Type"]
)


def load_raw(path: Path = DATA_PATH) -> pd.DataFrame:
    """Load the raw file (no header) assigning the official column names."""
    return pd.read_csv(path, header=None, names=COLUMNS)


def audit(df: pd.DataFrame) -> dict:
    """Return the audit metrics. Does not modify the dataframe."""
    nulls = df.isnull().sum()
    return {
        "rows": df.shape[0],
        "columns": df.shape[1],
        "dtypes": df.dtypes.astype(str),
        "nulls_per_column": nulls,
        "nulls_total": int(nulls.sum()),
        "duplicates": int(df.duplicated().sum()),
    }


def main() -> None:
    result = audit(load_raw())

    summary = pd.DataFrame(
        {
            "Metric": ["Rows", "Columns", "Nulls", "Duplicates"],
            "Value": [
                result["rows"],
                result["columns"],
                result["nulls_total"],
                result["duplicates"],
            ],
        }
    )

    print("== Audit summary ==")
    print(summary.to_string(index=False))
    print("\n== Dtypes (count per type) ==")
    print(result["dtypes"].value_counts().to_string())
    print("\n== Dtype per column ==")
    print(result["dtypes"].to_string())
    print("\n== Nulls per column (only columns with nulls) ==")
    with_nulls = result["nulls_per_column"][result["nulls_per_column"] > 0]
    print(with_nulls.to_string() if not with_nulls.empty else "None")


if __name__ == "__main__":
    main()
