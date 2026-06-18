# 04 — Enums, Dataclasses, Constants, and Configuration Inventory

## A. Existing Enums

### `datp/core/enums.py`

#### `DatasetID`

- Base: `StrEnum`
- Members: `NBAIOT = "nbaiot"`, `CICIOT2023 = "ciciot2023"`
- Referenced by: `datp.artifacts.poison_layout`, `datp.data.catalog`, `datp.config.models`
- Parsed from: config YAML, dataset paths
- Scientific concepts: dataset identity

#### `ClientIdentity`

- Base: `StrEnum`
- Members: `DEVICE_DIRECTORY`, `MERGED_FILE`, `VICTIM_MAC`, `VIRTUAL_CLIENT`
- Referenced by: `datp.data.catalog`

#### `DeviceType`

- Base: `StrEnum`
- Members: `CUDA = "cuda"`, `CPU = "cpu"`
- Referenced by: `datp.core.device`

#### `ArtifactFile`

- Base: `StrEnum`
- Members: `MODEL_CHECKPOINT`, `DECODER_CHECKPOINT`, `MODEL_B0_CHECKPOINT`, `SCORING_SENTINEL`, `SCORING_MANIFEST`, `METRICS`, `METRICS_TMP`, `REPORTING_AUDIT`, `BOOTSTRAP_CIS_JSON`, `BOOTSTRAP_CIS_CSV`, `METRICS_SCHEMA_VALIDATION`, `SCALER`, `MANIFEST`, `LOG`, `CONVERGENCE_CURVE`, `CONVERGENCE_SUMMARY`, `PARAMS_SNAPSHOT`, `JS_DIVERGENCE`, `RUN_IN_PROGRESS`, `RUN_DONE`, `RUN_ABORTED`, `RESOLVED_CONFIG`
- Referenced by: `datp.artifacts.names`, `datp.artifacts.layout`, `datp.artifacts.existence`

#### `PathToken`

- Base: `StrEnum`
- Members: `PARQUET_EXT`, `PARQUET_GLOB`, `CSV_GLOB`, `SEED_PREFIX`, `ROUND_PREFIX`, `ALPHA_PREFIX`, `ALPHA_IID`
- Referenced by: `datp.artifacts.layout`, `datp.core.identity`

#### `Baseline`

- Base: `StrEnum`
- Members: `B0 = "b0"`, `B1 = "b1"`, `B2 = "b2"`, `B3 = "b3"`, `B4 = "b4"`
- Referenced by: widespread

#### `Regime`

- Base: `StrEnum`
- Members: `A = "a"`, `B = "b"`, `C = "c"`
- Referenced by: widespread

#### `ThresholdAggregationMethod`

- Base: `StrEnum`
- Members: `ELIGIBLE_CLIENT_ARITHMETIC_MEAN`, `PER_CLIENT_PERCENTILE`, `ELIGIBLE_FAMILY_ARITHMETIC_MEAN`, `ELIGIBLE_CLUSTER_ARITHMETIC_MEAN`, `POOLED_PERCENTILE`

#### `ThresholdSource`

- Base: `StrEnum`
- Members: `B0_POOLED`, `B1_SHARED`, `B2_PER_CLIENT`, `B3_FAMILY`, `B4_CLUSTER`, `TAU_GLOBAL_FALLBACK`

#### `ScoringStage`

- Base: `StrEnum`
- Members: `CAL = "cal"`, `TEST_BENIGN = "test_benign"`, `TEST_ATTACK = "test_attack"`

#### `AbsorptionClass`

- Base: `StrEnum`
- Members: `STRONG_RETENTION`, `PARTIAL`, `NEAR_FULL`

#### `B4RegimeAMode`

- Base: `StrEnum`
- Members: `FIXED = "fixed"`, `SILHOUETTE = "silhouette"`

#### `NormalizationScope`

- Base: `StrEnum`
- Members: `GLOBAL`, `PER_CLIENT`, `PER_CLIENT_ZSCORE`, `POOLED_ZSCORE`

#### Other enums in `datp/core/enums.py`:

- `ClientStatus`: `ELIGIBLE`, `CALIBRATION_PENDING`
- `BaselineRunStatus`: `DONE`, `SKIPPED`, `FAILED`
- `PipelineStage`: `PREPARE`, `TRAIN`, `SCORE`, `THRESHOLD`, `EVALUATE`, `REPORT`
- `Activation`: `RELU`, `LEAKY_RELU`, `ELU`, `TANH`, `SIGMOID`
- `B0NormalizationMode`: `PER_CLIENT_PREPARED`, `POOLED_ZSCORE`
- `BaselineRole`: `CONTROLLED_THRESHOLD`, `CENTRALIZED_REFERENCE`

