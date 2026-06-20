# Obsolete Terms Audit

Generated: 2026-06-20. Read-only — no code was modified.
Scope: `src/`, `tests/`, `Makefile`, `CLAUDE.md`, `README.md`, `COMMANDS.md`, `.claude/`, `docs/` (excluding `docs/tickets/`).

Categories:
- **ACTIVE**: Lives in shipped production code (enum values, function names, file names, constants, CLI flags) — must be renamed.
- **COMMENT/DOCSTRING**: In a comment or docstring — should be reworded but lower risk.
- **TEST**: In a test file — must be updated alongside the renamed production symbol.
- **CONFIG**: In YAML/config — must be updated alongside renamed model fields.
- **DOCS**: In markdown docs — must be updated after production renames.
- **AGENT/SKILL**: In .claude/ agent or skill files — update after renames.

---

## 1. Threshold Policy Old Names

### 1.1 `B1_GLOBAL` / `"b1_global"`

| File | Line/Context | Term | Category | What it should become |
|---|---|---|---|---|
| `src/datp/attacks/enums.py` | `ThresholdPolicy.B1_GLOBAL = "b1_global"` | Enum member and string value | ACTIVE | `GLOBAL_MEAN = "global_mean"` |
| `src/datp/attacks/constants.py` | `DEFAULT_POLICIES` tuple contains `ThresholdPolicy.B1_GLOBAL` | Enum member reference | ACTIVE | Update after enum rename |
| `src/datp/config/attack_config.py` | `for_bounded_mvp()` builds with `DEFAULT_POLICIES` | Indirect via constant | ACTIVE (indirect) | Update after enum rename |
| `tests/integration/attacks/test_smoke_harness.py` | Lines 89, 523, 530 — `ThresholdPolicy.B1_GLOBAL` | Enum member reference | TEST | Update after rename |
| `tests/unit/app/cli/test_poison_cli.py` | Lines 86 — asserts `"b1_global"` in CLI output | String assertion on serialized value | TEST | Update after enum rename |
| `src/datp/scoring/loading.py` | Docstring line 1: "B1/B2/B3/B4 share one ScoreProvider per (regime, seed, alpha) cell" | COMMENT/DOCSTRING | Reword to domain terms |
| `src/datp/thresholding/eligibility.py` | Comment: "tau_global = (1/K_elig)×Στᵢ (B1 formula)" | COMMENT | Reword |
| `src/datp/config/models.py` | Comment line 186: "CV(FPR)[B1, Regime A]" | COMMENT | Reword |
| `src/datp/reporting/figures.py` | Lines 72-73, 133 — `Baseline.B1`, "B1 client-averaged threshold" | ACTIVE + COMMENT | Label string update |
| `src/datp/reporting/build.py` | Many lines — `Baseline.B1`, `StatsField.B1_CV_FPR_REGIME_A_MEAN` | ACTIVE | Update after renames |
| `src/datp/checkpointing/summary.py` | Line 274: `Baseline.B1` | ACTIVE | Update after rename |
| `src/datp/statistics/bootstrap.py` | Docstring: "CV(FPR)[B1] − CV(FPR)[B2]" | COMMENT/DOCSTRING | Reword |
| `src/datp/statistics/enums.py` | `WILCOXON_B1_VS_B2 = "wilcoxon_b1_vs_b2"`, `CLIFFS_DELTA_B1_VS_B2 = "cliffs_delta_b1_vs_b2"`, `B1_CV_FPR_REGIME_A_MEAN = "b1_cv_fpr_regime_a_mean"` | ACTIVE | Rename with domain terms |
| `src/datp/validation/constants.py` | `BLOCKED_RESUME_REGIME_A_COMMAND`, `REGIME_C_SCOPE_NOTE` includes "primary Regime A B1-vs-B2 claim" | ACTIVE (string value) | Reword command and note |
| `src/datp/validation/enums.py` | `B1_NOT_POOLED_PERCENTILE`, `B1_MEAN_NOT_POOLED_PERCENTILE` in `WarningCode` | ACTIVE | Rename without B-code prefix |
| `src/datp/validation/schemas.py` | Docstrings: "Regime A B1-vs-B2 claim", "B1−B2 / B1−B4 deltas" | COMMENT/DOCSTRING | Reword |
| `src/datp/reporting/enums.py` | `B1_VS_B2 = "b1_vs_b2"`, `B1_VS_B4 = "b1_vs_b4"` in `ComparisonLabel` | ACTIVE | Rename with domain terms |
| `src/datp/reporting/constants.py` | `REGIME_C_ALPHA_DISPLAY_ORDER`, `REGIME_C_ALPHA_TICK_LABELS` | ACTIVE | Rename without regime prefix |
| `src/datp/reporting/build.py` | `ComparisonLabel.B1_VS_B2`, `ComparisonLabel.B1_VS_B4`, `StatsField.B1_CV_FPR_REGIME_A_MEAN`, strings "Primary endpoint: Regime A, B1 vs B2" | ACTIVE + COMMENT | Update after renames |
| `.claude/skills/long-run-monitoring-skill.md` | Context banner: `{B1_GLOBAL, B2_PERSONALIZED, B4_CLUSTER}` | AGENT/SKILL | Update to new names |
| `.claude/skills/paper-claim-discipline-skill.md` | Same banner | AGENT/SKILL | Update |
| `.claude/skills/experiment-gate-skill.md` | Same banner | AGENT/SKILL | Update |
| `README.md` | "B1 averages eligible client thresholds", table B1/B2/B3/B4, `make run-regime-a` | DOCS | Update after renames |
| `COMMANDS.md` | "B0/B1/B2/B4 × 5 seeds", "B1/B2/B4 across 6 α levels" | DOCS | Update |

