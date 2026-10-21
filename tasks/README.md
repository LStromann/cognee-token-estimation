# Task format
One YAML file per task in `tasks/<topic>/`. Fields:

```yaml
id: po-xsrc-001          # unique; pilot uses the first N ids per topic
topic: project_ops       # coding | project_ops | meetings
type: cross_source       # recall | cross_source | temporal | action | codebase_qa | code_fix | multi_turn | control
hops: 3                  # number of sources needed (1-3)
needs: [memory, mcp]     # any of: memory, mcp, skill, code
turns:                   # >1 turn = multi-turn session via --resume
  - "prompt"
gold: "reference answer incl. sources"
grader:
  kind: llm_judge        # llm_judge | contains | state_check | tests
  rubric: "Pass if ..."
```
Grader variants:
- `contains`: `values: ["4", "jitter"]`. All values must appear in the final answer.
- `state_check`: `checks: [{server: linear, collection: issues, where: {title_contains: "retry", assignee: priya}, created_in_run: true}]`
- `tests`: `hidden_tests: tasks/coding/hidden/<id>` (copied to `<workspace>/tests/hidden` after the agent finishes) and `command: "pytest -q tests/hidden"`.

Files named `*TEMPLATE*` are examples and are skipped by the runner.
