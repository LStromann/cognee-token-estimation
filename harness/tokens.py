"""Exact token accounting from the proxy log (one port, one counting method).

Buckets per run (exact, from API responses):
  claude_*   Claude Code's own LLM calls (incl. subagents / side calls)
  cognee_*   Cognee's internal LLM calls (retrieval at eval; ingestion at warm-up)

Attribution (cognee arm): which of Claude's input tokens exist because of Cognee.
  context  = text Cognee injected: results of mcp__cognee__* tools + hook output.
             Hook output is identified by the hook's own log ($CTB_COGNEE_HOOK_LOG), so
             NOTHING is added to the context for measurement.
  tooldefs = Cognee's tool definitions sent with every request (fixed overhead).
  *_first  = tokens when first sent (usually a cache write)
  *_resent = tokens re-sent on every later request (usually cache reads)
Unique blocks are counted with the API's count_tokens endpoint (exact up to a few framing tokens).
"""
import gzip, hashlib, json, pathlib
from collections import defaultdict

KEYS = ["input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"]


def load(log_path):
    p = pathlib.Path(log_path)
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def _gen(r):
    return "count_tokens" not in r["path"] and not r["path"].startswith("/_ctb")


def buckets(records, run_id=None, prefix=None):
    out = defaultdict(lambda: {**{k: 0 for k in KEYS}, "requests": 0, "usage_missing": 0})
    for r in records:
        if (run_id and r["run_id"] != run_id) or (prefix and not r["run_id"].startswith(prefix)) or not _gen(r):
            continue
        b = out[r["source"]]
        b["requests"] += 1
        b["usage_missing"] += int(bool(r.get("usage_missing")))
        for k in KEYS:
            b[k] += r["usage"].get(k, 0) or 0
    for b in out.values():
        b["total"] = sum(b[k] for k in KEYS)
    return dict(out)


def flatten(bk, sources):
    rec = {}
    for s in sources:
        b = bk.get(s, {})
        for k in KEYS + ["total", "requests", "usage_missing"]:
            rec[f"{s}_{k}"] = b.get(k, 0)
    return rec


def _sha(x):
    return hashlib.sha1((x if isinstance(x, str) else json.dumps(x, sort_keys=True)).encode()).hexdigest()


class TokenCounter:
    """count_tokens with a persistent cache. Talks to the API directly, never via the proxy."""

    def __init__(self, cache_path, base_url):
        import anthropic
        self.client = anthropic.Anthropic(base_url=base_url)
        self.path = pathlib.Path(cache_path)
        self.cache = json.loads(self.path.read_text()) if self.path.exists() else {}

    def _count(self, model, text, tools=None):
        kw = {"tools": tools} if tools else {}
        return self.client.messages.count_tokens(
            model=model, messages=[{"role": "user", "content": text}], **kw).input_tokens

    def _cached(self, key, fn):
        if key not in self.cache:
            self.cache[key] = fn()
            self.path.write_text(json.dumps(self.cache))
        return self.cache[key]

    def tokens(self, model, text):
        overhead = self._cached(f"{model}:__overhead__", lambda: self._count(model, "x") - 1)
        return self._cached(f"{model}:{_sha(text)}", lambda: max(0, self._count(model, text) - overhead))

    def tool_tokens(self, model, all_tools, subset_names):
        """Exact marginal tokens of `subset_names` within this tool list."""
        rest = [t for t in all_tools if t.get("name") not in subset_names]
        key = f"{model}:tools:{_sha(all_tools)}"
        return self._cached(key, lambda: max(0, self._count(model, "x", all_tools) -
                                             (self._count(model, "x", rest) if rest else self._count(model, "x"))))


def _text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    return json.dumps(content, ensure_ascii=False)


def load_hook_log(path, text_field="text", offset=0):
    """Injected texts from a hook log (wrapper jsonl or the plugin's own log), from byte `offset` on."""
    texts = []
    p = pathlib.Path(path)
    if not p.exists():
        return texts
    with open(p, "rb") as fh:
        fh.seek(offset)
        lines = fh.read().decode("utf-8", "replace").splitlines()
    for line in lines:
        if not line.strip():
            continue
        t = line.strip()
        if text_field:
            try:
                t = json.loads(line).get(text_field) or ""
            except (json.JSONDecodeError, AttributeError):
                pass
        t = t.strip() if isinstance(t, str) else ""
        if t and t not in texts:
            texts.append(t)
    return texts


def cognee_attribution(records, run_id, out_dir, tcfg, counter, hook_texts=()):
    prefix = tcfg["cognee_tool_prefix"]
    reqs = sorted((r for r in records if r["run_id"] == run_id and r["source"] == "claude"
                   and r.get("body_file") and _gen(r)), key=lambda r: r["n"])
    seen, ctx_first, ctx_resent, n_carry, per_req = {}, 0, 0, 0, []
    tool_first, tool_resent, tool_seen_once = 0, 0, False
    unmatched_hooks = set(hook_texts)
    for r in reqs:
        body = json.loads(gzip.open(out_dir / r["body_file"]).read())
        model = r.get("model") or body.get("model")
        names, blocks, haystack = {}, {}, []
        system = body.get("system")
        haystack.append(system if isinstance(system, str) else _text(system or []))
        for msg in body.get("messages", []):
            content = msg.get("content")
            content = [{"type": "text", "text": content}] if isinstance(content, str) else (content or [])
            for b in content:
                t = b.get("type")
                if t == "tool_use":
                    names[b["id"]] = b.get("name", "")
                elif t == "tool_result":
                    if names.get(b.get("tool_use_id"), "").startswith(prefix):
                        blocks[("tool", b["tool_use_id"])] = _text(b.get("content"))
                    else:
                        haystack.append(_text(b.get("content")))
                elif t == "text":
                    haystack.append(b.get("text", ""))
        hay = "\n".join(haystack)
        for h in hook_texts:                       # hook output, matched verbatim
            if h in hay:
                blocks[("hook", _sha(h))] = h
                unmatched_hooks.discard(h)
        carried = 0
        for k, txt in blocks.items():
            if k not in seen:
                seen[k] = counter.tokens(model, txt)
                ctx_first += seen[k]
            else:
                ctx_resent += seen[k]
            carried += seen[k]
        n_carry += int(bool(blocks))
        # Cognee tool definitions in this request (fixed overhead)
        tools = body.get("tools") or []
        cnames = {t.get("name") for t in tools if str(t.get("name", "")).startswith(prefix)}
        tdef = counter.tool_tokens(model, tools, cnames) if cnames else 0
        if tdef:
            if tool_seen_once:
                tool_resent += tdef
            else:
                tool_first += tdef
                tool_seen_once = True
        per_req.append({"n": r["n"], "cognee_ctx": carried, "cognee_tooldefs": tdef,
                        **{k: r["usage"].get(k, 0) for k in KEYS}})
    return {"cognee_ctx_injected": sum(seen.values()), "cognee_ctx_first": ctx_first,
            "cognee_ctx_resent": ctx_resent, "cognee_ctx_carried": ctx_first + ctx_resent,
            "cognee_ctx_blocks": len(seen), "cognee_ctx_requests": n_carry,
            "cognee_tooldefs_first": tool_first, "cognee_tooldefs_resent": tool_resent,
            "cognee_tooldefs_carried": tool_first + tool_resent,
            "cognee_hook_unmatched": len(unmatched_hooks),
            "claude_requests_with_body": len(reqs)}, per_req
