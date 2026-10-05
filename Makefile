# Constitutional Rules:
# 1. Declare .PHONY individually above each target
# 2. Preserve explicit dependency creation targets (e.g., .local/bin/uv)
#    - File sentinels prevent unnecessary rebuilds
#    - Always create if missing, never rely on implicit behavior
#    - Ensures idempotent builds and clear dependency tracking
# 3. Declare dependency targets BELOW their use, not above
#    - Keeps primary targets at the top for visibility
#    - Pushes implementation details and sentinels to the bottom
#    - Easier to read: use first, then see how it works
# 4. Sentinels must be real files created by their actions
#    - Never add fake marker files (.uv-synced, .build-done, etc.)
#    - Use actual outputs: uv.lock from uv sync, compiled binaries, etc.
#    - Real files ensure Make's timestamp logic is accurate
# 5. No redundant wrapper targets
#    - If a target only depends on a file with no action (@true), use the file directly
#    - Example: don't use "install: uv.lock \n @true", depend on uv.lock instead
#    - Every target must do work or provide user convenience
# 6. No unnecessary targets
#    - Every target must be either primary (user-facing) or supporting (used by others)
#    - If a target is never called, it is dead code and should be removed
#    - Keeps Makefile lean and focused on actual workflow
# 7. Use order-only prerequisites (|) for setup tasks
#    - Use regular dependencies (space) when file changes should trigger rebuild
#    - Use order-only (|) when file just needs to exist first, not affect timestamps
#    - Example: uv.lock depends on pyproject.toml (rebuild if changed), needs uv (order only)
# 8. Only canonical targets in the Makefile
#    - Include primary targets (server, main test suite, clean)
#    - Exclude exploratory/debugging tools (manual curl tests, ad-hoc scripts)
#    - Users can still run exploratory commands manually (uv run, curl, etc.)
#    - Makefile is the canonical workflow, not a command palette

.PHONY: server
server: uv.lock
	uv run python -m server.llm_server

.PHONY: test-sli
test-sli: uv.lock
	uv run python -m unittest server.tests.test_sli -v

.PHONY: test
test: uv.lock
	uv pip install coverage
	uv run coverage run -m unittest discover -s server/tests -p "test_*.py" -v
	uv run coverage report -m
	@echo "Coverage report: htmlcov/index.html"

.PHONY: server-quantized
server-quantized: uv.lock
	uv pip install bitsandbytes
	QUANTIZE=true uv run python -m server.llm_server

.PHONY: clean
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -delete
	rm -rf .venv venv htmlcov .coverage

uv.lock: pyproject.toml | $(HOME)/.local/bin/uv
	uv sync

$(HOME)/.local/bin/uv:
	pip install uv
	pip install --user transformers torch flask flask-cors
