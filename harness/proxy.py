"""Token-accounting reverse proxy: ONE port, ONE way of counting (usage from API responses).

  Claude Code:  ANTHROPIC_BASE_URL=http://127.0.0.1:8787          -> source=claude
  Cognee LLM:   endpoint http://127.0.0.1:8787/cognee             -> source=cognee (prefix stripped)
Routes (path prefix -> source, optional upstream) come from config `tokens.routes`.
Every response's `usage` is parsed (Anthropic format; OpenAI also supported)
and appended to <out>/proxy.jsonl, tagged with the current run context
(set by the harness via POST /_ctb/context). For phase=eval, claude request bodies are saved
(gzip) so injected Cognee context can be attributed per request.

  python -m harness.proxy --out results/<name>
"""
import argparse, asyncio, gzip, itertools, json, pathlib, time

from aiohttp import ClientSession, ClientTimeout, web

from harness.config import load_config

HOP = {"host", "content-length", "transfer-encoding", "connection", "keep-alive",
       "accept-encoding", "content-encoding"}
CTX = {"run_id": "unassigned", "phase": "none", "arm": "none", "topic": "none"}
COUNTER = itertools.count(1)


def _num(d):
    return {k: v for k, v in (d or {}).items() if isinstance(v, (int, float)) and not isinstance(v, bool)}


def normalize_openai(u):
    cached = (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0) or 0
    prompt = u.get("prompt_tokens", u.get("input_tokens", 0)) or 0
    return {"input_tokens": prompt - cached, "cache_read_input_tokens": cached,
            "output_tokens": u.get("completion_tokens", 0) or 0}


def parse_usage(raw, ctype):
    """Return (model, usage) normalised to Anthropic keys."""
    model, usage = None, {}
    if "event-stream" in ctype:
        for line in raw.decode("utf-8", "replace").splitlines():
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if not data or data == "[DONE]":
                continue
            try:
                ev = json.loads(data)
            except json.JSONDecodeError:
                continue
            if ev.get("type") == "message_start":                     # Anthropic
                model = ev["message"].get("model")
                usage.update(_num(ev["message"].get("usage")))
            elif ev.get("type") == "message_delta":                   # Anthropic (cumulative)
                usage.update({k: v for k, v in _num(ev.get("usage")).items() if v is not None})
            elif ev.get("usage"):                                     # OpenAI stream chunk
                usage.update(normalize_openai(ev["usage"]))
                model = ev.get("model", model)
    else:
        try:
            j = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return model, usage
        model = j.get("model") if isinstance(j, dict) else None
        u = (j.get("usage") or {}) if isinstance(j, dict) else {}
        if "input_tokens" in u and "prompt_tokens" not in u:
            usage = _num(u)
        elif u:
            usage = normalize_openai(u)
    return model, usage


def route(path, routes, default_upstream):
    for prefix, r in sorted(routes.items(), key=lambda kv: -len(kv[0])):
        if path == prefix or path.startswith(prefix + "/"):
            return r["source"], r.get("upstream", default_upstream), path[len(prefix):] or "/"
    return "claude", default_upstream, path


def make_handler(routes, default_upstream, session, log_path, out_dir):
    async def handler(request):
        if request.path == "/_ctb/health":
            return web.json_response({"ok": True, "ctx": CTX})
        if request.path == "/_ctb/context":
            CTX.update(await request.json())
            return web.json_response(CTX)
        source, upstream, path = route(request.path, routes, default_upstream)
        qs = ("?" + request.query_string) if request.query_string else ""
        body = await request.read()
        headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP}
        headers["accept-encoding"] = "identity"
        n, ctx, t0 = next(COUNTER), dict(CTX), time.time()
        async with session.request(request.method, upstream.rstrip("/") + path + qs,
                                   headers=headers, data=body) as up:
            resp = web.StreamResponse(status=up.status,
                                      headers={k: v for k, v in up.headers.items() if k.lower() not in HOP})
            await resp.prepare(request)
            chunks = []
            async for chunk in up.content.iter_any():
                chunks.append(chunk)
                await resp.write(chunk)
            model, usage = parse_usage(b"".join(chunks), up.headers.get("content-type", ""))
            rec = {"n": n, "ts": t0, "latency_s": round(time.time() - t0, 3), "source": source, **ctx,
                   "method": request.method, "path": path, "status": up.status,
                   "model": model, "usage": usage, "usage_missing": not usage}
            if source == "claude" and ctx["phase"] == "eval" and path.endswith("/messages"):
                rel = pathlib.Path("requests") / ctx["run_id"] / f"{n:06d}.json.gz"
                (out_dir / rel).parent.mkdir(parents=True, exist_ok=True)
                with gzip.open(out_dir / rel, "wb") as fh:
                    fh.write(body)
                rec["body_file"] = str(rel)
            with open(log_path, "a") as fh:      # logged BEFORE eof -> client never finishes first
                fh.write(json.dumps(rec) + "\n")
            await resp.write_eof()
            return resp
    return handler


async def serve(cfg, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    t = cfg["tokens"]
    session = ClientSession(timeout=ClientTimeout(total=None, sock_connect=30, sock_read=900))
    app = web.Application(client_max_size=1024 ** 3)
    app.router.add_route("*", "/{tail:.*}", make_handler(t.get("routes") or {}, t["upstream"], session,
                                                         out_dir / "proxy.jsonl", out_dir))
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    await web.TCPSite(runner, t["proxy_host"], t["port"]).start()
    print(f"proxy {t['proxy_host']}:{t['port']} -> {t['upstream']}  routes={list((t.get('routes') or {}))}", flush=True)
    await asyncio.Event().wait()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--config", default="config/experiment.yaml")
    a = ap.parse_args()
    asyncio.run(serve(load_config(a.config), pathlib.Path(a.out)))


if __name__ == "__main__":
    main()
