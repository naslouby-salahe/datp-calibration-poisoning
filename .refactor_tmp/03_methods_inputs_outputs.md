# 03 — Methods, Functions, Inputs, Outputs, and Side Effects

## A. Inventory Method

Functions were enumerated via AST parsing (graphify) and manually validated by reading every source file across all packages. The graphify AST extraction processed 487 files total.

## B. Public Symbols

### `datp.core` — Core infrastructure functions

#### `datp.core.seeds.set_seeds`

- Kind: `function`
- Location: `src/datp/core/seeds.py:12`
- Package: `datp.core`
- Module: `datp.core.seeds`
- Inputs: `seed: int`
- Defaults: none
- Output: `None`
- Side effects: Sets Python random, NumPy, PyTorch, cuDNN seeds
- Reads from disk: none
- Writes to disk: none
- Uses enums: none
- Scientific concepts: determinism

#### `datp.core.seed_sequence.make_seed_rng`

- Kind: `function`
- Location: `src/datp/core/seed_sequence.py:46`
- Inputs: `training_seed: int`, `poisoning_seed: int`, `client_idx: int`, `scope_idx: int`, `child_index: int=0`
- Output: `np.random.Generator`
- Side effects: none
- Scientific concepts: SeedSequence derivation, no integer addition

#### `datp.core.seed_sequence.derive_seed_record`

- Kind: `function`
- Location: `src/datp/core/seed_sequence.py:71`
- Inputs: `training_seed: int`, `poisoning_seed: int`, `client_idx: int`, `scope_idx: int`
- Output: `SeedRecord`

#### `datp.core.provenance.utc_timestamp`

- Kind: `function`
- Location: `src/datp/core/provenance.py:18`

#### `datp.core.provenance.sha256_bytes`

- Kind: `function`
- Location: `src/datp/core/provenance.py:21`

#### `datp.core.provenance.hash_file`

- Kind: `function`
- Location: `src/datp/core/provenance.py:25`

#### `datp.core.provenance.hash_jsonable`

- Kind: `function`
- Location: `src/datp/core/provenance.py:37`

#### `datp.core.provenance.git_commit`

- Kind: `function`
- Location: `src/datp/core/provenance.py:43`

#### `datp.core.provenance.source_hash`

- Kind: `function`
- Location: `src/datp/core/provenance.py:55`

#### `datp.core.provenance.array_hash`

- Kind: `function`
- Location: `src/datp/core/provenance.py:64`

#### `datp.core.device.resolve_device`

- Kind: `function`
- Location: `src/datp/core/device.py:12`
- Inputs: `require_cuda: bool`
- Output: `torch.device`
- Exceptions: `RuntimeError` when CUDA required but unavailable
- Scientific concepts: CUDA/CPU device resolution

#### `datp.core.errors.fmt`

- Kind: `function`
- Location: `src/datp/core/errors.py:9`
- Inputs: `module: str`, `problem: str`, `expected: str`, `got: str`
- Output: `str`

#### `datp.core.errors.fmt_missing`

- Kind: `function`
- Location: `src/datp/core/errors.py:15`
- Inputs: `module: str`, `what: str`
- Output: `str`

#### `datp.core.logging.configure_logging`

- Kind: `function`
- Location: `src/datp/core/logging.py`
- Inputs: `config: LoggingConfig`, `log_dir: Path | None`
- Output: logger instance

#### `datp.core.identity.make_run_id`

- Kind: `function`
- Location: `src/datp/core/identity.py:71`
- Inputs: `regime: Regime`, `seed: int`, `alpha: float | None = None`
- Output: `str`

#### `datp.core.identity.alpha_label`

- Kind: `function`
- Location: `src/datp/core/identity.py:48`
- Inputs: `alpha: float | None`
- Output: `str | None`

#### `datp.core.identity.alpha_from_label`

- Kind: `function`
- Location: `src/datp/core/identity.py:55`
- Inputs: `label: str | None`
- Output: `float | None`

#### `datp.core.identity.format_alpha_dir`

- Kind: `function`
- Location: `src/datp/core/identity.py:61`
- Inputs: `alpha: float`
- Output: `str`

