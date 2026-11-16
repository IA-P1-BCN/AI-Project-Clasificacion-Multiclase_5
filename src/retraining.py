"""New data collection and retraining pipeline (ticket #36): validate, ingest and store new labeled samples, and retrain the model pipeline without data leakage."""
from pathlib import Path
import sys
import tempfile

import pandas as pd

from data_audit import COLUMNS, load_raw
from data_cleaning import (
    FEATURES,
    NUMERIC_FEATURES,
    SOIL_FEATURES,
    TARGET,
    WILDERNESS_FEATURES,
    clean,
)
from data_split import split_train_val_test
from export_model import (
    METADATA_PATH,
    MODEL_PATH,
    export,
    fit_pipeline,
    validation_metrics,
)
from feature_scaling import BINARY_FEATURES
from target_encoding import COVER_TYPES

ROOT = Path(__file__).resolve().parents[1]
NEW_DATA_PATH = ROOT / "data" / "processed" / "new_samples.csv"

# Physical bounds matching app/schemas.py (#34).
NUMERIC_BOUNDS: dict[str, tuple[float, float]] = {
    "Elevation": (0.0, 5000.0),
    "Aspect": (0.0, 360.0),
    "Slope": (0.0, 90.0),
    "Horizontal_Distance_To_Hydrology": (0.0, 10000.0),
    "Vertical_Distance_To_Hydrology": (-500.0, 1000.0),
    "Horizontal_Distance_To_Roadways": (0.0, 10000.0),
    "Hillshade_9am": (0.0, 255.0),
    "Hillshade_Noon": (0.0, 255.0),
    "Hillshade_3pm": (0.0, 255.0),
    "Horizontal_Distance_To_Fire_Points": (0.0, 10000.0),
}

COMPACT_FIELDS = NUMERIC_FEATURES + ["Wilderness_Area", "Soil_Type", TARGET]


def expand_compact_sample(sample: dict) -> dict:
    """Convert a compact 13-field record (10 numerics + Wilderness_Area + Soil_Type + Cover_Type) into the 55 canonical COLUMNS."""
    missing = set(COMPACT_FIELDS) - set(sample)
    extra = set(sample) - set(COMPACT_FIELDS)
    if missing or extra:
        raise ValueError(
            f"Compact sample must have fields {COMPACT_FIELDS}; "
            f"missing={sorted(missing)}, extra={sorted(extra)}"
        )
    try:
        values = {name: float(sample[name]) for name in COMPACT_FIELDS}
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Compact sample has a non-numeric value: {exc}") from exc
    for name, value in values.items():
        if value != value:  # NaN
            raise ValueError(f"Null values are not allowed; {name} is NaN")
    for name in ("Wilderness_Area", "Soil_Type", TARGET):
        if not values[name].is_integer():
            raise ValueError(f"{name} must be an integer, got {sample[name]}")
    wilderness = int(values["Wilderness_Area"])
    soil = int(values["Soil_Type"])
    if not (1 <= wilderness <= len(WILDERNESS_FEATURES)):
        raise ValueError(f"Wilderness_Area must be in 1..4, got {wilderness}")
    if not (1 <= soil <= len(SOIL_FEATURES)):
        raise ValueError(f"Soil_Type must be in 1..40, got {soil}")

    # The API (#34) accepts decimals; the dataset stores whole units, so numerics are rounded.
    row = {col: int(round(values[col])) for col in NUMERIC_FEATURES}
    for idx, col in enumerate(WILDERNESS_FEATURES, start=1):
        row[col] = int(wilderness == idx)
    for idx, col in enumerate(SOIL_FEATURES, start=1):
        row[col] = int(soil == idx)
    row[TARGET] = int(values[TARGET])
    return row


