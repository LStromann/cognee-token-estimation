"""Slots, workspaces, MCP configs, snapshots. One active slot per arm at a FIXED path
(Claude Code keys project memory by absolute path, so the path must not change between
warm-up and eval)."""
import json, pathlib, shutil, subprocess, sys
from harness.config import ROOT


def slot_dir(cfg, arm):
    return pathlib.Path(cfg["work_dir"]) / "active" / arm


def snap_dir(cfg, arm, topic):
    return pathlib.Path(cfg["work_dir"]) / "snapshots" / arm / topic


class _Safe(dict):
    def __missing__(self, k):
        return "{" + k + "}"


def _fmt(s, **kw):
    return s.format_map(_Safe(kw)) if isinstance(s, str) else s


def _fmt_obj(o, **kw):
    if isinstance(o, dict):
        return {k: _fmt_obj(v, **kw) for k, v in o.items()}
    if isinstance(o, list):
        return [_fmt_obj(v, **kw) for v in o]
    return _fmt(o, **kw)


def cognee_env(cfg, fmt):
    import os
    return {**os.environ, **{k: _fmt(v, **fmt) for k, v in (cfg["cognee"].get("proxy_env") or {}).items()}}


def sh(cmd, cfg=None, fmt=None, **kw):
    """Run a Cognee lifecycle command with Cognee's LLM/embeddings routed through the proxy."""
    if cmd:
        fmt = {**(fmt or {}), **kw}
        subprocess.run(_fmt(cmd, **fmt), shell=True, check=True, env=cognee_env(cfg, fmt) if cfg else None)


def build_fresh(cfg, arm, topic, fmt=None):
    slot = slot_dir(cfg, arm)
    if slot.exists():
        shutil.rmtree(slot)
    ws = slot / "workspace"
    if topic == "coding" and cfg["coding_repo"]["url"]:
        cache = slot.parent.parent / "repo_cache"
        if not cache.exists():
            subprocess.run(["git", "clone", cfg["coding_repo"]["url"], str(cache)], check=True)
        shutil.copytree(cache, ws, symlinks=True)
        subprocess.run(["git", "reset", "--hard", cfg["coding_repo"]["commit"]], cwd=ws, check=True)
        subprocess.run(["git", "clean", "-fdx"], cwd=ws, check=True)
    else:
        ws.mkdir(parents=True)
    shutil.copy(ROOT / "env/CLAUDE.md", ws / "CLAUDE.md")
    shutil.copytree(ROOT / "env/skills", ws / ".claude/skills", dirs_exist_ok=True)
    (slot / "config").mkdir(parents=True)
    shutil.copytree(ROOT / "fixtures/mcp", slot / "state")
    if arm == "cognee":
        sh(cfg["cognee"]["reset_cmd"], cfg, fmt, arm=arm, topic=topic, snapshot="", workspace=ws)
    return slot


def write_mcp_config(cfg, arm, topic, slot, mock_log, fmt=None):
    adef = cfg["arm_defs"][arm]
    servers = {}
    for name in adef["mcp_servers"]:
        servers[name] = {"command": sys.executable, "args": ["-m", f"mcp_mocks.{name}_server"],
                         "env": {"PYTHONPATH": str(ROOT), "MOCK_STATE_DIR": str(slot / "state"),
                                 "MOCK_LOG": str(mock_log)}}
    fmt = {**(fmt or {}), "topic": topic, "arm": arm}
    for name, spec in (adef.get("extra_mcp") or {}).items():
        spec = _fmt_obj(spec, **fmt)
        if name == "cognee":  # route Cognee's internal LLM/embedding calls through the proxy
            spec["env"] = {**(spec.get("env") or {}),
                           **{k: _fmt(v, **fmt) for k, v in (cfg["cognee"].get("proxy_env") or {}).items()}}
        servers[name] = spec
    path = slot / "mcp.json"
    path.write_text(json.dumps({"mcpServers": servers}, indent=1))
    return path, write_settings(cfg, arm, slot, fmt)


