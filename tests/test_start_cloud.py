"""Unit tests for the cloud entrypoint scripts/start_cloud.py (ticket #39).

No network access: downloads use file:// URLs and the processes are short
local Python commands, so the tests run in CI as they are.
"""
import hashlib
import importlib.util
import socket
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("start_cloud", ROOT / "scripts" / "start_cloud.py")
start_cloud = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(start_cloud)


@pytest.fixture
def payload(tmp_path):
    """A small file standing in for a model artifact, with its SHA-256."""
    path = tmp_path / "source" / "model.joblib"
    path.parent.mkdir()
    content = b"not really a model\n" * 1000
    path.write_bytes(content)
    return path, hashlib.sha256(content).hexdigest()


def _free_port() -> int:
    """A local TCP port with nothing listening on it."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _python(code: str) -> subprocess.Popen:
    return subprocess.Popen([sys.executable, "-c", code])


# --- sha256_of / download_file ---

def test_sha256_of_matches_hashlib(payload):
    path, expected = payload
    assert start_cloud.sha256_of(path, chunk_size=64) == expected


def test_download_file_with_right_sha256(payload, tmp_path):
    path, expected = payload
    dest = tmp_path / "models" / "model.joblib"

    info = start_cloud.download_file(path.as_uri(), dest, expected.upper())

    assert dest.read_bytes() == path.read_bytes()
    assert info["sha256"] == expected
    assert info["size_bytes"] == path.stat().st_size
    assert not dest.with_name(dest.name + ".part").exists()


def test_download_file_with_wrong_sha256_leaves_nothing(payload, tmp_path):
    path, _ = payload
    dest = tmp_path / "models" / "model.joblib"

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        start_cloud.download_file(path.as_uri(), dest, "0" * 64)

    assert not dest.exists()
    assert not dest.with_name(dest.name + ".part").exists()


# --- wait_for_url / supervise ---

def test_wait_for_url_fails_fast_when_process_exits():
    proc = _python("import sys; sys.exit(3)")
    proc.wait()

    with pytest.raises(RuntimeError, match="exited with code 3"):
        start_cloud.wait_for_url(f"http://127.0.0.1:{_free_port()}/health", timeout_s=30.0, proc=proc)


def test_wait_for_url_times_out_without_process():
    with pytest.raises(TimeoutError):
        start_cloud.wait_for_url(f"http://127.0.0.1:{_free_port()}/health", timeout_s=1.0)


def test_supervise_returns_child_code_and_stops_the_other():
    failing = _python("import sys; sys.exit(3)")
    long_running = _python("import time; time.sleep(60)")

    code = start_cloud.supervise({"api": failing, "ui": long_running}, poll_interval_s=0.1)

    assert code == 3
    assert long_running.poll() is not None


def test_supervise_treats_a_clean_exit_as_failure():
    finished = _python("pass")
    long_running = _python("import time; time.sleep(60)")

    code = start_cloud.supervise({"api": long_running, "ui": finished}, poll_interval_s=0.1)

    assert code == 1
    assert long_running.poll() is not None


# --- model configuration (review of PR #116, points 1 and 2) ---

def test_missing_model_without_model_url_fails(tmp_path):
    model_path = tmp_path / "model.joblib"

    with pytest.raises(RuntimeError, match="MODEL_URL is unset"):
        start_cloud.ensure_cloud_model(model_path, env={})

    assert not model_path.exists()


def test_bootstrap_model_only_with_explicit_opt_in(tmp_path):
    model_path = tmp_path / "model.joblib"

    info = start_cloud.ensure_cloud_model(model_path, env={start_cloud.ALLOW_BOOTSTRAP_ENV: "1"})

    assert info["status"] == "bootstrapped"
    assert model_path.exists()


def test_model_url_without_sha256_fails_before_downloading(payload, tmp_path):
    path, _ = payload
    model_path = tmp_path / "models" / "model.joblib"
    env = {"MODEL_URL": path.as_uri()}

    with pytest.raises(ValueError, match="MODEL_SHA256"):
        start_cloud.ensure_cloud_model(model_path, env=env)
    with pytest.raises(ValueError, match="MODEL_SHA256"):
        start_cloud.fetch_remote_model(model_path, env=env)

    assert not model_path.parent.exists()
