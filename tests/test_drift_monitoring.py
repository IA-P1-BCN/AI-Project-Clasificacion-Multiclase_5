"""Unit tests for the data drift monitoring (ticket #53)."""
import json

import numpy as np
import pandas as pd
import pytest

import database
import drift_monitoring as dm
from data_cleaning import SOIL_FEATURES, WILDERNESS_FEATURES
from target_encoding import CLASS_NAMES

_weights = np.random.default_rng(0).exponential(1.0, 40) ** 2
SOIL_WEIGHTS = _weights / _weights.sum()  # a few common soil types and many rare ones


def make_inputs(n: int, seed: int, elevation_shift: float = 0.0) -> pd.DataFrame:
    """Synthetic stand-in for the 12 monitored inputs."""
    rng = np.random.default_rng(seed)
    data = {
        "Elevation": rng.normal(2900, 280, n) + elevation_shift,
        "Aspect": rng.uniform(0, 360, n),
        "Slope": rng.gamma(4, 3, n),
        "Horizontal_Distance_To_Hydrology": rng.exponential(250, n),
        "Vertical_Distance_To_Hydrology": rng.normal(40, 60, n),
        "Horizontal_Distance_To_Roadways": rng.uniform(0, 5000, n),
        "Hillshade_9am": rng.normal(212, 25, n),
        "Hillshade_Noon": rng.normal(223, 18, n),
        "Hillshade_3pm": rng.normal(142, 38, n),
        "Horizontal_Distance_To_Fire_Points": rng.uniform(0, 5000, n),
        "Wilderness_Area": rng.choice([1, 2, 3, 4], n, p=[0.45, 0.05, 0.45, 0.05]),
        "Soil_Type": rng.choice(np.arange(1, 41), n, p=SOIL_WEIGHTS),
    }
    return pd.DataFrame(data)[dm.MONITORED]


@pytest.fixture(scope="module")
def reference():
    return dm.build_reference(make_inputs(20_000, seed=1))


def with_ids(inputs: pd.DataFrame) -> pd.DataFrame:
    rows = inputs.copy()
    rows.insert(0, "id", range(1, len(rows) + 1))
    rows.insert(1, "created_at_utc", [f"2026-11-17T10:{i // 60:02d}:{i % 60:02d}+00:00" for i in range(len(rows))])
    return rows


# ---- metric ----

def test_psi_of_identical_distributions_is_zero():
    assert dm.psi([0.2, 0.3, 0.5], [0.2, 0.3, 0.5]) == pytest.approx(0.0)


def test_psi_known_value_and_symmetry():
    assert dm.psi([0.5, 0.5], [0.25, 0.75]) == pytest.approx(0.2747, abs=1e-4)
    assert dm.psi([0.25, 0.75], [0.5, 0.5]) == pytest.approx(dm.psi([0.5, 0.5], [0.25, 0.75]))


def test_psi_stays_finite_with_empty_bins():
    value = dm.psi([0.5, 0.5, 0.0], [0.5, 0.0, 0.5])
    assert np.isfinite(value) and value > 0


def test_levels():
    assert dm.level_of(0.05) == "ok"
    assert dm.level_of(0.1) == "warning"
    assert dm.level_of(0.249) == "warning"
    assert dm.level_of(0.25) == "alert"


# ---- reference ----

def test_inputs_from_features_gives_the_12_stored_inputs(synthetic_xy):
    X, _ = synthetic_xy
    inputs = dm.inputs_from_features(X)
    assert list(inputs.columns) == dm.MONITORED and len(inputs) == len(X)
    assert inputs["Wilderness_Area"].between(1, 4).all() and inputs["Soil_Type"].between(1, 40).all()
    first = X.iloc[0]
    assert inputs["Wilderness_Area"].iloc[0] == first[WILDERNESS_FEATURES].to_numpy().argmax() + 1
    assert inputs["Soil_Type"].iloc[0] == first[SOIL_FEATURES].to_numpy().argmax() + 1