### `datp/core/metric_enums.py`

#### `MetricName`

- Base: `StrEnum`
- Members: `FPR`, `TPR`, `TNR`, `FNR`, `PRECISION`, `RECALL`, `MACRO_F1`, `BALANCED_ACCURACY`, `AUROC`, `PR_AUC`, `CV_FPR`, `CV_TPR`, `MEAN_FPR`, `STD_FPR`, `IQR_FPR`, `IQR_TPR`, `WORST_CLIENT_FPR`, `WORST_BA`, `P10_MACRO_F1`, `WORST_CLIENT_TPR`, `WORST_CLIENT_MACRO_F1`, `WORST_CLIENT_BALANCED_ACCURACY`, `MAX_MIN_FPR_GAP`, `TAU_GLOBAL`, `WORST_CLIENT_ID`

#### `PayloadKey`

- Base: `StrEnum`
- Members: 30+ members covering metrics payload serialization keys

#### `ConfusionKey`

- Base: `StrEnum`
- Members: `TP`, `FP`, `TN`, `FN`

#### `AuditField`

- Base: `StrEnum`
- Members: schema keys for reporting audit payload

#### `ValidationField`

- Base: `StrEnum`
- Members: `STATUS`, `SOURCE`, `VALIDATED_REGIMES`, `SEEDS`, `REGIME_C_ALPHAS`

### `datp/core/poison_enums.py`

#### `ThresholdPolicy`

- Base: `StrEnum`
- Members: `B1_GLOBAL = "b1_global"`, `B2_PERSONALIZED = "b2_personalized"`, `B4_CLUSTER = "b4_cluster"`
- Note: B3 excluded by protocol

#### `AttackerObjective`

- Base: `StrEnum`
- Members: `THRESHOLD_RAISE = "threshold_raise"`, `THRESHOLD_LOWER = "threshold_lower"`

#### `PoisoningSourceStrategy`

- Base: `StrEnum`
- Members: `RANDOM_BENIGN`, `HIGH_SCORE_BENIGN`, `LOW_SCORE_BENIGN`, `LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY`

#### `CalibrationInjectionRule`

- Base: `StrEnum`
- Members: `REPLACE_FIXED_BUDGET = "replace_fixed_budget"`

#### `PoisoningKnowledge`

- Base: `StrEnum`
- Members: `GRAY_BOX_SCORE_ACCESS`, `WHITE_BOX_DIAGNOSTIC_ONLY`

#### `PoisoningTargetScope`

- Base: `StrEnum`
- Members: `SINGLE_CLIENT`, `MULTI_CLIENT`, `ALL_CLIENTS_DIAGNOSTIC_ONLY`

#### `PoisoningDefense`

- Base: `StrEnum`
- Members: `NONE`, `TRIMMED_CALIBRATION`

#### `ExperimentScale`

- Base: `StrEnum`
- Members: `SMOKE`, `BOUNDED`, `FULL`, `STRETCH`

#### `AuditDisposition`

- Base: `StrEnum`
- Members: `KEEP_CORE`, `REFACTOR_CORE`, `QUARANTINE_JOURNAL`, `REMOVE_STALE`, `BLOCK_UNSAFE`

### `datp/artifacts/names.py`

#### `ArtifactDir`

- Base: `StrEnum`
- Members: `OUTPUTS`, `RESULTS`, `CHECKPOINTS`, `SCORES`, `LOGS`, `CONSOLE_LOGS`, `ANALYSIS`, `FIGURES`, `TABLES`, `CONFUSION_MATRICES`

#### `RunState`

- Base: `StrEnum`
- Members: `IN_PROGRESS`, `DONE`, `ABORTED`, `CORRUPT`

### `datp/artifacts/poison_names.py`

#### `ManifestFile`

- Base: `StrEnum`
- Members: `PROJECT_AUDIT_REPORT`, `CLEAN_SCORE_ARTIFACTS`, `NBAIOT_BOUNDED_SWEEP_MANIFEST`, `PAPER_FIGURE_MANIFEST`, `RUN_MANIFEST`

#### `RunFile`

