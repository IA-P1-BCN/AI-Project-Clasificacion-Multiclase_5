"""Data integrity tests (ticket #40): schema, nulls and one-hot invariants.

The synthetic-fixture tests always run. The ``*_real_dataset`` tests run only
when ``data/raw/covtype.data`` is present (it is git-ignored), so CI, which has
no dataset, skips them instead of failing.
"""
import pandas as pd
import pytest

from conftest import RAW_DATA_PATH
from data_audit import COLUMNS, audit, load_raw
from data_cleaning import FEATURES, NUMERIC_FEATURES, SOIL_FEATURES, WILDERNESS_FEATURES
from target_encoding import COVER_TYPES

EXPECTED_ROWS = 581_012  # UCI Covertype

requires_dataset = pytest.mark.skipif(
    not RAW_DATA_PATH.exists(), reason="raw dataset data/raw/covtype.data not present"
)


# --- Schema / constants (always run) ---------------------------------------


def test_columns_count_and_structure():
    assert len(COLUMNS) == 55  # 54 features + target
    assert FEATURES == COLUMNS[:54]
    assert COLUMNS[-1] == "Cover_Type"


def test_feature_blocks_partition_the_54_features():
    assert len(NUMERIC_FEATURES) == 10
    assert len(WILDERNESS_FEATURES) == 4
    assert len(SOIL_FEATURES) == 40
    assert NUMERIC_FEATURES + WILDERNESS_FEATURES + SOIL_FEATURES == FEATURES
    # No overlap between the three blocks.
    assert len(set(NUMERIC_FEATURES) | set(WILDERNESS_FEATURES) | set(SOIL_FEATURES)) == 54


# --- audit() and integrity checks on a known frame (always run) ------------


def test_audit_reports_schema_and_no_nulls(synthetic_dataset):
    result = audit(synthetic_dataset)
    assert result["rows"] == len(synthetic_dataset)
    assert result["columns"] == 55
    assert result["nulls_total"] == 0


def test_audit_detects_injected_nulls(synthetic_dataset):
    corrupted = synthetic_dataset.copy()
    corrupted.loc[0, "Elevation"] = pd.NA
    assert audit(corrupted)["nulls_total"] == 1


def test_one_hot_blocks_have_exactly_one_active(synthetic_dataset):
    assert synthetic_dataset[WILDERNESS_FEATURES].sum(axis=1).eq(1).all()
    assert synthetic_dataset[SOIL_FEATURES].sum(axis=1).eq(1).all()


def test_binary_columns_are_zero_or_one(synthetic_dataset):
    binary = synthetic_dataset[WILDERNESS_FEATURES + SOIL_FEATURES]
    assert binary.isin([0, 1]).all().all()


def test_target_values_are_valid_cover_types(synthetic_dataset):
    assert set(synthetic_dataset["Cover_Type"].unique()) <= set(COVER_TYPES)


def test_load_raw_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_raw(tmp_path / "does_not_exist.data")


# --- Gated on the real dataset ---------------------------------------------


@requires_dataset
def test_real_dataset_schema_and_size():
    df = load_raw()
    assert df.shape == (EXPECTED_ROWS, 55)
    assert list(df.columns) == COLUMNS


@requires_dataset
def test_real_dataset_has_no_nulls():
    assert audit(load_raw())["nulls_total"] == 0


@requires_dataset
def test_real_dataset_invariants():
    df = load_raw()
    assert set(df["Cover_Type"].unique()) == set(COVER_TYPES)
    assert df[WILDERNESS_FEATURES].sum(axis=1).eq(1).all()
    assert df[SOIL_FEATURES].sum(axis=1).eq(1).all()
    assert df[WILDERNESS_FEATURES + SOIL_FEATURES].isin([0, 1]).all().all()