def _coerce_to_frame(samples: pd.DataFrame | dict | list[dict]) -> pd.DataFrame:
    """Normalize dict, list of dicts, or DataFrame (compact or 55-column) into a 55-column DataFrame."""
    if isinstance(samples, dict):
        records = [samples]
    elif isinstance(samples, list):
        if not samples:
            raise ValueError("Cannot ingest an empty sample list.")
        records = samples
    elif isinstance(samples, pd.DataFrame):
        if samples.empty:
            raise ValueError("Cannot ingest an empty DataFrame.")
        if list(samples.columns) == COLUMNS:
            return samples.copy()
        if set(samples.columns) == set(COMPACT_FIELDS):
            records = samples.to_dict(orient="records")
        else:
            raise ValueError(
                f"DataFrame columns must match the 55 COLUMNS or the 13 COMPACT_FIELDS; "
                f"got {list(samples.columns)}"
            )
    else:
        raise TypeError(f"Unsupported sample input type: {type(samples).__name__}")

    expanded = []
    for rec in records:
        if set(rec) == set(COLUMNS):
            expanded.append({col: rec[col] for col in COLUMNS})
        else:
            expanded.append(expand_compact_sample(rec))
    return pd.DataFrame(expanded, columns=COLUMNS)


def validate_samples(df: pd.DataFrame) -> pd.DataFrame:
    """Validate that a DataFrame conforms to the 55-column Covertype schema and physical bounds.

    Returns an int64 copy ordered by COLUMNS, or raises ValueError.
    """
    if list(df.columns) != COLUMNS:
        raise ValueError(f"Expected the 55 canonical COLUMNS in order; got {list(df.columns)}")
    if df.isna().any().any():
        null_cols = df.columns[df.isna().any()].tolist()
        raise ValueError(f"Null values are not allowed; found nulls in {null_cols}")

    numeric = df.apply(pd.to_numeric, errors="raise")
    fractional = numeric.columns[(numeric % 1 != 0).any()].tolist()
    if fractional:
        raise ValueError(f"All 55 columns must hold integer values; found decimals in {fractional}")

    for col, (low, high) in NUMERIC_BOUNDS.items():
        series = numeric[col]
        out_of_bounds = (series < low) | (series > high)
        if out_of_bounds.any():
            bad_val = series[out_of_bounds].iloc[0]
            raise ValueError(f"{col}={bad_val} is outside allowed bounds [{low}, {high}]")

    for col in BINARY_FEATURES:
        invalid_bin = ~df[col].isin([0, 1])
        if invalid_bin.any():
            raise ValueError(f"Binary column {col} must contain only 0 or 1")

    if (df[WILDERNESS_FEATURES].sum(axis=1) != 1).any():
        raise ValueError("Each row must have exactly one active Wilderness_Area indicator")
    if (df[SOIL_FEATURES].sum(axis=1) != 1).any():
        raise ValueError("Each row must have exactly one active Soil_Type indicator")

    if (~df[TARGET].isin(COVER_TYPES)).any():
        bad_targets = sorted(set(df[TARGET].unique()) - set(COVER_TYPES))
        raise ValueError(f"Invalid {TARGET} label(s): {bad_targets}. Expected {COVER_TYPES}")

    return df[COLUMNS].astype("int64")


def load_new_samples(path: Path = NEW_DATA_PATH) -> pd.DataFrame:
    """Load and validate stored new samples from CSV; returns an empty 55-column DataFrame if none exist."""
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(columns=COLUMNS, dtype="int64")
    df = pd.read_csv(path)
    if df.empty:
        return pd.DataFrame(columns=COLUMNS, dtype="int64")
    return validate_samples(df)


