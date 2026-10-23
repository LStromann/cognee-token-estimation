"""Cognify must finish before the next session and before snapshot."""
import os
import subprocess
import sys
import time

import pytest

from harness.graph_wait import wait_for_graph


def _cfg(tmp, timeout):
    cmd = (
        "python3 -m harness.cognee_ctl {action} --arm {{arm}} --topic {{topic}} "
        "--dataset {{dataset}} --snapshot '{{snapshot}}' --workspace '{{workspace}}'"
    )
    return {
        "_dry_run": True,
        "work_dir": str(tmp),
        "cognee": {
            "dataset": "ctb_{topic}",
            "proxy_env": {},
            "after_session_cmd": cmd.format(action="kick"),
            "status_cmd": cmd.format(action="status"),
            "wait": {"poll_s": 0.05, "timeout_s": timeout, "ready_statuses": ["completed", "idle"]},
        },
    }


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("CTB_WORK_DIR", str(tmp_path))
    monkeypatch.setenv("CTB_COGNEE_BACKEND", "file")
    monkeypatch.delenv("SYSTEM_ROOT_DIRECTORY", raising=False)
    monkeypatch.delenv("DATA_ROOT_DIRECTORY", raising=False)
    return tmp_path


def test_wait_blocks_until_cognify_completes(isolated, monkeypatch):
    monkeypatch.setenv("CTB_COGNEE_READY_DELAY_S", "0.4")
    started = time.time()
    status = wait_for_graph(
        _cfg(isolated, timeout=5), {}, arm="cognee", topic="meetings", workspace=isolated / "ws",
    )
    elapsed = time.time() - started
    assert status["status"] == "completed"
    assert elapsed >= 0.25


def test_wait_fails_instead_of_continuing_on_a_stuck_graph(isolated, monkeypatch):
    monkeypatch.setenv("CTB_COGNEE_READY_DELAY_S", "30")
    with pytest.raises(SystemExit):
        wait_for_graph(
            _cfg(isolated, timeout=0.3), {}, arm="cognee", topic="meetings", workspace=isolated / "ws",
        )


def test_snapshot_exits_while_cognify_is_running(isolated, monkeypatch):
    monkeypatch.setenv("CTB_COGNEE_READY_DELAY_S", "30")
    env = os.environ.copy()
    base = [sys.executable, "-m", "harness.cognee_ctl"]
    common = ["--arm", "cognee", "--topic", "meetings", "--dataset", "ctb_meetings",
              "--workspace", str(isolated)]
    subprocess.run(base + ["kick", *common], env=env, check=True)
    proc = subprocess.run(
        base + ["snapshot", *common, "--snapshot", str(isolated / "snap")],
        env=env, capture_output=True, text=True,
    )
    assert proc.returncode == 3
    assert "running" in proc.stdout
