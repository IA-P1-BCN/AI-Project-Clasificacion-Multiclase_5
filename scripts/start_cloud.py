"""Cloud deployment entrypoint and readiness verifier (issue #39).

Target: Render free plan (512 MB, 0.1 CPU), configured in `render.yaml`. It
serves the tuned XGBoost of #52 (model B, release `model-b-v1`) as the only
model: the Random Forest of #32 needs ~1.17 GiB of RAM and does not fit.

Model provisioning: an existing `MODEL_PATH` is used as-is; otherwise, when
`MODEL_URL` is set, the exported model is downloaded (optionally checked
against `MODEL_SHA256`); only when neither is available does it fall back to a
synthetic bootstrap model.

Supports three runtime modes via `SERVICE_ROLE`:
- `all` (default): ensures a model artifact is present at
  `MODEL_PATH`, initializes the database, starts the FastAPI backend on
  `127.0.0.1:8000`, waits for `/health` (up to `API_STARTUP_TIMEOUT` seconds,
  default 300, so a 0.1-CPU instance has time to import and load), and runs
  the Streamlit frontend in the foreground on `0.0.0.0:$PORT`.
- `api`: runs only the FastAPI backend (`uvicorn app.api:app`) on `0.0.0.0:$PORT`.
- `app`: runs only the Streamlit frontend (`streamlit run app/main.py`) on `0.0.0.0:$PORT`.

Model provisioning and database initialization run in a child process
(`--provision`) that exits before the services start, so its memory is released:
the long-lived launcher only uses the standard library.

Run `python scripts/start_cloud.py --check` to execute a self-cleaning end-to-end
verification of the cloud bootstrap, FastAPI endpoints and Streamlit health check.
"""

from __future__ import annotations

import hashlib
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


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

# Project and ML modules (pandas, scikit-learn, XGBoost, SQLAlchemy) are imported
# inside the functions that need them: the long-lived launcher process of
# `run_services` stays on the standard library, so on Render's 512 MB it does
# not hold ~100 MiB of imports next to the API and Streamlit.

RANDOM_STATE = 42
# Seconds to wait for FastAPI /health in `SERVICE_ROLE=all`. Generous because
# Render's free plan has 0.1 CPU: imports plus model loading take ~1 minute.
API_STARTUP_TIMEOUT_S = float(os.getenv("API_STARTUP_TIMEOUT", "300"))
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
    import numpy as np
    import pandas as pd
    from data_cleaning import FEATURES, SOIL_FEATURES, WILDERNESS_FEATURES
    from target_encoding import CLASS_NAMES

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


def sha256_of(path: Path, chunk_size: int = 1 << 20) -> str:
    """Return the hex SHA-256 digest of a file, read in chunks."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(
    url: str,
    dest: Path,
    expected_sha256: str | None = None,
    chunk_size: int = 1 << 20,
) -> dict:
    """Download `url` to `dest` atomically and optionally verify its SHA-256.

    The file is written to a temporary sibling and renamed only after the
    checksum matches, so a failed or partial download never leaves a broken
    artifact at `dest`.
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    req = urllib.request.Request(url)
    digest = hashlib.sha256()
    size = 0
    try:
        with urllib.request.urlopen(req, timeout=60.0) as resp, tmp.open("wb") as fh:
            for chunk in iter(lambda: resp.read(chunk_size), b""):
                fh.write(chunk)
                digest.update(chunk)
                size += len(chunk)
        actual = digest.hexdigest()
        if expected_sha256 and actual != expected_sha256.strip().lower():
            raise ValueError(f"SHA-256 mismatch for {url}: expected {expected_sha256}, got {actual}")
        tmp.replace(dest)
    finally:
        if tmp.exists():
            tmp.unlink()
    return {"path": str(dest), "size_bytes": size, "sha256": actual}


def fetch_remote_model(model_path: Path | None = None, env: dict | None = None) -> dict | None:
    """Download the exported model from `MODEL_URL` when it is not present yet.

    Returns None when `MODEL_URL` is unset. When it is set, any failure (network,
    checksum, serving contract) raises, so a misconfigured deployment fails
    loudly instead of silently falling back to the synthetic bootstrap model.
    `MODEL_METADATA_URL` (optional) fetches `model_metadata.json` next to it.
    """
    from app.serving import MODEL_PATH, load_model

    env = os.environ if env is None else env
    url = (env.get("MODEL_URL") or "").strip()
    if not url:
        return None
    model_path = Path(model_path or MODEL_PATH)
    if load_model(model_path).ready:
        return {"status": "existing", "model_path": str(model_path)}

    info = download_file(url, model_path, env.get("MODEL_SHA256") or None)
    metadata_url = (env.get("MODEL_METADATA_URL") or "").strip()
    if metadata_url:
        download_file(metadata_url, model_path.with_name("model_metadata.json"))

    verified = load_model(model_path)
    if not verified.ready:
        raise RuntimeError(f"Downloaded model failed serving contract: {verified.error}")
    return {
        "status": "downloaded",
        "model_path": str(model_path),
        "size_bytes": info["size_bytes"],
        "sha256": info["sha256"],
    }


