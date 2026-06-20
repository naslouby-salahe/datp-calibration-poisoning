# Code Inventory

Generated: 2026-06-20. Read-only audit — no code was modified.

---

## Source modules (src/datp/)

### src/datp/__init__.py
Purpose: Package root with `check_imports()`.
Key functions: `check_imports`.
Obsolete naming: None observed.
Needed by datp-cp: Yes.

### src/datp/app/cli/
CLI entry point package.

**__main__.py** — CLI main entry.
**__init__.py** — Registers all CLI sub-apps.

**config.py**
Purpose: `datp config preview` command.
Uses: `Regime` enum in CLI option and function signature. CLI flag is `--regime=<R>` (e.g. `--regime=a`).
Obsolete: CLI flag `--regime` is active and present in COMMANDS.md/Makefile.

**sweep.py**
Purpose: `datp sweep` command.
Uses: `Regime` enum in `regime: Regime | None` option. CLI `--regime` flag active.
Obsolete: `--regime` flag on `sweep` is one of the targets for removal per rework contract.

**poison.py**
Purpose: Calibration-poisoning CLI (`preview`, `dry-run`, `smoke`, `run-bounded-sweep`, `stages`).
Uses:
- `ExperimentStage.NBAIOT_BOUNDED` — in default args and logic (lines 48, 64, 75, 120, 125, 128).
- `ExperimentStage.NBAIOT_SMOKE` — referenced (line 105).
- `CalibrationPoisoningConfig.for_bounded_mvp()` — called directly (line 76).
- `write_nbaiot_bounded_sweep_manifest` — CLI delegates to it.
- CLI command name `"run-bounded-sweep"` is domain-named (OK).
Obsolete: `for_bounded_mvp()` method name contains `mvp`.

**status.py**
Purpose: `datp status` command. Uses `Regime` enum, prints "Regime A/B/C" labels.
Obsolete: Regime naming active.

**audit.py**
Purpose: `datp audit results` command.
Obsolete: Not observed.

**report.py**
Purpose: `datp report` sub-app.
Obsolete: Not audited deeply; no active term hits in search.

**checkpoint_protocol.py**
Purpose: Checkpoint-protocol CLI.
Uses: `Regime.A` directly (lines 186, 189, 207, 210). Comments reference "Regime A", "B1-B4".
Obsolete: Regime naming; B1/B2/B3/B4 shorthand in comment line 88.

---

### src/datp/artifacts/
**constants.py** — Re-exports `MANIFEST_FILE`, `SCALER_FILE`. Clean.

**existence.py** — Artifact existence checks. No obsolete terms observed.

**io.py** — Artifact IO. No obsolete terms observed.

**layout.py**
Purpose: `ArtifactLayout` — canonical path builder per regime.
Key class: `ArtifactLayout(base_dir, regime)`.
Uses: `Regime` enum pervasively — `self.regime.value` used to build paths.
Path tokens: `outputs/<regime>/...` — literal regime letter (a/b/c) embedded in output directory paths.
Obsolete: `Regime` import and usage is pervasive; regime-labeled subdirectory structure is active.

**lifecycle.py** — Run lifecycle markers. No obsolete terms.

**markers.py** — Artifact markers. No obsolete terms.

**names.py** — `ArtifactFile`, `PathToken`, etc. enums. No obsolete terms.

**poison_layout.py**
Purpose: `PoisonLayout` — canonical path builder for poisoning outputs.
Key class: `PoisonLayout(base_dir)`, `CellId`, `CellPaths`.
Key method: `nbaiot_bounded_sweep_manifest()` — returns path to `nbaiot_bounded_sweep_manifest.json`.
Output root: `outputs/conference_calibration_poisoning/`.
Obsolete: `nbaiot_bounded_sweep_manifest()` method name encodes dataset name; `NBAIOT_BOUNDED_SWEEP_MANIFEST` artifact filename; `paper_figure_manifest()` method; `PAPER_FIGURE_MANIFEST` artifact filename.

**poison_names.py**
Purpose: Canonical artifact filenames and scalar constants.
Key enums/constants:
- `ManifestFile.NBAIOT_BOUNDED_SWEEP_MANIFEST = "nbaiot_bounded_sweep_manifest.json"`
- `ManifestFile.PAPER_FIGURE_MANIFEST = "paper_figure_manifest.json"`
- `CALIBRATION_POISONING_OUTPUT_ROOT = "conference_calibration_poisoning"`
- `N_MIN`, `TAIL_MASS`, `MATERIALITY_FACTOR`, `THRESHOLD_QUANTILE`, `TRIM_FRACTION_PRIMARY`, `TRIM_FRACTION_APPENDIX`, `B4_K`, `B4_N_INIT`, `B4_MAX_ITER`.
Obsolete: `NBAIOT_BOUNDED_SWEEP_MANIFEST` encodes dataset; `PAPER_FIGURE_MANIFEST` is phase-coded.

