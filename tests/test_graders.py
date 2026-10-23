"""Graders for llm_judge, state_check, and hidden tests, plus the secondary judge."""
import json
import shutil

from harness.config import ROOT
from harness.fake_upstream import serve_background
from harness.graders import llm_judge, run_tests, secondary_judge, state_check


def test_hidden_tests_fail_on_the_overlay_and_pass_on_the_solution(tmp_path):
    slot = tmp_path / "slot"
    ws = slot / "workspace"
    shutil.copytree(ROOT / "coding_overlay", ws)
    grader = {
        "hidden_tests": "tasks/coding/hidden/cd-fix-001",
        "command": "python3 -m pytest -q tests/hidden --rootdir=. --override-ini=pythonpath=. -p no:cacheprovider",
    }
    failed = run_tests(grader, slot)
    assert failed["success"] is False
    shutil.copytree(ROOT / "tasks" / "coding" / "solutions" / "tidepool_sync", ws / "tidepool_sync",
                    dirs_exist_ok=True)
    passed = run_tests(grader, slot)
    assert passed["success"] is True


def test_state_check_sees_a_created_issue(tmp_path):
    state = tmp_path / "slot" / "state" / "linear"
    shutil.copytree(ROOT / "fixtures" / "mcp" / "linear", state)
    data = json.loads((state / "data.json").read_text())
    data["issues"].append({
        "id": "LIN-900", "title": "Align the spec", "state": "Todo", "assignee": "priya",
        "description": "Use 4 retries with jitter", "labels": [], "created_in_run": True,
    })
    (state / "data.json").write_text(json.dumps(data))
    result = state_check([{
        "server": "linear", "collection": "issues", "created_in_run": True,
        "where": {"assignee": "priya", "description_contains": "4 retries"},
    }], tmp_path / "slot")
    assert result["success"] is True


def test_primary_and_secondary_judges_disagree_on_the_review_marker(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dry-run")
    monkeypatch.setenv("OPENAI_API_KEY", "dry-run")
    proc, base = serve_background()
    try:
        task = {
            "turns": ["What is the cap?"],
            "gold": "The cap is 4.",
            "grader": {"kind": "llm_judge", "rubric": "Pass if the cap is 4."},
        }
        answer = "The cap is 4.\n[[review]]"
        primary = llm_judge(task, answer, "claude-sonnet-5-5", base)
        secondary = secondary_judge(task, answer, {
            "enabled": True, "provider": "openai", "model": "gpt-4.1-mini",
            "base_url": base + "/v1", "api_key_env": "OPENAI_API_KEY",
        })
        assert primary["success"] is True
        assert secondary["error"] is None
        assert secondary["success"] is False
    finally:
        proc.terminate()
