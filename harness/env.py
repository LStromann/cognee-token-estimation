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


# Claude Code's own traffic must stay on the unprefixed proxy. These two variables
# retarget the Anthropic SDK, so they belong on Cognee's processes only (the MCP
# server and the hook commands), never on the claude process itself.
CLAUDE_EXCLUDED_PROXY_KEYS = {"ANTHROPIC_BASE_URL", "ANTHROPIC_API_BASE"}


def enrich_fmt(cfg, fmt=None, **kw):
    """Fill lifecycle placeholders, including per-arm Cognee data directories."""
    import os
    fmt = {**(fmt or {}), **{k: v for k, v in kw.items() if v is not None}}
    work = str(cfg.get("work_dir") or "/tmp/ctb")
    arm = str(fmt.get("arm") or "_")
    topic = str(fmt.get("topic") or "_")
    fmt.setdefault("work_dir", work)
    fmt.setdefault("plugin_root", (cfg.get("cognee") or {}).get("plugin_root") or "")
    fmt.setdefault("snapshot", fmt.get("snapshot") or "")
    fmt.setdefault("workspace", fmt.get("workspace") or "")
    fmt["dataset"] = _fmt((cfg.get("cognee") or {}).get("dataset") or "ctb_{topic}", **fmt)
    fmt["cognee_system"] = str(pathlib.Path(work) / "cognee" / arm / topic / "system")
    fmt["cognee_data"] = str(pathlib.Path(work) / "cognee" / arm / topic / "data")
    fmt.setdefault("anthropic_api_key", os.environ.get("ANTHROPIC_API_KEY", ""))
    return fmt


def cognee_env(cfg, fmt):
    """Environment for Cognee lifecycle commands, hooks, and the Cognee MCP server."""
    import os
    fmt = enrich_fmt(cfg, fmt)
    formatted = {k: _fmt(v, **fmt) for k, v in (cfg["cognee"].get("proxy_env") or {}).items()}
    formatted = {k: v for k, v in formatted.items() if v != ""}
    merged = {**os.environ, **formatted}
    prior = os.environ.get("PYTHONPATH")
    merged["PYTHONPATH"] = str(ROOT) + (os.pathsep + prior if prior else "")
    merged["CTB_WORK_DIR"] = str(cfg.get("work_dir") or merged.get("CTB_WORK_DIR") or "/tmp/ctb")
    if fmt.get("proxy_cognee"):
        merged["CTB_PROXY_COGNEE"] = fmt["proxy_cognee"]
    if cfg.get("_dry_run"):
        merged["CTB_COGNEE_BACKEND"] = "file"
    return merged


def sh(cmd, cfg=None, fmt=None, **kw):
    """Run a Cognee lifecycle command with Cognee's LLM/embeddings routed through the proxy."""
    if cmd:
        fmt = enrich_fmt(cfg, fmt, **kw) if cfg else {**(fmt or {}), **kw}
        subprocess.run(_fmt(cmd, **fmt), shell=True, check=True, env=cognee_env(cfg, fmt) if cfg else None)


def build_fresh(cfg, arm, topic, fmt=None):
    slot = slot_dir(cfg, arm)
    if slot.exists():
        shutil.rmtree(slot)
    ws = slot / "workspace"
    repo = cfg.get("coding_repo") or {}
    if topic == "coding" and repo.get("url") and not cfg.get("_dry_run"):
        if not repo.get("commit"):
            raise SystemExit("coding_repo.commit is empty. Pin a commit in config/experiment.yaml.")
        cache = slot.parent.parent / "repo_cache"
        if not cache.exists():
            subprocess.run(["git", "clone", repo["url"], str(cache)], check=True)
        shutil.copytree(cache, ws, symlinks=True)
        subprocess.run(["git", "reset", "--hard", repo["commit"]], cwd=ws, check=True)
        subprocess.run(["git", "clean", "-fdx"], cwd=ws, check=True)
    elif topic == "coding":
        ws.mkdir(parents=True)
        offline = ROOT / "fixtures" / "coding_offline"
        if offline.exists():
            shutil.copytree(offline, ws, dirs_exist_ok=True)
    else:
        ws.mkdir(parents=True)
    if topic == "coding" and (ROOT / "coding_overlay").exists():
        shutil.copytree(ROOT / "coding_overlay", ws, dirs_exist_ok=True)
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
    fmt = enrich_fmt(cfg, fmt, topic=topic, arm=arm)
    for name, spec in (adef.get("extra_mcp") or {}).items():
        spec = _fmt_obj(spec, **fmt)
        if name == "cognee":  # route Cognee's internal LLM/embedding calls through the proxy
            spec["env"] = {**(spec.get("env") or {}),
                           **{k: _fmt(v, **fmt) for k, v in (cfg["cognee"].get("proxy_env") or {}).items()}}
            spec["env"] = {k: v for k, v in spec["env"].items() if v != ""}
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
    """Env for Claude Code (and the hooks it spawns) in this arm.

    ANTHROPIC_BASE_URL stays the unprefixed proxy so Claude's own calls are
    source=claude. Hook commands in the cognee arm prefix ANTHROPIC_BASE_URL with
    the /cognee route themselves, which is what the plugin's server inherits.
    """
    import os
    fmt = enrich_fmt(cfg, fmt, arm=arm)
    prior = os.environ.get("PYTHONPATH")
    e = {"ANTHROPIC_BASE_URL": fmt["proxy"],
         "CTB_HOOKS_FILE": str(slot / "hooks.json"),
         "CTB_SETTINGS_FILE": str(slot / "settings.json"),
         "CTB_COGNEE_HOOK_LOG": str(slot / f"{log_prefix}.cognee_hook.jsonl"),
         "CTB_ARM": arm,
         "PYTHONPATH": str(ROOT) + (os.pathsep + prior if prior else "")}
    if arm == "cognee":
        formatted = {k: _fmt(v, **fmt) for k, v in (cfg["cognee"].get("proxy_env") or {}).items()
                     if k not in CLAUDE_EXCLUDED_PROXY_KEYS}
        e.update({k: v for k, v in formatted.items() if v != ""})
    e["ANTHROPIC_BASE_URL"] = fmt["proxy"]
    if cfg.get("_dry_run"):
        e["CTB_DRY_RUN"] = "1"
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
