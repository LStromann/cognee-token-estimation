# Token measurement

There is one proxy, one port and one counting method. Every LLM call goes through `harness/proxy.py`, and token counts are read from the `usage` field of each API response. Nothing is estimated.

## Setup
```
Claude Code  ── ANTHROPIC_BASE_URL=http://127.0.0.1:8787 ─────────▶ source=claude ─┐
Cognee (LLM) ── LLM endpoint      http://127.0.0.1:8787/cognee ──▶ source=cognee ─┴─▶ api.anthropic.com
```
- **Cognee's LLM:** Cognee uses Claude as its LLM, so all tokens come from the same tokenizer and the same usage format. The `/cognee` path prefix tags Cognee's calls; the proxy strips it before forwarding. Cognee's Python Anthropic adapter ignores `LLM_ENDPOINT`. Route it by setting `ANTHROPIC_BASE_URL` to `http://127.0.0.1:8787/cognee` on Cognee's processes only (MCP server env and hook commands). Claude Code keeps the unprefixed URL, so its own calls stay `source=claude`. Embeddings stay on fastembed and are not counted.
- **Embeddings:** these run locally (e.g. fastembed), so they use no API tokens. If you use an API embedding model instead, add a route for it. It is then reported separately and never added to the totals.
- **Run tagging:** the harness tags each request with its run (`POST /_ctb/context`).
- **What is never counted:** the judge and `count_tokens` calls go directly to the API.

## What is measured per run
| Field | Meaning |
|---|---|
| `claude_*` | Claude Code's tokens: input, cache write, cache read, output. This includes subagents and side calls. |
| `cognee_*` | Cognee's own LLM tokens during the task (retrieval) |
| ingestion | Cognee's LLM tokens while building memory at warm-up (`ingest.json`). Amortised per task in the analysis. |
| `cognee_ctx_*` | Cognee context inside Claude's input: `injected` (unique tokens), `first` (first send), `resent` (re-sent on every later request), `carried` (first + resent) |
| `cognee_tooldefs_*` | Cognee's tool definitions, which are sent with every request (fixed overhead) |

## How Cognee's context is found
Nothing is added to the context for measurement.
- **MCP:** tool results whose names start with `mcp__cognee__` (standalone `cognee-mcp`) or `mcp__cognee-memory__` (the Claude plugin).
- **Hooks, option A:** if the Cognee plugin already writes a hook log, set `cognee.hook_log.path` (and `text_field` for jsonl). The harness reads only the lines written during each run.
- **Hooks, option B:** the harness wraps each real Cognee hook command (`cognee.hooks` in the config) in `harness/hooks/tee_hook.py`. The wrapper passes input, output and exit code through unchanged, and logs whatever the hook injected (plain stdout, `additionalContext`, or exit-2 stderr) to `$CTB_COGNEE_HOOK_LOG`. The analysis then finds that exact text in Claude's requests. **The Cognee plugin needs no changes.**
- **Tool definitions:** the exact marginal token count of Cognee's tool definitions in each request, i.e. `count_tokens` with all tools minus `count_tokens` without Cognee's tools.
- **Counting:** each unique block is counted once with `count_tokens` (exact to within a few framing tokens). Request bodies are deleted after counting.

## Decomposition (report)
```
net_delta = exploration_delta + carried_ctx + tooldefs + cognee_internal + ingest_share
```
- `exploration_delta` is what Cognee saved Claude (fewer reads, searches and turns).
- `carried_ctx` and `tooldefs` are what the fuller context cost.
- `carry_multiplier` = carried ÷ injected: how often each Cognee token is billed again.

The report also shows:
- the delta with and without ingestion;
- break-even, i.e. the number of tasks until ingestion pays off;
- a relative-cost view, because cache reads cost far less than fresh input.

## Checks
- Each run's proxy total is compared with Claude Code's own stream-json usage. Differences above 1% are flagged.
- Logged hook texts that can't be found in Claude's requests are flagged.
- **Native-memory check after warm-up** (`make check-memory`). If the baseline has no native memory (CLAUDE.md unchanged and no memory files), the comparison would really be Cognee vs no memory. In that case, fix the warm-up before running, for example by setting `warmup.memory_prompting: explicit`.
