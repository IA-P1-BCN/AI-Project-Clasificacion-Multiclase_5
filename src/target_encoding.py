"""Target encoding (ticket #15): encode Cover_Type (1-7) to 0-6 and save the mapping.

The class set is fixed by the ontology, so the encoding is a deterministic shift
(encoded = Cover_Type - 1). Nothing is learned from data, so there is no fit step
and no way to leak. The label -> class-name mapping is written to a JSON artifact
for the app to decode predictions at inference time.
"""
import json
from pathlib import Path

import pandas as pd

from data_audit import load_raw
from data_cleaning import TARGET, clean

MAPPING_PATH = Path(__file__).resolve().parents[1] / "models" / "label_mapping.json"

# Single source of truth: Cover_Type (1-7) -> dominant tree species (see ontology).
CLASS_NAMES = {
    1: "Spruce/Fir",
    2: "Lodgepole Pine",
    3: "Ponderosa Pine",
    4: "Cottonwood/Willow",
    5: "Aspen",
    6: "Douglas-fir",
    7: "Krummholz",
}
COVER_TYPES = sorted(CLASS_NAMES)  # [1, 2, 3, 4, 5, 6, 7]
# Model-facing 0-indexed labels, as XGBoost/LightGBM require.
ENCODE = {cover_type: cover_type - 1 for cover_type in COVER_TYPES}
DECODE = {encoded: cover_type for cover_type, encoded in ENCODE.items()}


def encode_target(y: pd.Series) -> pd.Series:
    """Map Cover_Type labels (1-7) to encoded labels (0-6).

    Raises ValueError if any value is not a known Cover_Type, so an unexpected
    class fails loudly instead of producing a silent off-by-one.
    """
    unknown = set(y.unique()) - set(ENCODE)
    if unknown:
        raise ValueError(f"Unknown Cover_Type label(s): {sorted(unknown)}. Expected {COVER_TYPES}.")
    return y.map(ENCODE).astype("int64")


def decode_target(y_encoded: pd.Series) -> pd.Series:
    """Map encoded labels (0-6) back to Cover_Type labels (1-7)."""
    unknown = set(y_encoded.unique()) - set(DECODE)
    if unknown:
        raise ValueError(f"Unknown encoded label(s): {sorted(unknown)}. Expected {sorted(DECODE)}.")
    return y_encoded.map(DECODE).astype("int64")


def label_mapping() -> list[dict]:
    """The encoded label -> Cover_Type + class name mapping, ordered by encoded label."""
    return [
        {"encoded": encoded, "cover_type": cover_type, "name": CLASS_NAMES[cover_type]}
        for encoded, cover_type in sorted(DECODE.items())
    ]


def save_mapping(path: Path = MAPPING_PATH) -> Path:
    """Write the label mapping to a JSON artifact for the app. Returns the path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(label_mapping(), indent=2) + "\n", encoding="utf-8")
    return path


def load_mapping(path: Path = MAPPING_PATH) -> list[dict]:
    """Read the label mapping JSON artifact written by save_mapping()."""
    if not path.exists():
        raise FileNotFoundError(f"Mapping not found at {path}. Run `python src/target_encoding.py` first.")
    return json.loads(path.read_text(encoding="utf-8"))


def check_encoding(y: pd.Series) -> None:
    """Raise AssertionError if the encoding is not consistent for y.

    Verifies encoded labels are 0-6, the round-trip is the identity, and all
    seven classes are present (full coverage of the mapping).
    """
    y_encoded = encode_target(y)
    assert set(y_encoded.unique()) <= set(range(len(COVER_TYPES))), "encoded labels outside 0-6"
    assert decode_target(y_encoded).equals(y.astype("int64")), "round-trip changed the labels"
    assert set(y.unique()) == set(COVER_TYPES), "not all seven classes are present in y"


def main() -> None:
    df = clean(load_raw())
    y = df[TARGET]

    check_encoding(y)
    path = save_mapping()
    y_encoded = encode_target(y)

    mapping = pd.DataFrame(label_mapping())
    counts = y_encoded.value_counts().sort_index()
    mapping["rows"] = mapping["encoded"].map(counts)
    mapping["share"] = (mapping["rows"] / len(y) * 100).round(2)

    print("== Target encoding (Cover_Type 1-7 -> encoded 0-6) ==")
    print(mapping.to_string(index=False))
    print(f"\nRows encoded: {len(y):,}")
    print("Consistency check passed: labels map to 0-6, round-trip is exact, all 7 classes present.")
    print(f"Mapping saved for the app at: {path}")


if __name__ == "__main__":
    main()