def ingest_samples(
    samples: pd.DataFrame | dict | list[dict],
    path: Path = NEW_DATA_PATH,
) -> pd.DataFrame:
    """Validate incoming labeled samples, append to storage CSV, deduplicate via clean(), and save."""
    path = Path(path)
    incoming = validate_samples(_coerce_to_frame(samples))
    existing = load_new_samples(path)
    combined = (
        incoming if existing.empty else pd.concat([existing, incoming], ignore_index=True)
    )
    cleaned = clean(combined).reset_index(drop=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(path, index=False)
    return cleaned


def prepare_retraining_splits(
    raw_df: pd.DataFrame,
    new_samples_df: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series, int]:
    """Build leakage-free (X_train, X_val, X_test, y_train, y_val, y_test, added_rows).

    The canonical dataset is split first with `split_train_val_test` (#16) so
    `validation` and `test` stay fixed and untouched. Validated `new_samples_df`
    rows are filtered to exclude any row whose 54 features already appear in
    `validation` or `test` (preventing held-out leakage) and then appended to
    the training partition only, followed by `clean()` to drop exact duplicates.
    """
    base = clean(raw_df)
    X_train, X_val, X_test, y_train, y_val, y_test = split_train_val_test(
        base[FEATURES], base[TARGET]
    )
    if new_samples_df is None or new_samples_df.empty:
        return X_train, X_val, X_test, y_train, y_val, y_test, 0

    validated_new = validate_samples(new_samples_df)

    # Guard against held-out leakage: reject any new sample whose 54 features match a validation or test row.
    held_out_keys = pd.concat([X_val, X_test], ignore_index=True).drop_duplicates()
    merged_flags = validated_new[FEATURES].merge(
        held_out_keys, on=FEATURES, how="left", indicator=True
    )
    non_leaking_new = validated_new.loc[
        (merged_flags["_merge"] == "left_only").to_numpy()
    ]

    train_df = X_train.copy()
    train_df[TARGET] = y_train.to_numpy()
    base_train_len = len(train_df)

    augmented_train = clean(
        pd.concat([train_df, non_leaking_new], ignore_index=True)
    ).reset_index(drop=True)
    added_rows = len(augmented_train) - base_train_len

    return (
        augmented_train[FEATURES],
        X_val,
        X_test,
        augmented_train[TARGET],
        y_val,
        y_test,
        added_rows,
    )


def retrain_pipeline(
    raw_df: pd.DataFrame,
    new_samples_df: pd.DataFrame,
    min_macro_f1: float = 0.90,
    promote: bool = False,
    model_path: Path = MODEL_PATH,
    metadata_path: Path = METADATA_PATH,
) -> dict:
    """Fit the model pipeline on the augmented training split, evaluate on the fixed validation split, and optionally export."""
    X_train, X_val, _, y_train, y_val, _, added_rows = prepare_retraining_splits(
        raw_df, new_samples_df
    )
    pipeline = fit_pipeline(X_train, y_train)
    metrics = validation_metrics(pipeline, X_val, y_val)
    rows = {
        "train_base": int(len(y_train) - added_rows),
        "new_samples_added": int(added_rows),
        "train_total": int(len(y_train)),
        "validation": int(len(y_val)),
    }
    passed_gate = metrics["macro_f1"] >= min_macro_f1
    promoted = False
    metadata = None
    if promote and passed_gate:
        metadata = export(
            pipeline, rows=rows, metrics=metrics, model_path=model_path, metadata_path=metadata_path
        )
        promoted = True

    return {
        "rows": rows,
        "validation_metrics": metrics,
        "min_macro_f1": float(min_macro_f1),
        "passed_gate": bool(passed_gate),
        "promoted": bool(promoted),
        "metadata": metadata,
    }


def _run_self_checks(raw_df: pd.DataFrame) -> dict:
    """Verify ingestion, validation, deduplication, leakage protection and retraining in a temporary directory."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_csv = Path(tmp_dir) / "new_samples.csv"

        # 1. Ingest a compact 13-field sample and a second distinct compact sample.
        sample_a = {
            "Elevation": 2950,
            "Aspect": 160,
            "Slope": 14,
            "Horizontal_Distance_To_Hydrology": 240,
            "Vertical_Distance_To_Hydrology": 35,
            "Horizontal_Distance_To_Roadways": 2100,
            "Hillshade_9am": 218,
            "Hillshade_Noon": 228,
            "Hillshade_3pm": 142,
            "Horizontal_Distance_To_Fire_Points": 1850,
            "Wilderness_Area": 1,
            "Soil_Type": 29,
            "Cover_Type": 2,
        }
        sample_b = {**sample_a, "Elevation": 3350, "Wilderness_Area": 3, "Soil_Type": 38, "Cover_Type": 7}

        stored = ingest_samples([sample_a, sample_b], path=tmp_csv)
        assert len(stored) == 2, f"Expected 2 stored samples, got {len(stored)}"

        # 2. Re-ingesting the same sample must deduplicate via clean().
        stored_again = ingest_samples(sample_a, path=tmp_csv)
        assert len(stored_again) == 2, "Duplicate sample was not dropped on re-ingestion"

        # 3. Invalid samples must raise ValueError without corrupting storage.
        for bad_sample in [
            {**sample_a, "Elevation": 9999},  # out of bounds
            {**sample_a, "Cover_Type": 9},  # invalid class
            {**sample_a, "Soil_Type": 99},  # invalid soil type
        ]:
            try:
                ingest_samples(bad_sample, path=tmp_csv)
            except ValueError:
                pass
            else:
                raise AssertionError(f"Invalid sample was not rejected: {bad_sample}")

        assert len(load_new_samples(tmp_csv)) == 2, "Storage changed after rejected sample"

        # 4. Verify prepare_retraining_splits on the canonical dataset:
        #    include 1 held-out validation row (must be filtered out) + 2 genuinely new rows.
        _, X_val_full, X_test_full, _, y_val_full, _ = split_train_val_test(
            raw_df[FEATURES], raw_df[TARGET]
        )
        leaked_row = X_val_full.iloc[[0]].copy()
        leaked_row[TARGET] = int(y_val_full.iloc[0])
        mixed_batch = pd.concat([stored_again, leaked_row], ignore_index=True)

        X_tr, X_v, X_te, y_tr, y_v, y_te, added = prepare_retraining_splits(
            raw_df, mixed_batch
        )
        assert len(y_v) == len(y_val_full) == 87152, "Validation size changed"
        assert len(y_te) == len(X_test_full) == 87152, "Test size changed"
        assert added == 2, f"Expected 2 non-overlapping rows added to train, got {added}"

        # 5. End-to-end retraining check on a stratified 20,000-row sample of raw_df.
        sample_df = raw_df.groupby(TARGET, group_keys=False).apply(
            lambda g: g.sample(frac=20000 / len(raw_df), random_state=42),
            include_groups=False,
        )
        sample_df[TARGET] = raw_df.loc[sample_df.index, TARGET]
        sample_df = sample_df[COLUMNS].reset_index(drop=True)

        tmp_model = Path(tmp_dir) / "model.joblib"
        tmp_meta = Path(tmp_dir) / "model_metadata.json"
        retrain_res = retrain_pipeline(
            sample_df,
            stored_again,
            min_macro_f1=0.50,
            promote=True,
            model_path=tmp_model,
            metadata_path=tmp_meta,
        )
        assert retrain_res["promoted"], "Expected retrained pipeline to pass gate and export"
        assert tmp_model.exists() and tmp_meta.exists(), "Exported artifacts missing"

        return {
            "stored_rows": len(stored_again),
            "canonical_train_base": len(y_tr) - added,
            "canonical_added": added,
            "canonical_train_total": len(y_tr),
            "canonical_val_rows": len(y_v),
            "canonical_test_rows": len(y_te),
            "sample_retrain_metrics": retrain_res["validation_metrics"],
        }


def main() -> None:
    df = clean(load_raw())
    run_full = "--full" in sys.argv[1:]

    print("== New data collection + retraining pipeline (ticket #36) ==")
    print(f"Default new-samples storage path: {NEW_DATA_PATH}")
    print(f"Schema: {len(COLUMNS)} columns ({len(FEATURES)} FEATURES + {TARGET} in {COVER_TYPES})")

    checks = _run_self_checks(df)
    print("\n== Ingestion, validation & leakage-guard checks ==")
    print(f"Compact & 55-column ingestion + deduplication: passed ({checks['stored_rows']} unique rows)")
    print("Out-of-bounds / invalid-label / invalid-one-hot rejection: passed")
    print(
        f"Canonical split protection: train={checks['canonical_train_base']:,} + "
        f"{checks['canonical_added']} new -> {checks['canonical_train_total']:,} | "
        f"validation={checks['canonical_val_rows']:,} (unchanged) | "
        f"test={checks['canonical_test_rows']:,} (unchanged)"
    )
    print(
        f"Sample retraining & export check (20,000 stratified rows): "
        f"val accuracy={checks['sample_retrain_metrics']['accuracy']:.4f}, "
        f"val macro_f1={checks['sample_retrain_metrics']['macro_f1']:.4f} (passed)"
    )

    if run_full:
        new_df = load_new_samples(NEW_DATA_PATH)
        print(f"\n== Full retraining on canonical split ({len(new_df):,} stored new samples) ==")
        res = retrain_pipeline(df, new_df, promote=False)
        print(f"Rows: {res['rows']}")
        print(
            f"Validation accuracy: {res['validation_metrics']['accuracy']:.4f} | "
            f"macro F1: {res['validation_metrics']['macro_f1']:.4f} | "
            f"gate (>={res['min_macro_f1']:.2f}): {res['passed_gate']}"
        )


if __name__ == "__main__":
    main()
