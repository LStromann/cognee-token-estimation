# Design

**Goal:** tokens saved by Cognee compared with Claude Code native memory, in a realistic setup with CLAUDE.md, skills and MCP tools.

- **Arms:** `baseline` (native memory, CLAUDE.md, skills and mock MCPs) and `cognee` (the same plus Cognee). This is the only difference.
- **Runtime:** headless Claude Code with an API key, `--output-format stream-json`, a pinned CLI version, and models taken from config.
- **Isolation:** each arm gets its own `CLAUDE_CONFIG_DIR`, `--strict-mcp-config` and `--settings` file. Mock MCP state is restored before every run.
- **Warm-up:** identical scripted sessions per topic and arm, run with `warmup_model`. Afterwards everything is snapshotted: workspace, config dir, mock state and Cognee dataset.
- **Eval:** restore the snapshot, then run the task in a fresh session (`--resume` only within multi-turn tasks). Arm order is interleaved.
- **Tokens:** exact, via one local proxy on one port. Cognee also uses Claude, so there is one tokenizer. Claude's and Cognee's tokens are kept in separate buckets. The Cognee context and tool definitions inside Claude's input are attributed per request, and nothing is added to the context for measurement.
- **Memory check:** after warm-up, verify that the baseline actually has native memory.
- **Analysis:** paired deltas (cognee − baseline) per model, topic and type, with bootstrap CIs. Savings count only where both arms pass.