---

### 1.2 `B2_PERSONALIZED` / `"b2_personalized"`

| File | Line/Context | Term | Category | What it should become |
|---|---|---|---|---|
| `src/datp/attacks/enums.py` | `ThresholdPolicy.B2_PERSONALIZED = "b2_personalized"` | Enum member and string value | ACTIVE | `PER_CLIENT = "per_client"` |
| `src/datp/attacks/constants.py` | `DEFAULT_POLICIES` contains `ThresholdPolicy.B2_PERSONALIZED` | ACTIVE | Update after enum rename |
| `tests/integration/attacks/test_smoke_harness.py` | Lines 90, 164, 184, 191, 265, 272, 323, 359, 367, 400, 401, 427, 449, 474, 500, 530, 573, 581 — `ThresholdPolicy.B2_PERSONALIZED` | TEST | Update after rename |
| `tests/unit/app/cli/test_poison_cli.py` | Line 87: asserts `"b2_personalized"` in output | TEST | Update after rename |
| `src/datp/thresholding/eligibility.py` | Line 164: `strategy=Baseline.B2`; line 176: `Baseline.B2` | ACTIVE | Update after rename |
| `src/datp/checkpointing/summary.py` | Lines 173, 275: `Baseline.B2`; comment "B2 CV(FPR), worst-FPR, and coverage advantages" | ACTIVE + COMMENT | Update after rename |
| `src/datp/reporting/enums.py` | `B4_VS_B2 = "b4_vs_b2"` | ACTIVE | Rename |
| `src/datp/reporting/figures.py` | Lines 79-80: `Baseline.B2` | ACTIVE | Update |
| `src/datp/reporting/build.py` | `Baseline.B2`, `ComparisonLabel.B4_VS_B2`, strings "B1 vs B2" | ACTIVE | Update |
| `src/datp/validation/enums.py` | `B2_UTILITY_TRADEOFF` in `WarningCode` | ACTIVE | Rename |
| `src/datp/reporting/constants.py` | Referenced in `REGIME_C_BONFERRONI = "regime_c_bonferroni_b1_vs_b2"` | ACTIVE | Rename |
| `src/datp/statistics/enums.py` | `REGIME_C_BONFERRONI = "regime_c_bonferroni_b1_vs_b2"` | ACTIVE | Rename |

---

### 1.3 `B3` / `B3_FAMILY` / `b3_family`

| File | Line/Context | Term | Category | What it should become |
|---|---|---|---|---|
| `src/datp/thresholding/strategies/b3_family.py` | Filename and entire module | Filename | ACTIVE | `global_family.py` or `family_mean.py` |
| `src/datp/thresholding/strategies/b3_family.py` | Docstring: "B3 — Family-mean threshold (Regime A only)" | COMMENT/DOCSTRING | Reword |
| `src/datp/thresholding/thresholds.py` | `from datp.thresholding.strategies import b3_family as b3_mod` | ACTIVE import | Update after file rename |
| `src/datp/thresholding/thresholds.py` | `if inputs.baseline == Baseline.B3:` | ACTIVE | Update |
| `src/datp/core/enums.py` | `Baseline.B3 = "b3"`; `REGIME_BASELINES[Regime.A]` includes `Baseline.B3`; `CONTROLLED_BASELINES` includes `Baseline.B3` | ACTIVE | Rename `Baseline.B3` or restructure |
| `src/datp/core/enums.py` | `ThresholdSource.B3_FAMILY = "b3"` | ACTIVE | Rename |
| `src/datp/checkpointing/invariants.py` | Lines 159, 163: checks `Baseline.B3`, error message "B3 is invalid outside Regime A" | ACTIVE + COMMENT | Update after rename |
| `src/datp/attacks/guardrails.py` | Lines 88, 93-104: "Policy guardrail (B3 excluded)", "Calibration-poisoning guardrail: policy {policy!r} is B3. B3 is excluded…" | ACTIVE + COMMENT | Update messaging |
| `src/datp/config/models.py` | `quality_gates.b3_dispersion_threshold` field | ACTIVE (config field) | Rename field |
| `src/datp/conf/config.yaml` | `b3_dispersion_threshold: 0.25` | CONFIG | Rename key |
| `src/datp/validation/enums.py` | `B3_TAXONOMY_TOO_COARSE` in `WarningCode` | ACTIVE | Rename |
| `src/datp/thresholding/strategies/__init__.py` | Docstring: "family (B3)" | COMMENT/DOCSTRING | Reword |
| `src/datp/thresholding/__init__.py` | Docstring: "Threshold derivation strategies (B0-B4)" | COMMENT/DOCSTRING | Reword |
| `src/datp/app/cli/checkpoint_protocol.py` | Line 95: `Baseline.B3, Baseline.B4` in tuple; comment line 88: "B1-B4 results" | ACTIVE + COMMENT | Update |
| `tests/integration/thresholding/test_baseline_scope.py` | Lines 49, 66, 83: `test_b3_excluded_regime_c`, `test_b3_excluded_regime_b`, `test_b3_allowed_regime_a` | TEST | Rename tests |
| `tests/unit/thresholding/strategies/test_b0_centralized.py` | Line 346: `test_b0_rejects_regime_c` | TEST | Rename test |
| `README.md` | Table: "B3 | Device-family threshold, Regime A only"; "B3 is a Regime A diagnostic" | DOCS | Update |