#### `datp.core.identity.parse_alpha_dir`

- Kind: `function`
- Location: `src/datp/core/identity.py:67`
- Inputs: `name: str`
- Output: `float | None`

#### `datp.core.identity.seed_segment`

- Kind: `function`
- Location: `src/datp/core/identity.py:77`
- Inputs: `seed: int`
- Output: `str`

#### `datp.core.enums.classify_absorption`

- Kind: `function`
- Location: `src/datp/core/enums.py` (near end of file)
- Inputs: `ratio: float`, `strong_retention_threshold: float`, `partial_threshold: float`
- Output: `AbsorptionClass`

### `datp.attacks` — Attack functions

#### `datp.attacks.injector.inject_fixed_budget`

- Kind: `function`
- Location: `src/datp/attacks/injector.py:33`
- Inputs: `clean_cal: np.ndarray`, `reservoir: ReservoirResult`, `fraction: float`, `rng: np.random.Generator`
- Defaults: none
- Output: `InjectionResult`
- Exceptions: `ValueError` when fraction outside [0,1] or reservoir INFEASIBLE
- Side effects: none (operates on copy)
- Reads from disk: none
- Writes to disk: none
- Uses enums: `ReservoirStatus`
- Scientific concepts: REPLACE_FIXED_BUDGET injection, no in-place mutation

#### `datp.attacks.reservoir.build_reservoir`

- Kind: `function`
- Location: `src/datp/attacks/reservoir.py:50`
- Inputs: `clean_cal: np.ndarray`, `source: PoisoningSourceStrategy`, `tail_mass: float`
- Output: `ReservoirResult`
- Exceptions: `ValueError` for unsupported source strategy
- Side effects: none
- Scientific concepts: victim-local reservoir, RANDOM/HIGH/LOW sources, degenerate tail detection

#### `datp.attacks.source_strategies.select_reservoir`

- Kind: `function`
- Location: `src/datp/attacks/source_strategies.py:55`
- Inputs: `source: PoisoningSourceStrategy`, `clean_cal: np.ndarray`, `tail_mass: float`, `allow_diagnostic: bool = False`
- Output: `ReservoirResult`
- Exceptions: `DiagnosticSourceError` if diagnostic source without allow_diagnostic

#### `datp.attacks.source_strategies.objective_for_source`

- Kind: `function`
- Location: `src/datp/attacks/source_strategies.py:85`
- Inputs: `source: PoisoningSourceStrategy`
- Output: `AttackerObjective | None`

#### `datp.attacks.source_strategies.near_null_criterion`

- Kind: `function`
- Location: `src/datp/attacks/source_strategies.py:99`
- Inputs: `delta_tau: float`, `delta_tau_null_threshold: float`
- Output: `bool`

#### `datp.attacks.cell_runner.inject_single_victim`

- Kind: `function`
- Location: `src/datp/attacks/cell_runner.py` (near line 35)
- Inputs: `collection: ScoreCollection`, `victim_id: str`, `source: PoisoningSourceStrategy`, `fraction: float`, `training_seed: int`, `poisoning_seed: int`, `scope_idx: int = 0`
- Output: `SingleVictimOutcome`
- Side effects: none
- Scientific concepts: single-victim injection with SeedSequence

#### `datp.attacks.cell_runner.recompute_pair`

- Kind: `function`
- Location: `src/datp/attacks/cell_runner.py`
- Inputs: `collection: ScoreCollection`, `poisoned_cal: dict[str, np.ndarray]`, `policy: ThresholdPolicy`, `q: float`, `seed: int = 0`
- Output: `PolicyPair`
- Scientific concepts: threshold recomputation from (possibly poisoned) calibration scores

#### `datp.attacks.bounded_sweep_cell.lock_mu_flag_threshold`

- Kind: `function`
- Location: `src/datp/attacks/bounded_sweep_cell.py:40`
- Inputs: `collection: ScoreCollection`, `q: float = THRESHOLD_QUANTILE`
- Output: `float`
- Side effects: none
- Scientific concepts: mu_flag_threshold locked once per training seed from clean B1

#### `datp.attacks.bounded_sweep_cell.run_sweep_cell`

