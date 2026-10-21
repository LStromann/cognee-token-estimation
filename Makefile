PY ?= python
validate: ; $(PY) -m harness.validate_tasks
capture-schemas: ; @echo "see mcp_mocks/capture_schemas.py --help"
fixtures: ; $(PY) -m mcp_mocks.generate_fixtures
warmup: ; $(PY) -m harness.run --phase warmup && $(PY) -m harness.check_memory
check-memory: ; $(PY) -m harness.check_memory
pilot: ; $(PY) -m harness.run --phase eval --pilot
run: ; $(PY) -m harness.run --phase eval
analyze: ; $(PY) -m analysis.analyze
.PHONY: validate capture-schemas fixtures warmup check-memory pilot run analyze