---

### 1.4 `B4_CLUSTER` / `"b4_cluster"` / B4 naming

| File | Line/Context | Term | Category | What it should become |
|---|---|---|---|---|
| `src/datp/attacks/enums.py` | `ThresholdPolicy.B4_CLUSTER = "b4_cluster"` | ACTIVE | `CLUSTER_MEAN = "cluster_mean"` |
| `src/datp/attacks/constants.py` | `DEFAULT_POLICIES` contains `ThresholdPolicy.B4_CLUSTER` | ACTIVE | Update after enum rename |
| `src/datp/thresholding/strategies/b4_cluster.py` | Filename | ACTIVE | `cluster_mean.py` |
| `src/datp/thresholding/strategies/b4_cluster.py` | Docstring: "B4 — Cluster-mean threshold" | COMMENT/DOCSTRING | Reword |
| `src/datp/thresholding/strategies/b4_cluster.py` | `k_regime_a: int`, `_select_regime_a_k` function, comments "Regime A k", "Invalid Regime A k", "Regime A: K=k_regime_a fixed" | ACTIVE + COMMENT | Rename parameter/function |
| `src/datp/thresholding/thresholds.py` | `from datp.thresholding.strategies import b4_cluster as b4_mod` | ACTIVE import | Update after rename |
| `src/datp/thresholding/thresholds.py` | `if inputs.baseline == Baseline.B4:` | ACTIVE | Update |
| `src/datp/core/enums.py` | `Baseline.B4 = "b4"`, `ThresholdSource.B4_CLUSTER = "b4"`, `B4RegimeAMode` class | ACTIVE | Rename; `B4RegimeAMode` → `ClusterKSelectionMode` |
| `src/datp/core/enums.py` | `B4_FINGERPRINT_FEATURES`, `THRESHOLD_AGGREGATION_BY_BASELINE[Baseline.B4]`, `BASELINE_THRESHOLD_SOURCE[Baseline.B4]` | ACTIVE | Update after rename |
| `src/datp/config/models.py` | `b4_regime_a_mode: B4RegimeAMode`, `b4_k_regime_a: int`, `b4_k_candidates`, `b4_n_init`, `b4_max_iter`, `b4_random_state` in `ThresholdConfig` | ACTIVE | Rename fields (preserve `b4_*` only if domain-motivated) |
| `src/datp/conf/config.yaml` | `b4_regime_a_mode: fixed`, `b4_k_regime_a: 3`, `b4_k_candidates`, `b4_n_init`, `b4_max_iter`, `b4_random_state` | CONFIG | Rename keys alongside model field renames |
| `src/datp/attacks/b4_recompute.py` | Filename encodes B4 | ACTIVE | `cluster_threshold_recompute.py` |
| `src/datp/attacks/constants.py` | Imports `B4_K, B4_MAX_ITER, B4_N_INIT` from `poison_names` | ACTIVE | Rename constants if B4 prefix dropped |
| `src/datp/artifacts/poison_names.py` | `B4_K = 3`, `B4_N_INIT = 10`, `B4_MAX_ITER = 300` | ACTIVE | Rename or keep if still meaningful |
| `src/datp/config/attack_config.py` | `B4ClusterConfig` class, validator docstrings "B4 k must be 3 for Regime A", "B4 random_state must be 42 for Regime A" | ACTIVE + COMMENT | Rename class; reword messages |
| `src/datp/testsupport/smoke_harness.py` | `from datp.thresholding.strategies.b4_cluster import compute as b4_compute`; `b4_cluster_count` function; comments "B4 cluster-count probe", "B4 Δτ decomposition", "B4 on a calibration dict" | ACTIVE + COMMENT | Update imports and function name |
| `src/datp/validation/enums.py` | `B4_CLUSTER_DIAGNOSTICS_INCOMPLETE`, `B4_SINGLE_CLUSTER` in `WarningCode` | ACTIVE | Rename without B4 prefix |
| `src/datp/validation/constants.py` | `B4_CLUSTER_STABILITY_CSV = "b4_cluster_stability.csv"` | ACTIVE | Rename |
| `src/datp/reporting/enums.py` | `B1_VS_B4 = "b1_vs_b4"`, `B4_VS_B2 = "b4_vs_b2"` | ACTIVE | Rename |
| `src/datp/reporting/build.py` | `ComparisonLabel.B1_VS_B4` | ACTIVE | Update |
| `tests/unit/app/cli/test_poison_cli.py` | Line 88: asserts `"b4_cluster"` in output | TEST | Update after rename |
| `tests/integration/attacks/test_smoke_harness.py` | Line 91: `ThresholdPolicy.B4_CLUSTER`; line 295: `ThresholdPolicy.B4_CLUSTER`; `b4_cluster_count` call line 547, 560 | TEST | Update after renames |
| `tests/integration/attacks/test_bounded_sweep_run.py` | Comment line 32: "B4_CLUSTER's locked K=3 requires eligible_count > k" | COMMENT | Reword |
| `tests/unit/thresholding/strategies/test_threshold_strategies.py` | Imports `b4_cluster as b4`; `k_regime_a=3`; `test_regime_a_k_fixed_3` | TEST + ACTIVE import | Update |
| `tests/unit/thresholding/strategies/test_b4_cluster.py` | Filename | TEST file name | Rename to `test_cluster_mean.py` |

