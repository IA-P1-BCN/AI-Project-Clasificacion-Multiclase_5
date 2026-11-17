"""Unit tests for the A/B test between two models (ticket #52)."""
import random
import sqlite3

import pytest

import database
from ab_testing import (
    MIN_FEEDBACK_PER_VARIANT,
    build_report,
    choose_variant,
    decide,
    traffic_share_b,
    two_proportion_ztest,
)
from target_encoding import CLASS_NAMES

REQUEST = {
    "Elevation": 2900.0,
    "Aspect": 150.0,
    "Slope": 12.0,
    "Horizontal_Distance_To_Hydrology": 250.0,
    "Vertical_Distance_To_Hydrology": 40.0,
    "Horizontal_Distance_To_Roadways": 2300.0,
    "Hillshade_9am": 215.0,
    "Hillshade_Noon": 225.0,
    "Hillshade_3pm": 140.0,
    "Horizontal_Distance_To_Fire_Points": 1900.0,
    "Wilderness_Area": 1,
    "Soil_Type": 29,
}


def _prediction(cover_type: int = 2, confidence: float = 0.9) -> dict:
    return {
        "cover_type": cover_type,
        "class_name": CLASS_NAMES[cover_type],
        "confidence": confidence,
        "probabilities": {name: 1 / 7 for name in CLASS_NAMES.values()},
    }


def _stats(correct_a, n_a, correct_b, n_b) -> dict:
    return {
        "A": {"variant": "A", "model_version": "0.1.0", "predictions": n_a, "feedback": n_a,
              "correct": correct_a, "average_confidence": 0.9},
        "B": {"variant": "B", "model_version": "0.2.0", "predictions": n_b, "feedback": n_b,
              "correct": correct_b, "average_confidence": 0.9},
    }


@pytest.fixture
def db_url(tmp_path):
    url = f"sqlite:///{(tmp_path / 'ab.db').as_posix()}"
    database.init_db(url)
    return url


def _store(db_url, variant, true_cover_type=None, predicted=2):
    prediction_id = database.save_prediction(
        REQUEST, _prediction(predicted), variant=variant, db_url=db_url
    )
    if true_cover_type is not None:
        database.save_feedback(prediction_id, true_cover_type, db_url=db_url)
    return prediction_id


# ---- traffic split ----

def test_split_zero_sends_everything_to_a():
    rng = random.Random(42)
    assert {choose_variant(0.0, True, rng=rng) for _ in range(200)} == {"A"}


def test_split_one_sends_everything_to_b():
    rng = random.Random(42)
    assert {choose_variant(1.0, True, rng=rng) for _ in range(200)} == {"B"}


def test_split_follows_the_configured_share():
    rng = random.Random(42)
    draws = [choose_variant(0.3, True, rng=rng) for _ in range(10_000)]
    assert abs(draws.count("B") / len(draws) - 0.3) < 0.02


def test_without_challenger_everything_goes_to_a():
    rng = random.Random(42)
    assert {choose_variant(1.0, False, rng=rng) for _ in range(100)} == {"A"}


def test_forced_variant_wins_over_the_split():
    assert choose_variant(0.0, False, forced="b") == "B"
    assert choose_variant(1.0, True, forced="A") == "A"
    with pytest.raises(ValueError):
        choose_variant(0.5, True, forced="C")


def test_traffic_share_validation():
    assert traffic_share_b("0.5") == 0.5
    assert traffic_share_b(0) == 0.0
    for bad in ("2", "-0.1", "abc"):
        with pytest.raises(ValueError):
            traffic_share_b(bad)


# ---- statistics and decision ----

def test_ztest_known_values():
    test = two_proportion_ztest(500, 1000, 550, 1000)
    assert test["z"] == pytest.approx(2.239, abs=1e-3)
    assert test["p_value"] == pytest.approx(0.0252, abs=1e-3)


def test_ztest_is_symmetric():
    forward = two_proportion_ztest(500, 1000, 550, 1000)
    backward = two_proportion_ztest(550, 1000, 500, 1000)
    assert backward["z"] == pytest.approx(-forward["z"])
    assert backward["p_value"] == pytest.approx(forward["p_value"])


