# datp-cp canonical workflow.

SHELL := /bin/bash

PYTHON := .venv/bin/python
PYTEST := $(PYTHON) -m pytest
DATP := $(PYTHON) -m datp.app.cli
OUTPUTS_DIR := outputs

.DEFAULT_GOAL := help

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

.PHONY: help
help: ## Show available targets.
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-28s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Static checks and tests
# ---------------------------------------------------------------------------

.PHONY: check
check: ## Run ruff, pyright, and the full test suite.
	$(PYTHON) -m ruff check src/ tests/
	$(PYTHON) -m pyright src/
	$(PYTEST) tests/ --tb=short -q

.PHONY: datp-cp-unit-tests
datp-cp-unit-tests: ## Run unit tests only (faster iteration during development).
	$(PYTEST) tests/unit/ --tb=short -q

# ---------------------------------------------------------------------------
# datp-cp workflow — run targets in order
# ---------------------------------------------------------------------------

.PHONY: datp-cp-clean
datp-cp-clean: ## [1] Generate clean N-BaIoT artifacts (scores, thresholds, manifests).
	$(DATP) sweep --base-dir=$(OUTPUTS_DIR) --data-root=.

.PHONY: datp-cp-smoke
datp-cp-smoke: ## [2] Run synthetic smoke invariant tests (must pass before main run).
	$(PYTEST) tests/integration/attacks/test_smoke_harness.py -v --tb=short

.PHONY: datp-cp-smoke-preview
datp-cp-smoke-preview: ## Print the smoke stage config preview (does not run invariant tests).
	$(DATP) poison smoke

.PHONY: datp-cp-dry-run
datp-cp-dry-run: ## [3] Enumerate the N-BaIoT main run plan without execution.
	$(DATP) poison dry-run --stage nbaiot_main

.PHONY: datp-cp-run
datp-cp-run: ## [4] Run the authorized N-BaIoT main calibration-poisoning matrix.
	$(DATP) poison run-bounded-sweep --base-dir=$(OUTPUTS_DIR)

.PHONY: audit-results
audit-results: ## [5] Audit completed result artifacts and manifest provenance.
	$(DATP) audit results --base-dir=$(OUTPUTS_DIR) --data-root=.

.PHONY: status
status: ## Show current experiment artifact status (complete/missing/aborted counts).
	$(DATP) status --base-dir=$(OUTPUTS_DIR)

.PHONY: datp-cp-report
datp-cp-report: ## [6] Build report artifacts (figures, tables, statistics) from completed outputs.
	$(DATP) report all --base-dir=$(OUTPUTS_DIR)

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

.PHONY: clean
clean: ## Remove Python caches and temporary run markers.
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find $(OUTPUTS_DIR) -name "*.tmp" -delete 2>/dev/null || true