---

### src/datp/attacks/

**bounded_sweep_cell.py**
Purpose: Runs one bounded sweep cell on real N-BaIoT data.
Docstring references `REGIME_A_NBAIOT` (line 3).
Obsolete: Docstring uses `REGIME_A_NBAIOT` label.

**bounded_sweep_manifest.py**
Purpose: Typed Pydantic schema for the bounded sweep manifest artifact.
Key class: `BoundedSweepManifest`, `BoundedSweepResultRow`.
Docstring references: `NBAIOT_BOUNDED_SWEEP_MANIFEST`, `nbaiot_bounded_sweep_manifest.json`, `PoisonLayout.nbaiot_bounded_sweep_manifest()`.
Obsolete: Module-level docstring and field references use the artifact filename which is dataset-coded.

**bounded_sweep_matrix.py**
Purpose: Enumerates cells for bounded/full sweep.
Key functions: `enumerate_bounded_sweep_matrix`, `enumerate_full_sweep_matrix`.
Uses `ExperimentScale.BOUNDED`, `ExperimentScale.FULL`.

**bounded_sweep_run.py**
Purpose: End-to-end bounded run orchestrator + manifest writer.
Key functions: `run_nbaiot_bounded_sweep`, `write_nbaiot_bounded_sweep_manifest`.
Uses: `Regime.A` (line 35), `CalibrationPoisoningConfig.for_bounded_mvp()` (line 181).
Obsolete: `for_bounded_mvp()` method name; `write_nbaiot_bounded_sweep_manifest` function name encodes dataset; references to `REGIME_A_NBAIOT` in docstring.

**cell_runner.py** — Core injection/recompute primitives. No obsolete names observed.

**compromise_patterns.py** — Compromise pattern logic. No obsolete names observed.

**constants.py**
Purpose: Attack-protocol constants.
Key constants: `BOUNDED_SWEEP_FRACTIONS`, `DEFAULT_POLICIES`, `BOUNDED_SWEEP_SOURCES`, `TRAINING_SEEDS`, `POISONING_SEEDS`, `ANALYSIS_SEEDS`, `COMPROMISE_PATTERN_SEED`, `B4_RANDOM_STATE`.
`DEFAULT_POLICIES` contains `ThresholdPolicy.B1_GLOBAL`, `ThresholdPolicy.B2_PERSONALIZED`, `ThresholdPolicy.B4_CLUSTER`.
Obsolete: The three default policy enum values have B-coded names.

**defenses.py** — Defense implementations. No obsolete names observed.

**diagnostics.py** — Blast radius, spillover. No obsolete names.

**enums.py**
Purpose: Attack-protocol enums.
Key enums:
- `ThresholdPolicy`: `B1_GLOBAL = "b1_global"`, `B2_PERSONALIZED = "b2_personalized"`, `B4_CLUSTER = "b4_cluster"`.
- `AttackerObjective`: `THRESHOLD_RAISE`, `THRESHOLD_LOWER` (OK — domain-named).
- `PoisoningSourceStrategy`: `RANDOM_BENIGN`, `HIGH_SCORE_BENIGN`, `LOW_SCORE_BENIGN`, `TARGETED_REMOVAL_LOW_SCORE`.
- `CalibrationInjectionRule`: `REPLACE_FIXED_BUDGET` (OK).
- `PoisoningKnowledge`: `GRAY_BOX_SCORE_ACCESS`, `WHITE_BOX`.
- `PoisoningTargetScope`: `SINGLE_CLIENT`, `MULTI_CLIENT`, `ALL_CLIENTS`.
- `PoisoningDefense`: `NONE`, `TRIMMED_CALIBRATION` (OK).
- `ReservoirStatus`: `FEASIBLE`, `INFEASIBLE_DEGENERATE_TAIL` (OK).
- `DIAGNOSTIC_ONLY_SOURCES`: contains `TARGETED_REMOVAL_LOW_SCORE`.
- `DIAGNOSTIC_ONLY_SCOPES`: contains `ALL_CLIENTS`.
- `DIAGNOSTIC_ONLY_KNOWLEDGE`: contains `WHITE_BOX`.
Obsolete: `B1_GLOBAL`, `B2_PERSONALIZED`, `B4_CLUSTER` policy names; `TARGETED_REMOVAL_LOW_SCORE` source name; `WHITE_BOX` knowledge name; `ALL_CLIENTS` scope name.