- Base: `StrEnum`
- Members: `POISONED_SCORES`, `THRESHOLD_DELTAS`, `CELL_METRICS`, `SEED_RECORD`, `PROVENANCE`, `RUN_DONE`, `RUN_IN_PROGRESS`

### `datp/core/identity.py`

#### `AlphaLabel`

- Base: `StrEnum`
- Members: `IID = "iid"`

### `datp/attacks/reservoir.py`

#### `ReservoirStatus`

- Base: `StrEnum`
- Members: `FEASIBLE`, `INFEASIBLE_DEGENERATE_TAIL`

### `datp/experiments/enums.py`

#### `DiagnosticStep`, `SweepStep`, `ContingencyDecision`

- All `StrEnum` with step/decision members

### `datp/checkpointing/enums.py`

- `ConvergenceStatus`, `CheckpointProtocolMode`, `CheckpointConvergenceMode`, `PrimaryCheckpointSelectionRule`, `CheckpointArtifactPathMode`, `CheckpointArtifactStatus`, `CheckpointSelectionVerdict`, `ConvergenceSummaryKey`, `EvidenceRole`

### `datp/reporting/enums.py`

- `FigureName`: `FIGURE_1`, `FIGURE_2`, `FIGURE_3`, `FIGURE_4`

### `datp/config/stages.py`

- `ExperimentStage`

### `datp/data/catalog.py`

- `SplitPolicyKind`, `SplitPolicyRole`, `CapStrategy`

## B. Enumerated Raw Domain Values

### Raw values representing attack direction

- Values: `"raise"`, `"lower"`
- Locations: function parameters, configuration values, string comparisons
- Current forms: function parameters, string comparisons
- Related existing enums: `AttackerObjective`

### Raw values representing threshold policies

- Values: `"b1_global"`, `"b2_personalized"`, `"b4_cluster"`, `"b1"`, `"b2"`, `"b4"`
- Locations: CLI parsing, manifest serialization, test expectations
- Related existing enums: `ThresholdPolicy`

### Raw values representing fraction strings

- Values: `"0.00"`, `"0.10"`, `"0.20"`, `"0.40"`, `"0.05"`
- Locations: path construction, fraction formatting
- Current forms: `f"f_{fraction:.2f}"` in `poison_layout.py`

## C. Existing Dataclasses

### `datp/core/types.py`

- `FrozenModel` — Pydantic BaseModel base class
- `MetricsProvenance` — provenance metadata for metrics artifacts
- `AnalysisRowBase` — base class for analysis result rows
- `B3FamilyInfo` — frozen, slots: `tau_family`, `eligible_count`, `members`, `threshold_variance`, `singleton`
- `B3Metadata` — frozen, slots: `family_info: dict[str, B3FamilyInfo]`
- `B4ClusterInfo` — frozen, slots: `tau_cluster`, `members`
- `B4Metadata` — frozen, slots: `cluster_info`, `fingerprints`, `silhouette`, `silhouette_scores`, `k`
- `ClientThreshold` — frozen, slots: `client_id`, `threshold`, `calibration_pending`, `strategy`
- `ThresholdMetadata` — frozen, slots: `b3`, `b4`
- `ThresholdResult` — frozen, slots: `run`, `tau_global`, `client_thresholds`, `metadata`
- `ClientEvalResult` — Pydantic FrozenModel: `fpr`, `tpr`, `balanced_accuracy`, `macro_f1`, etc.
- `ClientEvalResultWithAuroc` — extends ClientEvalResult with `auroc`, `pr_auc`
- `BaselineResult` — Pydantic FrozenModel
- `B0Result` — Pydantic FrozenModel extends BaselineResult

### `datp/core/identity.py`

- `TrainingCellId` — frozen, slots: `regime`, `seed`, `alpha`
- `BaselineRunId` — frozen, slots: `cell`, `baseline`

### `datp/core/seed_sequence.py`

- `SeedRecord` — frozen, slots: `training_seed`, `poisoning_seed`, `client_idx`, `scope_idx`

### `datp/attacks/injector.py`

- `InjectionResult` — frozen, slots: `poisoned_cal`, `n_replaced`, `n_total`, `fraction`, `positions_replaced`

### `datp/attacks/reservoir.py`

- `ReservoirResult` — frozen, slots: `pool`, `status`, `source`, `n_pool`, `n_distinct`

### `datp/attacks/score_containers.py`

