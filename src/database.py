"""Database integration (ticket #37): persist model predictions and user feedback in MySQL (Docker) or SQLite (local fallback)."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from urllib.parse import urlparse

from data_cleaning import NUMERIC_FEATURES
from target_encoding import CLASS_NAMES, COVER_TYPES

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SQLITE_PATH = ROOT / "data" / "processed" / "multiclass.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"


def resolve_database_url(db_url: str | None = None) -> str:
    """Return the active DATABASE_URL (explicit argument -> env var -> default SQLite path)."""
    return db_url or os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL


def backend_of(db_url: str | None = None) -> str:
    """Return 'mysql' or 'sqlite' from the scheme of the database URL."""
    url = resolve_database_url(db_url)
    scheme = urlparse(url).scheme.lower()
    if scheme.startswith("mysql"):
        return "mysql"
    if scheme.startswith("sqlite"):
        return "sqlite"
    raise ValueError(f"Unsupported DATABASE_URL scheme '{scheme}'. Expected mysql:// or sqlite:///")


def _sqlite_path_from_url(url: str) -> Path:
    parsed = urlparse(url)
    raw_path = parsed.path
    if os.name == "nt" and raw_path.startswith("/") and len(raw_path) > 2 and raw_path[2] == ":":
        raw_path = raw_path[1:]
    return Path(raw_path)


@contextmanager
def _connect(db_url: str | None = None):
    """Yield a `(connection, placeholder, backend)` tuple with automatic commit/close."""
    url = resolve_database_url(db_url)
    backend = backend_of(url)
    if backend == "sqlite":
        db_path = _sqlite_path_from_url(url)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn, "?", "sqlite"
            conn.commit()
        finally:
            conn.close()
    else:
        import pymysql
        import pymysql.cursors

        parsed = urlparse(url)
        conn = pymysql.connect(
            host=parsed.hostname or "localhost",
            port=parsed.port or 3306,
            user=parsed.username or "app",
            password=parsed.password or "app",
            database=(parsed.path or "/multiclass").lstrip("/"),
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
        )
        try:
            yield conn, "%s", "mysql"
            conn.commit()
        finally:
            conn.close()


def _execute(conn, sql: str, params: tuple = ()):
    cursor = conn.cursor()
    cursor.execute(sql, params)
    return cursor


def init_db(db_url: str | None = None) -> None:
    """Create the `predictions` and `feedback` tables if they do not exist."""
    with _connect(db_url) as (conn, _, backend):
        id_col = (
            "INTEGER PRIMARY KEY AUTOINCREMENT"
            if backend == "sqlite"
            else "INT AUTO_INCREMENT PRIMARY KEY"
        )
        _execute(
            conn,
            f"""
            CREATE TABLE IF NOT EXISTS predictions (
                id {id_col},
                created_at_utc VARCHAR(32) NOT NULL,
                model_version VARCHAR(32) NOT NULL,
                Elevation DOUBLE NOT NULL,
                Aspect DOUBLE NOT NULL,
                Slope DOUBLE NOT NULL,
                Horizontal_Distance_To_Hydrology DOUBLE NOT NULL,
                Vertical_Distance_To_Hydrology DOUBLE NOT NULL,
                Horizontal_Distance_To_Roadways DOUBLE NOT NULL,
                Hillshade_9am DOUBLE NOT NULL,
                Hillshade_Noon DOUBLE NOT NULL,
                Hillshade_3pm DOUBLE NOT NULL,
                Horizontal_Distance_To_Fire_Points DOUBLE NOT NULL,
                Wilderness_Area INT NOT NULL,
                Soil_Type INT NOT NULL,
                predicted_cover_type INT NOT NULL,
                predicted_class_name VARCHAR(64) NOT NULL,
                confidence DOUBLE NOT NULL,
                probabilities_json TEXT NOT NULL
            )
            """,
        )
        _execute(
            conn,
            f"""
            CREATE TABLE IF NOT EXISTS feedback (
                id {id_col},
                prediction_id INT NOT NULL,
                created_at_utc VARCHAR(32) NOT NULL,
                true_cover_type INT NOT NULL,
                true_class_name VARCHAR(64) NOT NULL,
                is_correct INT NOT NULL,
                comment TEXT,
                FOREIGN KEY (prediction_id) REFERENCES predictions(id)
            )
            """,
        )


def _extract_field(request, name: str):
    if isinstance(request, dict):
        return request[name]
    return getattr(request, name)


def save_prediction(
    request,
    prediction: dict,
    model_version: str = "0.1.0",
    db_url: str | None = None,
) -> int:
    """Insert a prediction record and return its database `id`."""
    init_db(db_url)
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    numeric_vals = [float(_extract_field(request, col)) for col in NUMERIC_FEATURES]
    wilderness = int(_extract_field(request, "Wilderness_Area"))
    soil = int(_extract_field(request, "Soil_Type"))
    cover_type = int(prediction["cover_type"])
    class_name = str(prediction["class_name"])
    confidence = float(prediction["confidence"])
    probabilities_json = json.dumps(prediction["probabilities"])

    columns = (
        ["created_at_utc", "model_version"]
        + NUMERIC_FEATURES
        + [
            "Wilderness_Area",
            "Soil_Type",
            "predicted_cover_type",
            "predicted_class_name",
            "confidence",
            "probabilities_json",
        ]
    )
    values = tuple(
        [created_at, model_version]
        + numeric_vals
        + [wilderness, soil, cover_type, class_name, confidence, probabilities_json]
    )

    with _connect(db_url) as (conn, ph, _):
        placeholders = ", ".join([ph] * len(columns))
        col_list = ", ".join(columns)
        cursor = _execute(
            conn,
            f"INSERT INTO predictions ({col_list}) VALUES ({placeholders})",
            values,
        )
        return int(cursor.lastrowid)


def _normalize_prediction_row(row) -> dict:
    data = dict(row)
    # Normalise column casing across MySQL / SQLite drivers
    probs_raw = data.pop("probabilities_json", "{}")
    data["probabilities"] = json.loads(probs_raw) if isinstance(probs_raw, str) else probs_raw
    return data


def get_prediction(prediction_id: int, db_url: str | None = None) -> dict | None:
    """Return a single prediction record by ID, or None if not found."""
    init_db(db_url)
    with _connect(db_url) as (conn, ph, _):
        cursor = _execute(
            conn,
            f"SELECT * FROM predictions WHERE id = {ph}",
            (int(prediction_id),),
        )
        row = cursor.fetchone()
        return _normalize_prediction_row(row) if row is not None else None


def list_predictions(limit: int = 100, db_url: str | None = None) -> list[dict]:
    """Return the most recent predictions (ordered by id descending)."""
    init_db(db_url)
    with _connect(db_url) as (conn, ph, _):
        cursor = _execute(
            conn,
            f"SELECT * FROM predictions ORDER BY id DESC LIMIT {ph}",
            (int(limit),),
        )
        return [_normalize_prediction_row(r) for r in cursor.fetchall()]


def save_feedback(
    prediction_id: int,
    true_cover_type: int,
    comment: str | None = None,
    db_url: str | None = None,
) -> int:
    """Validate and insert user feedback linked to `prediction_id`. Returns the feedback `id`."""
    true_cover_type = int(true_cover_type)
    if true_cover_type not in COVER_TYPES:
        raise ValueError(
            f"Invalid true_cover_type={true_cover_type}. Expected one of {COVER_TYPES}."
        )
    pred = get_prediction(prediction_id, db_url=db_url)
    if pred is None:
        raise ValueError(f"Prediction id={prediction_id} does not exist.")

    is_correct = int(int(pred["predicted_cover_type"]) == true_cover_type)
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    true_class_name = CLASS_NAMES[true_cover_type]

    with _connect(db_url) as (conn, ph, _):
        cursor = _execute(
            conn,
            f"""
            INSERT INTO feedback (
                prediction_id, created_at_utc, true_cover_type,
                true_class_name, is_correct, comment
            ) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """,
            (
                int(prediction_id),
                created_at,
                true_cover_type,
                true_class_name,
                is_correct,
                comment,
            ),
        )
        return int(cursor.lastrowid)


def list_feedback(limit: int = 100, db_url: str | None = None) -> list[dict]:
    """Return recent feedback entries joined with their originating prediction."""
    init_db(db_url)
    with _connect(db_url) as (conn, ph, _):
        cursor = _execute(
            conn,
            f"""
            SELECT
                f.id AS feedback_id,
                f.prediction_id,
                f.created_at_utc AS feedback_created_at_utc,
                f.true_cover_type,
                f.true_class_name,
                f.is_correct,
                f.comment,
                p.predicted_cover_type,
                p.predicted_class_name,
                p.confidence,
                p.model_version,
                p.Elevation,
                p.Aspect,
                p.Slope,
                p.Horizontal_Distance_To_Hydrology,
                p.Vertical_Distance_To_Hydrology,
                p.Horizontal_Distance_To_Roadways,
                p.Hillshade_9am,
                p.Hillshade_Noon,
                p.Hillshade_3pm,
                p.Horizontal_Distance_To_Fire_Points,
                p.Wilderness_Area,
                p.Soil_Type
            FROM feedback f
            JOIN predictions p ON p.id = f.prediction_id
            ORDER BY f.id DESC
            LIMIT {ph}
            """,
            (int(limit),),
        )
        rows = []
        for r in cursor.fetchall():
            item = dict(r)
            item["is_correct"] = bool(item["is_correct"])
            rows.append(item)
        return rows


def feedback_metrics(db_url: str | None = None) -> dict:
    """Production-monitoring metrics aggregated from stored predictions and feedback.

    Read-only. Returns the prediction and feedback counts, feedback coverage,
    the live accuracy measured on labelled feedback, the average confidence of
    the predictions that received feedback, and the per-class feedback accuracy
    (by true `Cover_Type`). Denominators of zero yield `None` instead of raising,
    so the endpoint works before any feedback has been collected.
    """
    init_db(db_url)
    with _connect(db_url) as (conn, _, _):
        predictions_total = int(
            _execute(conn, "SELECT COUNT(*) AS c FROM predictions").fetchone()["c"]
        )
        totals = _execute(
            conn,
            "SELECT COUNT(*) AS n, COALESCE(SUM(is_correct), 0) AS correct FROM feedback",
        ).fetchone()
        feedback_total = int(totals["n"])
        correct_total = int(totals["correct"])

        avg_conf_row = _execute(
            conn,
            """
            SELECT AVG(p.confidence) AS avg_conf
            FROM feedback f JOIN predictions p ON p.id = f.prediction_id
            """,
        ).fetchone()
        avg_confidence = avg_conf_row["avg_conf"]

        per_class_rows = _execute(
            conn,
            """
            SELECT true_cover_type,
                   COUNT(*) AS n,
                   COALESCE(SUM(is_correct), 0) AS correct
            FROM feedback
            GROUP BY true_cover_type
            """,
        ).fetchall()

    counts = {int(r["true_cover_type"]): (int(r["n"]), int(r["correct"])) for r in per_class_rows}
    per_class = []
    for cover_type in COVER_TYPES:
        n, correct = counts.get(cover_type, (0, 0))
        per_class.append(
            {
                "cover_type": cover_type,
                "class_name": CLASS_NAMES[cover_type],
                "feedback_count": n,
                "correct": correct,
                "accuracy": (correct / n) if n else None,
            }
        )

    return {
        "predictions_total": predictions_total,
        "feedback_total": feedback_total,
        "feedback_coverage": (feedback_total / predictions_total) if predictions_total else None,
        "correct_total": correct_total,
        "live_accuracy": (correct_total / feedback_total) if feedback_total else None,
        "average_confidence": float(avg_confidence) if avg_confidence is not None else None,
        "per_class": per_class,
    }


def db_status(db_url: str | None = None) -> dict:
    """Return connection health and row counts for `/health` and diagnostics; never raises."""
    url = resolve_database_url(db_url)
    try:
        backend = backend_of(url)
        init_db(url)
        with _connect(url) as (conn, _, _):
            pred_count = int(_execute(conn, "SELECT COUNT(*) AS c FROM predictions").fetchone()["c"])
            fb_count = int(_execute(conn, "SELECT COUNT(*) AS c FROM feedback").fetchone()["c"])
        return {
            "connected": True,
            "backend": backend,
            "predictions_count": pred_count,
            "feedback_count": fb_count,
            "error": None,
        }
    except Exception as exc:
        return {
            "connected": False,
            "backend": "unknown",
            "predictions_count": 0,
            "feedback_count": 0,
            "error": str(exc),
        }


def _run_self_checks() -> dict:
    """Verify schema initialization, prediction/feedback CRUD, joins and validation constraints."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_db = Path(tmp_dir) / "test_multiclass.db"
        url = f"sqlite:///{tmp_db.as_posix()}"

        init_db(url)

        sample_req = {
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
        sample_pred = {
            "cover_type": 2,
            "class_name": CLASS_NAMES[2],
            "confidence": 0.95,
            "probabilities": {CLASS_NAMES[c]: (0.95 if c == 2 else 0.05 / 6) for c in COVER_TYPES},
        }

        pred_id_1 = save_prediction(sample_req, sample_pred, db_url=url)
        pred_id_2 = save_prediction(
            {**sample_req, "Elevation": 3400.0, "Soil_Type": 38},
            {**sample_pred, "cover_type": 7, "class_name": CLASS_NAMES[7]},
            db_url=url,
        )
        assert pred_id_1 == 1 and pred_id_2 == 2, "Unexpected prediction IDs"

        fetched = get_prediction(pred_id_1, db_url=url)
        assert fetched is not None and fetched["predicted_cover_type"] == 2
        assert abs(sum(fetched["probabilities"].values()) - 1.0) < 1e-6

        all_preds = list_predictions(db_url=url)
        assert len(all_preds) == 2

        # Feedback: one matching prediction (is_correct=True) and one mismatch (is_correct=False)
        fb_id_1 = save_feedback(pred_id_1, true_cover_type=2, comment="Verified Lodgepole Pine", db_url=url)
        fb_id_2 = save_feedback(pred_id_2, true_cover_type=1, comment="Actually Spruce/Fir", db_url=url)
        assert fb_id_1 == 1 and fb_id_2 == 2

        joined_fb = list_feedback(db_url=url)
        assert len(joined_fb) == 2
        by_pred = {row["prediction_id"]: row for row in joined_fb}
        assert by_pred[pred_id_1]["is_correct"] is True
        assert by_pred[pred_id_2]["is_correct"] is False

        # Reject invalid true_cover_type and non-existent prediction_id
        for bad_args in [(pred_id_1, 99), (9999, 2)]:
            try:
                save_feedback(*bad_args, db_url=url)
            except ValueError:
                pass
            else:
                raise AssertionError(f"Expected ValueError for save_feedback{bad_args}")

        status = db_status(url)
        assert status["connected"] and status["predictions_count"] == 2 and status["feedback_count"] == 2

        # Monitoring metrics: 2 feedback entries, 1 correct -> live accuracy 0.5
        metrics = feedback_metrics(url)
        assert metrics["predictions_total"] == 2 and metrics["feedback_total"] == 2
        assert metrics["correct_total"] == 1 and metrics["live_accuracy"] == 0.5
        assert metrics["feedback_coverage"] == 1.0
        by_class = {row["cover_type"]: row for row in metrics["per_class"]}
        assert by_class[2]["feedback_count"] == 1 and by_class[2]["accuracy"] == 1.0
        assert by_class[1]["feedback_count"] == 1 and by_class[1]["accuracy"] == 0.0
        assert by_class[3]["feedback_count"] == 0 and by_class[3]["accuracy"] is None
        return status


def main() -> None:
    print("== Database integration verification (ticket #37) ==")
    status = _run_self_checks()
    print(f"Active driver tested: {status['backend']} (MySQL 8.0 configured in docker-compose.yml)")
    print("Tables verified: predictions (19 columns), feedback (7 columns, FK -> predictions.id)")
    print(
        f"CRUD & join checks: passed "
        f"(predictions={status['predictions_count']}, feedback={status['feedback_count']})"
    )
    print("Constraint checks (invalid Cover_Type / missing prediction_id rejection): passed")
    print("Monitoring metrics (feedback_metrics: counts, live accuracy, per-class): passed")

    # The checks above run on a temporary SQLite file; also report the configured database.
    if os.getenv("DATABASE_URL"):
        live = db_status()
        if not live["connected"]:
            raise SystemExit(f"Configured DATABASE_URL is not reachable: {live['error']}")
        print(
            f"Configured DATABASE_URL: connected ({live['backend']}, "
            f"predictions={live['predictions_count']}, feedback={live['feedback_count']})"
        )


if __name__ == "__main__":
    main()
