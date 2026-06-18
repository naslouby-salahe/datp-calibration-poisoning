# 02 — Package Inventory

## A. Repository Package Map

```
src/datp/
├── __init__.py          — Package root, runtime env config, import check
├── analyses/            — Analysis package (empty __init__.py)
├── app/
│   ├── __init__.py
│   ├── __main__.py      — `python -m datp` entrypoint
│   └── cli/             — Typer CLI commands
├── artifacts/           — Path layout, I/O, markers, constants, lifecycle
├── attacks/             — Calibration poisoning: injector, reservoir, sources, B4, etc.
├── checkpointing/       — Checkpoint protocol, invariants, summary, status
├── conf/                — YAML configuration files
├── config/              — Pydantic/Hydra config models, composition, stages
├── core/                — Core enums, types, identity, seeds, errors, logging, tracking
├── data/                — Dataset catalog, splits, regimes, scaling, manifests
├── evaluation/          — Metric computation, ranking, confusion, artifact validation
├── experiments/         — Sweep orchestration, diagnostic, executor, stages
├── federated/           — Federated training: clients, strategies, simulation, checkpoints
├── modeling/            — Autoencoder model, centralized training
├── reporting/           — Figures, tables, build, validation, enums
├── scoring/             — Score generation, loading, schema
├── statistics/          — CV, bootstrap, Wilcoxon, divergence, effect size
├── testsupport/         — Test helpers: synthetic scores, checkpoint protocol, smoke harness
├── thresholding/        — Threshold strategies (B0-B4), eligibility, metrics serialization
└── validation/          — Result validation, invariants, convergence, datasets, provenance
```

## B. Dependency and Graph Inventory

### Graph Tool

- Tool attempted: `graphify`
- Command: `graphify update .`
- Result: `available` — graphify 0.8.39 installed
- Graph output: 7907 nodes, 19069 edges, 463 communities, built from commit `516fcdfc`
- Extraction: 54% EXTRACTED, 46% INFERRED
- Fallback used: none (graphify was available)

### Static dependency observations

- Package: `datp.core`
  - Imports: `enum`, `math`, `time`, `hashlib`, `json`, `subprocess`, `os`, `random`, `logging`, `contextlib`, `functools`
  - External deps: `numpy`, `torch`, `structlog`, `rich`, `mlflow`
  - Imported by: all other `datp.*` packages
  - No internal `datp.*` imports (leaf package)

- Package: `datp.config`
  - Imports from: `datp.core`, `datp.artifacts`, `datp.data`
  - Imported by: `datp.app.cli`, `datp.experiments`, `datp.attacks`

- Package: `datp.artifacts`
  - Imports from: `datp.core`, `datp.data`, `datp.evaluation`, `datp.thresholding`
  - Imported by: `datp.app.cli`, `datp.experiments`, `datp.attacks`

- Package: `datp.attacks`
  - Imports from: `datp.artifacts`, `datp.core`, `datp.thresholding`, `datp.config`, `datp.data`
  - Imported by: `datp.app.cli`

- Package: `datp.data`
  - Imports from: `datp.core`
  - Imported by: `datp.artifacts`, `datp.config`, `datp.experiments`, `datp.evaluation`, `datp.federated`

- Package: `datp.evaluation`
  - Imports from: `datp.core`, `datp.data`, `datp.scoring`, `datp.statistics`
  - Imported by: `datp.artifacts`, `datp.experiments`

- Package: `datp.experiments`
  - Imports from: `datp.artifacts`, `datp.checkpointing`, `datp.config`, `datp.core`, `datp.data`, `datp.evaluation`, `datp.federated`, `datp.scoring`, `datp.thresholding`
  - Imported by: `datp.app.cli`

- Package: `datp.federated`
  - Imports from: `datp.artifacts`, `datp.checkpointing`, `datp.config`, `datp.core`, `datp.data`, `datp.modeling`
  - Imported by: `datp.experiments`

- Package: `datp.thresholding`
  - Imports from: `datp.core`, `datp.data`, `datp.evaluation`, `datp.scoring`
  - Imported by: `datp.attacks`, `datp.artifacts`, `datp.experiments`

- Package: `datp.reporting`
  - Imports from: `datp.core`, `datp.data`, `datp.evaluation`, `datp.artifacts`, `datp.attacks`, `datp.statistics`
  - Imported by: `datp.app.cli`