- Kind: `function`
- Location: `src/datp/attacks/bounded_sweep_cell.py:76`
- Inputs: `collection`, `victim_id`, `policy`, `source`, `fraction`, `training_seed`, `poisoning_seed`, `mu_flag_threshold`, `scope_idx=0`, `q`, `b4_seed=0`, `auroc_records`
- Output: `SweepCellResult`

#### `datp.attacks.bounded_sweep_matrix.enumerate_bounded_sweep_matrix`

- Kind: `function`
- Location: `src/datp/attacks/bounded_sweep_matrix.py:72`
- Inputs: `victims_by_training_seed: Mapping[int, Sequence[str]]`
- Output: `tuple[SweepCellSpec, ...]`

#### `datp.attacks.bounded_sweep_matrix.enumerate_full_sweep_matrix`

- Kind: `function`
- Location: `src/datp/attacks/bounded_sweep_matrix.py:83`
- Inputs: `victims_by_training_seed: Mapping[int, Sequence[str]]`
- Output: `tuple[SweepCellSpec, ...]`

#### `datp.attacks.bounded_sweep_run.run_nbaiot_bounded_sweep`

- Kind: `function`
- Location: `src/datp/attacks/bounded_sweep_run.py:99`
- Inputs: `base_dir: Path`
- Output: `BoundedSweepManifest`

#### `datp.attacks.bounded_sweep_run.write_nbaiot_bounded_sweep_manifest`

- Kind: `function`
- Location: `src/datp/attacks/bounded_sweep_run.py:154`
- Inputs: `base_dir: Path`
- Output: `Path` (written path)
- Writes to disk: bounded sweep manifest JSON

#### `datp.attacks.b4_recompute.compute_b4_pair`

- Kind: `function`
- Location: `src/datp/attacks/b4_recompute.py:131`
- Inputs: `collection: ScoreCollection`, `poisoned_cal: dict[str, np.ndarray]`, `q: float`, `k`, `n_init`, `max_iter`, `random_state`, `n_min`, `seed: int = 0`
- Output: `B4ThresholdPair`

#### `datp.attacks.guardrails.assert_no_inplace_mutation`

- Kind: `function`
- Location: `src/datp/attacks/guardrails.py:37`
- Inputs: `original: np.ndarray`, `after: np.ndarray`, `label: str = "calibration array"`
- Exceptions: `GuardrailError`

#### `datp.attacks.guardrails.assert_reservoir_not_test_or_training`

- Kind: `function`
- Location: `src/datp/attacks/guardrails.py:67`
- Inputs: `reservoir_label: str`
- Exceptions: `GuardrailError`

#### `datp.attacks.guardrails.assert_policy_not_b3`

- Kind: `function`
- Location: `src/datp/attacks/guardrails.py:91`
- Inputs: `policy: ThresholdPolicy`
- Exceptions: `GuardrailError`

#### `datp.attacks.guardrails.assert_fractions_in_locked_grid`

- Kind: `function`
- Location: `src/datp/attacks/guardrails.py:110`
- Inputs: `fractions: Sequence[float]`, `scale: ExperimentScale`
- Exceptions: `GuardrailError`

#### `datp.attacks.guardrails.assert_bounded_scale_requires_single_client`

- Kind: `function`
- Location: `src/datp/attacks/guardrails.py:148`
- Inputs: `scale: ExperimentScale`, `target_scope_value: str`
- Exceptions: `GuardrailError`

#### `datp.attacks.metric_engine.compute_delta_tau`

- Kind: `function`
- Location: `src/datp/attacks/metric_engine.py`
- Inputs: per-client thresholds and relevant equations
- Output: `DeltaTauResult`

#### `datp.attacks.metric_engine.compute_fleet_fpr`

- Kind: `function`
- Location: `src/datp/attacks/metric_engine.py`
- Output: `FleetFprResult`

#### `datp.attacks.metric_engine.compute_auroc_records`

- Kind: `function`
- Location: `src/datp/attacks/metric_engine.py`
- Output: `dict[str, AurocRecord]`

#### `datp.attacks.metric_engine.compute_mu_flag_threshold`

