"""Cognee dataset lifecycle for one arm and topic.

    python -m harness.cognee_ctl reset|kick|status|snapshot|restore \\
        --arm cognee --topic meetings --dataset ctb_meetings \\
        --snapshot /path --workspace /path

`status` prints one JSON object: {"status": "idle|running|completed|error", "detail": "..."}.

Backend:
- `file` (CTB_COGNEE_BACKEND=file): a local stand-in used by --dry-run. `kick` stays
  `running` until CTB_COGNEE_READY_DELAY_S elapses, so the harness can prove it waits.
- `cognee` (default): `cognee-cli` forget / cognify / datasets status. Data lives in
  SYSTEM_ROOT_DIRECTORY and DATA_ROOT_DIRECTORY (absolute paths). Snapshot and restore
  copy those two trees. There is no Cognee export API; copying the roots is the
  documented migration path.

`snapshot` refuses to copy while status is `running`, so a partial graph is not saved.
"""
import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import urllib.request

UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def roots(arm, topic):
    base = pathlib.Path(os.environ.get("CTB_WORK_DIR", "/tmp/ctb")) / "cognee" / arm / topic
    system = pathlib.Path(os.environ.get("SYSTEM_ROOT_DIRECTORY") or (base / "system"))
    data = pathlib.Path(os.environ.get("DATA_ROOT_DIRECTORY") or (base / "data"))
    return system, data


def _emit(status, detail=""):
    print(json.dumps({"status": status, "detail": detail}), flush=True)


def _status_path(system):
    return system / "ctb_status.json"


def file_read(system):
    path = _status_path(system)
    if not path.exists():
        return {"status": "idle", "detail": "no dataset yet"}
    doc = json.loads(path.read_text())
    if doc.get("status") == "running" and time.time() >= float(doc.get("ready_at") or 0):
        doc["status"] = "completed"
        doc["detail"] = "file-backend cognify finished"
        path.write_text(json.dumps(doc))
    return {"status": doc.get("status", "idle"), "detail": doc.get("detail", "")}


def file_kick(system, data):
    system.mkdir(parents=True, exist_ok=True)
    data.mkdir(parents=True, exist_ok=True)
    delay = float(os.environ.get("CTB_COGNEE_READY_DELAY_S", "0.25"))
    doc = {"status": "running", "ready_at": time.time() + delay, "detail": "cognify running"}
    _status_path(system).write_text(json.dumps(doc))
    url = os.environ.get("CTB_PROXY_COGNEE") or ""
    if url:
        body = json.dumps({
            "model": os.environ.get("LLM_MODEL", "anthropic/claude-sonnet-5-5"),
            "max_tokens": 16,
            "messages": [{"role": "user", "content": "cognify status check"}],
        }).encode()
        req = urllib.request.Request(
            url.rstrip("/") + "/v1/messages", data=body,
            headers={"content-type": "application/json", "anthropic-version": "2023-06-01",
                     "x-api-key": os.environ.get("LLM_API_KEY") or os.environ.get("ANTHROPIC_API_KEY") or "dry-run"},
        )
        try:
            urllib.request.urlopen(req, timeout=30).read()
        except Exception as exc:  # the graph wait must still be observable if the proxy blips
            print(f"cognee_ctl: ingest ping failed: {exc}", file=sys.stderr)
    _emit("running", "cognify kicked")


def file_reset(system, data):
    shutil.rmtree(system, ignore_errors=True)
    shutil.rmtree(data, ignore_errors=True)
    system.mkdir(parents=True, exist_ok=True)
    data.mkdir(parents=True, exist_ok=True)
    _status_path(system).write_text(json.dumps({"status": "idle", "detail": "reset"}))
    _emit("idle", "reset")


def _cli(args, check=False):
    return subprocess.run(args, capture_output=True, text=True, stdin=subprocess.DEVNULL, check=check)


def _dataset_id(dataset):
    listed = _cli(["cognee-cli", "datasets", "list"])
    if listed.returncode != 0:
        return None, listed.stderr or listed.stdout
    for line in (listed.stdout or "").splitlines():
        if dataset in line:
            match = UUID_RE.search(line)
            if match:
                return match.group(0), ""
    return None, ""


