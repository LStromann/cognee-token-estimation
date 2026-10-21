"""Start/stop the token proxy and switch its run context."""
import json, subprocess, sys, time, urllib.request
from harness.config import ROOT


def _base(cfg):
    t = cfg["tokens"]
    return f"http://{t['proxy_host']}:{t['port']}"


def urls(cfg):
    """{proxy} for Claude Code, {proxy_<source>} per route (e.g. {proxy_cognee})."""
    base = _base(cfg)
    return {"proxy": base, **{f"proxy_{r['source']}": base + prefix
                              for prefix, r in (cfg["tokens"].get("routes") or {}).items()}}


def sources(cfg):
    return ["claude"] + [r["source"] for r in (cfg["tokens"].get("routes") or {}).values()]


def start(cfg, out_dir):
    p = subprocess.Popen([sys.executable, "-m", "harness.proxy", "--out", str(out_dir)], cwd=ROOT)
    for _ in range(100):
        try:
            urllib.request.urlopen(_base(cfg) + "/_ctb/health", timeout=1)
            return p
        except Exception:
            time.sleep(0.1)
    p.kill()
    raise SystemExit("token proxy did not start")


def set_context(cfg, **ctx):
    req = urllib.request.Request(_base(cfg) + "/_ctb/context", data=json.dumps(ctx).encode(),
                                 headers={"content-type": "application/json"}, method="POST")
    urllib.request.urlopen(req, timeout=5).read()


def stop(p):
    p.terminate()
    try:
        p.wait(5)
    except subprocess.TimeoutExpired:
        p.kill()