- Kind: `function`
- Location: `src/datp/attacks/metric_engine.py`
- Output: `float`

#### `datp.attacks.metric_engine.compute_metrics`

- Kind: `function`
- Location: `src/datp/attacks/metric_engine.py`
- Inputs: `collection`, `pair`, `mu_flag_threshold`, `auroc_records`
- Output: `MetricResult`

#### `datp.attacks.inference.collect_paired_deltas`

- Kind: `function`
- Location: `src/datp/attacks/inference.py`
- Inputs: manifest results
- Output: paired delta structures

#### `datp.attacks.inference.compute_seed_aggregates`

- Kind: `function`

#### `datp.attacks.inference.sign_test`

- Kind: `function`

#### `datp.attacks.inference.holm_adjust`

- Kind: `function`

#### `datp.attacks.inference.bootstrap_seed_aggregates`

- Kind: `function`

#### `datp.attacks.inference.compute_inference`

- Kind: `function`

#### `datp.attacks.diagnostics.compute_asr`

- Kind: `function`
- Scientific concepts: attack success rate

#### `datp.attacks.diagnostics.compute_blast_radius`

- Kind: `function`

#### `datp.attacks.diagnostics.compute_spillover`

- Kind: `function`

#### `datp.attacks.defenses.apply_defense`

- Kind: `function`
- Inputs: defense configuration, calibration scores
- Output: modified calibration scores
- Scientific concepts: trimmed calibration defense

#### `datp.attacks.compromise_patterns.select_pairs`

- Kind: `function`
- Inputs: victim set, seed
- Output: `CompromiseResult`
- Scientific concepts: co-victim pair selection

#### `datp.attacks.compromise_patterns.select_triples`

- Kind: `function`

#### `datp.attacks.real_score_loader.load_real_score_collection`

- Kind: `function`
- Inputs: data path, regime
- Output: `ScoreCollection`
- Reads from disk: Parquet score files

### `datp.artifacts` — Artifact and layout functions

#### `datp.artifacts.io.write_json_atomic`

- Kind: `function`
- Location: `src/datp/artifacts/io.py:28`
- Inputs: `path: Path`, `data: Any`
- Output: `Path`
- Writes to disk: atomic JSON via tmp->rename

#### `datp.artifacts.io.write_csv`

- Kind: `function`
- Location: `src/datp/artifacts/io.py:44`
- Inputs: `path: Path`, `records: Sequence[BaseModel]`
- Writes to disk: atomic CSV via tmp->rename

#### `datp.artifacts.io.write_metrics_atomic`

- Kind: `function`
- Location: `src/datp/artifacts/io.py:54`
- Inputs: `run_dir: Path`, `metrics: Any`
- Output: `Path`

#### `datp.artifacts.existence.results_exist`

- Kind: `function`
- Location: `src/datp/artifacts/existence.py:14`
- Inputs: `baseline: Baseline`, `regime: Regime`, `seed: int`, `alpha: float | None`, `base_dir: Path`
- Output: `bool`
- Reads from disk: metrics.json, validates payload schema

#### `datp.artifacts.lifecycle.check_run_state`

- Kind: `function`
- Location: `src/datp/artifacts/lifecycle.py:19`
- Inputs: `run_dir: Path`
- Output: `RunState`

### `datp.thresholding` — Threshold functions

#### `datp.thresholding.eligibility.identify_eligible`

- Kind: `function`
- Location: `src/datp/thresholding/eligibility.py:14`
- Inputs: `client_errors: dict[str, np.ndarray]`, `n_min: int`
- Output: `tuple[list[str], list[str]]` (eligible_ids, pending_ids)

#### `datp.thresholding.eligibility.compute_client_thresholds`

- Kind: `function`
- Location: `src/datp/thresholding/eligibility.py:26`
- Inputs: `client_errors: dict[str, np.ndarray]`, `eligible: list[str]`, `q: float`
- Output: `dict[str, float]`

#### `datp.thresholding.eligibility.compute_tau_global`

- Kind: `function`
- Location: `src/datp/thresholding/eligibility.py:34`
- Inputs: `client_taus: dict[str, float]`
- Output: `float`
- Scientific concepts: tau_global = (1/K_elig) * sum(tau_i)

