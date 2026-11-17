"""Cloud deployment entrypoint and readiness verifier (issue #39).

Supports three runtime modes via `SERVICE_ROLE`:
- `all` (default in `render.yaml`): ensures a model artifact is present at
  `MODEL_PATH`, initializes the database, starts the FastAPI backend on
  `127.0.0.1:8000`, waits for `/health`, and runs the Streamlit frontend in the
  foreground on `0.0.0.0:$PORT`.
- `api`: runs only the FastAPI backend (`uvicorn app.api:app`) on `0.0.0.0:$PORT`.
- `app`: runs only the Streamlit frontend (`streamlit run app/main.py`) on `0.0.0.0:$PORT`.

Run `python scripts/start_cloud.py --check` to execute a self-cleaning end-to-end
verification of the cloud bootstrap, FastAPI endpoints and Streamlit health check.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from app.serving import MODEL_PATH, load_model  # noqa: E402
from data_cleaning import (  # noqa: E402
    FEATURES,
    SOIL_FEATURES,
    WILDERNESS_FEATURES,
)
from database import init_db  # noqa: E402
from export_model import build_pipeline, label_mapping  # noqa: E402
from target_encoding import CLASS_NAMES  # noqa: E402

RANDOM_STATE = 42
CLOUD_BOOTSTRAP_VERSION = "0.1.0-cloud-bootstrap"

# Class-conditional elevation centers (meters) matching Covertype domain ranges
# so the lightweight cloud fallback produces realistic 7-class probabilities
# when deployed without the 71.7 MiB git-ignored raw file.
CLASS_ELEVATION_CENTERS = {
    1: (3120.0, 140.0),  # Spruce/Fir
    2: (2920.0, 150.0),  # Lodgepole Pine
    3: (2420.0, 130.0),  # Ponderosa Pine
    4: (2150.0, 90.0),   # Cottonwood/Willow
    5: (2780.0, 100.0),  # Aspen
    6: (2480.0, 125.0),  # Douglas-fir
    7: (3360.0, 110.0),  # Krummholz
}


def build_bootstrap_dataset(rows_per_class: int = 200, random_state: int = RANDOM_STATE) -> tuple[pd.DataFrame, pd.Series]:
    """Generate a deterministic 7-class cartographic dataset within physical bounds."""
    rng = np.random.default_rng(random_state)
    records: list[dict[str, int]] = []
    targets: list[int] = []

    for cover_type in sorted(CLASS_NAMES):
        elev_mean, elev_std = CLASS_ELEVATION_CENTERS[cover_type]
        for _ in range(rows_per_class):
            row: dict[str, int] = {
                "Elevation": int(np.clip(rng.normal(elev_mean, elev_std), 1800, 3900)),
                "Aspect": int(rng.integers(0, 360)),
                "Slope": int(np.clip(rng.normal(14 + cover_type, 6), 0, 60)),
                "Horizontal_Distance_To_Hydrology": int(np.clip(rng.exponential(220), 0, 5000)),
                "Vertical_Distance_To_Hydrology": int(np.clip(rng.normal(40, 50), -200, 600)),
                "Horizontal_Distance_To_Roadways": int(np.clip(rng.normal(2200 - cover_type * 120, 800), 0, 7000)),
                "Hillshade_9am": int(np.clip(rng.normal(212, 24), 0, 255)),
                "Hillshade_Noon": int(np.clip(rng.normal(223, 18), 0, 255)),
                "Hillshade_3pm": int(np.clip(rng.normal(142, 35), 0, 255)),
                "Horizontal_Distance_To_Fire_Points": int(np.clip(rng.normal(1950, 900), 0, 7000)),
            }
            wilderness_idx = int((cover_type - 1) % len(WILDERNESS_FEATURES)) + 1
            soil_idx = int((cover_type * 5 + rng.integers(0, 3)) % len(SOIL_FEATURES)) + 1
            for idx, col in enumerate(WILDERNESS_FEATURES, start=1):
                row[col] = int(idx == wilderness_idx)
            for idx, col in enumerate(SOIL_FEATURES, start=1):
                row[col] = int(idx == soil_idx)
            records.append(row)
            targets.append(cover_type)

    X = pd.DataFrame(records, columns=FEATURES)
    y = pd.Series(targets, name="Cover_Type", dtype="int64")
    return X, y


def ensure_cloud_model(model_path: Path = MODEL_PATH) -> dict:
    """Ensure a loadable 54-feature pipeline exists at `model_path`.

    If `model_path` already exists and passes `load_model()`, it is kept untouched.
    Otherwise, fits a lightweight 30-tree RandomForest pipeline on the
    deterministic 7-class bootstrap dataset so cloud containers without the
    git-ignored dataset start cleanly within a 512 MB RAM budget.
    """
    model_path = Path(model_path)
    loaded = load_model(model_path)
    if loaded.ready:
        return {"status": "existing", "model_path": str(model_path)}

    model_path.parent.mkdir(parents=True, exist_ok=True)
    X_boot, y_boot = build_bootstrap_dataset()
    pipeline = build_pipeline()
    pipeline.named_steps["model"].set_params(
        n_estimators=30,
        max_depth=12,
        random_state=RANDOM_STATE,
        n_jobs=1,
    )
    pipeline.fit(X_boot, y_boot)
    joblib.dump(pipeline, model_path, compress=3)

    metadata_path = model_path.with_name("model_metadata.json")
    if not metadata_path.exists():
        metadata = {
            "model_version": CLOUD_BOOTSTRAP_VERSION,
            "note": (
                "Lightweight cloud bootstrap model generated automatically because "
                "models/model.joblib and data/raw/covtype.data are git-ignored. "
                "Run `python src/export_model.py` with the full dataset to replace."
            ),
            "random_state": RANDOM_STATE,
            "features": list(FEATURES),
            "label_mapping": label_mapping(pipeline.classes_),
        }
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    verified = load_model(model_path)
    if not verified.ready:
        raise RuntimeError(f"Bootstrap model failed serving contract: {verified.error}")
    return {"status": "bootstrapped", "model_path": str(model_path)}


def wait_for_url(url: str, timeout_s: float = 30.0) -> dict | str:
    """Poll `url` until HTTP 200 or raise TimeoutError."""
    deadline = time.monotonic() + timeout_s
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2.0) as resp:
                body = resp.read().decode("utf-8")
                if resp.status == 200:
                    try:
                        return json.loads(body)
                    except json.JSONDecodeError:
                        return body
        except Exception as exc:
            last_error = exc
        time.sleep(0.4)
    raise TimeoutError(f"Service at {url} did not become ready within {timeout_s}s: {last_error}")


def post_json(url: str, payload: dict) -> dict:
    """Send a JSON POST request and return the parsed JSON body."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_self_check() -> int:
    """Verify cloud model provisioning, DB init, FastAPI and Streamlit in an isolated temp dir."""
    print("== Cloud deployment self-check (issue #39) ==")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        model_path = tmp_path / "model.joblib"
        db_path = tmp_path / "cloud_check.db"
        db_url = f"sqlite:///{db_path.as_posix()}"

        model_info = ensure_cloud_model(model_path)
        print(f"1. Model artifact check: {model_info['status']} ({model_path.stat().st_size / 1024:.1f} KB)")

        init_db(db_url)
        print("2. Database schema check: initialized (SQLite cloud fallback)")

        env = os.environ.copy()
        env["MODEL_PATH"] = str(model_path)
        env["DATABASE_URL"] = db_url
        env["API_URL"] = "http://127.0.0.1:18000"

        api_proc = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn", "app.api:app",
                "--host", "127.0.0.1", "--port", "18000", "--log-level", "warning",
            ],
            cwd=str(ROOT),
            env=env,
        )
        ui_proc = subprocess.Popen(
            [
                sys.executable, "-m", "streamlit", "run", "app/main.py",
                "--server.port=18501", "--server.address=127.0.0.1",
                "--server.headless=true", "--logger.level=error",
            ],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            health = wait_for_url("http://127.0.0.1:18000/health", timeout_s=25.0)
            assert isinstance(health, dict) and health.get("status") == "ok", health
            assert health.get("model_loaded") is True, health
            assert health.get("db_connected") is True, health
            print(f"3. FastAPI /health check: {health}")

            sample_payload = {
                "Elevation": 2900,
                "Aspect": 150,
                "Slope": 12,
                "Horizontal_Distance_To_Hydrology": 250,
                "Vertical_Distance_To_Hydrology": 40,
                "Horizontal_Distance_To_Roadways": 2300,
                "Hillshade_9am": 215,
                "Hillshade_Noon": 225,
                "Hillshade_3pm": 140,
                "Horizontal_Distance_To_Fire_Points": 1900,
                "Wilderness_Area": 1,
                "Soil_Type": 29,
            }
            pred = post_json("http://127.0.0.1:18000/predict", sample_payload)
            assert pred["cover_type"] in range(1, 8), pred
            assert isinstance(pred["prediction_id"], int), pred
            print(
                f"4. FastAPI /predict check: cover_type={pred['cover_type']} "
                f"({pred['class_name']}), confidence={pred['confidence']:.4f}, "
                f"prediction_id={pred['prediction_id']}"
            )

            fb = post_json(
                "http://127.0.0.1:18000/feedback",
                {"prediction_id": pred["prediction_id"], "true_cover_type": pred["cover_type"]},
            )
            assert fb["is_correct"] is True, fb
            metrics = wait_for_url("http://127.0.0.1:18000/metrics", timeout_s=5.0)
            assert isinstance(metrics, dict) and metrics.get("feedback_count") == 1, metrics
            print(
                f"5. FastAPI /feedback & /metrics check: feedback_count={metrics['feedback_count']}, "
                f"accuracy={metrics['accuracy']}"
            )

            st_health = wait_for_url("http://127.0.0.1:18501/_stcore/health", timeout_s=25.0)
            print(f"6. Streamlit /_stcore/health check: {st_health}")
        finally:
            for proc in (ui_proc, api_proc):
                proc.terminate()
                try:
                    proc.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    proc.kill()

    print("All cloud deployment checks passed.")
    return 0


def run_services() -> int:
    """Start the configured cloud service role (`all`, `api` or `app`)."""
    role = os.getenv("SERVICE_ROLE", "all").strip().lower()
    port = os.getenv("PORT", "8501" if role != "api" else "8000")
    api_port = os.getenv("API_PORT", "8000")

    model_info = ensure_cloud_model(MODEL_PATH)
    print(f"[start_cloud] model status: {model_info['status']} at {model_info['model_path']}", flush=True)

    try:
        init_db()
        print("[start_cloud] database initialized.", flush=True)
    except Exception as exc:
        print(f"[start_cloud] warning: database init skipped ({exc})", flush=True)

    if role == "api":
        cmd = [
            sys.executable, "-m", "uvicorn", "app.api:app",
            "--host", "0.0.0.0", "--port", str(port),
        ]
        return subprocess.call(cmd, cwd=str(ROOT))

    if role == "app":
        cmd = [
            sys.executable, "-m", "streamlit", "run", "app/main.py",
            f"--server.port={port}", "--server.address=0.0.0.0", "--server.headless=true",
        ]
        return subprocess.call(cmd, cwd=str(ROOT))

    # Default `all`: run FastAPI on loopback and Streamlit on public $PORT
    os.environ.setdefault("API_URL", f"http://127.0.0.1:{api_port}")
    api_proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "app.api:app",
            "--host", "127.0.0.1", "--port", str(api_port),
        ],
        cwd=str(ROOT),
    )
    wait_for_url(f"http://127.0.0.1:{api_port}/health", timeout_s=30.0)
    print(f"[start_cloud] FastAPI healthy at http://127.0.0.1:{api_port}", flush=True)

    ui_proc = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", "app/main.py",
            f"--server.port={port}", "--server.address=0.0.0.0", "--server.headless=true",
        ],
        cwd=str(ROOT),
    )

    def handle_signal(signum, _frame):
        for proc in (ui_proc, api_proc):
            if proc.poll() is None:
                proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    exit_code = ui_proc.wait()
    if api_proc.poll() is None:
        api_proc.terminate()
    return exit_code


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if "--check" in args:
        return run_self_check()
    return run_services()


if __name__ == "__main__":
    sys.exit(main())
