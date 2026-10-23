"""Dry-run stand-in for the Claude Code CLI.

Speaks --output-format stream-json, sends the real HTTP calls through
ANTHROPIC_BASE_URL (the token proxy), runs the arm's hooks, and applies the
side effects the graders look for. It is only invoked when the harness is in
--dry-run. Task gold is read from CTB_TASK_FILE, which the real claude process
does not receive.
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import urllib.request

import yaml

# Tasks whose dry-run answer carries a marker the secondary judge rejects.
# The primary judge still sees the gold text. This only exists so the sample
# report shows the disagreement flag.
# One llm_judge task per topic that the stratified pilot actually runs, so
# `make pilot-dry` shows disagreement flags in the sample report.
DISAGREE_IDS = {"cd-qa-001", "po-recall-001", "mt-recall-001"}
SOLUTION = pathlib.Path(__file__).resolve().parent.parent / "tasks" / "coding" / "solutions" / "tidepool_sync"


def _post(path, body, profile=None):
    base = os.environ.get("ANTHROPIC_BASE_URL", "http://127.0.0.1:8787").rstrip("/")
    req = urllib.request.Request(
        base + path, data=json.dumps(body).encode(),
        headers={
            "content-type": "application/json",
            "anthropic-version": "2023-06-01",
            "x-api-key": os.environ.get("ANTHROPIC_API_KEY", "dry-run"),
            **({"X-CTB-Usage-Profile": profile} if profile else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode())
    return payload.get("usage") or {}


def _contexts(stdout):
    text = (stdout or "").strip()
    if not text:
        return []
    try:
        doc = json.loads(text)
    except json.JSONDecodeError:
        return [text]
    ctx = (doc.get("hookSpecificOutput") or {}).get("additionalContext")
    return [ctx.strip()] if isinstance(ctx, str) and ctx.strip() else []


def run_hooks():
    path = os.environ.get("CTB_SETTINGS_FILE")
    if not path or not os.path.exists(path):
        return []
    settings = json.loads(pathlib.Path(path).read_text())
    found = []
    for entries in (settings.get("hooks") or {}).values():
        for entry in entries:
            for hook in entry.get("hooks") or []:
                cmd = hook.get("command")
                if not cmd:
                    continue
                proc = subprocess.run(cmd, shell=True, input=b"{}", capture_output=True)
                found.extend(_contexts(proc.stdout.decode("utf-8", "replace")))
    return found


def load_task():
    path = os.environ.get("CTB_TASK_FILE")
    if not path or not os.path.exists(path):
        return None
    return yaml.safe_load(pathlib.Path(path).read_text())


def remember_native():
    """Leave a native-memory trace so the baseline arm is not 'no memory'."""
    ws = pathlib.Path.cwd()
    md = ws / "CLAUDE.md"
    text = md.read_text() if md.exists() else ""
    note = "\n\n## Memory\n- Keep Fernhill decisions from Linear, Granola, Notion, and Slack.\n"
    if "## Memory" not in text:
        md.write_text(text + note)


def apply_checks(task):
    state = pathlib.Path.cwd().parent / "state"
    for check in task["grader"].get("checks") or []:
        path = state / check["server"] / "data.json"
        data = json.loads(path.read_text())
        coll = data[check["collection"]]
        if check.get("created_in_run"):
            item = {"created_in_run": True}
            for key, value in (check.get("where") or {}).items():
                if key.endswith("_contains"):
                    field = key[:-9]
                    item[field] = (item.get(field) or "") + f" {value}"
                else:
                    item[key] = value
            if check["server"] == "linear" and check["collection"] == "issues":
                nxt = max(int(i["id"].split("-")[1]) for i in coll) + 1
                item.setdefault("id", f"LIN-{nxt}")
                item.setdefault("title", "Bring the source in line with the latest decision")
                item.setdefault("state", "Todo")
                item.setdefault("labels", [])
            if check["server"] == "slack":
                item.setdefault("ts", "run")
                item.setdefault("user", "me")
            if check["server"] == "notion":
                item.setdefault("id", f"NP-run-{len(coll) + 1}")
                item.setdefault("title", item.get("title") or "page")
                item.setdefault("content", item.get("content") or "")
                item.setdefault("owner", "me")
                item.setdefault("last_edited", "run")
            coll.append(item)
        path.write_text(json.dumps(data, indent=1, ensure_ascii=False))


def apply_solution():
    dest = pathlib.Path.cwd() / "tidepool_sync"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(SOLUTION, dest)


def answer_for(task, prompt, last):
    if task is None:
        return "Warm-up notes recorded for later sessions."
    if not last:
        return "Noted. I will use the next turn for the draft."
    text = task.get("gold") or "done"
    if task.get("id") in DISAGREE_IDS:
        text += "\n[[review]]"
    return text


def llm_calls(arm, model, prompt, hook_texts):
    """Return (claude_usage_sum, call_count). Cognee-internal calls are not summed."""
    total = {"input_tokens": 0, "output_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}
    if arm == "cognee":
        tools = [
            {"name": "mcp__cognee__search", "description": "Search Cognee memory",
             "input_schema": {"type": "object", "properties": {}}},
            {"name": "Read", "description": "Read a file",
             "input_schema": {"type": "object", "properties": {}}},
        ]
        body = {
            "model": model, "max_tokens": 32,
            "system": "\n".join(hook_texts),
            "tools": tools,
            "messages": [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": [
                    {"type": "tool_use", "id": "toolu_cognee", "name": "mcp__cognee__search",
                     "input": {"query": prompt[:120]}}]},
                {"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": "toolu_cognee",
                     "content": "cognee hit: stable idempotency key and retry cap 4"}]},
            ],
        }
        for profile in (None, "resent"):
            usage = _post("/v1/messages", body, profile)
            for key in total:
                total[key] += usage.get(key, 0) or 0
        _post("/cognee/v1/messages", {"model": model, "max_tokens": 16,
                                      "messages": [{"role": "user", "content": "retrieve " + prompt[:80]}]})
        return total
    for _ in range(4):
        usage = _post("/v1/messages", {"model": model, "max_tokens": 16,
                                       "messages": [{"role": "user", "content": prompt}]})
        for key in total:
            total[key] += usage.get(key, 0) or 0
    return total


def emit(prompt, model):
    task = load_task()
    turn = int(os.environ.get("CTB_TURN_INDEX", "0"))
    n_turns = len(task["turns"]) if task else 1
    last = turn >= n_turns - 1
    phase = os.environ.get("CTB_PHASE", "")
    if phase == "warmup":
        remember_native()
    hook_texts = run_hooks()
    arm = os.environ.get("CTB_ARM", "baseline")
    usage = llm_calls(arm, model, prompt, hook_texts)
    if task and last and phase != "warmup":
        kind = task["grader"]["kind"]
        if kind == "state_check":
            apply_checks(task)
        elif kind == "tests":
            apply_solution()
    answer = answer_for(task, prompt, last)
    mcp_path = pathlib.Path.cwd().parent / "mcp.json"
    servers = []
    if mcp_path.exists():
        servers = [{"name": name, "status": "connected"}
                   for name in json.loads(mcp_path.read_text()).get("mcpServers", {})]
    session = os.environ.get("CTB_SESSION_ID") or "dry-session"
    events = [
        {"type": "system", "subtype": "init", "session_id": session, "mcp_servers": servers},
        {"type": "assistant", "message": {"id": f"dry-{turn}", "model": model, "usage": usage,
                                          "content": [{"type": "text", "text": answer}]}},
        {"type": "result", "subtype": "success", "is_error": False, "result": answer,
         "session_id": session, "num_turns": 1, "total_cost_usd": 0, "usage": usage},
    ]
    sys.stdout.write("".join(json.dumps(event) + "\n" for event in events))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--prompt", required=True)
    ap.add_argument("--model", default="dry-run")
    args, _unknown = ap.parse_known_args()
    try:
        emit(args.prompt, args.model)
    except Exception as exc:
        sys.stderr.write(f"fake_claude: {exc}\n")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