---

## 2. Regime Naming

### 2.1 `Regime` enum and `regime_*` references

| File | Line/Context | Term | Category | What it should become |
|---|---|---|---|---|
| `src/datp/core/enums.py` | `class Regime(enum.StrEnum): A="a", B="b", C="c"` | ACTIVE | Core enum — rework contract must decide whether to remove or rename values |
| `src/datp/core/regime.py` | `enforce_regime` decorator, imports `Regime` | ACTIVE | Tied to `Regime` enum; must be removed or repurposed |
| `src/datp/data/regimes/regime_a.py` | Filename, `prepare_regime_a` function | ACTIVE | Rename file + function |
| `src/datp/data/regimes/regime_b.py` | Filename, `prepare_regime_b` function | ACTIVE | Rename file + function |
| `src/datp/data/regimes/regime_c.py` | Filename, `partition_regime_c` function | ACTIVE | Rename file + function |
| `src/datp/data/regimes/catalog.py` | `dataset_for_regime` function; uses `Regime` | ACTIVE | Update after rename |
| `src/datp/data/regimes/prepare.py` | Dispatch over `Regime`; calls `prepare_regime_a/b/c` | ACTIVE | Update after renames |
| `src/datp/data/paths.py` | `regime_c_prepared_dir` function; literal `"regime_c"` in path; `prepared_root_for_regime` | ACTIVE | Rename function; remove `"regime_c"` literal from path output |
| `src/datp/core/enums.py` | `REGIME_BASELINES`, `STATS_REPORTING_BASELINES` constants | ACTIVE | Rename constants |
| `src/datp/config/models.py` | `regime_c_train_fraction`, `regime_c_cal_fraction` in `DatasetConfig`; `regime_c_alphas`, `regime_c_n_clients` in `ExperimentConfig`; `regime: Regime | None` in `DatpConfig`; `b4_regime_a_mode: B4RegimeAMode` in `ThresholdConfig`; validator comment "must use Regime A" | ACTIVE | Rename fields; update validator |
| `src/datp/conf/config.yaml` | `regime_c_train_fraction`, `regime_c_cal_fraction`, `b4_regime_a_mode`, `b4_k_regime_a`, `regime_c_alphas`, `regime_c_n_clients`; `regime: null` | CONFIG | Rename all keys |
| `src/datp/conf/regime/a.yaml` | Filename `a.yaml`; contains `regime: a` | CONFIG | Rename file |
| `src/datp/conf/regime/b.yaml` | Filename `b.yaml`; contains `regime: b` | CONFIG | Rename file |
| `src/datp/conf/regime/c.yaml` | Filename `c.yaml`; contains `regime: c` | CONFIG | Rename file |
| `src/datp/artifacts/layout.py` | `ArtifactLayout(base_dir, regime: Regime)`; `self.regime.value` in path construction; builds `outputs/<regime>/` | ACTIVE | Regime letter embedded in output paths; must decide if path structure changes |
| `src/datp/checkpointing/enums.py` | `GLOBAL_LOWER_TAIL_TRADEOFF_FROM_REGIME_A = "global_lower_tail_tradeoff_from_regime_a"` | ACTIVE | Rename to domain term |
| `src/datp/checkpointing/invariants.py` | `regime: Regime` fields; "B3 is invalid outside Regime A" error; `context.regime != Regime.A` | ACTIVE + COMMENT | Update after enum rename |
| `src/datp/checkpointing/status.py` | `regime: Regime` field | ACTIVE | Update |
| `src/datp/checkpointing/summary.py` | `regime: Regime`; `PrimaryCheckpointSelectionRule.GLOBAL_LOWER_TAIL_TRADEOFF_FROM_REGIME_A` | ACTIVE | Update |
| `src/datp/app/cli/config.py` | `regime: Regime` CLI option; `--regime=<R>` flag help text | ACTIVE | Update |
| `src/datp/app/cli/sweep.py` | `regime: Regime | None` CLI option; `--regime` flag | ACTIVE | Remove if sweep command is replaced |
| `src/datp/app/cli/status.py` | `regime: Regime` field; prints "Regime A/B/C" | ACTIVE | Update |
| `src/datp/app/cli/checkpoint_protocol.py` | `regime: Regime = typer.Option(...)` args; hard-codes `Regime.A` in lines 186, 189, 207, 210 | ACTIVE | Update |
| `src/datp/experiments/sweep.py` | `REGIME_BASELINES`, `spec.regime` throughout | ACTIVE | Update after rename |
| `src/datp/experiments/console.py` | `_Label.REGIME_ALL = "ALL"`; `regime_display` | ACTIVE | Update |
| `src/datp/federated/simulation.py` | `TrainingCellId(regime=ctx.regime, ...)` | ACTIVE | Update |
| `src/datp/validation/constants.py` | `BLOCKED_RESUME_REGIME_A_COMMAND = "datp sweep --regime=a --resume"`, `DIAGNOSTIC_REGIME_A_COMMAND = "datp diagnostic --regime a --seed 0"`, `REGIME_C_SCOPE_NOTE`, `REGIME_C_ALPHA_AUDIT_CSV`, `REGIME_C_SEVERITY_TREND_CSV` | ACTIVE | Rename constants; update string values |
| `src/datp/validation/enums.py` | `REGIME_C_ALPHA_AUDIT_MISSING`, `REGIME_C_PREPARED_MANIFEST_MISSING` in `WarningCode` | ACTIVE | Rename |
| `src/datp/validation/results.py` | `AuditOutputName.REGIME_C_ALPHA_AUDIT`, `REGIME_C_SEVERITY_TREND` | ACTIVE | Rename |
| `src/datp/statistics/enums.py` | `SECONDARY_REGIME_A = "secondary_regime_a"`, `SECONDARY_REGIME_B = "secondary_regime_b"`, `REGIME_C = "regime_c"`, `REGIME_C_BONFERRONI = "regime_c_bonferroni_b1_vs_b2"`, `B1_CV_FPR_REGIME_A_MEAN = "b1_cv_fpr_regime_a_mean"` | ACTIVE | Rename all |
| `src/datp/statistics/wilcoxon.py` | Docstring: "Secondary for Regime A (n=9 limit); primary for Regime C…" | COMMENT/DOCSTRING | Reword |
| `src/datp/reporting/constants.py` | `REGIME_C_ALPHA_DISPLAY_ORDER`, `REGIME_C_ALPHA_TICK_LABELS` | ACTIVE | Rename |
| `src/datp/reporting/enums.py` | Comment: "Regime C IID comparison and the primary B1-minus-B2" | COMMENT/DOCSTRING | Reword |
| `src/datp/reporting/build.py` | `REGIME_BASELINES`, `Regime.A/B/C`, `StatsField.SECONDARY_REGIME_A/B`, `StatsField.REGIME_C`, `b1_cv_fpr_regime_a_mean`, string "Primary endpoint: Regime A" | ACTIVE | Update throughout |
| `src/datp/reporting/figures.py` | `REGIME_C_ALPHA_DISPLAY_ORDER`, `REGIME_C_ALPHA_TICK_LABELS` | ACTIVE | Update after rename |
| `src/datp/core/metric_enums.py` | `REGIME_C_ALPHAS = "regime_c_alphas"` in `ValidationField` | ACTIVE | Rename |
| `src/datp/thresholding/metrics_serialization.py` | `regime: Regime` field | ACTIVE | Update |
| `src/datp/thresholding/thresholds.py` | `regime: Regime` param; `_derive_b3(args, tau_global, regime)` | ACTIVE | Update |
| `src/datp/thresholding/strategies/b4_cluster.py` | `regime: Regime` param; `@enforce_regime(Regime.A, Regime.B, Regime.C)`; comments "Regime B or C" | ACTIVE | Update |
| `src/datp/thresholding/strategies/b3_family.py` | `@enforce_regime(Regime.A)`; comment "Regime A only" | ACTIVE | Update |
| `src/datp/attacks/bounded_sweep_cell.py` | Docstring: "Orchestrates the real-data bounded matrix on `REGIME_A_NBAIOT`" | COMMENT/DOCSTRING | Reword; remove `REGIME_A_NBAIOT` label |
| `src/datp/attacks/bounded_sweep_run.py` | `from datp.core.enums import Regime`; `regime=Regime.A` call to `load_real_score_collection` | ACTIVE | Update after rename |
| `src/datp/attacks/real_score_loader.py` | Uses `Regime.A` | ACTIVE | Update |
| `src/datp/scoring/loading.py` | Docstring: "(regime, seed, alpha) cell" | COMMENT/DOCSTRING | Reword |
| `tests/unit/app/cli/test_status.py` | `_REGIME_A_CELLS = 25`, `_REGIME_B_CELLS = 20`, `_REGIME_C_CELLS = 90` | TEST | Rename constants |
| `tests/integration/data/regime_c/test_data_regime_c.py` | Imports `datp.data.regimes.regime_c`; calls `partition_regime_c`; path assertions containing `"regime_c"` | TEST | Update after file/function rename |
| `tests/integration/federated/test_fl_simulation.py` | Functions `test_regime_b_smoke`, `test_regime_c_loop`, `test_regime_a_smoke` | TEST | Rename functions |
| `tests/integration/thresholding/test_baseline_scope.py` | `_dummy_regime_a`, `_dummy_regime_ab`; test method names with "regime" | TEST | Update |
| `tests/unit/checkpointing/test_training_protocol.py` | `test_canonical_regime_a_b4_is_fixed_k3`; `b4_k_regime_a`; `b4_regime_a_mode` | TEST | Rename test; update field name refs |
| `tests/unit/thresholding/strategies/test_threshold_strategies.py` | `k_regime_a=3`; `test_regime_a_k_fixed_3` | TEST | Update parameter ref; rename test |
| `tests/unit/core/test_regime.py` | Tests `Regime` enum and `enforce_regime` | TEST | Revise or remove test |
| `Makefile` | `--regime=a`, `--regime=b`, `--regime=c` in `run-regime-*` targets; `config-preview --regime=a` | ACTIVE (Makefile) | Remove targets |
| `COMMANDS.md` | "Regime A: N-BaIoT…", "Regime B: CICIoT2023…", "Regime C: N-BaIoT Dirichlet…"; `--regime=a` in examples | DOCS | Remove/rewrite sections |
| `README.md` | Regime A/B/C descriptions; table with Regime column | DOCS | Rewrite |

