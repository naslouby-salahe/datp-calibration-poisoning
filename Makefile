# DATP — Device-Aware Threshold Personalization
# Canonical build/run targets. All commands assume venv is active.
# See README.md for the repository workflow overview.

SHELL := /bin/bash

# ---------------------------------------------------------------------------
# Console log capture — every top-level `make` invocation is logged to
# outputs/console_logs/datp_<target>_<YYYY-MM-DD_HH-MM-SS>.log automatically.
# Mirrors CONSOLE_LOGS_DIR in src/datp/artifacts/constants.py.
# ---------------------------------------------------------------------------
_CONSOLE_LOG_DIR := outputs/console_logs

ifndef _DATP_LOGGED
# ═══════════════════════════════════════════════════════════════════════════
# Outer wrapper — re-invokes make under tee for automatic console capture.
# Both stdout and stderr are captured. Console still prints live via tee.
# Set _DATP_LOGGED=1 in the environment to bypass logging if needed.
# ═══════════════════════════════════════════════════════════════════════════

_empty :=
_space := $(_empty) $(_empty)
_log_targets := $(or $(MAKECMDGOALS),help)
_log_sanitized := $(subst $(_space),_,$(strip $(subst /,-,$(subst :,-,$(_log_targets)))))
_log_ts := $(shell date '+%Y-%m-%d_%H-%M-%S')
_log_file := $(_CONSOLE_LOG_DIR)/$(_log_ts)__datp__$(_log_sanitized).log

.PHONY: _datp_logged_run
_datp_logged_run:
	@mkdir -p "$(_CONSOLE_LOG_DIR)"
	@_DATP_LOGGED=1 $(MAKE) --no-print-directory $(or $(MAKECMDGOALS),help) 2>&1 | tee "$(_log_file)"; exit $${PIPESTATUS[0]}

ifeq ($(MAKECMDGOALS),)
  .DEFAULT_GOAL := _datp_logged_run
else
  _first_goal := $(firstword $(MAKECMDGOALS))
  _rest_goals := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  .PHONY: $(_first_goal)
  $(_first_goal): _datp_logged_run ;
  ifneq ($(_rest_goals),)
    .PHONY: $(_rest_goals)
    $(_rest_goals):
	@:
  endif
endif

else
# ═══════════════════════════════════════════════════════════════════════════
# Inner make — actual recipes (reached via _DATP_LOGGED=1 from wrapper)
# ═══════════════════════════════════════════════════════════════════════════

.DEFAULT_GOAL := help