**guardrails.py**
Purpose: Attack-protocol guardrails.
Comments reference "B3 excluded", "B3 is not part of default policy enum".
Uses `ExperimentScale`.
Obsolete: B3 references in comments.

**inference.py** — Score inference. No obsolete names.

**injector.py** — Calibration injection. No obsolete names.

**metric_engine.py** — Fleet FPR, AUROC, mu_flag. No obsolete names.

**real_score_loader.py** — Loads real N-BaIoT scores. Uses `Regime.A` internally.

**reservoir.py**
Purpose: Reservoir sampling. References `TARGETED_REMOVAL_LOW_SCORE` (line 71).
Obsolete: Source strategy name in logic.

**run_logger.py** — Run logging. Uses `ExperimentScale`.

**run_manifest.py** — Per-cell run manifest. Uses `ExperimentScale`.

**score_containers.py** — Score containers. No obsolete names.

**source_strategies.py**
Docstring references `TARGETED_REMOVAL_LOW_SCORE` (line 9).
Obsolete: Source strategy name in docstring.

**threshold_recompute.py** — Threshold recomputation. No obsolete names.

**types.py** — Attack type aliases. No obsolete names.

**b4_recompute.py** — B4 threshold recomputation. No explicit obsolete names.

---

### src/datp/checkpointing/

**enums.py**
Key enum: `PrimaryCheckpointSelectionRule.GLOBAL_LOWER_TAIL_TRADEOFF_FROM_REGIME_A = "global_lower_tail_tradeoff_from_regime_a"`.
Obsolete: Enum value name and string contain `_FROM_REGIME_A`.

**invariants.py**
Uses `Regime`, `Baseline.B3`, checks `context.regime != Regime.A` (line 159).
Comments reference "Regime A", "B3 is invalid outside Regime A".
Obsolete: Regime/B3 references in comments.

**status.py** — Uses `Regime` field in dataclass.

**summary.py**
Comments reference "B2 CV(FPR)", "B1", "Regime A".
Uses `Baseline.B1`, `Baseline.B2`.
`PrimaryCheckpointSelectionRule.GLOBAL_LOWER_TAIL_TRADEOFF_FROM_REGIME_A` used (line 198).
Obsolete: Regime-named enum value.

---

### src/datp/config/

**attack_config.py**
Key class: `CalibrationPoisoningConfig`.
Key method: `for_bounded_mvp()` — class method (line 253).
Docstring for `B4ClusterConfig` references "Regime A" (line 94, 110, 117).
Uses `ExperimentScale.BOUNDED`, `ExperimentScale.FULL`.
Obsolete: `for_bounded_mvp()` method name; "Regime A" in docstrings.

**compose.py** — Config composition. Uses `REGIME_BASELINES`.

**models.py**
`DatpConfig` uses `Regime`, `Baseline` fields.
Comment line 186: "Preliminary single-seed GO threshold for CV(FPR)[B1, Regime A]."
`B4RegimeAMode` enum from `core.enums`.
Validator `_validate_checkpoint_selection` checks `regime != Regime.A` (line 117).
Obsolete: "Regime A" in comments; `B4RegimeAMode` name.

**stages.py**
Key enum: `ExperimentStage`:
- `COMMON = "common"` — to be removed.
- `AUDIT_READONLY = "audit_readonly"` — rename to `FINAL_AUDIT`.
- `NBAIOT_SMOKE = "nbaiot_smoke"` — rename to `SYNTHETIC_SMOKE`.
- `NBAIOT_BOUNDED = "nbaiot_bounded"` — rename to `NBAIOT_MAIN`.
- `NBAIOT_FULL = "nbaiot_full"` — rename to `NBAIOT_FULL_OPTIONAL`.
- `CICIOT2023_STRETCH = "ciciot2023_stretch"` — rename to `STRETCH_DIAGNOSTIC_ONLY`.
- `PAPER_FIGURES = "paper_figures"` — to be removed.
Uses `ExperimentScale` (import from experiments.enums).
Obsolete: All `ExperimentStage` values.

---

### src/datp/conf/
**config.yaml** — Hydra config. Contains `regime_c_train_fraction`, `regime_c_cal_fraction`, `b4_regime_a_mode`, `b4_k_regime_a`, `regime_c_alphas`, `regime_c_n_clients`. Regime-coded config field names are in YAML and mirror Python model field names.
**regime/a.yaml**, **regime/b.yaml**, **regime/c.yaml** — Per-regime Hydra overrides. Files are named a/b/c (regime letters).
Obsolete: Field names `regime_c_*`, `b4_regime_a_mode`, `b4_k_regime_a` and directory names `regime/a.yaml` etc.

---

### src/datp/core/