def test_reference_structure(reference):
    assert set(reference["features"]) == set(dm.MONITORED)
    for spec in reference["features"].values():
        assert sum(spec["expected"]) == pytest.approx(1.0)
    numeric = reference["features"]["Elevation"]
    assert numeric["type"] == "numeric" and len(numeric["expected"]) == len(numeric["edges"]) + 1
    soil = reference["features"]["Soil_Type"]
    assert len(soil["expected"]) == len(soil["categories"]) + 1  # last bin is "other"
    rare = [c for c in range(1, 41) if SOIL_WEIGHTS[c - 1] < dm.RARE_SHARE * 0.5]
    assert all(c not in soil["categories"] for c in rare)  # clearly rare types are merged
    json.dumps(reference)  # serializable


def test_reference_round_trip(reference, tmp_path):
    path = tmp_path / "drift_reference.json"
    dm.save_reference(reference, path)
    assert dm.load_reference(path)["features"]["Elevation"] == reference["features"]["Elevation"]


def test_load_reference_errors(tmp_path):
    with pytest.raises(FileNotFoundError):
        dm.load_reference(tmp_path / "missing.json")
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"features": {"Elevation": {}}}), encoding="utf-8")
    with pytest.raises(ValueError):
        dm.load_reference(bad)


# ---- window ----

def test_window_without_drift_is_ok(reference):
    report = dm.window_report(reference, make_inputs(1000, seed=2))
    assert report["status"] == "ok" and report["max_psi"] < dm.PSI_WARNING
    assert report["alerts"] == []


def test_elevation_shift_is_detected(reference):
    report = dm.window_report(reference, make_inputs(1000, seed=3, elevation_shift=300))
    assert report["status"] == "alert" and report["max_feature"] == "Elevation"
    assert report["alerts"][0]["feature"] == "Elevation"


def test_small_elevation_shift_is_tolerated(reference):
    assert dm.window_report(reference, make_inputs(1000, seed=4, elevation_shift=50))["status"] == "ok"


def test_soil_mix_change_is_detected(reference):
    window = make_inputs(1000, seed=5)
    most_common = int(np.argmax(SOIL_WEIGHTS)) + 1
    window.loc[window.index[:500], "Soil_Type"] = most_common
    report = dm.window_report(reference, window)
    assert report["status"] == "alert" and report["features"]["Soil_Type"]["level"] == "alert"


def test_unseen_category_is_flagged(reference):
    window = make_inputs(1000, seed=6)
    window.loc[window.index[:400], "Soil_Type"] = 99
    assert dm.window_report(reference, window)["features"]["Soil_Type"]["level"] != "ok"


def test_small_window_is_insufficient(reference):
    report = dm.window_report(reference, make_inputs(dm.MIN_ROWS - 1, seed=7))
    assert report["status"] == "insufficient_data" and report["features"] == {}


# ---- windows over time ----

def test_windows_track_the_drift_over_time(reference):
    rows = with_ids(pd.concat(
        [make_inputs(1000, seed=8), make_inputs(500, seed=9, elevation_shift=300)], ignore_index=True
    ))
    report = dm.windows_report(reference, rows, window_size=500, n_windows=3)
    windows = report["windows"]
    assert [w["status"] for w in windows] == ["ok", "ok", "alert"]
    assert [(w["first_id"], w["last_id"]) for w in windows] == [(1, 500), (501, 1000), (1001, 1500)]
    assert windows[-1]["alerts"][0]["feature"] == "Elevation"
    assert windows[0]["start_utc"] < windows[-1]["end_utc"]


def test_oldest_window_can_be_partial(reference):
    rows = with_ids(make_inputs(1200, seed=10))
    windows = dm.windows_report(reference, rows, window_size=500, n_windows=3, min_rows=250)["windows"]
    assert [w["rows"] for w in windows] == [200, 500, 500]
    assert windows[0]["status"] == "insufficient_data"


def test_windows_report_on_no_rows(reference):
    assert dm.windows_report(reference, with_ids(make_inputs(0, seed=11)))["windows"] == []


# ---- alerting ----

def _alert_window(reference):
    rows = with_ids(make_inputs(500, seed=12, elevation_shift=300))
    return dm.windows_report(reference, rows, window_size=500, n_windows=1)["windows"][-1]


