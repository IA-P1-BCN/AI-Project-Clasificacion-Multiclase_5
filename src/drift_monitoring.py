"""Data drift monitoring (ticket #53): detect when the inputs received by the API stop
looking like the data the model was trained on.

Metric: Population Stability Index (PSI) per input feature, computed on a window of
consecutive stored predictions against a reference profile built from the train split.
Levels: PSI < 0.1 ok, < 0.25 warning, otherwise alert. See docs/DRIFT_MONITORING.md.

Commands (run with the pinned versions, inside Docker):

    python src/drift_monitoring.py build                          # reference profile
    python src/drift_monitoring.py check                          # latest window of the database
    python src/drift_monitoring.py simulate [n_windows] [size]    # false alarms and detection
"""
import json
import logging
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from data_cleaning import NUMERIC_FEATURES, SOIL_FEATURES, WILDERNESS_FEATURES

logger = logging.getLogger("uvicorn.error")

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_PATH = Path(os.getenv("DRIFT_REFERENCE_PATH", ROOT / "models" / "drift_reference.json"))

CATEGORICAL = ["Wilderness_Area", "Soil_Type"]
MONITORED = NUMERIC_FEATURES + CATEGORICAL  # the 12 inputs the API stores

N_BINS = 10  # decile bins for numeric features
EPSILON = 1e-4  # floor of a bin proportion, so PSI stays finite
RARE_SHARE = 0.01  # categories below this share of the reference are merged into "other"
PSI_WARNING = 0.1
PSI_ALERT = 0.25
MIN_ROWS = 200  # a window with fewer rows is `insufficient_data`
LEVELS = ("ok", "warning", "alert")


def _env_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, default))
    except ValueError:
        return default
    return value if value > 0 else default


WINDOW_SIZE = _env_int("DRIFT_WINDOW", 500)


# ---------------------------------------------------------------- reference and metric

def inputs_from_features(X: pd.DataFrame) -> pd.DataFrame:
    """The 12 monitored inputs from a frame with the 54 FEATURES.

    The one-hot blocks become `Wilderness_Area` (1-4) and `Soil_Type` (1-40), the
    representation the API stores, so the reference and the live data match.
    """
    inputs = X[NUMERIC_FEATURES].astype(float).reset_index(drop=True)
    inputs["Wilderness_Area"] = X[WILDERNESS_FEATURES].to_numpy().argmax(axis=1) + 1
    inputs["Soil_Type"] = X[SOIL_FEATURES].to_numpy().argmax(axis=1) + 1
    return inputs


def feature_shares(spec: dict, values) -> np.ndarray:
    """Proportion of `values` in each bin of a feature spec of the reference."""
    values = np.asarray(values)
    if spec["type"] == "numeric":
        index = np.searchsorted(np.asarray(spec["edges"], dtype=float), values.astype(float), side="left")
        bins = len(spec["edges"]) + 1
    else:
        categories = spec["categories"]
        lookup = {category: position for position, category in enumerate(categories)}
        index = np.fromiter(
            (lookup.get(int(value), len(categories)) for value in values),
            dtype=int,
            count=len(values),
        )
        bins = len(categories) + 1  # the last bin is "other" (rare or never seen)
    return np.bincount(index, minlength=bins) / len(values)


def psi(expected, actual) -> float:
    """Population Stability Index between two lists of bin proportions."""
    e = np.clip(np.asarray(expected, dtype=float), EPSILON, None)
    a = np.clip(np.asarray(actual, dtype=float), EPSILON, None)
    return float(np.sum((a - e) * np.log(a / e)))


def level_of(value: float) -> str:
    if value >= PSI_ALERT:
        return "alert"
    if value >= PSI_WARNING:
        return "warning"
    return "ok"


def build_reference(inputs: pd.DataFrame, n_bins: int = N_BINS) -> dict:
    """Reference profile of the training inputs: bins and expected proportions per feature."""
    features = {}
    for name in NUMERIC_FEATURES:
        values = inputs[name].to_numpy(dtype=float)
        inner = np.linspace(0, 1, n_bins + 1)[1:-1]
        edges = np.unique(np.quantile(values, inner))  # ties collapse into fewer bins
        spec = {"type": "numeric", "edges": [float(edge) for edge in edges]}
        spec["expected"] = [float(p) for p in feature_shares(spec, values)]
        features[name] = spec
    for name in CATEGORICAL:
        shares = inputs[name].astype(int).value_counts(normalize=True)
        keep = sorted(int(category) for category, share in shares.items() if share >= RARE_SHARE)
        spec = {"type": "categorical", "categories": keep}
        spec["expected"] = [float(p) for p in feature_shares(spec, inputs[name].to_numpy())]
        features[name] = spec
    return {
        "n_rows": int(len(inputs)),
        "n_bins": int(n_bins),
        "rare_share": RARE_SHARE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "features": features,
    }