def write_settings(cfg, arm, slot, fmt):
    """Arm settings + (cognee arm) the Cognee hooks, each wrapped in tee_hook.py for logging."""
    adef = cfg["arm_defs"][arm]
    base = json.loads((ROOT / adef["settings"]).read_text()) if adef.get("settings") else {}
    base.pop("_comment", None)
    hooks = [_fmt_obj(h, **fmt) for h in (cfg["cognee"].get("hooks") or [])] if arm == "cognee" else []
    use_plugin_log = bool((cfg["cognee"].get("hook_log") or {}).get("path"))
    if hooks:
        (slot / "hooks.json").write_text(json.dumps(hooks, indent=1))
        tee = ROOT / "harness" / "hooks" / "tee_hook.py"
        merged = base.setdefault("hooks", {})
        for i, h in enumerate(hooks):
            cmd = h["command"] if use_plugin_log else f'"{sys.executable}" "{tee}" {i}'
            entry = {"hooks": [{"type": "command", "command": cmd}]}
            if h.get("matcher"):
                entry["matcher"] = h["matcher"]
            merged.setdefault(h["event"], []).append(entry)
    path = slot / "settings.json"
    path.write_text(json.dumps(base, indent=1))
    return path


def run_env(cfg, arm, slot, fmt, log_prefix):
    """Env for Claude Code (and the hooks it spawns) in this arm."""
    e = {"ANTHROPIC_BASE_URL": fmt["proxy"],
         "CTB_HOOKS_FILE": str(slot / "hooks.json"),
         "CTB_COGNEE_HOOK_LOG": str(slot / f"{log_prefix}.cognee_hook.jsonl")}
    if arm == "cognee":  # Cognee hooks also call Cognee's LLM -> through the proxy
        e.update({k: _fmt(v, **fmt) for k, v in (cfg["cognee"].get("proxy_env") or {}).items()})
    return e


def snapshot(cfg, arm, topic, meta, fmt=None):
    slot, snap = slot_dir(cfg, arm), snap_dir(cfg, arm, topic)
    if snap.exists():
        shutil.rmtree(snap)
    snap.mkdir(parents=True)
    for part in ("workspace", "config", "state"):
        shutil.copytree(slot / part, snap / part, symlinks=True)
    if arm == "cognee":
        sh(cfg["cognee"]["snapshot_cmd"], cfg, fmt, arm=arm, topic=topic, snapshot=snap, workspace=slot / "workspace")
    (snap / "meta.json").write_text(json.dumps(meta, indent=1))


def restore(cfg, arm, topic, fmt=None):
    slot, snap = slot_dir(cfg, arm), snap_dir(cfg, arm, topic)
    if not snap.exists():
        raise SystemExit(f"No snapshot for {arm}/{topic}. Run `make warmup` first.")
    if slot.exists():
        shutil.rmtree(slot)
    slot.mkdir(parents=True)
    for part in ("workspace", "config", "state"):
        shutil.copytree(snap / part, slot / part, symlinks=True)
    if arm == "cognee":
        sh(cfg["cognee"]["restore_cmd"], cfg, fmt, arm=arm, topic=topic, snapshot=snap, workspace=slot / "workspace")
    return slot, json.loads((snap / "meta.json").read_text())


def memory_summary(slot):
    """What native Claude Code memory exists after warm-up (CLAUDE.md edits + memory files)."""
    ws, cfgdir = slot / "workspace", slot / "config"
    orig = (ROOT / "env/CLAUDE.md").read_text()
    md = ws / "CLAUDE.md"
    changed = md.exists() and md.read_text() != orig
    files = []
    for base in (cfgdir, ws / ".claude"):
        for f in base.rglob("*.md") if base.exists() else []:
            rel = f.relative_to(slot)
            if "skills" in rel.parts:
                continue
            if "memory" in [p.lower() for p in rel.parts] or f.name in ("CLAUDE.md", "CLAUDE.local.md"):
                files.append(str(rel))
    local = ws / "CLAUDE.local.md"
    if local.exists():
        files.append(str(local.relative_to(slot)))
    size = sum((slot / f).stat().st_size for f in files)
    return {"claude_md_changed": changed, "claude_md_bytes": md.stat().st_size if md.exists() else 0,
            "memory_files": files, "memory_bytes": size, "has_native_memory": changed or bool(files)}


def plugin_hook_log(cfg, slot):
    """Path of the Cognee plugin's own hook log for this slot, or None (-> wrapper log is used)."""
    import os
    hl = cfg["cognee"].get("hook_log") or {}
    if not hl.get("path"):
        return None
    return pathlib.Path(_fmt(hl["path"], workspace=slot / "workspace", config_dir=slot / "config",
                             home=os.path.expanduser("~")))