- Package: `datp.scoring`
  - Imports from: `datp.artifacts`, `datp.core`, `datp.data`, `datp.modeling`
  - Imported by: `datp.evaluation`, `datp.thresholding`, `datp.attacks`

- Package: `datp.statistics`
  - Imports from: `datp.core`
  - Imported by: `datp.evaluation`, `datp.reporting`, `datp.checkpointing`

- Package: `datp.validation`
  - Imports from: `datp.artifacts`, `datp.core`, `datp.checkpointing`, `datp.data`, `datp.evaluation`
  - Imported by: `datp.app.cli`

## C. Package Entries

### C.1 `datp.core`

- Path: `src/datp/core`
- Package initialization file: `src/datp/core/__init__.py` (not explicitly read, likely empty or re-export)
- Modules manually read:
  - `src/datp/core/enums.py`
  - `src/datp/core/poison_enums.py`
  - `src/datp/core/types.py`
  - `src/datp/core/identity.py`
  - `src/datp/core/seeds.py`
  - `src/datp/core/seed_sequence.py`
  - `src/datp/core/regime.py`
  - `src/datp/core/metric_enums.py`
  - `src/datp/core/provenance.py`
  - `src/datp/core/device.py`
  - `src/datp/core/errors.py`
  - `src/datp/core/logging.py`
  - `src/datp/core/tracking.py`
- Related test modules:
  - `tests/unit/core/test_enums.py`
  - `tests/unit/core/test_identity.py`
  - `tests/unit/core/test_seeds.py`
  - `tests/unit/core/test_seed_sequence.py`
  - `tests/unit/core/test_regime.py`
  - `tests/unit/core/test_provenance.py`
  - `tests/unit/core/test_device.py`
  - `tests/unit/core/test_errors.py`
  - `tests/unit/core/test_log_rotation.py`
  - `tests/unit/core/test_tracking.py`
  - `tests/unit/core/test_canonical_ownership.py`
  - `tests/unit/core/test_dataclass_architecture.py`
  - `tests/unit/core/test_model_boundary_architecture.py`
  - `tests/unit/core/test_no_scientific_policy_leaks.py`
- Related configuration modules:
  - `src/datp/config/models.py`
- Direct imports:
  - Standard library: `enum`, `math`, `time`, `hashlib`, `json`, `subprocess`, `os`, `random`, `logging`, `contextlib`, `functools`, `dataclasses`
  - External: `numpy`, `torch`, `structlog`, `rich`, `mlflow`, `pydantic`
  - Internal: none (leaf package)
- Declared classes:
  - `FrozenModel` (Pydantic BaseModel)
  - `MetricsProvenance` (Pydantic BaseModel)
  - `AnalysisRowBase` (Pydantic BaseModel)
  - `B3FamilyInfo`, `B3Metadata`, `B4ClusterInfo`, `B4Metadata`
  - `ClientThreshold`, `ThresholdMetadata`, `ThresholdResult`
  - `ClientEvalResult`, `ClientEvalResultWithAuroc`
  - `BaselineResult`, `B0Result`
  - `TrainingCellId`, `BaselineRunId`
  - `SeedRecord`
  - `_MlflowRun`, `_MlflowModule`
  - `_LoggerProtocol`, `_StdlibBoundLogger`
- Declared functions:
  - `classify_absorption`, `alpha_label`, `alpha_from_label`, `format_alpha_dir`, `parse_alpha_dir`
  - `seed_segment`, `make_run_id`, `set_seeds`
  - `make_seed_rng`, `derive_seed_record`
  - `enforce_regime` (decorator)
  - `resolve_device`
  - `fmt`, `fmt_missing`
  - `configure_logging`, `get_logger`
  - `utc_timestamp`, `sha256_bytes`, `hash_file`, `hash_jsonable`, `git_commit`, `source_hash`, `array_hash`
  - `init_tracking`, `tracking_run`, `log_metrics`, `log_params`, `log_artifact`
- Declared enums:
  - `DatasetID`, `ClientIdentity`, `DeviceType`, `ArtifactFile`, `PathToken`
  - `Baseline`, `Regime`, `ClientStatus`, `BaselineRunStatus`
  - `ThresholdAggregationMethod`, `ThresholdSource`, `NormalizationScope`
  - `PipelineStage`, `Activation`, `B0NormalizationMode`, `B4RegimeAMode`
  - `BaselineRole`, `ScoringStage`, `AbsorptionClass`
  - `MetricName`, `PayloadKey`, `ConfusionKey`, `AuditField`, `ValidationField`
  - `AlphaLabel`
