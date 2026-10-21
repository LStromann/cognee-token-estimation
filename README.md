# Cognee token-savings benchmark

Measures how many tokens Cognee saves compared with Claude Code's native memory, using paired runs on realistic agentic tasks.

## Design
- **Arms:**
  - `baseline`: Claude Code with native memory (CLAUDE.md, auto-memory), skills and MCP tools.
  - `cognee`: the same, plus Cognee (MCP and/or hooks). This is the only difference.
- **Tasks:** 150 tasks, 3 topics × 50 (`coding`, `project_ops`, `meetings`). Each task is graded by an LLM judge, a state check on the mocks, or hidden tests. Types and sizing are in [docs/test-plan.md](docs/test-plan.md).
- **Environment:** mock MCP servers (Linear, Granola, Notion, Slack, GitHub) backed by fixed fixtures of a fictional company, so every run is reproducible.
- **Procedure:**
  1. Run scripted warm-up sessions per topic and arm, then snapshot.
  2. For each task × repetition × arm (in random order): restore the snapshot, run the task headless in a fresh session, grade it, and record tokens.
- **Tokens:** exact. All LLM calls (Claude Code and Cognee's own Claude calls) go through one local proxy on `:8787`, which logs the API-reported `usage`. Cognee's calls go via `/cognee` and are kept in a separate bucket. Details are in [docs/token-measurement.md](docs/token-measurement.md).

## Output
`results/<name>/report.md` shows paired deltas (cognee − baseline) per model, topic and task type. Only pairs where both arms pass count toward token deltas. The net delta decomposes as:

```
net_delta = exploration_delta + carried_ctx + tooldefs + cognee_internal + ingest_share
```
| Term | Meaning |
|---|---|
| `exploration_delta` | Change in Claude's own work, i.e. the saving |
| `carried_ctx` | Cognee-injected context, counted every time it is re-sent |
| `tooldefs` | Cognee's tool definitions per request |
| `cognee_internal` | Cognee's own LLM calls |
| `ingest_share` | Warm-up ingestion, amortised per task |

The report also includes:
- success rates;
- median and 95% bootstrap CI;
- a cache-weighted cost view;
- break-even (the number of tasks until ingestion pays off).

Raw data: `runs.jsonl` (one row per run) and `pairs.csv`.

## Run
```bash
pip install -e . && export ANTHROPIC_API_KEY=...
make validate   # tasks vs sizing plan
make warmup     # build memory + snapshots; warns if baseline has no native memory
make pilot      # 15 tasks, 2 reps, to check the harness and variance
make run        # full run
make analyze
```
To test other models, use `--models a,b` or edit `models:` in the config. The judge model and warm-up model stay fixed.

## Setup TODOs (`config/experiment.yaml`)
- **Cognee MCP command** (`config/arms/cognee.yaml`) and **hooks**.
- **Hook attribution:** either set `cognee.hook_log.path` to the plugin's own hook log, or list the hook commands under `cognee.hooks`; the harness then wraps them and logs what they inject. Either way, nothing is added to the context.
- **Cognee proxy settings:** `cognee.proxy_env`, so Cognee uses Claude via the proxy with local embeddings.
- **Cognee lifecycle:** the reset, snapshot and restore commands.
- **Coding repo:** URL and pinned commit.
- **More tasks:** 7 of 150 exist.

## Caveats
- Claude Code keys memory by absolute path, so each arm uses a fixed working directory and runs inside an arm are sequential. Parallelise with containers.
- Runs use `bypassPermissions`, so use a container or VM.
- Variance is real. Set the number of repetitions from the pilot.

## Layout
```
config/  docs/  env/ (CLAUDE.md, skills)  mcp_mocks/  fixtures/  tasks/  warmup/
harness/ (runner, proxy, hook wrapper, graders)  analysis/  results/
```