**enums.py**
Key enums: `Regime` (A/B/C), `Baseline` (B0-B4), `B4RegimeAMode`, `ThresholdSource` (B0_POOLED, B1_SHARED, B2_PER_CLIENT, B3_FAMILY, B4_CLUSTER), `ScoringStage`, etc.
Constants: `REGIME_BASELINES`, `STATS_REPORTING_BASELINES`, `CONTROLLED_BASELINES`.
Function `policy_for_baseline` maps `Baseline.B1 → ThresholdPolicy.B1_GLOBAL`, etc.
`B4RegimeAMode.FIXED/SILHOUETTE` — contains "Regime A" in class name.
Obsolete: `ThresholdSource` values encode B-codes; `B4RegimeAMode` class name; `REGIME_BASELINES` constant name; `Baseline.B3` member; `Regime` enum; `ThresholdSource.B1_SHARED`, `B2_PER_CLIENT`, `B3_FAMILY`, `B4_CLUSTER` values.

**regime.py**
Purpose: `enforce_regime` decorator. Enforces Regime enum restriction on functions.
Core coupling to `Regime` enum.

**logging.py**, **errors.py**, **identity.py**, **provenance.py**, **seed_sequence.py**, **seeds.py**, **tracking.py**, **types.py**, **metric_enums.py** — Supporting modules. `metric_enums.py` has `REGIME_C_ALPHAS = "regime_c_alphas"` field name.

**device.py** — Device resolution. No obsolete names.

---

### src/datp/data/

**catalog.py** — Dataset catalog. `DatasetID.NBAIOT`, `DatasetID.CICIOT2023` — domain-named.

**contracts.py** — Data contracts/types. No obsolete names.

**manifests.py** — Manifest creation. No obsolete names.

**paths.py**
Function `regime_c_prepared_dir` — embeds "regime_c" in path construction.
Function `prepared_root_for_regime` — uses `Regime` enum.
Obsolete: "regime_c" literal in path function and output path.

**regimes/__init__.py**, **regimes/catalog.py**, **regimes/prepare.py**
Purpose: Regime-level data preparation dispatch.
All files embed `Regime.A/B/C` logic.

**regimes/regime_a.py** — `prepare_regime_a` function; uses `@enforce_regime(Regime.A)`.
**regimes/regime_b.py** — `prepare_regime_b` function; uses `@enforce_regime(Regime.B)`.
**regimes/regime_c.py** — `partition_regime_c` function; writes `regime_c/` subdirectory paths.
Obsolete: All three files are named `regime_a.py`, `regime_b.py`, `regime_c.py`; function names embed regime labels; output paths contain literal `"regime_c"`.

