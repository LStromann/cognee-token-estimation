"""Anthropic- and OpenAI-shaped LLM stub. The token proxy forwards here in --dry-run.

Token counts come from the request body, so the proxy's usage log is deterministic.
Judge requests (the harness prompt contains "Reference answer:") return pass/fail JSON.
A secondary-model request fails when the answer contains [[review]], which is how the
dry-run demonstrates disagreement flags. Nothing here is a Cognee result.
"""
import argparse
import json
import sys
from aiohttp import web

MARKER = "[[review]]"


def _text_from(body):
    chunks = []
    system = body.get("system")
    if isinstance(system, str):
        chunks.append(system)
    for msg in body.get("messages") or []:
        content = msg.get("content")
        if isinstance(content, str):
            chunks.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    chunks.append(block.get("text") or "")
                elif isinstance(block, str):
                    chunks.append(block)
    return "\n".join(chunks)


def _between(text, start, end):
    i = text.find(start)
    if i < 0:
        return ""
    i += len(start)
    j = text.find(end, i)
    return text[i:j if j >= 0 else None].strip()


def _usage(body, profile):
    n = max(8, len(json.dumps(body)) // 8)
    tools = body.get("tools") or []
    n += 7 * len(tools)
    if profile == "resent":
        return {"input_tokens": 0, "output_tokens": 8, "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": n}
    return {"input_tokens": n, "output_tokens": 12, "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0}


def _judge(text, model):
    gold = _between(text, "Reference answer:", "Rubric:")
    answer = _between(text, "<answer>", "</answer>")
    passed = bool(gold) and (gold in answer or answer in gold)
    if not gold:
        passed = bool(answer.strip())
    reason = "synthetic judge: answer contains the reference"
    if "gpt-" in (model or "") or (model or "").startswith("gpt") or (model or "").startswith("o"):
        if MARKER in answer:
            passed = False
            reason = "synthetic secondary judge disagrees ([[review]] marker)"
        else:
            reason = "synthetic secondary judge agrees"
    return {"pass": passed, "reason": reason}


def _completion_text(body):
    text = _text_from(body)
    if "Reference answer:" in text and "<answer>" in text:
        verdict = _judge(text, body.get("model") or "")
        return json.dumps(verdict)
    return "synthetic completion"


async def messages(request):
    body = json.loads(await request.read() or b"{}")
    profile = request.headers.get("X-CTB-Usage-Profile", "")
    usage = _usage(body, profile)
    text = _completion_text(body)
    if request.path.endswith("/count_tokens"):
        return web.json_response({"input_tokens": usage["input_tokens"] + usage["cache_read_input_tokens"]})
    return web.json_response({
        "id": "msg_dry_run", "type": "message", "role": "assistant",
        "model": body.get("model") or "dry-run",
        "content": [{"type": "text", "text": text}],
        "stop_reason": "end_turn", "usage": usage,
    })


async def chat(request):
    body = json.loads(await request.read() or b"{}")
    # OpenAI shape: messages only. Reuse the judge detector.
    wrapped = {"model": body.get("model"), "messages": body.get("messages") or []}
    text = _completion_text(wrapped)
    usage = _usage(wrapped, "")
    return web.json_response({
        "id": "chat_dry_run", "model": body.get("model") or "dry-run",
        "choices": [{"message": {"role": "assistant", "content": text}}],
        "usage": {"prompt_tokens": usage["input_tokens"], "completion_tokens": usage["output_tokens"]},
    })


def make_app():
    app = web.Application()
    app.router.add_get("/_ctb/health", lambda _r: web.json_response({"ok": True, "backend": "fake"}))
    app.router.add_post("/v1/messages", messages)
    app.router.add_post("/v1/messages/count_tokens", messages)
    app.router.add_post("/v1/chat/completions", chat)
    return app


def serve_background(host="127.0.0.1", port=0):
    """Start the stub in a subprocess. Returns (process, base_url without /v1)."""
    import socket
    import subprocess
    import time
    import urllib.request
    from harness.config import ROOT
    if not port:
        sock = socket.socket()
        sock.bind((host, 0))
        port = sock.getsockname()[1]
        sock.close()
    proc = subprocess.Popen([sys.executable, "-m", "harness.fake_upstream", "--host", host, "--port", str(port)], cwd=ROOT)
    url = f"http://{host}:{port}"
    for _ in range(100):
        try:
            urllib.request.urlopen(url + "/_ctb/health", timeout=1)
            return proc, url
        except Exception:
            time.sleep(0.05)
    proc.kill()
    raise SystemExit("fake LLM backend did not start")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8788)
    args = ap.parse_args()
    web.run_app(make_app(), host=args.host, port=args.port, print=None)


if __name__ == "__main__":
    main()
