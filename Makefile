PY ?= python3
export PY

validate: ; $(PY) -m harness.validate_tasks
capture-schemas: ; @echo "see mcp_mocks/capture_schemas.py --help"
fixtures: ; $(PY) mcp_mocks/build_company.py && $(PY) tasks/build_tasks.py
warmup: ; $(PY) -m harness.run --phase warmup && $(PY) -m harness.check_memory
check-memory: ; $(PY) -m harness.check_memory
pilot: ; $(PY) -m harness.run --phase eval --pilot
run: ; $(PY) -m harness.run --phase eval
analyze: ; $(PY) -m analysis.analyze

# Offline pipeline. No API key. Writes results/dry-run-synthetic/report.md, labelled synthetic.
pilot-dry:
	CTB_DRY_RUN=1 CTB_WORK_DIR=/tmp/ctb-dry-run CTB_RESULT_NAME=dry-run-synthetic \
	  $(PY) -m harness.run --phase warmup --dry-run
	CTB_DRY_RUN=1 CTB_WORK_DIR=/tmp/ctb-dry-run CTB_RESULT_NAME=dry-run-synthetic \
	  $(PY) -m harness.check_memory
	CTB_DRY_RUN=1 CTB_WORK_DIR=/tmp/ctb-dry-run CTB_RESULT_NAME=dry-run-synthetic \
	  $(PY) -m harness.run --phase eval --pilot --dry-run --models claude-opus-5-5,claude-sonnet-5-5
	CTB_RESULT_NAME=dry-run-synthetic $(PY) -m analysis.analyze --runs results/dry-run-synthetic/runs.jsonl

.PHONY: validate capture-schemas fixtures warmup check-memory pilot run analyze pilot-dry