def ensure_cloud_model(model_path: Path | None = None, env: dict | None = None) -> dict:
    """Ensure a loadable 54-feature pipeline exists at `model_path`.

    Resolution order:
    1. `model_path` already exists and passes `load_model()`: kept untouched.
    2. `MODEL_URL` is set: the real exported model is downloaded (see
       `fetch_remote_model`); failures raise instead of falling back.
    3. Otherwise, fits a lightweight 30-tree RandomForest pipeline on the
       deterministic 7-class synthetic bootstrap dataset so a container without
       the git-ignored artifacts still starts. Its predictions are NOT those of
       the project model (`model_version = "0.1.0-cloud-bootstrap"`).
    """
    import joblib
    from app.serving import MODEL_PATH, load_model
    from data_cleaning import FEATURES
    from export_model import build_pipeline, label_mapping

    model_path = Path(model_path or MODEL_PATH)
    loaded = load_model(model_path)
    if loaded.ready:
        return {"status": "existing", "model_path": str(model_path)}

    remote = fetch_remote_model(model_path, env)
    if remote is not None:
        return remote

    print(
        "[start_cloud] WARNING: no model at MODEL_PATH and MODEL_URL is unset; "
        "serving a synthetic bootstrap model, not the trained project model.",
        flush=True,
    )
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
            "label_mapping": label_mapping(pipeline),
        }
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    verified = load_model(model_path)
    if not verified.ready:
        raise RuntimeError(f"Bootstrap model failed serving contract: {verified.error}")
    return {"status": "bootstrapped", "model_path": str(model_path)}


def wait_for_url(url: str, timeout_s: float = 30.0, proc: subprocess.Popen | None = None) -> dict | str:
    """Poll `url` until HTTP 200 or raise TimeoutError.

    When `proc` is given and it exits first (e.g. killed for running out of
    memory), raise RuntimeError at once instead of waiting for the timeout.
    """
    deadline = time.monotonic() + timeout_s
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if proc is not None and proc.poll() is not None:
            raise RuntimeError(f"Process serving {url} exited with code {proc.returncode} before becoming ready")
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
    from database import init_db

    print("== Cloud deployment self-check (issue #39) ==")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        model_path = tmp_path / "model.joblib"
        db_path = tmp_path / "cloud_check.db"
        db_url = f"sqlite:///{db_path.as_posix()}"

        model_info = ensure_cloud_model(model_path, env={})
        print(f"1. Model artifact check: {model_info['status']} ({model_path.stat().st_size / 1024:.1f} KB)")

        # Exercise the MODEL_URL download path offline through a file:// URL.
        expected = sha256_of(model_path)
        remote_env = {"MODEL_URL": model_path.as_uri(), "MODEL_SHA256": expected}
        downloaded = ensure_cloud_model(tmp_path / "downloaded" / "model.joblib", env=remote_env)
        assert downloaded["status"] == "downloaded" and downloaded["sha256"] == expected, downloaded
        try:
            fetch_remote_model(
                tmp_path / "bad" / "model.joblib",
                env={"MODEL_URL": model_path.as_uri(), "MODEL_SHA256": "0" * 64},
            )
        except ValueError:
            assert not (tmp_path / "bad" / "model.joblib").exists()
        else:
            raise AssertionError("a SHA-256 mismatch must abort the download")
        print("1b. MODEL_URL download check: downloaded + SHA-256 verified, mismatch rejected")

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
            assert isinstance(metrics, dict) and metrics.get("feedback_total") == 1, metrics
            print(
                f"5. FastAPI /feedback & /metrics check: feedback_total={metrics['feedback_total']}, "
                f"live_accuracy={metrics['live_accuracy']}"
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


def provision() -> int:
    """Ensure the model at MODEL_PATH and initialize the database (child of `run_services`)."""
    from database import init_db

    model_info = ensure_cloud_model()
    print(f"[start_cloud] model status: {model_info['status']} at {model_info['model_path']}", flush=True)

    try:
        init_db()
        print("[start_cloud] database initialized.", flush=True)
    except Exception as exc:
        print(f"[start_cloud] warning: database init skipped ({exc})", flush=True)
    return 0


def run_services() -> int:
    """Start the configured cloud service role (`all`, `api` or `app`)."""
    role = os.getenv("SERVICE_ROLE", "all").strip().lower()
    port = os.getenv("PORT", "8501" if role != "api" else "8000")
    api_port = os.getenv("API_PORT", "8000")

    # Provision in a child process: its memory (ML imports, model loaded for
    # verification) goes back to the OS before the API loads its own copy.
    subprocess.run([sys.executable, str(Path(__file__).resolve()), "--provision"], check=True)

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
    wait_for_url(f"http://127.0.0.1:{api_port}/health", timeout_s=API_STARTUP_TIMEOUT_S, proc=api_proc)
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
    if "--provision" in args:
        return provision()
    return run_services()


if __name__ == "__main__":
    sys.exit(main())