#### `datp.thresholding.eligibility.build_threshold_result`

- Kind: `function`
- Location: `src/datp/thresholding/eligibility.py:44`
- Inputs: `run`, `tau_global`, `eligible_thresholds`, `pending_clients`, `b3_metadata`, `b4_metadata`
- Output: `ThresholdResult`

#### `datp.statistics.cv.cv`

- Kind: `function`
- Inputs: array of values
- Output: `float` — coefficient of variation (sigma/mu, no epsilon)

#### `datp.statistics.bootstrap.bca_ci`

- Kind: `function`
- Inputs: data array, n_bootstrap, ci_level, seed
- Output: `BootstrapResult`

## C. Internal Scientific and Domain Symbols

(All documented in sections above under their respective packages.)

## D. Serialization, Layout, and Manifest Symbols

### PoisonLayout methods

#### `PoisonLayout.run_dir(cell: CellId) -> Path`

- Location: `src/datp/artifacts/poison_layout.py:87`

#### `PoisonLayout.cell_paths(cell: CellId) -> CellPaths`

- Location: `src/datp/artifacts/poison_layout.py:96`

#### `PoisonLayout.project_audit_report() -> Path`

#### `PoisonLayout.clean_score_artifacts_manifest() -> Path`

#### `PoisonLayout.nbaiot_bounded_sweep_manifest() -> Path`

#### `PoisonLayout.paper_figure_manifest() -> Path`

### ArtifactLayout methods

#### `ArtifactLayout.checkpoint_dir(cell: TrainingCellId) -> Path`

#### `ArtifactLayout.score_cell(cell: TrainingCellId) -> ScoreCellPaths`

#### `ArtifactLayout.baseline_run(run: BaselineRunId) -> BaselineRunPaths`

#### `ArtifactLayout.score_file(cell, stage, client_id) -> Path`

## E. CLI and Orchestration Symbols

(All documented in `datp.app.cli` package entry above.)

## F. Validation Symbols

(All documented in `datp.validation` package entry.)

## G. Repeated Input Groups

### Repeated input group: calibration-poisoning cell identity

- Fields observed:
  - `threshold_policy` / `policy: ThresholdPolicy`
  - `source_strategy` / `source: PoisoningSourceStrategy`
  - `attack_objective` / `objective: AttackerObjective`
  - `poison_fraction` / `fraction: float`
  - `training_seed: int`
  - `poisoning_seed: int`
  - `victim_client_id` / `victim_id: str`
- Observed in:
  - `SweepCellSpec` (dataclass in `bounded_sweep_matrix.py`)
  - `CellId` (dataclass in `poison_layout.py`)
  - `SweepCellResult` (dataclass in `bounded_sweep_cell.py`)
  - `BoundedSweepResultRow` (Pydantic model in `bounded_sweep_manifest.py`)
  - `SeedRecord` (dataclass in `seed_sequence.py`)
  - Function parameters in `run_sweep_cell`, `inject_single_victim`
- Existing typed containers containing some or all fields:
  - `SweepCellSpec` — training_seed, poisoning_seed, victim_id, policy, source, fraction, target_scope
  - `CellId` — scale, dataset, policy, objective, source, fraction, target_scope, training_seed, poisoning_seed
  - `SeedRecord` — training_seed, poisoning_seed, client_idx, scope_idx

### Repeated input group: B4 clustering parameters

- Fields:
  - `k` / `n_clusters`: int
  - `n_init`: int
  - `max_iter`: int
  - `random_state`: int
- Locations:
  - `datp.artifacts.poison_names` (constants `B4_K`, `B4_N_INIT`, `B4_MAX_ITER`, `B4_RANDOM_STATE`)
  - `datp.attacks.b4_recompute.py` (function parameters)
  - `datp.config.models.py` (ThresholdConfig)
  - `datp.config.attack_config.py` (B4ClusterConfig)
- Existing owner objects:
  - `B4ClusterConfig` in `datp.config.attack_config`
  - `ThresholdConfig` in `datp.config.models`