PYTHON      := .venv/bin/python
PYTEST      := $(PYTHON) -m pytest
DATP        := $(PYTHON) -m datp.app.cli
OUTPUTS_DIR := outputs

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
.PHONY: help
help:  ## Show this help message
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-30s\033[0m %s\n", $$1, $$2}'

# ═══════════════════════════════════════════════════════════════════════════
# Testing
# ═══════════════════════════════════════════════════════════════════════════
.PHONY: test test-unit test-integration test-e2e

test:  ## Run full test suite (unit + integration + e2e)
	$(PYTEST) tests/ --tb=short -q

test-unit:  ## Run unit tests only
	$(PYTEST) tests/unit/ --tb=short -q

test-integration:  ## Run integration tests only
	$(PYTEST) tests/integration/ --tb=short -q

test-e2e:  ## Run end-to-end tests (tiny real-data subsets)
	$(PYTEST) tests/e2e/ --tb=short -q -v

# ═══════════════════════════════════════════════════════════════════════════
# Type checking / linting
# ═══════════════════════════════════════════════════════════════════════════
.PHONY: typecheck lint

typecheck:  ## Run pyright type checking on baselines + evaluation
	@command -v pyright >/dev/null 2>&1 || { echo "pyright not installed — run: pip install pyright"; exit 1; }
	pyright src/datp/experiments/baselines/ src/datp/evaluation/

lint:  ## Run ruff linter (if installed)
	@command -v ruff >/dev/null 2>&1 || { echo "ruff not installed — run: pip install ruff"; exit 1; }
	ruff check src/ tests/

# ═══════════════════════════════════════════════════════════════════════════
# Gate validation
# ═══════════════════════════════════════════════════════════════════════════
.PHONY: gates gate-all gate0 gate1 gate2 gate3-code

gates: gate0 gate1 gate2 gate3-code  ## Run all code-testable gates in order (Gate 0, 1, 2, 3-code)
	@echo "=== DATP Gates: gate0, gate1, gate2, gate3-code complete ==="

gate-all: gates  ## Alias for gates
	@:

gate0:  ## Verify Gate 0 conditions (environment)
	$(PYTEST) tests/unit/core/test_seeds.py tests/unit/federated/test_determinism.py \
		tests/unit/config/test_config_validation.py tests/unit/artifacts/test_artifacts.py \
		tests/integration/diagnostic/test_smoke_env.py \
		--tb=short -q
	$(PYTHON) -c "import datp; datp.check_imports(); print('G0-1: PASS')"

gate1:  ## Verify Gate 1 conditions (data preparation)
	$(PYTEST) tests/integration/data/nbaiot/test_data_nbaiot.py \
		tests/integration/data/ciciot2023/test_data_ciciot.py \
		tests/integration/data/regime_c/test_data_regime_c.py \
		tests/integration/data/test_data_audit.py \
		tests/unit/data/common/test_storage_format.py \
		tests/unit/data/test_manifest.py \
		tests/unit/data/common/test_schema_audit.py \
		--tb=short -q

gate2:  ## Verify Gate 2 conditions (centralized/local baselines)
	$(PYTEST) tests/unit/thresholding/strategies/test_b0_centralized.py \
		tests/unit/thresholding/test_thresholds.py \
		tests/unit/thresholding/strategies/test_threshold_strategies.py \
		tests/unit/statistics/test_statistics.py \
		tests/unit/models/test_model.py \
		--tb=short -q

gate3-code:  ## Verify Gate 3 code-testable conditions
	$(PYTEST) tests/integration/federated/test_fl_simulation.py \
		tests/unit/federated/test_convergence.py \
		tests/unit/thresholding/strategies/test_threshold_strategies.py \
		tests/integration/thresholding/test_baseline_scope.py \
		tests/unit/models/test_cuda_placement.py \
		tests/unit/artifacts/test_results_exist.py \
		tests/unit/artifacts/test_paths.py \
		--tb=short -q

# ═══════════════════════════════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════════════════════════════
.PHONY: config-preview

config-preview:  ## Preview resolved config for B1+Regime A (seed 0)
	$(DATP) config preview --regime=a --baseline=b1 --seed=0

# ═══════════════════════════════════════════════════════════════════════════
# Main experiment runs — per regime
# ═══════════════════════════════════════════════════════════════════════════
.PHONY: run-regime-a run-regime-b run-regime-c run-main-matrix

run-regime-a:  ## Run Regime A: N-BaIoT natural device split (25 cells; est. ~2 h)
	@echo "=== DATP: Regime A (N-BaIoT, B0/B1/B2/B3/B4 × 5 seeds = 25 cells) ==="
	@echo "Prerequisites: gate0, gate1, gate2, and gate3-code must PASS."
	$(DATP) sweep --regime=a --base-dir=$(OUTPUTS_DIR) --data-root=.

run-regime-b:  ## Run Regime B: CICIoT2023 external validation/support (20 cells; est. ~8-10 h)
	@echo "=== DATP: Regime B (CICIoT2023, B0/B1/B2/B4 × 5 seeds = 20 cells) ==="
	$(DATP) sweep --regime=b --base-dir=$(OUTPUTS_DIR) --data-root=.

run-regime-c:  ## Run Regime C: N-BaIoT Dirichlet severity sweep (90 cells; est. ~6-8 h)
	@echo "=== DATP: Regime C (N-BaIoT Dirichlet severity sweep, B1/B2/B4 × 6α × 5 seeds = 90 cells) ==="
	$(DATP) sweep --regime=c --base-dir=$(OUTPUTS_DIR) --data-root=.

run-main-matrix:  ## Run full 135-cell experiment matrix (REAL DATA + GPU; 24 to 72 hours on GPU, hardware-dependent)
	@echo "WARNING: This launches the full 135-cell experiment matrix."
	@echo "Prerequisites: gate0, gate1, gate2, and gate3-code must PASS."
	@echo "Estimated runtime: 24 to 72 hours on GPU, hardware-dependent."
	@read -p "Continue? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	$(DATP) sweep --base-dir=$(OUTPUTS_DIR) --data-root=.

# ═══════════════════════════════════════════════════════════════════════════
# Sweep utilities
# ═══════════════════════════════════════════════════════════════════════════
.PHONY: sweep-dry-run status audit-results poison-stages poison-dry-run run-poison-bounded

sweep-dry-run:  ## Validate sweep matrix without launching runs (est. <1 min)
	$(DATP) sweep --dry-run --base-dir=$(OUTPUTS_DIR) --data-root=.

status:  ## Show experiment completion status (est. <1 min)
	$(DATP) status --base-dir=$(OUTPUTS_DIR)

audit-results:  ## Audit completed result artifacts and write artifacts/audit/ (est. <1 min)
	@echo "=== DATP: Results audit ==="
	$(DATP) audit results --base-dir=$(OUTPUTS_DIR) --data-root=.

poison-stages:  ## List calibration-poisoning stages and gates
	$(DATP) poison stages

poison-dry-run:  ## Enumerate the bounded N-BaIoT poisoning stage without running
	$(DATP) poison dry-run --stage nbaiot_bounded

run-poison-bounded:  ## Run the authorized bounded N-BaIoT calibration-poisoning matrix
	$(DATP) poison run-bounded-sweep --base-dir=$(OUTPUTS_DIR)

# ═══════════════════════════════════════════════════════════════════════════
# Reporting — figures, tables, statistics
# ═══════════════════════════════════════════════════════════════════════════
# All reporting requires completed experiment results in outputs/results/.
.PHONY: build-stats build-figures build-tables docs

build-stats:  ## Compute bootstrap CIs and secondary statistics from sweep results
	@echo "=== Build: Statistical analysis ==="
	$(DATP) report stats --base-dir=$(OUTPUTS_DIR)

build-figures:  ## Generate Figures 1–4 from sweep results
	@echo "=== Build: Figures 1–4 ==="
	$(DATP) report figures --base-dir=$(OUTPUTS_DIR)

build-tables:  ## Generate Tables 3–4 from sweep results
	@echo "=== Build: Tables 3–4 ==="
	$(DATP) report tables --base-dir=$(OUTPUTS_DIR)

docs:  ## Generate all reporting artifacts from sweep results
	@echo "=== Build: All reporting artifacts ==="
	$(DATP) report all --base-dir=$(OUTPUTS_DIR)

# ═══════════════════════════════════════════════════════════════════════════
# Cleanup
# ═══════════════════════════════════════════════════════════════════════════
.PHONY: clean-temp clean-pyc

clean-temp:  ## Remove temporary/aborted run artifacts
	find outputs/ -name "*.tmp" -delete 2>/dev/null || true
	find outputs/ -name "ABORTED.txt" -exec echo "Found: {}" \; 2>/dev/null || true
	@echo "Temp files cleaned. ABORTED.txt files listed (not deleted — review first)."

clean-pyc:  ## Remove Python bytecode caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "Python cache files removed."

endif  # _DATP_LOGGED
