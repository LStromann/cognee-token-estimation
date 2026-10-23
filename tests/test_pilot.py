"""Pilot selection spreads across task types."""
from harness.config import load_tasks


def test_pilot_includes_a_code_fix_and_an_action():
    coding = load_tasks(["coding"], pilot_n=5)
    project = load_tasks(["project_ops"], pilot_n=5)
    meetings = load_tasks(["meetings"], pilot_n=5)
    assert any(task["type"] == "code_fix" for task in coding)
    assert any(task["type"] == "action" for task in project)
    assert any(task["type"] == "action" for task in meetings)
    assert len(coding) == len(project) == len(meetings) == 5
