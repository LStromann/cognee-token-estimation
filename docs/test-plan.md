# Test Plan

## Topics
| Topic | Environment | MCP servers mainly used |
|---|---|---|
| `coding` | Real repo at a pinned commit, plus hidden tests | GitHub, Linear, Slack |
| `project_ops` | Fictional company "Fernhill Labs" | Linear, Notion, Slack |
| `meetings` | Same company | Granola, Notion, Slack |

All three topics share one consistent storyline (`fixtures/company_story.md`). The same people, decisions and IDs appear in every tool.

## Task types
| Type | What it tests | Example | Grader | Hops |
|---|---|---|---|---|
| `recall` | Retrieving a single fact learned in earlier sessions, instead of looking it up again | "Who owns the retry spec?" | LLM judge | 1 |
| `cross_source` | Linking facts across tools (meeting → ticket → spec → PR). This is where a graph should help most. | "Is PR #91 consistent with the latest decision?" | LLM judge | 2–3 |
| `temporal` | Knowing which version of a fact is current, with stale docs as traps | "Current Webhooks GA date?" (the Notion page is stale) | LLM judge | 2 |
| `action` | Doing something correctly using context: creating or updating items | "Create a ticket for the spec owner…" | State check on mock DB | 1–2 |
| `codebase_qa` | Codebase understanding without re-exploring | "Where is retry logic configured, and what calls it?" | LLM judge vs gold | 1–3 |
| `code_fix` | A real code change informed by context from tickets and meetings | "Fix LIN-155 duplicates" | Hidden tests | 2–3 |
| `multi_turn` | Follow-ups within one session (`--resume`) | Question → draft Slack message | LLM judge on the final turn | 2 |
| `control` | Tasks that need no memory. Measures Cognee's pure overhead. | "Summarise the Onboarding Checklist" | LLM judge | 1 |

Within each type, balance hops (1/2/3) as evenly as the type allows.

## Sizing
| Type | coding | project_ops | meetings | Total |
|---|---|---|---|---|
| recall | 5 | 10 | 10 | 25 |
| cross_source | 8 | 12 | 12 | 32 |
| temporal | 4 | 8 | 10 | 22 |
| action | – | 8 | 6 | 14 |
| codebase_qa | 15 | – | – | 15 |
| code_fix | 10 | – | – | 10 |
| multi_turn | 3 | 6 | 6 | 15 |
| control | 5 | 6 | 6 | 17 |
| **Total** | **50** | **50** | **50** | **150** |

**Run count:** tasks × arms × repetitions × models.
- Full run: 150 × 2 × 3 = **900 runs per model**.
- Pilot: 15 × 2 × 2 = **60 runs**.
- Warm-up: 3 topics × 2 arms × about 8–12 sessions, done once. Snapshots are reused across models.

**Budget:** take the average tokens per run from the pilot and multiply by the run count.

**Repetitions:** after the pilot, choose the number of repetitions so the bootstrap CI half-width on the median paired delta is below about 5%.

## Grading
- **LLM judge:** uses `judge_model` (fixed across all runs) with the task's `gold` and `rubric`, and returns pass/fail plus a reason.
- **State check:** inspects mock MCP state after the run. Only items created during the run count.
- **Tests:** hidden tests are copied into the workspace *after* the agent finishes, then run.
- Token savings count only on pairs where both arms pass. Success rate is reported separately.

## Metrics per run
Exact token counts come from the proxy; see `token-measurement.md` for details.
- **Claude tokens:** input, cache creation, cache read and output.
- **Cognee internal tokens:** LLM and embedding calls, kept separate from Claude's.
- **Cognee context carried:** the Cognee context inside Claude's input (injected, first send, re-sends).
- **Ingestion tokens per topic:** measured at warm-up, then amortised per task and used for break-even.
- **Other metrics:**
  - tool calls by group;
  - mock MCP response sizes;
  - turns and wall time;
  - success;
  - MCP connection status at init.

## Writing tasks (checklist)
- Every non-control task must depend on something that appears **only** in the warm-up history or across multiple tools.
- Temporal tasks need a stale source (a Notion page or ticket) that contradicts a newer meeting or Slack message.
- The gold answer cites its sources. The rubric says what is required and what counts as a fail.
- Don't name the answer's source in the prompt for `cross_source` and `temporal` tasks.
