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
pip install -e .
make validate          # 150 tasks must match the sizing plan; exits non-zero on a mismatch
make pilot-dry         # no API key: fake LLM, synthetic report at results/dry-run-synthetic/report.md
make fixtures          # regenerate Fernhill JSON and task YAML from fixtures/story.py
```

Real runs need Claude Code, Cognee, and a key:

```bash
export ANTHROPIC_API_KEY=...          # Claude Code and Cognee's Claude calls
export OPENAI_API_KEY=...             # secondary judge only; omit and those rows record secondary_error
# set cognee.plugin_root in config/experiment.yaml first (see below)
make warmup            # per topic and arm; waits for cognify before the next session and before snapshot
make check-memory      # baseline must have native memory (CLAUDE.md or memory files)
make pilot             # 5 tasks per topic, spread across types, 2 reps
make run               # 150 tasks x 2 arms x 3 reps, for every model in config
make analyze
```

Other agent models: `python -m harness.run --phase eval --models claude-opus-5-5,claude-sonnet-5-5` or edit `models:`. The judge model and the warm-up model stay fixed, so grading and memory do not move with the agent model. The report splits savings and accuracy per model.

`make pilot-dry` is the offline path. Its report is labelled synthetic. The stand-in agent uses a fixed call pattern so the decomposition is non-zero. Those numbers are not Cognee savings.

## Setup

Install once:

- Python 3.10+.
- This repo: `pip install -e .` (and `pytest` if you will run the tests).
- Claude Code CLI on `PATH` (`claude`). Real runs use `bypassPermissions`. Use a container or VM.
- Cognee with local embeddings: `pip install 'cognee[fastembed]'`. The first fastembed run downloads `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions).
- `uv` so `uvx cognee-mcp@latest` can start the MCP server (`config/arms/cognee.yaml`).
- The Cognee Claude Code plugin, from the public repo [topoteretes/cognee-integrations](https://github.com/topoteretes/cognee-integrations):

  ```bash
  claude plugin marketplace add topoteretes/cognee-integrations
  claude plugin install cognee-memory@cognee
  ```

  Then set **`cognee.plugin_root`** in `config/experiment.yaml` to the absolute directory that contains `scripts/hook_runner.py` (the `integrations/claude-code` tree of that plugin). That is the one manual path. `CLAUDE_PLUGIN_ROOT` is set for plugin-managed hooks, not for the `settings.json` hooks this harness writes, so the commands substitute `{plugin_root}`. A real run exits until that directory exists. `make pilot-dry` does not need it.

Hook commands are the plugin's published `hooks.json`, wrapped by `harness/hooks/tee_hook.py` so injected `additionalContext` can be attributed. Nothing is added to the prompt for measurement. `cognee.hook_log.path` stays empty: the plugin log records event names, not the injected passage. If a future plugin build stores that passage, set `hook_log.path` and `text_field` and the wrapper turns off.

Cognee's Claude traffic is tagged `source=cognee` by pointing **Cognee processes** at `http://127.0.0.1:8787/cognee`. The Python Anthropic adapter does not pass `LLM_ENDPOINT` into the SDK; it reads `ANTHROPIC_BASE_URL`. The harness sets that on the Cognee MCP server and prefixes it on each hook command, so a local server booted from SessionStart can inherit it. Claude Code itself stays on the unprefixed proxy. Leave `COGNEE_LLM_OBSERVER=false` (already in `proxy_env`). Do not also set `ANTHROPIC_BASE_URL` in `~/.cognee/.env`; a dotenv that overrides the hook prefix would mix Cognee tokens into `source=claude` or send them off-proxy. Whether the plugin rewrites the URL from its dotenv was not verified against every plugin release.

Dataset reset, cognify, status, snapshot, and restore go through `python -m harness.cognee_ctl`. The real backend calls `cognee-cli forget`, `cognee-cli cognify`, and `cognee-cli datasets status`. There is no export API: snapshot and restore copy `SYSTEM_ROOT_DIRECTORY` and `DATA_ROOT_DIRECTORY`. After every warm-up session, and again before snapshot, the harness polls until status is `completed` or `idle`. Snapshot exits 3 while status is `running`.

The coding topic clones `https://github.com/jd/tenacity.git` at `32ac68f0941319c0d2f4fb927f96e4ee29bb46c6` and copies `coding_overlay/tidepool_sync` on top. Hidden tests grade that overlay. Questions about tenacity are about that commit. Dry-run skips the clone and uses `fixtures/coding_offline`.

`server_cmd` is intentionally unset. The plugin starts its local API from the SessionStart hook (default `http://localhost:8011`) unless you set `COGNEE_MANAGED_ENDPOINT=true`. This repo does not guess a uvicorn module path.

## What you still set by hand

| Slot | Where | Why |
|---|---|---|
| `cognee.plugin_root` | `config/experiment.yaml` | Absolute plugin directory containing `scripts/`. Empty until you install the plugin. |
| `ANTHROPIC_API_KEY` | environment | Real Claude Code and Cognee LLM calls. |
| `OPENAI_API_KEY` | environment | Secondary judge. Unset means `secondary_error`, not a disagreement flag. |
| `secondary_judge.model` | config | Default `gpt-4.1-mini`. Change the model if you want a different cross-check. |
| `LLM_MODEL` | `cognee.proxy_env` | Default `anthropic/claude-sonnet-5-5`. Use an id your installed LiteLLM build accepts. |
| Claude Code version | `claude.expected_version` | Optional pin. The runner warns on mismatch. |

## Design choices to review

- **Tenacity plus a Fernhill overlay.** Coding stays in the headline formula. The library is pinned, unmodified, Apache-2.0. Bugs live in `coding_overlay/tidepool_sync`, which hidden tests grade. `tasks/coding/solutions/` is the dry-run stand-in for a correct patch. The grader never copies it. Real agents edit the overlay in the workspace.
- **Pilot is stratified by type**, so five tasks per topic include a code fix and an action. It is not the first ids in sort order.
- **`make validate` fails** when a topic/type count does not match `sizing`, or when gold, rubrics, checks, hops, or hidden tests are missing.
- **Cognee routing assumes the plugin's local server inherits the hook process environment.** If it sanitises the environment, Cognee's calls miss `/cognee` and are counted as Claude or not counted. Confirm on a real plugin install.
- **Both the plugin hooks and `uvx cognee-mcp` are on** in the cognee arm. That matches "MCP and/or hooks", and it can inject twice and add two sets of tool definitions. Turn one off if you want a single channel.
- **Tool prefixes** are `mcp__cognee__` and `mcp__cognee-memory__`.
- **Secondary disagreements are reported**, including task, model, arm, rep, and both reasons. They do not automatically fail the pair. In the dry-run, `cd-qa-001`, `po-recall-001`, and `mt-recall-001` append `[[review]]` so the sample report has flags. Those are the pilot's first judged task in each topic. The marker is not a property of the gold.
- **Graph wait** sits between warm-up sessions and again before snapshot. Partial memory is not restored into eval.
- **File-backend snapshot** (dry-run) and the real `cognee-cli` path both copy the system and data roots.

## Caveats
- Claude Code keys memory by absolute path, so each arm uses a fixed working directory and runs inside an arm are sequential. Parallelise with containers.
- Runs use `bypassPermissions`, so use a container or VM.
- Variance is real. Set the number of repetitions from the pilot.

## Layout
```
config/  docs/  env/ (CLAUDE.md, skills)  mcp_mocks/  fixtures/  tasks/  warmup/
harness/ (runner, proxy, hook wrapper, graders)  analysis/  results/
```
