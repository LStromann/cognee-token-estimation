"""Warm-up and eval runner (all LLM traffic metered by the token proxy).

  python -m harness.run --phase warmup [--arms cognee] [--topics meetings]
  python -m harness.run --phase eval [--pilot] [--models claude-opus-5-5,claude-sonnet-5-5]
                        [--reps 3] [--tasks po-xsrc-001,mt-*]
"""
import argparse, datetime, fnmatch, json, os, pathlib, random, shutil, time

from harness import env, proxy_ctl, tokens
from harness.claude_runner import claude_version, merge, run_turn
from harness.config import ROOT, load_config, load_tasks, load_warmup
from harness.graders import grade, secondary_judge
from harness.graph_wait import wait_for_graph


def run_session(turns, *, model, slot, arm, topic, cfg, fmt, log_prefix, task=None, phase="eval"):
    mock_log = slot / f"{log_prefix}.mock.jsonl"
    fmt = env.enrich_fmt(cfg, fmt, arm=arm, topic=topic, workspace=slot / "workspace")
    mcp_cfg, settings = env.write_mcp_config(cfg, arm, topic, slot, mock_log, fmt)
    extra = env.run_env(cfg, arm, slot, fmt, log_prefix)
    extra["CTB_PHASE"] = phase
    if task is not None and cfg.get("_dry_run"):
        extra["CTB_TASK_FILE"] = str(ROOT / task["_file"])
    out, session = [], None
    for i, prompt in enumerate(turns):
        extra["CTB_TURN_INDEX"] = str(i)
        m = run_turn(prompt, model=model, slot=slot, mcp_config=mcp_cfg, settings=settings,
                     ccfg=cfg["claude"], resume=session, raw_log=slot / f"{log_prefix}.stream.jsonl",
                     extra_env=extra)
        session = session or m.get("session_id")
        out.append(m)
    return merge(out), mock_log


def warmup(cfg, arms, topics, out_dir, fmt):
    version = claude_version(cfg["claude"]["binary"])
    ingest_file = out_dir / "ingest.json"
    ingest = json.loads(ingest_file.read_text()) if ingest_file.exists() else {}
    for arm in arms:
        for topic in topics:
            print(f"[warmup] {arm}/{topic}")
            prefix = f"warmup__{arm}__{topic}__"
            proxy_ctl.set_context(cfg, run_id=prefix + "setup", phase="warmup", arm=arm, topic=topic)
            slot = env.build_fresh(cfg, arm, topic, fmt)
            suffix = cfg["warmup"]["explicit_suffix"] if cfg["warmup"]["memory_prompting"] == "explicit" else ""
            for s in load_warmup(topic):
                proxy_ctl.set_context(cfg, run_id=prefix + s["id"], phase="warmup", arm=arm, topic=topic)
                run_session([t + suffix for t in s["turns"]], model=cfg["warmup_model"], slot=slot, arm=arm,
                            topic=topic, cfg=cfg, fmt=fmt, log_prefix=f"warmup-{s['id']}", phase="warmup")
                # Cognify runs after the session returns. Do not start the next session
                # until the graph is idle or completed, or a partial graph leaks forward.
                if arm == "cognee":
                    st = wait_for_graph(cfg, fmt, arm=arm, topic=topic, workspace=slot / "workspace")
                    print(f"[warmup] {arm}/{topic} {s['id']} graph ready ({st['status']})")
            if arm == "cognee":
                proxy_ctl.set_context(cfg, run_id=prefix + "ingest", phase="warmup", arm=arm, topic=topic)
                st = wait_for_graph(cfg, fmt, arm=arm, topic=topic, workspace=slot / "workspace",
                                    kick="after_warmup_cmd")
                print(f"[warmup] {arm}/{topic} final graph ready ({st['status']})")
            proxy_ctl.set_context(cfg, run_id=prefix + "snapshot", phase="warmup", arm=arm, topic=topic)
            bk = tokens.buckets(tokens.load(out_dir / "proxy.jsonl"), prefix=prefix)
            ingest.setdefault(topic, {})[arm] = bk  # Cognee's ingestion cost = cognee_* buckets here
            mem = env.memory_summary(slot)
            if not mem["has_native_memory"]:
                print(f"WARNING [{arm}/{topic}]: warm-up left NO native memory (CLAUDE.md unchanged, no memory "
                      f"files). The baseline would effectively be 'no memory'. See docs/test-plan.md.")
            env.snapshot(cfg, arm, topic, {"warmup_model": cfg["warmup_model"], "claude_version": version,
                                           "created": datetime.datetime.now().isoformat(), "tokens": bk,
                                           "memory": mem}, fmt)
            ingest_file.write_text(json.dumps(ingest, indent=1))