---

## 3. Old ExperimentStage Values

### 3.1 All `ExperimentStage` values

| File | Line/Context | Term | Category | What it should become |
|---|---|---|---|---|
| `src/datp/config/stages.py` | `ExperimentStage.COMMON = "common"` | ACTIVE | Remove |
| `src/datp/config/stages.py` | `ExperimentStage.AUDIT_READONLY = "audit_readonly"` | ACTIVE | `FINAL_AUDIT = "final_audit"` |
| `src/datp/config/stages.py` | `ExperimentStage.NBAIOT_SMOKE = "nbaiot_smoke"` | ACTIVE | `SYNTHETIC_SMOKE = "synthetic_smoke"` |
| `src/datp/config/stages.py` | `ExperimentStage.NBAIOT_BOUNDED = "nbaiot_bounded"` | ACTIVE | `NBAIOT_MAIN = "nbaiot_main"` |
| `src/datp/config/stages.py` | `ExperimentStage.NBAIOT_FULL = "nbaiot_full"` | ACTIVE | `NBAIOT_FULL_OPTIONAL = "nbaiot_full_optional"` |
| `src/datp/config/stages.py` | `ExperimentStage.CICIOT2023_STRETCH = "ciciot2023_stretch"` | ACTIVE | `STRETCH_DIAGNOSTIC_ONLY = "stretch_diagnostic_only"` |
| `src/datp/config/stages.py` | `ExperimentStage.PAPER_FIGURES = "paper_figures"` | ACTIVE | Remove |
| `src/datp/app/cli/poison.py` | Default arg `ExperimentStage.NBAIOT_BOUNDED` (lines 48, 64); logic `if stage == ExperimentStage.NBAIOT_BOUNDED:` (line 75); `ExperimentStage.NBAIOT_SMOKE` (line 105); `ExperimentStage.NBAIOT_BOUNDED` (lines 120, 125, 128) | ACTIVE | Update after rename |
| `tests/unit/config/test_stages.py` | Tests all `ExperimentStage` values | TEST | Update after rename |