**datasets/nbaiot/**, **datasets/ciciot2023/** — Dataset-specific preparation. Domain-named (OK).

**artifacts.py**, **common/**, **sampling.py**, **scaling.py**, **splits.py** — Clean.

---

### src/datp/evaluation/

All modules (`artifact_validation.py`, `confusion.py`, `metric_filtering.py`, `metrics.py`, `ranking.py`) — No active obsolete terms from search. Some reference `Baseline.B1/B2` indirectly.

---

### src/datp/experiments/

**enums.py**
Key enum: `ExperimentScale` — `SMOKE`, `BOUNDED`, `FULL`, `STRETCH`.
Also `DiagnosticStep`, `SweepStep`, `ContingencyDecision`.
Obsolete: `ExperimentScale` itself is to be removed per rework contract.

**models.py** — Experiment models. Uses `Regime`.

**executor.py** — Experiment executor. Uses `Regime`.

**sweep.py** — Sweep runner. Uses `Regime`, `REGIME_BASELINES`.

**stages/__init__.py**, **stages/prepare_data.py**, **stages/train_encoder.py** — Pipeline stages.

**console.py** — Console display. Uses `_Label.REGIME_ALL`.

**diagnostic.py** — Diagnostic runner.

**baselines/b0_centralized.py** — B0 centralized baseline.

**validator.py** — Experiment validator.

---

### src/datp/federated/
All modules — Use `Regime` in cell identity (`TrainingCellId.regime`). No explicit policy-name or stage-name hits beyond regime usage.

---

### src/datp/modeling/
**autoencoder.py**, **centralized_training.py** — Model modules. No obsolete terms.

---

### src/datp/reporting/

**constants.py**
Constants: `REGIME_C_ALPHA_DISPLAY_ORDER`, `REGIME_C_ALPHA_TICK_LABELS`.
Obsolete: Constant names embed regime label.

**enums.py**
`ComparisonLabel` enum: `B1_VS_B2 = "b1_vs_b2"`, `B1_VS_B4 = "b1_vs_b4"`, `B4_VS_B2 = "b4_vs_b2"`.
Comment references "Regime C IID comparison".
Obsolete: Enum values encode B-coded comparison pairs.

**build.py**
References: `REGIME_BASELINES`, `Regime.A/B/C`, `Baseline.B1/B2`, `StatsField.SECONDARY_REGIME_A/B`, `StatsField.REGIME_C`, `ComparisonLabel.B1_VS_B2/B4`.
Extensive regime/B-code usage.

**figures.py** — Uses `Baseline.B1/B2/B4`, `REGIME_C_ALPHA_DISPLAY_ORDER`.

**tables.py** — Uses regime/baseline references.

**engine.py**, **validation.py** — No explicit obsolete name hits in search.

---

### src/datp/scoring/

**loading.py**
Docstring line 1: "B1/B2/B3/B4 share one ScoreProvider per (regime, seed, alpha) cell".
Obsolete: Docstring uses B-coded names and "regime".

**cal_loading.py**, **generation.py**, **schema.py** — No active obsolete terms.

---

### src/datp/statistics/

**bootstrap.py**
Docstring: "Percentile-based bootstrap CI on per-seed deltas (e.g. CV(FPR)[B1] − CV(FPR)[B2])."
No enum-level issues.

**enums.py** (`StatsField`)
Values: `SECONDARY_REGIME_A = "secondary_regime_a"`, `SECONDARY_REGIME_B = "secondary_regime_b"`, `REGIME_C = "regime_c"`, `REGIME_C_BONFERRONI = "regime_c_bonferroni_b1_vs_b2"`, `B1_CV_FPR_REGIME_A_MEAN = "b1_cv_fpr_regime_a_mean"`.
`wilcoxon.py` docstring: "Secondary for Regime A (n=9 limit); primary for Regime C…".
Obsolete: Enum string values and names encode regime labels and B-codes.

---

### src/datp/testsupport/

**smoke_harness.py**
Comments reference "B1 / B2 / B4 threshold recomputation", "B4 Δτ decomposition".
Functions: `b4_cluster_count` (line 228) — function name has B4.
Uses `Baseline.B4`, `ThresholdPolicy.B2_PERSONALIZED`.
Obsolete: `b4_cluster_count` function name; policy/baseline references.

**checkpoint_protocol.py**, **synthetic_scores.py** — No obsolete naming observed.

---

### src/datp/thresholding/

**strategies/b1_global.py**
File name: `b1_global.py`. Docstring: "B1 — Global-mean threshold…".
Obsolete: Module filename; docstring.

**strategies/b2_personalized.py**
File name: `b2_personalized.py`. Docstring: "B2 - Per-client threshold…".
Obsolete: Module filename; docstring.

**strategies/b3_family.py**
File name: `b3_family.py`. Docstring: "B3 — Family-mean threshold (Regime A only)…".
Uses `@enforce_regime(Regime.A)`.
Obsolete: Module filename; docstring; "Regime A only" coupling.

**strategies/b4_cluster.py**
File name: `b4_cluster.py`. Docstring: "B4 — Cluster-mean threshold…".
Contains `k_regime_a`, `_select_regime_a_k` function, `@enforce_regime(Regime.A, Regime.B, Regime.C)`.
Obsolete: Module filename; `k_regime_a` parameter; `_select_regime_a_k` function; "Regime A/B/C" comments.

**strategies/__init__.py** — Docstring: "centralized (B0), global (B1), personalized (B2), family (B3), cluster (B4)". Obsolete: docstring.

**thresholds.py**
Imports `b1_global as b1_mod`, `b2_personalized as b2_mod`, `b3_family as b3_mod`, `b4_cluster as b4_mod`.
Dispatch via `Baseline.B1/B2/B3/B4`.
Obsolete: Module import aliases.

**eligibility.py** — Uses `Baseline.B2` internally; comment "B1 formula".

**metrics_serialization.py** — Uses `Regime`.

**__init__.py** — Docstring: "Threshold derivation strategies (B0-B4)…". Obsolete.

---

### src/datp/validation/

**constants.py**
Constants: `REGIME_C_ALPHA_AUDIT_CSV = "regime_c_alpha_audit.csv"`, `REGIME_C_SEVERITY_TREND_CSV = "regime_c_severity_trend.csv"`, `BLOCKED_RESUME_REGIME_A_COMMAND = "datp sweep --regime=a --resume"`, `DIAGNOSTIC_REGIME_A_COMMAND = "datp diagnostic --regime a --seed 0"`, `REGIME_C_SCOPE_NOTE`.
Obsolete: Constant names and string values embed regime labels and CLI flags.

**enums.py**
`WarningCode` values: `B0_AUROC_BELOW_THRESHOLD`, `B1_NOT_POOLED_PERCENTILE`, `B1_MEAN_NOT_POOLED_PERCENTILE`, `B2_UTILITY_TRADEOFF`, `B3_TAXONOMY_TOO_COARSE`, `B4_CLUSTER_DIAGNOSTICS_INCOMPLETE`, `B4_SINGLE_CLUSTER`, `REGIME_C_ALPHA_AUDIT_MISSING`, `REGIME_C_PREPARED_MANIFEST_MISSING`.
Obsolete: `B0/B1/B2/B3/B4`-prefixed warning codes; `REGIME_C_*` warning codes.

**results.py**
Uses: `REGIME_C_ALPHA_AUDIT_CSV`, `REGIME_C_SEVERITY_TREND_CSV`, `BLOCKED_RESUME_REGIME_A_COMMAND`.
`AuditOutputName` enum: `REGIME_C_ALPHA_AUDIT`, `REGIME_C_SEVERITY_TREND`.
Obsolete: Regime-coded names.

**schemas.py**
Docstrings reference "Per-(regime, alpha, seed)", "Regime A B1-vs-B2 claim", "Regime C structural audit".
`scope_note: str = REGIME_C_SCOPE_NOTE`.
Obsolete: Docstrings with regime and B-code terminology; `REGIME_C_SCOPE_NOTE` usage.

---

## CLI entry points

| Command | File | Notes |
|---|---|---|
| `datp config preview` | app/cli/config.py | Uses `--regime=<R>` flag |
| `datp sweep` | app/cli/sweep.py | Uses `--regime` flag |
| `datp poison preview` | app/cli/poison.py | Default stage `NBAIOT_BOUNDED` |
| `datp poison dry-run` | app/cli/poison.py | Default stage `NBAIOT_BOUNDED` |
| `datp poison smoke` | app/cli/poison.py | References `NBAIOT_SMOKE` |
| `datp poison run-bounded-sweep` | app/cli/poison.py | Calls `write_nbaiot_bounded_sweep_manifest` |
| `datp poison stages` | app/cli/poison.py | Lists all `ExperimentStage` values |
| `datp status` | app/cli/status.py | Prints "Regime A/B/C" labels |
| `datp audit results` | app/cli/audit.py | |
| `datp report` | app/cli/report.py | |
| `datp checkpoint-protocol` | app/cli/checkpoint_protocol.py | Uses `Regime.A` |

---

## Config objects and enums

| Name | File | Obsolete? |
|---|---|---|
| `ThresholdPolicy` (B1_GLOBAL, B2_PERSONALIZED, B4_CLUSTER) | attacks/enums.py | Yes — all three values |
| `PoisoningSourceStrategy.TARGETED_REMOVAL_LOW_SCORE` | attacks/enums.py | Yes |
| `PoisoningKnowledge.WHITE_BOX` | attacks/enums.py | Yes |
| `PoisoningTargetScope.ALL_CLIENTS` | attacks/enums.py | Yes |
| `ExperimentStage` (all values) | config/stages.py | Yes — all values per contract |
| `ExperimentScale` | experiments/enums.py | Yes — to be removed per contract |
| `Regime` (A, B, C) | core/enums.py | Yes — active but regime naming to be removed |
| `Baseline` (B0-B4) | core/enums.py | B3 is out of default scope; all B-codes in names |
| `ThresholdSource` | core/enums.py | Values B1_SHARED, B2_PER_CLIENT, B3_FAMILY, B4_CLUSTER |
| `B4RegimeAMode` | core/enums.py | Class name encodes regime |
| `StatsField` (REGIME_* values) | statistics/enums.py | Yes |
| `ComparisonLabel` (B1_VS_B2, etc.) | reporting/enums.py | Yes |
| `WarningCode` (B*_* / REGIME_C_*) | validation/enums.py | Yes |
| `PrimaryCheckpointSelectionRule.GLOBAL_LOWER_TAIL_TRADEOFF_FROM_REGIME_A` | checkpointing/enums.py | Yes |
| `DatpConfig` | config/models.py | Contains `regime`, `baseline`, `b4_regime_a_mode` fields |
| `CalibrationPoisoningConfig` | config/attack_config.py | `for_bounded_mvp()` method name |
| `B4ClusterConfig` | config/attack_config.py | Docstring references "Regime A" |

---

## Tests (tests/)

### tests/unit/

**tests/unit/app/cli/test_poison_cli.py**
Tests poison CLI commands. Asserts `"b1_global"`, `"b2_personalized"`, `"b4_cluster"` appear in output (lines 86-88).
Valid for datp-cp: Partially — tests the CLI, but string assertions on policy values will need updating.

**tests/unit/app/cli/test_status.py**
Constants `_REGIME_A_CELLS = 25`, `_REGIME_B_CELLS = 20`, `_REGIME_C_CELLS = 90`.
Valid for datp-cp: Partially — validates status output structure but uses regime-coded constants.

**tests/unit/attacks/test_bounded_sweep_matrix.py**
Uses `CalibrationPoisoningConfig.for_bounded_mvp()`.
Obsolete: `for_bounded_mvp()` call.

**tests/unit/attacks/test_poison_enums.py**
Likely tests `ThresholdPolicy`, `PoisoningSourceStrategy` enum values.
Valid for datp-cp: Yes after enum rename.

**tests/unit/checkpointing/test_training_protocol.py**
References `b4_k_regime_a`, `b4_regime_a_mode` (lines 86, 90, 94, 95).
Obsolete: Config field names.

**tests/unit/config/test_attack_config.py**
Calls `CalibrationPoisoningConfig.for_bounded_mvp()` extensively (lines 167-214).
Obsolete: `for_bounded_mvp()` method name.

**tests/unit/config/test_stages.py** — Tests `ExperimentStage` values. All stage values are obsolete.

**tests/unit/core/test_regime.py** — Tests `Regime` enum and `enforce_regime`.

**tests/unit/thresholding/strategies/test_threshold_strategies.py**
Imports: `b1_global as b1`, `b2_personalized as b2`, `b4_cluster as b4`.
References `k_regime_a=3`, `test_regime_a_k_fixed_3`.
Obsolete: Module names in imports; `k_regime_a` parameter; test name.

**tests/unit/artifacts/test_poison_layout.py**
Tests `nbaiot_bounded_sweep_manifest()` method and `NBAIOT_BOUNDED_SWEEP_MANIFEST` constant.
Obsolete: Method and constant names.

**tests/unit/test_makefile_targets.py**
Tests that COMMANDS.md `make X` references exist as Makefile targets. Uses regex scan.
Valid for datp-cp: Must be updated alongside Makefile changes.

### tests/integration/

**tests/integration/attacks/test_bounded_sweep_run.py**
Calls `write_nbaiot_bounded_sweep_manifest`, `CalibrationPoisoningConfig.for_bounded_mvp()`.
Constants: `_N_CLIENTS = 4` (comment references B4_CLUSTER).
Obsolete: Function name; method name.

**tests/integration/attacks/test_smoke_harness.py**
Uses `ThresholdPolicy.B1_GLOBAL`, `ThresholdPolicy.B2_PERSONALIZED`, `ThresholdPolicy.B4_CLUSTER`, `ExperimentScale.SMOKE`, `b4_cluster_count`.
Obsolete: Policy enum values; `ExperimentScale`; `b4_cluster_count` function name.

**tests/integration/data/regime_c/test_data_regime_c.py**
Imports `datp.data.regimes.regime_c`, `partition_regime_c`.
References `"regime_c"` in path assertions.
Obsolete: Module path and function name.

**tests/integration/federated/test_fl_simulation.py**
Functions: `test_regime_b_smoke`, `test_regime_c_loop`, `test_regime_a_smoke`.
Obsolete: Function names encode regime labels.

**tests/integration/thresholding/test_baseline_scope.py**
Uses `Regime.A/B/C`, `_dummy_regime_a`, `_dummy_regime_ab`, `Baseline.B3`.
Methods: `test_b3_excluded_regime_c`, `test_b3_excluded_regime_b`, `test_b3_allowed_regime_a`.
Obsolete: Regime and B3 references.

### tests/e2e/
**tests/e2e/test_checkpoint_protocol_smoke.py** — e2e checkpoint protocol test.

### tests/fixtures/
**tests/fixtures/nbaiot_raw.py**, **fl_training.py**, **cuda_model.py**, **flower_smoke.py**, **payloads.py**, **scoring_loading.py** — Fixture files.

### tests/conftest.py — Root conftest.

---

## Makefile targets

### Existing targets (as of audit):

| Target | Status per rework contract |
|---|---|
| `help` | Keep |
| `test` | Obsolete — remove |
| `test-unit` | Obsolete — remove |
| `test-integration` | Obsolete — remove |
| `test-e2e` | Obsolete — remove |
| `typecheck` | Obsolete — remove |
| `typecheck-attacks` | Obsolete — remove |
| `lint` | Obsolete — remove |
| `gates` | Obsolete — remove |
| `gate-all` | Obsolete — remove |
| `gate0` | Obsolete — remove |
| `gate1` | Obsolete — remove |
| `gate2` | Obsolete — remove |
| `gate3-code` | Obsolete — remove |
| `config-preview` | Obsolete — remove |
| `run-regime-a` | Obsolete — remove |
| `run-regime-b` | Obsolete — remove |
| `run-regime-c` | Obsolete — remove |
| `run-main-matrix` | Obsolete — remove |
| `sweep-dry-run` | Obsolete — remove |
| `status` | Keep (no new target name specified for status) |
| `audit-results` | Keep |
| `poison-stages` | Obsolete — remove |
| `poison-dry-run` | Obsolete — remove |
| `run-poison-bounded` | Obsolete — remove |
| `build-stats` | Obsolete — remove |
| `build-figures` | Obsolete — remove |
| `build-tables` | Obsolete — remove |
| `docs` | Obsolete — remove |
| `clean-temp` | Obsolete — remove |
| `clean-pyc` | Obsolete — remove |

### Expected new targets (not yet present):

| Target | Status |
|---|---|
| `check` | Missing |
| `datp-cp-clean` | Missing |
| `datp-cp-smoke` | Missing |
| `datp-cp-dry-run` | Missing |
| `datp-cp-run` | Missing |
| `datp-cp-report` | Missing |
| `clean` | Missing |

---

## Docs files

| File | Notes |
|---|---|
| `README.md` | Uses B1/B2/B3/B4 shorthand, "Regime A/B/C" labels, `make run-regime-*` commands |
| `COMMANDS.md` | References `make run-regime-a/b/c`, `make gate*`, `make poison-*`, B0-B4 labels, Regime A/B/C |
| `docs/DATP_CP_Roadmap.md` | Uses `LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY` (target name) |

---

## .claude/ contents

**agents/**: 11 agent definition `.md` files. Several reference CP2, B1_GLOBAL/B2_PERSONALIZED/B4_CLUSTER in their context banners.

**skills/**: 12 skill `.md` files. Several have CP2 banners (`long-run-monitoring-skill.md`, `paper-claim-discipline-skill.md`, `experiment-gate-skill.md`, etc.) and reference `{B1_GLOBAL, B2_PERSONALIZED, B4_CLUSTER}`.

**settings.json**, **settings.local.json** — Not audited for scientific naming.

**commands/**: Not listed in dir output (appears empty or absent).

---

## Artifact output paths

| Path | How produced | Obsolete? |
|---|---|---|
| `outputs/conference_calibration_poisoning/` | `CALIBRATION_POISONING_OUTPUT_ROOT` | No — domain-named |
| `outputs/conference_calibration_poisoning/nbaiot_bounded_sweep_manifest.json` | `ManifestFile.NBAIOT_BOUNDED_SWEEP_MANIFEST` | Yes — encodes dataset/scale |
| `outputs/conference_calibration_poisoning/paper_figure_manifest.json` | `ManifestFile.PAPER_FIGURE_MANIFEST` | Yes — phase-coded |
| `outputs/conference_calibration_poisoning/project_audit_report.json` | `ManifestFile.PROJECT_AUDIT_REPORT` | No |
| `outputs/conference_calibration_poisoning/clean_score_artifacts.json` | `ManifestFile.CLEAN_SCORE_ARTIFACTS` | No |
| `outputs/<bounded|full|smoke|stretch>/<nbaiot|ciciot2023>/...` | `PoisonLayout.run_dir(cell)` | `ExperimentScale` values embedded |
| `outputs/checkpoints/<regime>/seed_<N>/...` | `ArtifactLayout` | Regime letter embedded in path |
| `outputs/scores/<regime>/seed_<N>/...` | `ArtifactLayout` | Regime letter embedded in path |
| `outputs/results/<regime>/<baseline>/seed_<N>/...` | `ArtifactLayout` | Regime letter and baseline code embedded |
| `outputs/console_logs/...` | Makefile wrapper | No obsolete naming |
| `data/processed/<dataset>/regime_c/...` | `regime_c_prepared_dir` | "regime_c" literal in path |

---

## Old experiment orchestration (to be removed)

These modules orchestrate the old DATP sweep (journal/pre-CP2 work) and are being superseded:

| Module | Purpose | Status |
|---|---|---|
| `src/datp/experiments/sweep.py` | Old 135-cell sweep runner | Superseded by bounded_sweep_run.py path; still referenced by `datp sweep` CLI |
| `src/datp/data/regimes/regime_a.py` | N-BaIoT preparation dispatch | Active; uses Regime naming |
| `src/datp/data/regimes/regime_b.py` | CICIoT2023 preparation dispatch | Active; uses Regime naming |
| `src/datp/data/regimes/regime_c.py` | N-BaIoT Dirichlet partition | Active; outputs `regime_c/` paths |
| `src/datp/experiments/baselines/b0_centralized.py` | B0 centralized baseline | Active |
| Makefile `run-regime-a/b/c` | Old experiment launchers | Obsolete per contract |