- `ClientScores` — frozen, slots: `client_id`, `cal`, `test_benign`, `test_attack`
- `ScoreCollection` — frozen, slots: `clients`, `n_min`, `_eligible_ids`, `_pending_ids`
- `VictimSet` — frozen, slots: `eligible_ids`, `collection`

### `datp/artifacts/layout.py`

- `ScoreCellPaths` — frozen, slots: `cell`, `checkpoint_dir`, `score_dir`, `manifest_path`, `checkpoint_round`
- `BaselineRunPaths` — frozen, slots: `run`, `result_dir`, `log_dir`, `metrics_path`, `checkpoint_round`
- `ArtifactLayout` — frozen, slots: `base_dir`, `regime`

### `datp/artifacts/poison_layout.py`

- `CellId` — frozen, slots: `scale`, `dataset`, `policy`, `objective`, `source`, `fraction`, `target_scope`, `training_seed`, `poisoning_seed`
- `CellPaths` — frozen, slots: `cell`, `run_dir`, `poisoned_scores`, `threshold_deltas`, `cell_metrics`, `seed_record`, `provenance`, `run_done`, `run_in_progress`
- `PoisonLayout` — frozen, slots: `base_dir`

### `datp/attacks/b4_recompute.py`

- `B4DecompEntry` — frozen, slots: `client_id`, `tau_clean`, `tau_agg`, `tau_pois`, `delta_tau_agg`, `delta_tau_churn`, `delta_tau_total`
- `B4ThresholdPair` — frozen, slots: `policy`, `tau_global_clean`, `tau_global_pois`, `thresholds_clean`, `thresholds_pois`, `decomposition`

### `datp/attacks/bounded_sweep_matrix.py`

- `SweepCellSpec` — frozen, slots: `training_seed`, `poisoning_seed`, `victim_id`, `policy`, `source`, `fraction`, `target_scope`

### `datp/attacks/bounded_sweep_cell.py`

- `SweepCellResult` — frozen, slots: `policy`, `victim_id`, `source`, `fraction`, `training_seed`, `poisoning_seed`, `clean_pair`, `poisoned_pair`, `clean_metrics`, `poisoned_metrics`

### `datp/attacks/bounded_sweep_manifest.py`

- `BoundedSweepResultRow` — Pydantic BaseModel, frozen
- `BoundedSweepManifest` — Pydantic BaseModel, frozen

### `datp/attacks/run_manifest.py`

- `RunManifest`, `ProvenanceRecord`, `SeedRecordModel` — Pydantic models

### `datp/attacks/metric_engine.py`

- `MetricResult`, `FleetFprResult`, `DeltaTauResult`, `AurocRecord` — dataclasses

### `datp/attacks/compromise_patterns.py`

- `CompromiseEntry`, `CompromiseResult` — dataclasses

### `datp/attacks/run_logger.py`

- `RunLogEntry` — dataclass

### `datp/attacks/cell_runner.py`

- `PolicyPair`, `SingleVictimOutcome` — dataclasses

### `datp/evaluation/metrics.py`

- `ConfusionCounts`, `BinaryMetrics`, `ClientEvaluationRecord`, `DispersionMetrics`, `EvaluationResult`, `PerAttackFamilyTPR` — dataclasses

### `datp/evaluation/ranking.py`

- `BinaryRankingMetrics` — dataclass

### `datp/evaluation/artifact_validation.py`

- `ValidationIds`, `ClientRowContext` — dataclasses

### `datp/experiments/models.py`

- `PipelineRequest`, `SharedPipelineContext` — dataclasses
- `ContingencyRecord` — Pydantic FrozenModel

### `datp/checkpointing/invariants.py`

- `ScoreManifestIdentity`, `CheckpointEvaluationInvariant` — dataclasses

### `datp/checkpointing/summary.py`

- `CheckpointBaselineSummary`, `CheckpointRegimeAComparison`, `GlobalCheckpointSelection` — dataclasses

### `datp/validation/_audit_types.py`

- `_CellPanel`, `_AuditAccumulator` — dataclasses

### `datp/validation/schemas.py`

- `ValidationCheck` — Pydantic model

### `datp/data/catalog.py`

- `SplitPolicy`, `CapPolicy`, `DatasetSpec` — dataclasses or Pydantic models

## D. Repeated Structured Data Groups

### Repeated group: B4 clustering parameters

- Fields: `k`, `n_init`, `max_iter`, `random_state`
- Locations: `datp.artifacts.poison_names` (constants), `datp.attacks.b4_recompute.py` (function params), `datp.config.models.py` (ThresholdConfig), `datp.config.attack_config.py` (B4ClusterConfig)
- Existing owner objects: `B4ClusterConfig`, `ThresholdConfig`