---

### 3.2 `ExperimentScale` (to be removed)

| File | Line/Context | Term | Category | What it should become |
|---|---|---|---|---|
| `src/datp/experiments/enums.py` | `class ExperimentScale(enum.StrEnum): SMOKE, BOUNDED, FULL, STRETCH` | ACTIVE | Remove per contract |
| `src/datp/config/stages.py` | `from datp.experiments.enums import ExperimentScale`; `scale: ExperimentScale | None` field | ACTIVE | Remove |
| `src/datp/config/attack_config.py` | `from datp.experiments.enums import ExperimentScale`; `scale: ExperimentScale` field; validators checking `ExperimentScale.BOUNDED/FULL` | ACTIVE | Remove or replace |
| `src/datp/attacks/bounded_sweep_manifest.py` | `from datp.experiments.enums import ExperimentScale`; `scale: ExperimentScale = ExperimentScale.BOUNDED` | ACTIVE | Remove |
| `src/datp/attacks/bounded_sweep_matrix.py` | `from datp.experiments.enums import ExperimentScale`; checks `config.scale != ExperimentScale.BOUNDED/FULL` | ACTIVE | Remove |
| `src/datp/attacks/bounded_sweep_run.py` | (indirect via config) | ACTIVE | Remove |
| `src/datp/attacks/guardrails.py` | `from datp.experiments.enums import ExperimentScale`; `scale: ExperimentScale` param; checks `ExperimentScale.FULL/BOUNDED` | ACTIVE | Remove |
| `src/datp/attacks/run_logger.py` | `scale: ExperimentScale` field | ACTIVE | Remove |
| `src/datp/attacks/run_manifest.py` | `scale: ExperimentScale` field | ACTIVE | Remove |
| `src/datp/artifacts/poison_layout.py` | `from datp.experiments.enums import ExperimentScale`; `cell.scale.value` in path construction | ACTIVE | Remove |
| `tests/integration/attacks/test_smoke_harness.py` | `from datp.experiments.enums import ExperimentScale`; `scale=ExperimentScale.SMOKE` (lines 366, 400, 580) | TEST | Update |

---

## 4. Old Source Strategy Names