def save_reference(reference: dict, path: Path = REFERENCE_PATH) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(reference, indent=2) + "\n", encoding="utf-8")


def load_reference(path: Path = REFERENCE_PATH) -> dict:
    """Read and validate the reference profile; raises if it is missing or malformed."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Drift reference not found at {path}. Build it with: python src/drift_monitoring.py build")
    reference = json.loads(path.read_text(encoding="utf-8"))
    missing = [name for name in MONITORED if name not in reference.get("features", {})]
    if missing:
        raise ValueError(f"Drift reference at {path} lacks the features {missing}.")
    return reference


# ------------------------------------------------------------------ windows and alerts

def window_report(reference: dict, window: pd.DataFrame, min_rows: int = MIN_ROWS) -> dict:
    """PSI of every monitored feature for one window of inputs, and its status."""
    rows = int(len(window))
    if rows < min_rows:
        return {"status": "insufficient_data", "rows": rows, "max_psi": None,
                "max_feature": None, "features": {}, "alerts": []}
    features = {}
    for name, spec in reference["features"].items():
        value = psi(spec["expected"], feature_shares(spec, window[name].to_numpy()))
        features[name] = {"psi": value, "level": level_of(value)}
    max_feature = max(features, key=lambda name: features[name]["psi"])
    status = LEVELS[max(LEVELS.index(item["level"]) for item in features.values())]
    alerts = [
        {"feature": name, "psi": item["psi"], "level": item["level"]}
        for name, item in sorted(features.items(), key=lambda pair: -pair[1]["psi"])
        if item["level"] != "ok"
    ]
    return {"status": status, "rows": rows, "max_psi": features[max_feature]["psi"],
            "max_feature": max_feature, "features": features, "alerts": alerts}


def windows_report(reference: dict, rows: pd.DataFrame, window_size: int = WINDOW_SIZE,
                   n_windows: int = 5, min_rows: int = MIN_ROWS) -> dict:
    """Drift of the last `n_windows` windows of consecutive predictions, oldest first.

    `rows` has `id`, `created_at_utc` and the monitored inputs, ordered by id.
    Windows are counted back from the most recent prediction, so the latest one
    is always full; the oldest one may be partial.
    """
    windows = []
    end = len(rows)
    while end > 0 and len(windows) < n_windows:
        start = max(end - window_size, 0)
        chunk = rows.iloc[start:end]
        report = window_report(reference, chunk, min_rows)
        report.update(
            first_id=int(chunk["id"].iloc[0]),
            last_id=int(chunk["id"].iloc[-1]),
            start_utc=str(chunk["created_at_utc"].iloc[0]),
            end_utc=str(chunk["created_at_utc"].iloc[-1]),
        )
        windows.append(report)
        end = start
    windows.reverse()
    return {"window_size": int(window_size), "windows": windows}


def should_alert(window: dict) -> bool:
    return window["status"] in ("warning", "alert")


def exit_code(window: dict) -> int:
    """Exit code of the command-line check: 1 only for an alert."""
    return 1 if window["status"] == "alert" else 0


def alert_message(window: dict) -> dict:
    """JSON payload of a drift notification (`text` for Slack, `content` for Discord)."""
    top = ", ".join(f"{a['feature']} (PSI {a['psi']:.2f})" for a in window["alerts"][:3])
    text = (
        f"Data drift {window['status'].upper()}: max PSI {window['max_psi']:.2f} on "
        f"{window['max_feature']} over {window['rows']} predictions "
        f"(ids {window['first_id']}-{window['last_id']}). Top features: {top}."
    )
    return {
        "text": text,
        "content": text,
        "status": window["status"],
        "max_psi": window["max_psi"],
        "alerts": window["alerts"],
        "first_id": window["first_id"],
        "last_id": window["last_id"],
    }


def send_webhook(url: str, payload: dict, timeout: float = 5.0) -> bool:
    """POST the payload as JSON. Never raises: a failing webhook must not break the caller."""
    try:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "covertype-drift-monitor/1.0"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 300
    except Exception as exc:
        logger.warning("Drift webhook failed: %s", exc)
        return False


# -------------------------------------------------------------------------- simulation

def shift_elevation(meters: float):
    def apply(window: pd.DataFrame, rng) -> pd.DataFrame:
        window = window.copy()
        window["Elevation"] = window["Elevation"] + meters
        return window
    return apply


def change_soil_mix(share: float, soil_type: int):
    def apply(window: pd.DataFrame, rng) -> pd.DataFrame:
        window = window.copy()
        mask = rng.random(len(window)) < share
        window.loc[mask, "Soil_Type"] = soil_type
        return window
    return apply


def no_drift(window: pd.DataFrame, rng) -> pd.DataFrame:
    return window


SCENARIOS = {
    "No drift": no_drift,
    "Elevation +50 m": shift_elevation(50),
    "Elevation +100 m": shift_elevation(100),
    "Elevation +150 m": shift_elevation(150),
    "Elevation +300 m": shift_elevation(300),
    "30% of rows with Soil_Type 38": change_soil_mix(0.30, 38),
}


def simulate(reference: dict, inputs: pd.DataFrame, scenarios: dict, n_windows: int,
             window_size: int, rng) -> dict:
    """Draw `n_windows` random windows of `inputs` per scenario and count the statuses."""
    results = {}
    for name, apply in scenarios.items():
        statuses, max_psis, features = [], [], []
        for _ in range(n_windows):
            index = rng.choice(len(inputs), size=window_size, replace=False)
            window = apply(inputs.iloc[index].reset_index(drop=True), rng)
            report = window_report(reference, window)
            statuses.append(report["status"])
            max_psis.append(report["max_psi"])
            features.append(report["max_feature"])
        results[name] = {
            "windows": n_windows,
            "ok": statuses.count("ok"),
            "warning": statuses.count("warning"),
            "alert": statuses.count("alert"),
            "detection_rate": (statuses.count("warning") + statuses.count("alert")) / n_windows,
            "alert_rate": statuses.count("alert") / n_windows,
            "median_max_psi": float(np.median(max_psis)),
            "p95_max_psi": float(np.percentile(max_psis, 95)),
            "main_feature": max(set(features), key=features.count),
        }
    return results


# -------------------------------------------------------------------------- commands

def _train_validation_inputs():
    from data_audit import load_raw
    from data_cleaning import FEATURES, TARGET, clean
    from data_split import split_train_val_test

    df = clean(load_raw())
    X_train, X_val, *_ = split_train_val_test(df[FEATURES], df[TARGET])
    return inputs_from_features(X_train), inputs_from_features(X_val)


def build_command(args: list) -> int:
    train, validation = _train_validation_inputs()
    reference = build_reference(train)
    save_reference(reference)
    print(f"== Drift reference built from {reference['n_rows']:,} training rows ==")
    for name, spec in reference["features"].items():
        if spec["type"] == "numeric":
            detail = f"{len(spec['edges']) + 1} bins (deciles)"
        else:
            detail = f"{len(spec['categories'])} categories + other"
        print(f"{name:<36}{spec['type']:<13}{detail}")
    check = window_report(reference, validation)
    print(f"\nSanity check, whole validation set ({len(validation):,} rows) against the reference: "
          f"status {check['status']}, max PSI {check['max_psi']:.4f} ({check['max_feature']})")
    print(f"Reference written to {REFERENCE_PATH}")
    return 0


def check_command(args: list) -> int:
    from database import prediction_inputs

    reference = load_reference()
    rows = pd.DataFrame(prediction_inputs(limit=WINDOW_SIZE))
    if rows.empty:
        print("No predictions stored yet.")
        return 0
    window = windows_report(reference, rows, WINDOW_SIZE, n_windows=1)["windows"][-1]
    print(f"== Drift check: latest {window['rows']} predictions (ids {window['first_id']}-{window['last_id']}) ==")
    print(f"Status: {window['status']}")
    if window["status"] == "insufficient_data":
        print(f"Fewer than {MIN_ROWS} predictions in the window: nothing to decide yet.")
        return 0
    print(f"Max PSI: {window['max_psi']:.4f} ({window['max_feature']})")
    for item in window["alerts"]:
        print(f"  {item['level']:<8}{item['feature']:<36}PSI {item['psi']:.4f}")
    url = os.getenv("DRIFT_WEBHOOK_URL")
    if url and should_alert(window):
        print("Webhook:", "sent" if send_webhook(url, alert_message(window)) else "failed")
    return exit_code(window)


def simulate_command(args: list) -> int:
    n_windows = int(args[0]) if args else 200
    window_size = int(args[1]) if len(args) > 1 else WINDOW_SIZE
    train, validation = _train_validation_inputs()
    reference = build_reference(train)
    results = simulate(reference, validation, SCENARIOS, n_windows, window_size, np.random.default_rng(42))
    print(f"== Drift simulation: {n_windows} windows of {window_size} validation rows per scenario ==")
    print(f"Thresholds: warning at PSI >= {PSI_WARNING}, alert at PSI >= {PSI_ALERT}")
    print(f"\n{'scenario':<32}{'ok':>5}{'warning':>9}{'alert':>7}{'detected':>10}"
          f"{'median max PSI':>16}{'p95 max PSI':>13}  main feature")
    for name, item in results.items():
        print(f"{name:<32}{item['ok']:>5}{item['warning']:>9}{item['alert']:>7}"
              f"{item['detection_rate']:>10.0%}{item['median_max_psi']:>16.3f}"
              f"{item['p95_max_psi']:>13.3f}  {item['main_feature']}")
    return 0


COMMANDS = {"build": build_command, "check": check_command, "simulate": simulate_command}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in COMMANDS:
        print("Usage: python src/drift_monitoring.py {build|check|simulate} [args]")
        return 2
    return COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main())