def test_alert_decisions_and_exit_code(reference):
    window = _alert_window(reference)
    assert dm.should_alert(window) and dm.exit_code(window) == 1
    assert not dm.should_alert({"status": "ok"}) and dm.exit_code({"status": "ok"}) == 0
    assert dm.should_alert({"status": "warning"}) and dm.exit_code({"status": "warning"}) == 0
    assert not dm.should_alert({"status": "insufficient_data"})


def test_alert_message(reference):
    message = dm.alert_message(_alert_window(reference))
    assert message["text"] == message["content"] and "Elevation" in message["text"]
    assert message["status"] == "alert" and message["alerts"][0]["feature"] == "Elevation"


class _Response:
    status = 204

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_webhook_posts_json(reference, monkeypatch):
    sent = {}

    def fake_urlopen(request, timeout=None):
        sent["request"], sent["timeout"] = request, timeout
        return _Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    payload = dm.alert_message(_alert_window(reference))
    assert dm.send_webhook("https://example.invalid/hook", payload) is True
    request = sent["request"]
    assert request.get_method() == "POST" and request.full_url == "https://example.invalid/hook"
    assert json.loads(request.data)["status"] == "alert"
    assert request.get_header("Content-type") == "application/json"
    assert request.get_header("User-agent")


def test_failing_webhook_never_raises(monkeypatch):
    def broken(request, timeout=None):
        raise OSError("network down")

    monkeypatch.setattr("urllib.request.urlopen", broken)
    assert dm.send_webhook("https://example.invalid/hook", {"text": "x"}) is False


# ---- simulation ----

def test_simulation_detects_drift_without_false_alarms(reference):
    inputs = make_inputs(20_000, seed=13)
    scenarios = {"No drift": dm.no_drift, "Elevation +300 m": dm.shift_elevation(300)}
    results = dm.simulate(reference, inputs, scenarios, n_windows=10, window_size=500,
                          rng=np.random.default_rng(0))
    assert results["No drift"]["detection_rate"] == 0.0
    assert results["Elevation +300 m"]["alert_rate"] == 1.0
    assert results["Elevation +300 m"]["main_feature"] == "Elevation"


# ---- storage ----

REQUEST = {
    "Elevation": 2900.0, "Aspect": 150.0, "Slope": 12.0,
    "Horizontal_Distance_To_Hydrology": 250.0, "Vertical_Distance_To_Hydrology": 40.0,
    "Horizontal_Distance_To_Roadways": 2300.0, "Hillshade_9am": 215.0,
    "Hillshade_Noon": 225.0, "Hillshade_3pm": 140.0,
    "Horizontal_Distance_To_Fire_Points": 1900.0, "Wilderness_Area": 1, "Soil_Type": 29,
}
PREDICTION = {
    "cover_type": 2, "class_name": CLASS_NAMES[2], "confidence": 0.9,
    "probabilities": {name: 1 / 7 for name in CLASS_NAMES.values()},
}


def test_prediction_inputs_returns_the_latest_rows_oldest_first(tmp_path):
    url = f"sqlite:///{(tmp_path / 'drift.db').as_posix()}"
    for elevation in (2800.0, 2900.0, 3000.0, 3100.0, 3200.0):
        database.save_prediction({**REQUEST, "Elevation": elevation}, PREDICTION, db_url=url)
    rows = database.prediction_inputs(limit=3, db_url=url)
    assert [row["id"] for row in rows] == [3, 4, 5]
    assert [row["Elevation"] for row in rows] == [3000.0, 3100.0, 3200.0]
    assert {"created_at_utc", "Wilderness_Area", "Soil_Type"} <= set(rows[0])
    assert len(database.prediction_inputs(db_url=url)) == 5
    assert list(pd.DataFrame(rows).columns[:2]) == ["id", "created_at_utc"]


# ---- check and alert ----

def test_check_and_alert_logs_and_notifies(reference, monkeypatch, caplog):
    sent = []

    def fake_urlopen(request, timeout=None):
        sent.append(json.loads(request.data))
        return _Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    rows = with_ids(make_inputs(500, seed=14, elevation_shift=300))
    with caplog.at_level("WARNING", logger="uvicorn.error"):
        window = dm.check_and_alert(reference, rows, 500, "https://example.invalid/hook")
    assert window["status"] == "alert" and window["notified"] is True
    assert sent and sent[0]["status"] == "alert"
    assert "Data drift ALERT" in caplog.text