| File | Line/Context | Term | Category | What it should become |
|---|---|---|---|---|
| `src/datp/attacks/enums.py` | `PoisoningSourceStrategy.TARGETED_REMOVAL_LOW_SCORE = "targeted_removal_low_score"` | ACTIVE | `LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY = "low_score_targeted_removal_diagnostic_only"` |
| `src/datp/attacks/enums.py` | `DIAGNOSTIC_ONLY_SOURCES` frozenset contains `TARGETED_REMOVAL_LOW_SCORE` | ACTIVE | Update after rename |
| `src/datp/attacks/enums.py` | `objective_for_source` match: `PoisoningSourceStrategy.TARGETED_REMOVAL_LOW_SCORE` | ACTIVE | Update after rename |
| `src/datp/attacks/reservoir.py` | Line 71: `PoisoningSourceStrategy.TARGETED_REMOVAL_LOW_SCORE` | ACTIVE | Update after rename |
| `src/datp/attacks/source_strategies.py` | Docstring line 9: "TARGETED_REMOVAL_LOW_SCORE — requires explicit allow_diagnostic=True" | COMMENT/DOCSTRING | Reword with new name |

---

## 5. Old Knowledge / Scope Enum Values

### 5.1 `WHITE_BOX` → `WHITE_BOX_DIAGNOSTIC_ONLY`

| File | Line/Context | Term | Category | What it should become |
|---|---|---|---|---|
| `src/datp/attacks/enums.py` | `PoisoningKnowledge.WHITE_BOX = "white_box"` | ACTIVE | `WHITE_BOX_DIAGNOSTIC_ONLY = "white_box_diagnostic_only"` |
| `src/datp/attacks/enums.py` | `DIAGNOSTIC_ONLY_KNOWLEDGE` frozenset contains `WHITE_BOX` | ACTIVE | Update after rename |

### 5.2 `ALL_CLIENTS` → `ALL_CLIENTS_DIAGNOSTIC_ONLY`

| File | Line/Context | Term | Category | What it should become |
|---|---|---|---|---|
| `src/datp/attacks/enums.py` | `PoisoningTargetScope.ALL_CLIENTS = "all_clients"` | ACTIVE | `ALL_CLIENTS_DIAGNOSTIC_ONLY = "all_clients_diagnostic_only"` |
| `src/datp/attacks/enums.py` | `DIAGNOSTIC_ONLY_SCOPES` frozenset contains `ALL_CLIENTS` | ACTIVE | Update after rename |

---

## 6. Old Makefile Targets (must be removed)

| Target | File | Category | Status |
|---|---|---|---|
| `run-regime-a` | Makefile | ACTIVE | Remove |
| `run-regime-b` | Makefile | ACTIVE | Remove |
| `run-regime-c` | Makefile | ACTIVE | Remove |
| `run-main-matrix` | Makefile | ACTIVE | Remove |
| `sweep-dry-run` | Makefile | ACTIVE | Remove |
| `gate0` | Makefile | ACTIVE | Remove |
| `gate1` | Makefile | ACTIVE | Remove |
| `gate2` | Makefile | ACTIVE | Remove |
| `gate3-code` | Makefile | ACTIVE | Remove |
| `gates` | Makefile | ACTIVE | Remove |
| `gate-all` | Makefile | ACTIVE | Remove |
| `config-preview` | Makefile | ACTIVE | Remove |
| `build-stats` | Makefile | ACTIVE | Remove |
| `build-figures` | Makefile | ACTIVE | Remove |
| `build-tables` | Makefile | ACTIVE | Remove |
| `docs` | Makefile | ACTIVE | Remove |
| `test` | Makefile | ACTIVE | Remove |
| `test-unit` | Makefile | ACTIVE | Remove |
| `test-integration` | Makefile | ACTIVE | Remove |
| `test-e2e` | Makefile | ACTIVE | Remove |
| `typecheck` | Makefile | ACTIVE | Remove |
| `typecheck-attacks` | Makefile | ACTIVE | Remove |
| `lint` | Makefile | ACTIVE | Remove |
| `poison-stages` | Makefile | ACTIVE | Remove |
| `poison-dry-run` | Makefile | ACTIVE | Remove |
| `run-poison-bounded` | Makefile | ACTIVE | Remove |
| `clean-temp` | Makefile | ACTIVE | Remove |
| `clean-pyc` | Makefile | ACTIVE | Remove |

### Missing new targets (must be added):

| Target | Status |
|---|---|
| `check` | Missing |
| `datp-cp-clean` | Missing |
| `datp-cp-smoke` | Missing |
| `datp-cp-dry-run` | Missing |
| `datp-cp-run` | Missing |
| `datp-cp-report` | Missing |
| `clean` | Missing |

Note: `help`, `status`, `audit-results` appear to be keepers (no replacement name specified); `COMMANDS.md` and tests reference them.

---

## 7. `for_bounded_mvp` Method Name

| File | Line/Context | Term | Category | What it should become |
|---|---|---|---|---|
| `src/datp/config/attack_config.py` | `@classmethod def for_bounded_mvp(cls) -> "CalibrationPoisoningConfig":` | ACTIVE | `for_bounded_sweep()` or `bounded_sweep_config()` |
| `src/datp/app/cli/poison.py` | Line 76: `CalibrationPoisoningConfig.for_bounded_mvp()` | ACTIVE | Update after rename |
| `src/datp/attacks/bounded_sweep_run.py` | Line 181: `CalibrationPoisoningConfig.for_bounded_mvp()` | ACTIVE | Update after rename |
| `tests/unit/config/test_attack_config.py` | Lines 167-214: multiple `for_bounded_mvp()` calls | TEST | Update |
| `tests/unit/attacks/test_bounded_sweep_matrix.py` | Line 27: `CalibrationPoisoningConfig.for_bounded_mvp()` | TEST | Update |
| `tests/integration/attacks/test_bounded_sweep_run.py` | Line 33: `CalibrationPoisoningConfig.for_bounded_mvp()` | TEST | Update |

