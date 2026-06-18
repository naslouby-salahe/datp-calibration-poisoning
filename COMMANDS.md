# DATP — Command Reference

## 1. Setup

Use the tracked lockfile for reviewer/reproducibility setup:

```bash
uv sync --locked --extra test
```

```bash
source .venv/bin/activate
```
Activate the virtual environment after setup. Run this first in every shell session.

If `uv` is unavailable, `pip install -e ".[test]"` is a convenience-only fallback that installs the declared test extra but does not enforce `uv.lock`.

---

## 2. Environment checks

```bash
make help
```
List all Makefile targets.

```bash
make config-preview
```
Write `resolved_config.yaml` without training. < 1 s.

```bash
datp config preview --regime=<R> --baseline=<B> --seed=<S> [--alpha=<A>]
```
Preview resolved config for any experiment cell.

```bash
make typecheck
```
Pyright on baselines + evaluation. 5–15 s.

```bash
make lint
```
Ruff on `src/` and `tests/`. < 5 s.

---

## 3. Data preparation

```bash
make gate1
```
Validate partitions, manifests, calibration counts, and storage format. 1–2 min. Needs real data.

---

## 4. Gates And Dry Runs

```bash
make gate0
```
Environment gate: seeds, determinism, config, imports. 30–90 s.

```bash
make gate2
```
Centralized/local gate: B0, thresholds, statistics, model. 10–20 s.

```bash
make gate3-code
```
FL code gate: simulation, convergence, strategies. 2–3 min.

```bash
make gates
```
Run gate0 → gate1 → gate2 → gate3-code in order.

```bash
make sweep-dry-run
```
Validate the 135-cell sweep matrix, launch nothing. < 1 min.

---

## 5. Main experiments

```bash
make run-regime-a
```
Regime A: N-BaIoT natural device split, B0–B4 × 5 seeds (25 cells). ~2 h.

```bash
make run-regime-b
```
Regime B: CICIoT2023 external validation/support, B0/B1/B2/B4 × 5 seeds (20 cells). ~8–10 h.

```bash
make run-regime-c
```
Regime C: N-BaIoT Dirichlet severity sweep, B1/B2/B4 × 6α × 5 seeds (90 cells). ~6–8 h.

```bash
make run-main-matrix
```
Full 135-cell sweep, all regimes (prompts for confirmation). 24 to 72 hours on GPU, hardware-dependent.

B4 uses eligible-client clustering. Regime A follows the config-controlled `b4_regime_a_mode` and `b4_k_regime_a`; Regime B/C select K from the configured candidates.

---

## 6. Calibration Poisoning

```bash
make poison-stages
```
List all calibration-poisoning stages and their gates.

```bash
make poison-dry-run
```
Enumerate the bounded N-BaIoT poisoning stage without running it.

```bash
datp poison preview --stage nbaiot_bounded
```
Print the bounded stage configuration as JSON.

```bash
datp poison run-bounded-sweep --base-dir outputs
```
Run the authorized bounded N-BaIoT calibration-poisoning matrix against existing clean score artifacts and write the bounded-sweep manifest.

```bash
make run-poison-bounded
```
Make wrapper for the bounded poisoning run.

---

## 7. Audit / status

```bash
make status
```
Show complete/missing/aborted counts per regime. < 1 min.

```bash
make audit-results
```
Audit completed results; write all artifacts under `artifacts/audit/`. < 1 min.

---

## 8. Reporting

Reporting reads `outputs/results/`. In a clean checkout, restore the tracked final metrics archive first:

```bash
mkdir -p outputs
unzip -q results/metrics/full_metrics.zip -d outputs
```

This materializes `outputs/results/` from `results/metrics/full_metrics.zip`. This metrics-only clean-checkout path supports `make build-stats` and `make build-tables`.

```bash
make build-stats
```
Bootstrap CIs, Wilcoxon, effect sizes → `outputs/analysis/`.

```bash
make build-figures
```
Figures 1–4 → `outputs/figures/` (PDF + PNG + JSON sidecar). Full figure regeneration requires score artifacts under `outputs/scores/`; if those artifacts are absent, regenerate them through the experiment workflow.

```bash
make build-tables
```
Tables 3–4 → `outputs/tables/`.

```bash
make docs
```
Build all reporting artifacts.

```bash
datp report validate --base-dir=outputs
```
Validate reporting inputs without building figures or tables.

`results/statistics/sensitivity/` contains post hoc threshold-aggregation sensitivity analyses; these are not B1–B4 main baselines and do not change the controlled threshold-policy ladder.

---

## 9. Testing

```bash
make test-unit
```
Run unit tests only.

```bash
make test-integration
```
Run integration tests. Some integration tests require real raw datasets or runtime resources.

```bash
make test-e2e
```
Run end-to-end smoke tests.

```bash
make test
```
Run the full test suite.

---

## 10. Cleanup

```bash
make clean-temp
```
Remove `*.tmp`; list (not delete) any `ABORTED.txt` files. < 1 s.

```bash
make clean-pyc
```
Remove `__pycache__/` and `*.pyc`. < 1 s.

To bypass automatic Make console-log capture for lightweight local checks, prefix any target with `_DATP_LOGGED=1`, for example `_DATP_LOGGED=1 make help`.
