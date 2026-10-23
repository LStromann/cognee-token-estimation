"""Run headless Claude Code and turn its stream-json output into metrics."""
import json, os, subprocess, time
from collections import Counter

USAGE_KEYS = ["input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"]


def claude_version(binary="claude"):
    try:
        return subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:
        return "unknown"


def run_turn(prompt, *, model, slot, mcp_config, settings, ccfg, resume=None, raw_log=None, extra_env=None):
    cmd = [ccfg["binary"], *(ccfg.get("binary_args") or []), "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--model", model, "--mcp-config", str(mcp_config), "--strict-mcp-config",
           "--max-turns", str(ccfg["max_turns"]), "--permission-mode", ccfg["permission_mode"]]
    if settings:
        cmd += ["--settings", str(settings)]
    if resume:
        cmd += ["--resume", resume]
    env = {**os.environ, "CLAUDE_CONFIG_DIR": str(slot / "config"), **(extra_env or {})}
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=slot / "workspace", env=env, capture_output=True, text=True,
                           timeout=ccfg["timeout_s"])
        stdout, stderr, rc = p.stdout, p.stderr, p.returncode
    except subprocess.TimeoutExpired as e:
        stdout, stderr, rc = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or ""), "TIMEOUT", -1
    wall = time.time() - t0
    if raw_log:
        with open(raw_log, "a") as fh:
            fh.write(stdout)
    events = []
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    m = parse_stream(events)
    m.update(wall_s=wall, returncode=rc, stderr_tail=stderr[-500:])
    return m


def _group(tool_name):
    if tool_name.startswith("mcp__"):
        return "mcp:" + tool_name.split("__")[1]
    return tool_name


def parse_stream(events):
    usage_by_msg, names = {}, {}
    calls, result_chars = Counter(), Counter()
    result, mcp_status = None, {}
    for e in events:
        t = e.get("type")
        if t == "system" and e.get("subtype") == "init":
            mcp_status = {s.get("name"): s.get("status") for s in e.get("mcp_servers", [])}
        elif t == "assistant":
            msg = e.get("message", {})
            if msg.get("id") and msg.get("usage"):
                usage_by_msg[msg["id"]] = msg["usage"]  # dedupe: one usage per API message
            for b in msg.get("content", []) or []:
                if b.get("type") == "tool_use":
                    names[b["id"]] = b["name"]
                    calls[_group(b["name"])] += 1
        elif t == "user":
            content = e.get("message", {}).get("content", [])
            for b in content if isinstance(content, list) else []:
                if b.get("type") == "tool_result":
                    g = _group(names.get(b.get("tool_use_id"), "unknown"))
                    result_chars[g] += len(json.dumps(b.get("content"), ensure_ascii=False))
        elif t == "result":
            result = e
    if result and result.get("usage"):
        usage = {k: result["usage"].get(k, 0) or 0 for k in USAGE_KEYS}
    else:
        usage = {k: sum((u.get(k, 0) or 0) for u in usage_by_msg.values()) for k in USAGE_KEYS}
    return {
        **usage,
        "total_tokens": sum(usage.values()),
        "num_turns": (result or {}).get("num_turns"),
        "cost_usd": (result or {}).get("total_cost_usd"),
        "session_id": (result or {}).get("session_id"),
        "is_error": (result or {}).get("is_error", result is None),
        "answer": (result or {}).get("result", ""),
        "tool_calls": dict(calls),
        "tool_result_chars": dict(result_chars),
        "mcp_status": mcp_status,
    }


def merge(turns):
    """Aggregate metrics over the turns of a multi-turn task."""
    out = {k: sum(t.get(k, 0) or 0 for t in turns) for k in USAGE_KEYS + ["total_tokens", "wall_s"]}
    out["num_turns"] = sum(t.get("num_turns") or 0 for t in turns)
    out["cost_usd"] = sum(t.get("cost_usd") or 0 for t in turns)
    for k in ("tool_calls", "tool_result_chars"):
        c = Counter()
        for t in turns:
            c.update(t.get(k, {}))
        out[k] = dict(c)
    out["is_error"] = any(t.get("is_error") for t in turns)
    out["answer"] = turns[-1].get("answer", "") if turns else ""
    out["session_id"] = turns[0].get("session_id") if turns else None
    out["mcp_status"] = turns[0].get("mcp_status", {}) if turns else {}
    return out