---

## 8. Artifact File Names with Obsolete Encoding

| File | Line/Context | Term | Category | What it should become |
|---|---|---|---|---|
| `src/datp/artifacts/poison_names.py` | `ManifestFile.NBAIOT_BOUNDED_SWEEP_MANIFEST = "nbaiot_bounded_sweep_manifest.json"` | ACTIVE | `BOUNDED_SWEEP_MANIFEST = "bounded_sweep_manifest.json"` |
| `src/datp/artifacts/poison_names.py` | `ManifestFile.PAPER_FIGURE_MANIFEST = "paper_figure_manifest.json"` | ACTIVE | `FIGURE_MANIFEST = "figure_manifest.json"` or remove |
| `src/datp/artifacts/poison_layout.py` | `nbaiot_bounded_sweep_manifest()` method; `paper_figure_manifest()` method | ACTIVE | Rename methods after enum rename |
| `tests/unit/artifacts/test_poison_layout.py` | `nbaiot_bounded_sweep_manifest()`; `NBAIOT_BOUNDED_SWEEP_MANIFEST` | TEST | Update |
| `tests/integration/attacks/test_bounded_sweep_run.py` | `write_nbaiot_bounded_sweep_manifest`; assertion `out_path.name == "nbaiot_bounded_sweep_manifest.json"` | TEST | Update |
| `src/datp/app/cli/poison.py` | Docstring line 122: `nbaiot_bounded_sweep_manifest.json` | COMMENT/DOCSTRING | Update |
| `src/datp/attacks/bounded_sweep_manifest.py` | Module docstring lines 3-4 reference the artifact filename | COMMENT/DOCSTRING | Update |
| `src/datp/attacks/bounded_sweep_run.py` | Function name `write_nbaiot_bounded_sweep_manifest`; docstring; function name `run_nbaiot_bounded_sweep` | ACTIVE | Rename to `write_bounded_sweep_manifest`, `run_bounded_sweep` |

---

## 9. CP2 / MVP / Phase Labels in .claude/ Skills

| File | Context | Category | Action |
|---|---|---|---|
| `.claude/skills/long-run-monitoring-skill.md` | CP2 context banner; `{B1_GLOBAL, B2_PERSONALIZED, B4_CLUSTER}` | AGENT/SKILL | Update banner; update policy names |
| `.claude/skills/paper-claim-discipline-skill.md` | Same CP2 banner; `B1_GLOBAL/B2_PERSONALIZED/B4_CLUSTER`; "CP2 do-not-claim" | AGENT/SKILL | Update |
| `.claude/skills/experiment-gate-skill.md` | Same CP2 banner; `{B1_GLOBAL, B2_PERSONALIZED, B4_CLUSTER}` | AGENT/SKILL | Update |
| `.claude/skills/ticket-audit-skill.md` | "For CP2:", "CP2 (active):", `CP2_PROGRESS.md` references | AGENT/SKILL | Update to new contract paths |
| `.claude/skills/human-intervention-gate-skill.md` | "CP2 (active):" | AGENT/SKILL | Update |
| `.claude/skills/ticket-generation-skill.md` | "CP2 note:", "CP2 tickets already exist" | AGENT/SKILL | Update |
| `.claude/skills/ticket-completion-audit-skill.md` | "CP2 (active):" | AGENT/SKILL | Update |
| `.claude/skills/ticket-progress-skill.md` | "CP2 (active):" | AGENT/SKILL | Update |
| `CLAUDE.md` | Entire document uses CP2, B1_GLOBAL/B2_PERSONALIZED/B4_CLUSTER, REGIME_A_NBAIOT, ExperimentStage names, Makefile targets | DOCS | Full update after all code renames |

---

## 10. Safe-to-Ignore Findings

The following matches were found but are archival or intentionally stable:

| File | Term | Reason safe |
|---|---|---|
| `docs/tickets/` (excluded from search) | All CP2/ticket refs | Archival — excluded per audit scope |
| `docs/DATP_CP_Roadmap.md` | `LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY` | This is the *target* name per rework contract — used correctly as the new name |
| `src/datp/attacks/enums.py` `DIAGNOSTIC_ONLY_*` frozensets | `TARGETED_REMOVAL_LOW_SCORE`, `ALL_CLIENTS`, `WHITE_BOX` | These will be updated when the enum members are renamed — they are not independently named |
| `pyproject.toml` | No obsolete terms | Clean |
| `src/datp/artifacts/names.py` | No policy/regime terms | Clean |
| `src/datp/core/seeds.py` | No obsolete terms | Clean |
| `src/datp/core/seed_sequence.py` | No obsolete terms | Clean |
| `src/datp/data/catalog.py` | `DatasetID.NBAIOT`, `DatasetID.CICIOT2023` | Domain-named — not B/Regime coded |