def test_ztest_equal_rates_and_degenerate_case():
    equal = two_proportion_ztest(500, 1000, 500, 1000)
    assert equal["z"] == 0.0 and equal["p_value"] == pytest.approx(1.0)
    assert two_proportion_ztest(1000, 1000, 1000, 1000) == {"z": 0.0, "p_value": 1.0}


def test_decision_needs_enough_feedback():
    stats = _stats(190, MIN_FEEDBACK_PER_VARIANT - 1, 500, 500)
    assert decide(stats["A"], stats["B"])["decision"] == "insufficient_data"


def test_decision_winner_b_and_winner_a():
    forward = _stats(500, 1000, 550, 1000)
    assert decide(forward["A"], forward["B"])["decision"] == "winner_B"
    backward = _stats(550, 1000, 500, 1000)
    assert decide(backward["A"], backward["B"])["decision"] == "winner_A"


def test_decision_inconclusive_when_not_significant():
    stats = _stats(500, 1000, 520, 1000)
    assert decide(stats["A"], stats["B"])["decision"] == "inconclusive"


def test_decision_inconclusive_when_significant_but_tiny():
    # 0.4 points apart on 100,000 labels each: p < 0.05 but below MIN_EFFECT.
    stats = _stats(90_000, 100_000, 90_400, 100_000)
    result = decide(stats["A"], stats["B"])
    assert result["p_value"] < 0.05
    assert result["decision"] == "inconclusive"


def test_report_includes_accuracy_and_rule():
    report = build_report(_stats(500, 1000, 550, 1000))
    assert report["variants"]["A"]["live_accuracy"] == 0.5
    assert report["variants"]["B"]["live_accuracy"] == 0.55
    assert report["decision"] == "winner_B"
    assert report["rule"]["min_feedback_per_variant"] == MIN_FEEDBACK_PER_VARIANT


def test_report_without_feedback_has_no_accuracy():
    empty = {name: {"variant": name, "model_version": None, "predictions": 0, "feedback": 0,
                    "correct": 0, "average_confidence": None} for name in ("A", "B")}
    report = build_report(empty)
    assert report["decision"] == "insufficient_data"
    assert report["variants"]["A"]["live_accuracy"] is None


# ---- storage ----

def test_ab_metrics_counts_per_variant(db_url):
    _store(db_url, "A", true_cover_type=2)   # correct
    _store(db_url, "A", true_cover_type=1)   # wrong
    _store(db_url, "A")                      # no feedback
    _store(db_url, "B", true_cover_type=2)   # correct
    stats = database.ab_metrics(db_url)
    assert (stats["A"]["predictions"], stats["A"]["feedback"], stats["A"]["correct"]) == (3, 2, 1)
    assert (stats["B"]["predictions"], stats["B"]["feedback"], stats["B"]["correct"]) == (1, 1, 1)
    assert stats["A"]["average_confidence"] == pytest.approx(0.9)


def test_ab_metrics_on_empty_database(db_url):
    stats = database.ab_metrics(db_url)
    for name in ("A", "B"):
        assert stats[name]["predictions"] == 0 and stats[name]["average_confidence"] is None


def test_variant_defaults_to_a_and_is_validated(db_url):
    prediction_id = database.save_prediction(REQUEST, _prediction(), db_url=db_url)
    assert database.ab_metrics(db_url)["A"]["predictions"] == 1
    assert database.get_prediction(prediction_id, db_url=db_url)["variant"] == "A"
    with pytest.raises(ValueError):
        database.save_prediction(REQUEST, _prediction(), variant="C", db_url=db_url)


def test_migration_adds_variant_to_an_old_table(tmp_path):
    path = tmp_path / "old.db"
    url = f"sqlite:///{path.as_posix()}"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE predictions (id INTEGER PRIMARY KEY, model_version TEXT)")
        conn.execute("INSERT INTO predictions (model_version) VALUES ('0.1.0')")
    for _ in range(2):  # idempotent
        with database._connect(url) as (conn, _, backend):
            database._ensure_variant_column(conn, backend)
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT variant FROM predictions").fetchone()[0] == "A"