def real_status(dataset):
    if shutil.which("cognee-cli") is None:
        _emit("error", "cognee-cli is not on PATH. Install cognee (pip install 'cognee[fastembed]') or run --dry-run.")
        return
    dataset_id, err = _dataset_id(dataset)
    if err:
        _emit("error", err.strip()[:500])
        return
    if not dataset_id:
        _emit("idle", f"dataset {dataset} does not exist yet")
        return
    proc = _cli(["cognee-cli", "datasets", "status", dataset_id, "--pipelines", "cognify_pipeline"])
    text = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
    upper = text.upper()
    if "ERROR" in upper or "FAILED" in upper:
        _emit("error", text[-500:])
    elif "COMPLETED" in upper:
        _emit("completed", text[-500:])
    elif "STARTED" in upper or "PROCESSING" in upper or "RUNNING" in upper:
        _emit("running", text[-500:])
    elif proc.returncode != 0:
        _emit("error", text[-500:] or f"datasets status exited {proc.returncode}")
    else:
        # No recorded pipeline run. Nothing is in flight.
        _emit("idle", text[-500:] or "no cognify run recorded")


def real_reset(dataset):
    if shutil.which("cognee-cli") is None:
        _emit("error", "cognee-cli is not on PATH")
        raise SystemExit(2)
    proc = _cli(["cognee-cli", "forget", "--dataset", dataset])
    detail = (proc.stdout or proc.stderr or "").strip()
    # A missing dataset is an empty graph, which is what reset wants.
    _emit("idle", detail[-500:] or "forget returned")


def real_kick(dataset):
    if shutil.which("cognee-cli") is None:
        _emit("error", "cognee-cli is not on PATH")
        raise SystemExit(2)
    # cognify may block until the pipeline finishes. The harness still polls status
    # afterwards so a build that returns early cannot be snapshotted half-done.
    proc = _cli(["cognee-cli", "cognify", "--datasets", dataset])
    if proc.returncode != 0:
        _emit("error", (proc.stderr or proc.stdout or "cognify failed")[-500:])
        raise SystemExit(proc.returncode)
    _emit("running", "cognify invoked")


def copy_tree(src, dest):
    if dest.exists():
        shutil.rmtree(dest)
    if src.exists():
        shutil.copytree(src, dest)
    else:
        dest.mkdir(parents=True)


def do_snapshot(system, data, snapshot, current):
    if current["status"] == "running":
        _emit("running", "refusing to snapshot a cognify that is still running")
        raise SystemExit(3)
    dest = pathlib.Path(snapshot) / "cognee"
    dest.mkdir(parents=True, exist_ok=True)
    copy_tree(system, dest / "system")
    copy_tree(data, dest / "data")
    _emit(current["status"], f"snapshotted to {dest}")


def do_restore(system, data, snapshot):
    src = pathlib.Path(snapshot) / "cognee"
    if not src.exists():
        _emit("error", f"no cognee snapshot at {src}")
        raise SystemExit(2)
    copy_tree(src / "system", system)
    copy_tree(src / "data", data)
    _emit("completed", "restored")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["reset", "kick", "status", "snapshot", "restore"])
    ap.add_argument("--arm", default="cognee")
    ap.add_argument("--topic", default="none")
    ap.add_argument("--dataset", default="ctb")
    ap.add_argument("--snapshot", default="")
    ap.add_argument("--workspace", default="")
    args = ap.parse_args()
    system, data = roots(args.arm, args.topic)
    backend = os.environ.get("CTB_COGNEE_BACKEND", "cognee")
    if args.action == "status":
        if backend == "file":
            _emit(**{k: file_read(system)[k] for k in ("status", "detail")})
        else:
            real_status(args.dataset)
        return
    if args.action == "reset":
        file_reset(system, data) if backend == "file" else real_reset(args.dataset)
        return
    if args.action == "kick":
        file_kick(system, data) if backend == "file" else real_kick(args.dataset)
        return
    if backend == "file":
        current = file_read(system)
    elif args.action == "snapshot" and shutil.which("cognee-cli"):
        dataset_id, _err = _dataset_id(args.dataset)
        if not dataset_id:
            current = {"status": "idle", "detail": "no dataset"}
        else:
            proc = _cli(["cognee-cli", "datasets", "status", dataset_id, "--pipelines", "cognify_pipeline"])
            text = (proc.stdout or "").upper()
            if "STARTED" in text or "PROCESSING" in text or "RUNNING" in text:
                current = {"status": "running", "detail": "cli"}
            elif "COMPLETED" in text or not text.strip():
                current = {"status": "completed", "detail": "cli"}
            else:
                current = {"status": "idle", "detail": "cli"}
    elif args.action == "snapshot":
        current = {"status": "error", "detail": "cognee-cli missing"}
    else:
        current = {"status": "completed", "detail": "restore"}
    if args.action == "snapshot":
        if not args.snapshot:
            _emit("error", "snapshot path required")
            raise SystemExit(2)
        do_snapshot(system, data, args.snapshot, current)
        return
    if not args.snapshot:
        _emit("error", "snapshot path required")
        raise SystemExit(2)
    do_restore(system, data, args.snapshot)


if __name__ == "__main__":
    main()