def test_check_and_alert_is_quiet_without_drift(reference, monkeypatch):
    calls = []
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: calls.append(1))
    window = dm.check_and_alert(reference, with_ids(make_inputs(500, seed=15)), 500, "https://example.invalid/hook")
    assert window["status"] == "ok" and window["notified"] is None and calls == []


def test_check_and_alert_without_webhook_or_rows(reference):
    rows = with_ids(make_inputs(500, seed=16, elevation_shift=300))
    assert dm.check_and_alert(reference, rows, 500)["notified"] is None
    assert dm.check_and_alert(reference, rows.iloc[0:0], 500) is None


def test_check_frequency_reads_the_environment(monkeypatch):
    monkeypatch.delenv("DRIFT_CHECK_EVERY", raising=False)
    assert dm.drift_check_every() == 500
    for value, expected in (("0", 0), ("250", 250), ("abc", 500), ("-3", 500)):
        monkeypatch.setenv("DRIFT_CHECK_EVERY", value)
        assert dm.drift_check_every() == expected


# ---- API (skipped when FastAPI is not installed) ----

@pytest.fixture
def api(reference):
    module = pytest.importorskip("app.api")
    module.app.state.drift_reference = reference
    module.app.state.drift_error = None
    module.app.state.drift_check_every = 500
    return module


def test_drift_endpoint_reports_the_windows(api, reference, monkeypatch):
    rows = with_ids(pd.concat(
        [make_inputs(500, seed=20), make_inputs(500, seed=21, elevation_shift=300)], ignore_index=True
    ))
    monkeypatch.setattr(api, "prediction_inputs", lambda limit=5000, db_url=None: rows.tail(limit).to_dict("records"))
    monkeypatch.setattr(api, "WINDOW_SIZE", 500)
    response = api.drift(windows=2)
    api.DriftResponse.model_validate(response)  # the dict fits the response schema
    assert response["status"] == "alert" and response["latest"]["alerts"][0]["feature"] == "Elevation"
    assert [window["status"] for window in response["history"]] == ["ok"]
    assert response["reference"]["n_rows"] == reference["n_rows"]


def test_drift_endpoint_without_predictions_or_reference(api, monkeypatch):
    monkeypatch.setattr(api, "prediction_inputs", lambda limit=5000, db_url=None: [])
    response = api.drift(windows=3)
    api.DriftResponse.model_validate(response)
    assert response["status"] == "insufficient_data" and response["latest"] is None and response["history"] == []
    api.app.state.drift_reference = None
    api.app.state.drift_error = "no reference"
    with pytest.raises(api.HTTPException) as error:
        api.drift(windows=3)
    assert error.value.status_code == 503


def test_drift_check_is_due_every_n_predictions(api):
    assert api.drift_check_due(500) and api.drift_check_due(1000)
    assert not api.drift_check_due(499) and not api.drift_check_due(None)
    api.app.state.drift_check_every = 0
    assert not api.drift_check_due(500)
    api.app.state.drift_check_every = 500
    api.app.state.drift_reference = None
    assert not api.drift_check_due(500)


def test_background_check_alerts_and_never_raises(api, monkeypatch, caplog):
    rows = with_ids(make_inputs(500, seed=22, elevation_shift=300))
    monkeypatch.setattr(api, "prediction_inputs", lambda limit=5000, db_url=None: rows.to_dict("records"))
    monkeypatch.setattr(api, "WINDOW_SIZE", 500)
    monkeypatch.delenv("DRIFT_WEBHOOK_URL", raising=False)
    with caplog.at_level("WARNING", logger="uvicorn.error"):
        api.run_drift_check()
    assert "Data drift ALERT" in caplog.text

    def broken(limit=5000, db_url=None):
        raise OSError("database down")

    monkeypatch.setattr(api, "prediction_inputs", broken)
    api.run_drift_check()  # a failing database must not raise