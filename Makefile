# datp-cp canonical workflow.

SHELL := /bin/bash

PYTHON := .venv/bin/python
PYTEST := $(PYTHON) -m pytest
DATP := $(PYTHON) -m datp.app.cli
OUTPUTS_DIR := outputs

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show available targets.
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2}'

.PHONY: check
check: ## Run static checks and tests.
	$(PYTHON) -m ruff check src/ tests/
	$(PYTHON) -m pyright src/
	$(PYTEST) tests/ --tb=short -q

.PHONY: datp-cp-clean
datp-cp-clean: ## Generate clean N-BaIoT artifacts for datp-cp.
	$(DATP) sweep --base-dir=$(OUTPUTS_DIR) --data-root=.

.PHONY: datp-cp-smoke
datp-cp-smoke: ## Run synthetic calibration-poisoning smoke diagnostics.
	$(DATP) poison smoke

.PHONY: datp-cp-dry-run
datp-cp-dry-run: ## Enumerate the N-BaIoT main run plan without execution.
	$(DATP) poison dry-run --stage nbaiot_main

.PHONY: datp-cp-run
datp-cp-run: ## Run the authorized N-BaIoT main calibration-poisoning matrix.
	$(DATP) poison run-bounded-sweep --base-dir=$(OUTPUTS_DIR)

.PHONY: datp-cp-report
datp-cp-report: ## Build datp-cp report artifacts from completed outputs.
	$(DATP) report all --base-dir=$(OUTPUTS_DIR)

.PHONY: status
status: ## Show current experiment artifact status.
	$(DATP) status --base-dir=$(OUTPUTS_DIR)

.PHONY: audit-results
audit-results: ## Audit completed result artifacts.
	$(DATP) audit results --base-dir=$(OUTPUTS_DIR) --data-root=.

.PHONY: clean
clean: ## Remove Python caches and temporary run markers.
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find $(OUTPUTS_DIR) -name "*.tmp" -delete 2>/dev/null || true