- Domain concepts used:
  - All DATP domain concepts (dataset identity, regime, baseline, seed, threshold, metrics)
- Tests directly associated: 14 test files

### C.2 `datp.attacks`

- Path: `src/datp/attacks`
- Modules (21 files):
  - `__init__.py`, `b4_recompute.py`, `bounded_sweep_cell.py`, `bounded_sweep_manifest.py`, `bounded_sweep_matrix.py`, `bounded_sweep_run.py`, `cell_runner.py`, `compromise_patterns.py`, `defenses.py`, `diagnostics.py`, `guardrails.py`, `inference.py`, `injector.py`, `metric_engine.py`, `real_score_loader.py`, `reservoir.py`, `run_logger.py`, `run_manifest.py`, `score_containers.py`, `source_strategies.py`, `threshold_recompute.py`
- Related test files:
  - `tests/unit/attacks/` (20 test files)
  - `tests/integration/attacks/` (3 test files)
- Related CLI modules:
  - `datp.app.cli.poison`
- Direct imports:
  - `datp.artifacts.poison_names`, `datp.artifacts.poison_layout`
  - `datp.core.poison_enums`, `datp.core.enums`, `datp.core.seed_sequence`, `datp.core.identity`
  - `datp.thresholding.eligibility`, `datp.thresholding.thresholds`, `datp.thresholding.strategies.b4_cluster`
  - `datp.config.attack_config`
  - `datp.data.catalog`
  - `datp.evaluation.metrics` (via metric_engine)
- Static dependents:
  - `datp.app.cli.poison`
  - `datp.validation` (possibly)
- Declared classes:
  - `B4DecompEntry`, `B4ThresholdPair` (dataclasses)
  - `SweepCellResult` (dataclass)
  - `BoundedSweepResultRow`, `BoundedSweepManifest` (Pydantic models)
  - `SweepCellSpec` (dataclass)
  - `InjectionResult` (dataclass)
  - `ReservoirResult`, `ReservoirStatus` (enum)
  - `MetricResult`, `FleetFprResult`, `DeltaTauResult`, `AurocRecord` (dataclasses)
  - `ClientScores`, `ScoreCollection`, `VictimSet` (dataclasses)
  - `RunManifest`, `ProvenanceRecord`, `SeedRecordModel` (Pydantic models)
  - `DiagnosticSourceError` (exception)
  - `GuardrailError` (exception)
  - `CompromiseEntry`, `CompromiseResult` (dataclasses)
  - `RunLogEntry` (dataclass)
- Declared functions:
  - `compute_b4_pair`, `_run_b4`, `_client_to_cluster_key`, `_agg_thresholds`
  - `lock_mu_flag_threshold`, `run_sweep_cell`
  - `_enumerate_single_victim_matrix`, `enumerate_bounded_sweep_matrix`, `enumerate_full_sweep_matrix`
  - `_auroc_invariant`, `_row_for_cell`, `run_nbaiot_bounded_sweep`, `write_nbaiot_bounded_sweep_manifest`
  - `inject_single_victim`, `recompute_pair`, `_run_policy_pair` (cell_runner.py)
  - `select_pairs`, `select_triples` (compromise_patterns.py)
  - `apply_defense` (defenses.py)
  - `compute_asr`, `compute_blast_radius`, `compute_spillover` (diagnostics.py)
  - `assert_no_inplace_mutation`, `assert_reservoir_not_test_or_training`, `assert_policy_not_b3`, `assert_fractions_in_locked_grid`, `assert_bounded_scale_requires_single_client`
  - `collect_paired_deltas`, `compute_seed_aggregates`, `sign_test`, `holm_adjust`, `bootstrap_seed_aggregates`, `compute_inference`
  - `inject_fixed_budget`
  - `compute_delta_tau`, `compute_fleet_fpr`, `compute_auroc_records`, `compute_mu_flag_threshold`, `compute_metrics`
  - `load_real_score_collection`
  - `build_reservoir`
  - `build_manifest`, `emit_manifest`, `load_manifest`, `write_run_log_entry`
  - `is_diagnostic_source`, `select_reservoir`, `objective_for_source`, `near_null_criterion`, `DiagnosticSourceError`
  - `compute_b1_pair`, `compute_b2_pair`
- File I/O:
  - `bounded_sweep_run.py`: writes manifest JSON
  - `real_score_loader.py`: reads Parquet score files
  - `run_logger.py`: writes and reads JSON manifest files