### Repeated group: training/poisoning seed pair

- Fields: `training_seed`, `poisoning_seed`
- Locations: `SweepCellSpec`, `CellId`, `SeedRecord`, function parameters in `run_sweep_cell`, `inject_single_victim`, `run_nbaiot_bounded_sweep`
- Existing constants: `TRAINING_SEEDS`, `POISONING_SEEDS`

## E. Constants

### `datp/artifacts/poison_names.py`

- `CALIBRATION_POISONING_OUTPUT_ROOT = "conference_calibration_poisoning"` — category: output-root path fragment
- `N_MIN = 100` — category: scientific default
- `TAIL_MASS = 0.10` — category: scientific default
- `MATERIALITY_FACTOR = 0.1` — category: scientific default
- `THRESHOLD_QUANTILE = 0.95` — category: scientific default
- `TRIM_FRACTION_PRIMARY = 0.05` — category: scientific default
- `TRIM_FRACTION_APPENDIX = 0.10` — category: scientific default
- `B4_K = 3` — category: scientific default
- `B4_N_INIT = 10` — category: scientific default
- `B4_MAX_ITER = 300` — category: scientific default
- `B4_RANDOM_STATE = 42` — category: seed value
- `TRAINING_SEEDS = (0, 1, 2, 3, 4)` — category: seed value
- `POISONING_SEEDS = (100, 101, 102, 103, 104)` — category: seed value
- `ANALYSIS_SEEDS = (300, 301, 302, 303, 304)` — category: seed value
- `COMPROMISE_PATTERN_SEED = 400` — category: seed value

### `datp/core/poison_enums.py`

- `BOUNDED_SWEEP_FRACTIONS = (0.0, 0.10, 0.20, 0.40)` — category: scientific default
- `FULL_SWEEP_FRACTIONS = (0.0, 0.05, 0.10, 0.20, 0.40)` — category: scientific default
- `DEFAULT_POLICIES = (B1_GLOBAL, B2_PERSONALIZED, B4_CLUSTER)` — category: domain vocabulary
- `BOUNDED_SWEEP_OBJECTIVES = (THRESHOLD_RAISE, THRESHOLD_LOWER)` — category: domain vocabulary
- `BOUNDED_SWEEP_SOURCES = (RANDOM_BENIGN, HIGH_SCORE_BENIGN, LOW_SCORE_BENIGN)` — category: domain vocabulary

## F. Configuration Values and Defaults

### `DatpConfig` (in `datp/config/models.py`)

- Pydantic BaseModel fields (from `src/datp/conf/config.yaml`):
  - `model.input_dim: 115`, `encoder_dims: [80, 40, 20]`, `lr: 0.001`, `epochs: 200`, `patience: 10`
  - `dataset.feature_count: 115`, `n_min: 100`, `cap: 50000`, `b0_val_fraction: 0.1`
  - `machine.batch_size_train: 256`, `per_client_ram_gb: 1.5`
  - `federation.rounds_initial: 40`, `rounds_max: 150`, `relative_threshold: 0.005`, `local_epochs: 1`
  - `threshold.q: 0.95`, `b4_regime_a_mode: "fixed"`, `b4_k_regime_a: 3`, `b4_k_candidates: [2,3,4,5]`
  - `experiment.seeds: [0,1,2,3,4]`, `regime_c_alphas: [0.1, 0.3, 0.5, 1.0, 10.0, .inf]`
  - `statistics.n_bootstrap: 10000`, `ci_level: 0.95`, `significance_alpha: 0.05`
  - `quality_gates.b0_sanity_min: 0.90`
  - `reporting.figure2_max_points: 5000`
  - `runtime.lock_timeout_seconds: 3600.0`
  - `logging.level: "INFO"`

### `CalibrationPoisoningConfig` (in `datp/config/attack_config.py`)

- Pydantic model with seed pools, B4 cluster config

### `ExperimentStageConfig` (in `datp/config/stages.py`)

- Dataclass with gate requirements for each experiment stage

## G. Cross-References

- Constants file: `datp/artifacts/poison_names.py` is the primary constants location for CP2 scientific defaults
- Module-level constants: `datp/core/poison_enums.py` contains sweep-fraction and policy tuple constants
- Config-driven values: `datp/config/models.py` and `datp/conf/config.yaml`