def evaluate(cfg, models, tasks, reps, out_dir, fmt):
    (out_dir / "raw").mkdir(parents=True, exist_ok=True)
    runs_file = out_dir / "runs.jsonl"
    tcfg = cfg["tokens"]
    counter = tokens.TokenCounter(out_dir / "token_count_cache.json", tcfg["direct_base_url"])
    version = claude_version(cfg["claude"]["binary"])
    if cfg["claude"].get("expected_version") and cfg["claude"]["expected_version"] not in version:
        print(f"WARNING: claude version {version} != expected {cfg['claude']['expected_version']}")
    rng = random.Random(cfg["seed"])
    total, i = len(models) * len(tasks) * reps * len(cfg["arms"]), 0
    for model in models:
        for task in tasks:
            for rep in range(reps):
                arms = list(cfg["arms"])
                rng.shuffle(arms)  # interleave arm order
                for arm in arms:
                    i += 1
                    run_id = f"{model}__{arm}__{task['id']}__r{rep}"
                    print(f"[{i}/{total}] {run_id}")
                    proxy_ctl.set_context(cfg, run_id=run_id + "__restore", phase="restore", arm=arm, topic=task["topic"])
                    slot, meta = env.restore(cfg, arm, task["topic"], fmt)
                    if meta.get("warmup_model") != cfg["warmup_model"]:
                        print(f"WARNING: snapshot built with {meta.get('warmup_model')}")
                    plog = env.plugin_hook_log(cfg, slot) if arm == "cognee" else None
                    plog_offset = plog.stat().st_size if plog and plog.exists() else 0  # log may be shared/appended
                    proxy_ctl.set_context(cfg, run_id=run_id, phase="eval", arm=arm, topic=task["topic"])
                    m, mock_log = run_session(task["turns"], model=model, slot=slot, arm=arm, topic=task["topic"],
                                              cfg=cfg, fmt=fmt, log_prefix="eval", task=task, phase="eval")
                    proxy_ctl.set_context(cfg, run_id=run_id + "__post", phase="post", arm=arm, topic=task["topic"])
                    g = grade(task, m["answer"], slot, cfg["judge_model"], tcfg["direct_base_url"])
                    sec = secondary_judge(task, m["answer"], cfg.get("secondary_judge") or {}, tcfg["direct_base_url"])
                    disagree = bool(sec and not sec.get("error") and sec.get("success") is not None
                                    and bool(sec["success"]) != bool(g["success"]))

                    # ---- exact token accounting ----
                    records = tokens.load(out_dir / "proxy.jsonl")
                    tok = tokens.flatten(tokens.buckets(records, run_id=run_id), proxy_ctl.sources(cfg))
                    ctx = {}
                    if arm == "cognee":
                        if plog:
                            hook_texts = tokens.load_hook_log(plog, cfg["cognee"]["hook_log"].get("text_field", ""),
                                                              plog_offset)
                        else:
                            hook_texts = tokens.load_hook_log(slot / "eval.cognee_hook.jsonl")
                        ctx, per_req = tokens.cognee_attribution(records, run_id, out_dir, tcfg, counter, hook_texts)
                        (out_dir / "raw" / f"{run_id}.ctx_per_request.json").write_text(json.dumps(per_req))
                        if ctx["cognee_hook_unmatched"]:
                            print(f"WARNING: {ctx['cognee_hook_unmatched']} logged hook texts not found verbatim in requests")
                    if not tcfg.get("keep_request_bodies"):
                        shutil.rmtree(out_dir / "requests" / run_id, ignore_errors=True)
                    stream_total = m["total_tokens"]
                    diff = abs(tok["claude_total"] - stream_total) / max(tok["claude_total"], 1)

                    mock_calls = [json.loads(l) for l in mock_log.read_text().splitlines()] if mock_log.exists() else []
                    stream = slot / "eval.stream.jsonl"
                    (out_dir / "raw" / f"{run_id}.stream.jsonl").write_text(stream.read_text() if stream.exists() else "")
                    rec = {"run_id": run_id, "model": model, "arm": arm, "task_id": task["id"], "topic": task["topic"],
                           "type": task["type"], "hops": task.get("hops"), "rep": rep, "claude_version": version,
                           "ts": time.time(), **tok, **ctx,
                           **{f"stream_{k}": v for k, v in m.items() if k not in ("answer", "mcp_status")},
                           "answer": m["answer"], "mcp_status": m["mcp_status"],
                           "token_crosscheck_diff": round(diff, 4),
                           "token_crosscheck_flag": diff > tcfg["crosscheck_tolerance"],
                           **g, "mock_calls": len(mock_calls),
                           "mock_response_chars": sum(c["response_chars"] for c in mock_calls),
                           "dry_run": bool(cfg.get("_dry_run")),
                           "secondary_success": None if not sec else sec.get("success"),
                           "secondary_reason": "" if not sec else (sec.get("reason") or ""),
                           "secondary_error": "" if not sec else (sec.get("error") or ""),
                           "judge_disagreement": disagree}
                    with open(runs_file, "a") as fh:
                        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def require_plugin_root(cfg):
    """The Claude plugin's script directory is machine-specific. One config slot."""
    if cfg.get("_dry_run") or "cognee" not in cfg["arms"]:
        return
    root = str((cfg.get("cognee") or {}).get("plugin_root") or "").strip()
    scripts = pathlib.Path(root) / "scripts" if root else None
    if not scripts or not scripts.is_dir():
        raise SystemExit(
            "cognee.plugin_root is empty or has no scripts/ directory. Set it to the installed "
            "Cognee Claude Code plugin (integrations/claude-code from topoteretes/cognee-integrations). "
            "That is the one manual path. Offline pipeline: make pilot-dry."
        )