- CLI interaction:
  - Via `datp.app.cli.poison.run_bounded_sweep` command

### C.3 `datp.artifacts`

- Path: `src/datp/artifacts`
- Modules:
  - `__init__.py`, `constants.py`, `existence.py`, `io.py`, `layout.py`, `lifecycle.py`, `markers.py`, `names.py`, `poison_layout.py`, `poison_names.py`
- Related test files:
  - `tests/unit/artifacts/`
- Declared classes/dataclasses:
  - `ScoreCellPaths`, `BaselineRunPaths`, `ArtifactLayout` (dataclasses in `layout.py`)
  - `CellId`, `CellPaths`, `PoisonLayout` (dataclasses in `poison_layout.py`)
  - `RunLifecycle` (context manager in `lifecycle.py`)
- Declared enums:
  - `ArtifactDir`, `RunState` (in `names.py`)
  - `ManifestFile`, `RunFile` (in `poison_names.py`)
- Declared functions:
  - `results_exist`, `serialize_json_payload`, `write_json_atomic`, `write_csv`, `write_metrics_atomic`
  - `check_run_state`
  - `score_file`, `score_file_for_round` (methods on ArtifactLayout)
- Declared constants:
  - `MANIFEST_FILE`, `SCALER_FILE`
  - `CALIBRATION_POISONING_OUTPUT_ROOT`, `N_MIN`, `TAIL_MASS`, `MATERIALITY_FACTOR`, `THRESHOLD_QUANTILE`
  - `TRIM_FRACTION_PRIMARY`, `TRIM_FRACTION_APPENDIX`
  - `B4_K`, `B4_N_INIT`, `B4_MAX_ITER`, `B4_RANDOM_STATE`
  - `TRAINING_SEEDS`, `POISONING_SEEDS`, `ANALYSIS_SEEDS`, `COMPROMISE_PATTERN_SEED`

### C.4 `datp.config`

- Path: `src/datp/config`
- Modules:
  - `__init__.py`, `attack_config.py`, `compose.py`, `models.py`, `stages.py`
- Related test files:
  - `tests/unit/config/`
- Declared classes:
  - `CalibrationPoisoningConfig`, `SeedPools`, `B4ClusterConfig` (attack_config.py)
  - `ComposeError`, `ComposeRequest`, `compose_config`, `write_resolved_config`, `resolved_config_yaml`, `preview_config`
  - `SafetyBounds`, `ConvergenceConfig`, `ModelConfig`, `DatasetConfig`, `MachineConfig`, `FederationConfig`, `ThresholdConfig`, `ExperimentConfig`, `StatisticsConfig`, `QualityGateConfig`, `StyleConfig`, `LoggingConfig`, `RuntimeConfig`, `TrackingConfig`, `ReportingConfig`, `DatpConfig` (Pydantic models in models.py)
  - `ExperimentStageConfig`, `get_stage_config`, `all_stage_configs` (stages.py)
- Declared enums:
  - `ExperimentStage` (in stages.py)
- File I/O: reads/writes YAML config files via Hydra/OmegaConf

### C.5 `datp.data`

- Path: `src/datp/data`
- Modules (multiple, including `catalog.py`, `splits.py`, `regimes/`, `paths.py`, `scaling.py`, `manifest.py`, `common/`)
- Related test files:
  - `tests/unit/data/`
  - `tests/integration/data/`

### C.6 `datp.app.cli`

- Path: `src/datp/app/cli`
- Modules:
  - `__init__.py`, `__main__.py`, `audit.py`, `checkpoint_protocol.py`, `config.py`, `poison.py`, `report.py`, `status.py`, `sweep.py`
- Declared classes:
  - `_RegimeReport`, `_StatusReport` (dataclasses in status.py)
- Declared functions:
  - `main`, `cli_entry` (entry points)
  - `results` (audit command)
  - `preview`, `smoke`, `evaluate_from_scores`, `summary`, `status` (checkpoint commands)
  - `preview` (config command)
  - `preview`, `dry_run`, `smoke`, `run_bounded_sweep`, `stages` (poison commands)
  - `stats`, `validate`, `figures`, `tables`, `all_outputs` (report commands)
  - `status` (status command)
  - `sweep` (sweep command)

### C.7 `datp.evaluation`

