"""Offline warm-up, eval, and report. Numbers are synthetic."""
import os
import shutil
import socket
import subprocess
import sys

from harness.config import ROOT, load_config, load_tasks
from harness.dryrun import apply
from harness.fake_claude import DISAGREE_IDS
from harness.fake_upstream import serve_background
from harness.run import evaluate, warmup
from harness import proxy_ctl


TASKS = ["cd-fix-001", "cd-qa-001", "po-act-001", "po-recall-001", "mt-recall-001"]


def _free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def test_dry_run_pipeline_writes_a_synthetic_report(tmp_path, monkeypatch):
    monkeypatch.setenv("CTB_DRY_RUN", "1")
    monkeypatch.setenv("CTB_WORK_DIR", str(tmp_path / "work"))
    monkeypatch.setenv("CTB_RESULT_NAME", "pytest-synthetic")
    monkeypatch.setenv("CTB_COGNEE_READY_DELAY_S", "0.05")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dry-run")
    monkeypatch.setenv("OPENAI_API_KEY", "dry-run")
    monkeypatch.delenv("SYSTEM_ROOT_DIRECTORY", raising=False)
    monkeypatch.delenv("DATA_ROOT_DIRECTORY", raising=False)

    out = ROOT / "results" / "pytest-synthetic"
    shutil.rmtree(out, ignore_errors=True)
    proc, fake_url = serve_background()
    proxy = None
    try:
        cfg = load_config()
        apply(cfg, fake_base_url=fake_url)
        cfg["tokens"]["port"] = _free_port()
        out.mkdir(parents=True, exist_ok=True)
        fmt = proxy_ctl.urls(cfg)
        proxy = proxy_ctl.start(cfg, out)
        warmup(cfg, cfg["arms"], cfg["topics"], out, fmt)
        tasks = [task for task in load_tasks() if task["id"] in TASKS]
        assert len(tasks) == len(TASKS)
        evaluate(cfg, ["claude-opus-5-5", "claude-sonnet-5-5"], tasks, 1, out, fmt)
        subprocess.check_call(
            [sys.executable, "-m", "analysis.analyze", "--runs", str(out / "runs.jsonl")],
            cwd=ROOT, env={**os.environ, "CTB_RESULT_NAME": "pytest-synthetic"},
        )
        report = (out / "report.md").read_text()
        assert "SYNTHETIC DRY-RUN" in report
        assert "exploration_delta" in report
        assert "net_delta" in report
        assert "coding" in report
        assert "Judge disagreements" in report
        for task_id in DISAGREE_IDS:
            assert task_id in report
        assert (out / "pairs.csv").exists()
        assert (out / "ingest.json").exists()
    finally:
        if proxy is not None:
            proxy_ctl.stop(proxy)
        proc.terminate()
        shutil.rmtree(out, ignore_errors=True)
