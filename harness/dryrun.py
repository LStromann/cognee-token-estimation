"""Switch the loaded experiment config onto the offline fake-LLM backend."""
import os
import sys


def apply(cfg, *, fake_base_url):
    """Mutate cfg for --dry-run. fake_base_url is the stub server, with no /v1 suffix."""
    cfg["_dry_run"] = True
    cfg["name"] = os.environ.get("CTB_RESULT_NAME") or "dry-run-synthetic"
    cfg["work_dir"] = os.environ.get("CTB_WORK_DIR") or "/tmp/ctb-dry-run"
    cfg["claude"]["binary"] = sys.executable
    cfg["claude"]["binary_args"] = ["-m", "harness.fake_claude"]
    cfg["claude"]["timeout_s"] = min(int(cfg["claude"].get("timeout_s") or 120), 180)
    cfg["tokens"]["upstream"] = fake_base_url
    cfg["tokens"]["direct_base_url"] = fake_base_url
    judge = cfg.setdefault("secondary_judge", {})
    judge["enabled"] = True
    judge["base_url"] = fake_base_url.rstrip("/") + "/v1"
    cfg["cognee"]["hooks"] = [
        {"event": "SessionStart", "command": f'"{sys.executable}" -m harness.dryrun_hook SessionStart'},
        {"event": "UserPromptSubmit", "command": f'"{sys.executable}" -m harness.dryrun_hook UserPromptSubmit'},
    ]
    cfg["cognee"]["hook_log"] = {"path": "", "text_field": ""}
    wait = cfg["cognee"].setdefault("wait", {})
    wait["poll_s"] = 0.05
    wait["timeout_s"] = 20
    wait["ready_statuses"] = ["completed", "idle"]
    os.environ["CTB_DRY_RUN"] = "1"
    os.environ["CTB_COGNEE_BACKEND"] = "file"
    os.environ["CTB_WORK_DIR"] = cfg["work_dir"]
    os.environ["CTB_RESULT_NAME"] = cfg["name"]
    os.environ.setdefault("CTB_COGNEE_READY_DELAY_S", "0.2")
    os.environ.setdefault("ANTHROPIC_API_KEY", "dry-run")
    os.environ.setdefault("OPENAI_API_KEY", "dry-run")
    return cfg