- Path: `src/datp/evaluation`
- Modules:
  - `__init__.py`, `artifact_validation.py`, `confusion.py`, `metric_filtering.py`, `metrics.py`, `ranking.py`
- Declared classes:
  - `ValidationIds`, `ClientRowContext` (dataclasses in artifact_validation.py)
  - `ConfusionCounts`, `BinaryMetrics`, `ClientEvaluationRecord`, `DispersionMetrics`, `EvaluationResult`, `PerAttackFamilyTPR` (dataclasses in metrics.py)
  - `BinaryRankingMetrics` (dataclass in ranking.py)
  - `_FilteredMetrics` (dataclass in metric_filtering.py)
- Declared functions:
  - `validate_metrics_payload`, `client_rows`, `_validate_provenance`, `_validate_client_row`
  - `save_confusion_matrices`
  - `recompute_binary_metrics`, `compute_client_record`, `_aggregate_dispersion`, `build_evaluation_result`, `evaluate_baseline`, `compute_fpr`, `compute_empirical_coverage`, `compute_per_attack_tpr`
  - `compute_binary_ranking_metrics`

### C.8 `datp.experiments`

- Path: `src/datp/experiments`
- Modules:
  - `__init__.py`, `console.py`, `diagnostic.py`, `enums.py`, `executor.py`, `models.py`, `sweep.py`, `validator.py`, `stages/`
- Related test files:
  - `tests/unit/experiments/`

### C.9 `datp.federated`

- Path: `src/datp/federated`
- Modules:
  - `__init__.py`, `catalog.py`, `checkpoints.py`, `clients.py`, `convergence.py`, `data_loading.py`, `factories.py`, `local_training.py`, `parameters.py`, `protocols/`, `runtime.py`, `simulation.py`, `strategies.py`, `types.py`
- Related test files:
  - `tests/unit/federated/`

### C.10 `datp.thresholding`

- Path: `src/datp/thresholding`
- Modules:
  - `__init__.py`, `eligibility.py`, `metrics_serialization.py`, `thresholds.py`, `strategies/`
- Related test files:
  - `tests/unit/thresholding/`

### C.11 `datp.modeling`

- Path: `src/datp/modeling`
- Modules:
  - `__init__.py`, `autoencoder.py`, `centralized_training.py`
- Related test files:
  - `tests/unit/modeling/`

### C.12 `datp.reporting`

- Path: `src/datp/reporting`
- Modules:
  - `__init__.py`, `enums.py`, `constants.py`, `engine.py`, `build.py`, `figures.py`, `tables.py`, `validation.py`
- Related test files:
  - `tests/unit/reporting/`

### C.13 `datp.scoring`

- Path: `src/datp/scoring`
- Modules:
  - `__init__.py`, `cal_loading.py`, `generation.py`, `loading.py`, `schema.py`
- Related test files:
  - `tests/unit/scoring/`

### C.14 `datp.statistics`

- Path: `src/datp/statistics`
- Modules:
  - `__init__.py`, `bootstrap.py`, `constants.py`, `cv.py`, `divergence.py`, `effect_size.py`, `enums.py`, `spearman.py`, `wilcoxon.py`
- Related test files:
  - `tests/unit/statistics/`

### C.15 `datp.validation`

- Path: `src/datp/validation`
- Modules (18 files incl. `_audit_helpers.py`, `_audit_types.py`, `_client_pipeline.py`, `_recomputation.py`, `_warnings.py`, `constants.py`, `convergence.py`, `datasets.py`, `discovery.py`, `enums.py`, `invariants.py`, `metric_reproducer.py`, `provenance_gate.py`, `results.py`, `schemas.py`, `score_manifest.py`, `verdicts.py`)
- Related test files:
  - `tests/unit/validation/`

### C.16 `datp.testsupport`

- Path: `src/datp/testsupport`
- Modules:
  - `__init__.py`, `checkpoint_protocol.py`, `smoke_harness.py`, `synthetic_scores.py`
- Declared functions:
  - `build_fake_checkpoint_metrics`
  - `make_synthetic_client`, `make_eligible_client`, `make_pending_client`, `make_degenerate_tail_client`, `make_standard_score_set`

### C.17 `datp.checkpointing`

- Path: `src/datp/checkpointing`
- Modules:
  - `__init__.py`, `enums.py`, `invariants.py`, `status.py`, `summary.py`

### C.18 `datp.analyses`

- Path: `src/datp/analyses`
- Modules:
  - `__init__.py` (empty, only `from __future__ import annotations`)
