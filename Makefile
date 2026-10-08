# datp-cp canonical workflow.

SHELL := /bin/bash

PYTHON := .venv/bin/python
PYTEST := $(PYTHON) -m pytest
DATP_CLI := $(PYTHON) -m datp.cli
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
check: ## Run ruff (lint + format), pyright, and Semgrep (no tests).
	$(PYTHON) -m ruff check src/ tests/
	$(PYTHON) -m ruff format --check src/ tests/ tests_support/
	$(PYTHON) -m ruff check --select C901 src/datp/
	$(PYTHON) -m pyright src/
	mkdir -p $${TMPDIR:-/tmp}/datp-semgrep/config $${TMPDIR:-/tmp}/datp-semgrep/cache
	XDG_CONFIG_HOME=$${TMPDIR:-/tmp}/datp-semgrep/config XDG_CACHE_HOME=$${TMPDIR:-/tmp}/datp-semgrep/cache SEMGREP_SETTINGS_FILE=$${TMPDIR:-/tmp}/datp-semgrep/settings.yaml SEMGREP_LOG_FILE=$${TMPDIR:-/tmp}/datp-semgrep/semgrep.log semgrep --disable-version-check --no-git-ignore --config semgrep.yml src/datp/

.PHONY: test
test: ## Run unit and integration tests; fails below 90% coverage.
	$(PYTEST) tests/unit tests/integration --cov --tb=short -q

.PHONY: architecture
architecture: ## Run the architecture enforcement suite (local-only; see .gitignore).
	$(PYTEST) tests/architecture --tb=short -q

# ---------------------------------------------------------------------------
# datp-cp workflow — run targets in order
# ---------------------------------------------------------------------------

.PHONY: datp-cp-clean
datp-cp-clean: ## [1] Generate clean N-BaIoT artifacts (scores, thresholds, manifests).
	$(DATP_CLI) baseline

.PHONY: datp-cp-dry-run
datp-cp-dry-run: ## [3] Enumerate the baseline, poisoning and sensitivity grids without execution.
	$(DATP_CLI) plan

.PHONY: datp-cp-run
datp-cp-run: ## [4] Run the authorized N-BaIoT main calibration-poisoning matrix.
	$(DATP_CLI) poison

.PHONY: datp-cp-sensitivity
datp-cp-sensitivity: ## [4b] Run cluster-stability, scale-normalization and distinct-draw sensitivity analyses.
	$(DATP_CLI) sensitivity

.PHONY: status
status: ## Show current experiment artifact status (complete/missing/aborted counts).
	$(DATP_CLI) status

.PHONY: datp-cp-report
datp-cp-report: ## [5] Audit results and package every report output into results/.
	$(DATP_CLI) report

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

.PHONY: clean
clean: ## Remove Python caches and temporary run markers.
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find $(OUTPUTS_DIR) -name "*.tmp" -delete 2>/dev/null || true
