# Design

**Goal:** tokens saved by Cognee compared with Claude Code native memory, in a realistic setup with CLAUDE.md, skills and MCP tools.

- **Arms:** `baseline` (native memory, CLAUDE.md, skills and mock MCPs) and `cognee` (the same plus Cognee). This is the only difference.
- **Runtime:** headless Claude Code with an API key, `--output-format stream-json`, a pinned CLI version, and models taken from config.
- **Isolation:** each arm gets its own `CLAUDE_CONFIG_DIR`, `--strict-mcp-config` and `--settings` file. Mock MCP state is restored before every run.
- **Warm-up:** identical scripted sessions per topic and arm, run with `warmup_model`. Afterwards everything is snapshotted: workspace, config dir, mock state and Cognee dataset.
- **Graph sync:** after each Cognee warm-up session, and again before snapshot, the harness kicks cognify and polls `status_cmd` until the status is `completed` or `idle`. `running` and `error` are never ready. A timeout or an error stops the run. `snapshot` also exits 3 while a cognify is still running, so a partial graph is not saved and does not leak into the next session.
- **Eval:** restore the snapshot, then run the task in a fresh session (`--resume` only within multi-turn tasks). Arm order is interleaved. Coding tasks (hidden tests against the pinned tenacity checkout plus the Tidepool overlay) are in the same matrix as project_ops and meetings.
- **Accuracy:** an LLM judge (`judge_model`, fixed) grades `llm_judge` tasks. A secondary judge from another family (`secondary_judge`, default OpenAI `gpt-4.1-mini`) grades the same answer. The report lists tasks where the two successful verdicts differ so the gold can be reviewed. Disagreement does not drop the pair by itself. State checks and hidden tests are deterministic.
- **Tokens:** exact, via one local proxy on one port. Cognee also uses Claude, so there is one tokenizer. Claude's and Cognee's tokens are kept in separate buckets. The Cognee context and tool definitions inside Claude's input are attributed per request, and nothing is added to the context for measurement.
- **Models:** `--models a,b` (or `models:` in the config) repeats the matrix per agent model. The judge model and the warm-up model stay fixed. The report breaks token savings and accuracy out per model.
- **Memory check:** after warm-up, verify that the baseline actually has native memory.
- **Analysis:** paired deltas (cognee − baseline) per model, topic and type, with bootstrap CIs. Coding is inside the model-level headline, not a side table. Savings count only where both arms pass.