def main():
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["warmup", "eval"], required=True)
    ap.add_argument("--models"); ap.add_argument("--arms"); ap.add_argument("--topics")
    ap.add_argument("--tasks", help="comma-separated ids or globs")
    ap.add_argument("--reps", type=int); ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="fake LLM behind the proxy; no API key")
    a = ap.parse_args()
    dry = a.dry_run or os.environ.get("CTB_DRY_RUN") == "1"
    fake = None
    if dry:
        from harness.fake_upstream import serve_background
        from harness.dryrun import apply
        _proc, fake_url = serve_background()
        fake = _proc
        apply(cfg, fake_base_url=fake_url)
    require_plugin_root(cfg)
    split = lambda s: [x.strip() for x in s.split(",")] if s else None
    arms = split(a.arms) or cfg["arms"]
    topics = split(a.topics) or cfg["topics"]
    cfg["arms"] = arms
    out_dir = ROOT / "results" / cfg["name"]
    out_dir.mkdir(parents=True, exist_ok=True)
    fmt = proxy_ctl.urls(cfg)
    proxy = proxy_ctl.start(cfg, out_dir)
    try:
        if a.phase == "warmup":
            return warmup(cfg, arms, topics, out_dir, fmt)
        tasks = load_tasks(topics, cfg["pilot"]["tasks_per_topic"] if a.pilot else None)
        if a.tasks:
            pats = split(a.tasks)
            tasks = [t for t in tasks if any(fnmatch.fnmatch(t["id"], p) for p in pats)]
        reps = a.reps or (cfg["pilot"]["repetitions"] if a.pilot else cfg["repetitions"])
        evaluate(cfg, split(a.models) or cfg["models"], tasks, reps, out_dir, fmt)
    finally:
        proxy_ctl.stop(proxy)
        if fake is not None:
            fake.terminate()
            try:
                fake.wait(5)
            except Exception:
                fake.kill()


if __name__ == "__main__":
    main()
