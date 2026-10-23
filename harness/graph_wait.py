"""Block until Cognee's graph update for this dataset is finished.

Called after every warm-up session and again before snapshot. A session that
returns while cognify is still running must not be followed by another session
or by snapshot: that would leak a partial graph into the run.
"""
import json
import subprocess
import time

from harness import env


def _last_json(text):
    found = None
    for line in (text or "").splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                found = json.loads(line)
            except json.JSONDecodeError:
                continue
    return found


def read_status(cfg, fmt, *, arm, topic, workspace, snapshot=""):
    cmd = cfg["cognee"].get("status_cmd") or ""
    if not cmd.strip():
        raise SystemExit("cognee.status_cmd is empty; refusing to continue with unknown graph state")
    fmt = env.enrich_fmt(cfg, fmt, arm=arm, topic=topic, snapshot=snapshot, workspace=workspace)
    proc = subprocess.run(
        env._fmt(cmd, **fmt), shell=True, capture_output=True, text=True, env=env.cognee_env(cfg, fmt),
    )
    doc = _last_json(proc.stdout)
    if doc is None:
        raise SystemExit(f"cognee status command produced no JSON (exit {proc.returncode}): {(proc.stderr or proc.stdout)[-400:]}")
    doc["status"] = str(doc.get("status", "")).lower()
    return doc


def wait_for_graph(cfg, fmt, *, arm, topic, workspace, snapshot="", kick="after_session_cmd"):
    """Kick cognify (unless kick is None) and poll until the graph is ready.

    Ready statuses default to completed and idle. idle means no pipeline is in
    flight (a dataset that was never built, or a build that has finished and
    left no running row). running and error never count as ready.
    """
    if arm != "cognee":
        return {"status": "skipped", "detail": arm}
    cog = cfg["cognee"]
    if kick:
        command = cog.get(kick) or ""
        if not str(command).strip():
            raise SystemExit(f"cognee.{kick} is empty; refusing to continue while cognify may still be running")
        env.sh(command, cfg, fmt, arm=arm, topic=topic, snapshot=snapshot, workspace=workspace)
    wait = cog.get("wait") or {}
    poll = float(wait.get("poll_s", 2))
    timeout = float(wait.get("timeout_s", 900))
    ready = {s.lower() for s in (wait.get("ready_statuses") or ["completed", "idle"])}
    deadline = time.time() + timeout
    last = None
    while True:
        last = read_status(cfg, fmt, arm=arm, topic=topic, workspace=workspace, snapshot=snapshot)
        if last["status"] in ready:
            return last
        if last["status"] in {"error", "failed"}:
            raise SystemExit(f"cognify failed for {arm}/{topic}: {last}")
        if time.time() >= deadline:
            raise SystemExit(f"cognify still {last.get('status')} after {timeout}s for {arm}/{topic}; "
                             f"not snapshotting and not starting the next session. Last status: {last}")
        time.sleep(poll)
