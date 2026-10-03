from __future__ import annotations

import enum
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, cast

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from datp.enums import (
    CONTROLLED_POLICIES,
    Activation,
    ArtifactFile,
    AttackerObjective,
    CalibrationInjectionRule,
    LogLevel,
    NBaIoTBalancePolicy,
    PoisoningDefense,
    PoisoningKnowledge,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ThresholdPolicy,
)
from datp.types import (
    BatchSize,
    BootstrapCount,
    ByteCount,
    ClusterCount,
    DurationSeconds,
    EpochCount,
    FeatureCount,
    GpuShare,
    IntervalBound,
    IterationCount,
    LearningRate,
    MemoryAmount,
    NarrativeText,
    PoisonFraction,
    Quantile,
    RandomSeed,
    RoundCount,
    SampleCount,
    ScoreValue,
    SignedCount,
    Threshold,
    Tolerance,
    WorkerCount,
)


class ExperimentStage(enum.StrEnum):

    NBAIOT_MAIN = "nbaiot_main"


class StrictModel(BaseModel):

    model_config = ConfigDict(extra="forbid", frozen=True, protected_namespaces=())


class SafetyBounds(StrictModel):

    max_batch_size_train: BatchSize


class ConvergenceConfig(StrictModel):

    rounds_initial: RoundCount
    rounds_max: RoundCount
    relative_threshold: Threshold
    window: RoundCount
    round_timeout_s: DurationSeconds


class ModelConfig(StrictModel):

    input_dim: FeatureCount
    encoder_dims: list[SignedCount]
    lr: LearningRate
    epochs: EpochCount
    activation: Activation
    use_bn: bool


class DatasetConfig(StrictModel):

    feature_count: FeatureCount
    nbaiot_test_balance: NBaIoTBalancePolicy


class MachineConfig(StrictModel):

    batch_size_train: BatchSize = Field(gt=0)
    scoring_batch_size: BatchSize = Field(default=256, gt=0)
    require_cuda: bool = False
    ray_num_gpus_per_client: GpuShare = Field(default=0.0, ge=0)
    per_client_ram_gb: MemoryAmount = Field(gt=0)
    reserve_ram_gb: MemoryAmount = Field(ge=0)
    max_concurrent_override: WorkerCount | None = Field(gt=0, default=None)
    ray_object_store_mb: ByteCount = Field(gt=0)
    safety_bounds: SafetyBounds


class FederationConfig(StrictModel):

    convergence: ConvergenceConfig
    local_epochs: RoundCount


class ThresholdConfig(StrictModel):

    n_min: SampleCount
    q: Literal[95]
    cluster_k_nbaiot: Literal[3]
    cluster_n_init: IterationCount
    cluster_max_iter: IterationCount
    cluster_random_state: Literal[42]


class ExperimentConfig(StrictModel):

    seeds: list[RandomSeed]


class StatisticsConfig(StrictModel):

    n_bootstrap: BootstrapCount
    bootstrap_min_finite: BootstrapCount
    ci_level: IntervalBound
    bootstrap_seed: RandomSeed
    dispersion_threshold: Threshold


class StyleConfig(StrictModel):

    dpi: SignedCount
    font_size: SignedCount
    figsize_single_col: tuple[ScoreValue, ScoreValue]
    figsize_double_col: tuple[ScoreValue, ScoreValue]
    policy_colors: dict[ThresholdPolicy, NarrativeText]
    policy_labels: dict[ThresholdPolicy, NarrativeText]


class LoggingConfig(StrictModel):

    level: LogLevel
    json_format: bool
    max_bytes: ByteCount
    backup_count: SampleCount


class RuntimeConfig(StrictModel):

    ray_memory_threshold: Threshold
    sweep_workers: WorkerCount


class ReportingConfig(StrictModel):

    figure2_max_points: SignedCount
    figure2_rng_seed: RandomSeed
    metric_tol: Tolerance
    style: StyleConfig


class PoisoningParams(StrictModel):

    policies: tuple[ThresholdPolicy, ...]
    sources: tuple[PoisoningSourceStrategy, ...]
    objectives: tuple[AttackerObjective, ...]
    source_objective_pairs: tuple[tuple[PoisoningSourceStrategy, AttackerObjective], ...]
    fractions: tuple[PoisonFraction, ...]
    poisoning_seeds: tuple[RandomSeed, ...]
    analysis_seeds: tuple[RandomSeed, ...]
    tail_mass: PoisonFraction
    materiality_factor: ScoreValue
    trim_fraction_primary: PoisonFraction
    trim_fraction_appendix: PoisonFraction
    mu_flag_divisor: ScoreValue
    victim_majority_threshold: SignedCount
    iqr_floor_factor: ScoreValue
    sign_consistency_threshold: SignedCount
    scale_normalization_statistic_quantile: Quantile
    permutation_max_exact_seeds: RandomSeed
    eps_num: Tolerance


class SensitivityParams(StrictModel):

    sign_consistency_grid: tuple[SignedCount, ...]
    victim_majority_grid: tuple[SignedCount, ...]
    materiality_grid: tuple[ScoreValue, ...]
    iqr_floor_grid: tuple[ScoreValue, ...]
    cluster_k_grid: tuple[SignedCount, ...]
    cluster_n_init_grid: tuple[IterationCount, ...]
    cluster_random_states: tuple[RandomSeed, ...]
    cluster_fractions: tuple[PoisonFraction, ...]
    draw_variant_fractions: tuple[PoisonFraction, ...]


class DatpConfig(StrictModel):

    model: ModelConfig
    dataset: DatasetConfig
    machine: MachineConfig
    federation: FederationConfig
    threshold: ThresholdConfig
    experiment: ExperimentConfig
    statistics: StatisticsConfig
    poisoning: PoisoningParams
    sensitivity: SensitivityParams
    reporting: ReportingConfig
    runtime: RuntimeConfig
    logging: LoggingConfig

    stage: ExperimentStage | None = None
    policy: ThresholdPolicy | None = None
    seed: RandomSeed | None = None

    @model_validator(mode="after")
    def cross_field_validations(self) -> "DatpConfig":
        if self.model.input_dim != self.dataset.feature_count:
            raise ValueError(
                f"model.input_dim ({self.model.input_dim}) != dataset.feature_count"
            )
        if (
            self.machine.batch_size_train
            > self.machine.safety_bounds.max_batch_size_train
        ):
            raise ValueError("batch_size_train exceeds safety limits")
        return self


_CONFIG_FILE = Path(__file__).resolve().parents[2] / "config" / "config.yaml"


class ConfigError(Exception):
    pass


def _load_base_config() -> DatpConfig:
    try:
        return DatpConfig.model_validate(yaml.safe_load(_CONFIG_FILE.read_text()))
    except ValidationError as exc:
        raise ConfigError(str(exc)) from exc


BASE_CONFIG: DatpConfig = _load_base_config()



_POISONING = BASE_CONFIG.poisoning
_SENSITIVITY = BASE_CONFIG.sensitivity

NBAIOT_MAIN_SWEEP_FRACTIONS: tuple[PoisonFraction, ...] = _POISONING.fractions
NBAIOT_MAIN_SWEEP_FRACTION_SET: frozenset[PoisonFraction] = frozenset(_POISONING.fractions)
DEFAULT_POLICIES: tuple[ThresholdPolicy, ...] = _POISONING.policies
NBAIOT_MAIN_SWEEP_OBJECTIVES: tuple[AttackerObjective, ...] = _POISONING.objectives
NBAIOT_MAIN_SWEEP_SOURCES: tuple[PoisoningSourceStrategy, ...] = _POISONING.sources
NBAIOT_MAIN_SOURCE_OBJECTIVE_PAIRS: tuple[
    tuple[PoisoningSourceStrategy, AttackerObjective], ...
] = _POISONING.source_objective_pairs
TRAINING_SEEDS: tuple[RandomSeed, ...] = tuple(BASE_CONFIG.experiment.seeds)
POISONING_SEEDS: tuple[RandomSeed, ...] = _POISONING.poisoning_seeds
ANALYSIS_SEEDS: tuple[RandomSeed, ...] = _POISONING.analysis_seeds
CLUSTER_RANDOM_STATE: RandomSeed = RandomSeed(BASE_CONFIG.threshold.cluster_random_state)
N_MIN: SampleCount = BASE_CONFIG.threshold.n_min
TAIL_MASS: PoisonFraction = _POISONING.tail_mass
MATERIALITY_FACTOR: ScoreValue = _POISONING.materiality_factor
THRESHOLD_QUANTILE: Threshold = float(BASE_CONFIG.threshold.q)
TRIM_FRACTION_PRIMARY: PoisonFraction = _POISONING.trim_fraction_primary
TRIM_FRACTION_APPENDIX: PoisonFraction = _POISONING.trim_fraction_appendix
CLUSTER_K_NBAIOT: ClusterCount = BASE_CONFIG.threshold.cluster_k_nbaiot
CLUSTER_N_INIT: IterationCount = BASE_CONFIG.threshold.cluster_n_init
CLUSTER_MAX_ITER: IterationCount = BASE_CONFIG.threshold.cluster_max_iter
EPS_NUM: Tolerance = _POISONING.eps_num
SIGN_CONSISTENCY_THRESHOLD: SignedCount = _POISONING.sign_consistency_threshold
BOOTSTRAP_CI: IntervalBound = BASE_CONFIG.statistics.ci_level
BOOTSTRAP_N: BootstrapCount = BASE_CONFIG.statistics.n_bootstrap
BOOTSTRAP_MIN_FINITE: BootstrapCount = BASE_CONFIG.statistics.bootstrap_min_finite
MU_FLAG_DIVISOR: ScoreValue = _POISONING.mu_flag_divisor
VICTIM_MAJORITY_THRESHOLD: SignedCount = _POISONING.victim_majority_threshold
IQR_FLOOR_FACTOR: ScoreValue = _POISONING.iqr_floor_factor
SENSITIVITY_SIGN_CONSISTENCY_GRID: tuple[SignedCount, ...] = _SENSITIVITY.sign_consistency_grid
SENSITIVITY_VICTIM_MAJORITY_GRID: tuple[SignedCount, ...] = _SENSITIVITY.victim_majority_grid
SENSITIVITY_MATERIALITY_GRID: tuple[ScoreValue, ...] = _SENSITIVITY.materiality_grid
SENSITIVITY_IQR_FLOOR_GRID: tuple[ScoreValue, ...] = _SENSITIVITY.iqr_floor_grid
CLUSTER_SENSITIVITY_K_GRID: tuple[SignedCount, ...] = _SENSITIVITY.cluster_k_grid
CLUSTER_SENSITIVITY_N_INIT_GRID: tuple[IterationCount, ...] = _SENSITIVITY.cluster_n_init_grid
CLUSTER_SENSITIVITY_RANDOM_STATES: tuple[RandomSeed, ...] = _SENSITIVITY.cluster_random_states
CLUSTER_SENSITIVITY_FRACTIONS: tuple[PoisonFraction, ...] = _SENSITIVITY.cluster_fractions
DRAW_VARIANT_FRACTIONS: tuple[PoisonFraction, ...] = _SENSITIVITY.draw_variant_fractions
SCALE_NORMALIZATION_STATISTIC_QUANTILE: Quantile = _POISONING.scale_normalization_statistic_quantile
PERMUTATION_MAX_EXACT_SEEDS: RandomSeed = _POISONING.permutation_max_exact_seeds


_DEFAULT_POLICY_SET: frozenset[ThresholdPolicy] = frozenset(DEFAULT_POLICIES)


_NBAIOT_MAIN_SOURCE_SET: frozenset[PoisoningSourceStrategy] = frozenset(
    NBAIOT_MAIN_SWEEP_SOURCES
)


class SeedPools(StrictModel):

    training: tuple[RandomSeed, ...] = TRAINING_SEEDS
    poisoning: tuple[RandomSeed, ...] = POISONING_SEEDS
    analysis: tuple[RandomSeed, ...] = ANALYSIS_SEEDS
    split: RandomSeed = RandomSeed(0)
    @model_validator(mode="after")
    def validate_pools(self) -> "SeedPools":
        if not self.training:
            raise ValueError("seed pools must not be empty")
        if len({len(self.training), len(self.poisoning), len(self.analysis)}) > 1:
            raise ValueError("all seed pools must have the same length")
        all_seeds = list(self.training) + list(self.poisoning) + list(self.analysis)
        if len(all_seeds) != len(set(all_seeds)):
            raise ValueError("all seeds must be pairwise distinct")
        return self

    def __len__(self) -> int:
        return len(self.training)


class ClusterConfig(StrictModel):

    k: Literal[3] = CLUSTER_K_NBAIOT
    n_init: IterationCount = Field(default=CLUSTER_N_INIT, gt=0)
    max_iter: IterationCount = Field(default=CLUSTER_MAX_ITER, gt=0)
    random_state: Literal[42] = cast(Literal[42], CLUSTER_RANDOM_STATE)


class CalibrationPoisoningConfig(StrictModel):

    local_epochs: Literal[1] = 1

    policies: tuple[ThresholdPolicy, ...] = DEFAULT_POLICIES
    sources: tuple[PoisoningSourceStrategy, ...] = NBAIOT_MAIN_SWEEP_SOURCES
    objectives: tuple[AttackerObjective, ...] = NBAIOT_MAIN_SWEEP_OBJECTIVES

    injection_rule: Literal[CalibrationInjectionRule.REPLACE_FIXED_BUDGET] = (
        CalibrationInjectionRule.REPLACE_FIXED_BUDGET
    )
    knowledge: PoisoningKnowledge
    target_scope: PoisoningTargetScope
    defense: PoisoningDefense = PoisoningDefense.NONE
    trim_fraction: PoisonFraction = Field(default=TRIM_FRACTION_PRIMARY, ge=0.0, lt=0.5)
    stage: ExperimentStage

    fractions: tuple[PoisonFraction, ...] = NBAIOT_MAIN_SWEEP_FRACTIONS
    seeds: SeedPools = SeedPools()
    n_min: SampleCount = Field(default=N_MIN, gt=0)
    cluster: ClusterConfig = ClusterConfig()
    tail_mass: PoisonFraction = Field(default=TAIL_MASS, gt=0.0, le=1.0)
    mu_flag_threshold: Threshold | None = None

    @field_validator("policies")
    @classmethod
    def require_policies(cls, v: tuple[ThresholdPolicy, ...]) -> tuple[ThresholdPolicy, ...]:
        if not v:
            raise ValueError("Policies must not be empty")
        return v

    @field_validator("sources")
    @classmethod
    def require_sources(
        cls, v: tuple[PoisoningSourceStrategy, ...]
    ) -> tuple[PoisoningSourceStrategy, ...]:
        if not v:
            raise ValueError("Sources must not be empty")
        return v

    @field_validator("objectives")
    @classmethod
    def require_objectives(cls, v: tuple[AttackerObjective, ...]) -> tuple[AttackerObjective, ...]:
        if not v:
            raise ValueError("Objectives must not be empty")
        return v

    @field_validator("fractions", mode="before")
    @classmethod
    def validate_fractions(cls, v: object) -> object:
        if isinstance(v, (str, bytes)) or not isinstance(v, Sequence):
            return v
        fractions = cast(Sequence[object], v)
        if any(
            isinstance(item, (int, float)) and not (0.0 <= item <= 1.0)
            for item in fractions
        ):
            raise ValueError("Fractions must be within [0.0, 1.0]")
        return fractions

    @field_validator("fractions")
    @classmethod
    def require_fractions(cls, v: tuple[PoisonFraction, ...]) -> tuple[PoisonFraction, ...]:
        if not v:
            raise ValueError("Fractions must not be empty")
        return v

    @model_validator(mode="after")
    def nbaiot_main_grid_lock(self) -> "CalibrationPoisoningConfig":
        if self.target_scope != PoisoningTargetScope.SINGLE_CLIENT:
            raise ValueError("NBAIOT_MAIN stage requires SINGLE_CLIENT target scope")
        if frozenset(self.policies) != _DEFAULT_POLICY_SET:
            raise ValueError(f"Required exactly policies {_DEFAULT_POLICY_SET}")
        if frozenset(self.sources) != _NBAIOT_MAIN_SOURCE_SET:
            raise ValueError(f"Required exactly sources {_NBAIOT_MAIN_SOURCE_SET}")
        if frozenset(self.objectives) != frozenset(NBAIOT_MAIN_SWEEP_OBJECTIVES):
            raise ValueError(
                f"Required exactly objectives {set(NBAIOT_MAIN_SWEEP_OBJECTIVES)}"
            )
        if frozenset(self.fractions) != NBAIOT_MAIN_SWEEP_FRACTION_SET:
            raise ValueError(
                f"Required exactly fractions {sorted(NBAIOT_MAIN_SWEEP_FRACTION_SET)}"
            )
        return self

    @classmethod
    def for_bounded_sweep(cls) -> "CalibrationPoisoningConfig":
        return cls(
            knowledge=PoisoningKnowledge.GRAY_BOX_SCORE_ACCESS,
            target_scope=PoisoningTargetScope.SINGLE_CLIENT,
            stage=ExperimentStage.NBAIOT_MAIN,
        )


def run_config(
    *, stage: ExperimentStage, policy: ThresholdPolicy, seed: RandomSeed
) -> DatpConfig:
    if policy not in CONTROLLED_POLICIES:
        raise ConfigError(
            f"[config] {policy} invalid for {stage}. Expected: {sorted(CONTROLLED_POLICIES)}."
        )
    return BASE_CONFIG.model_copy(
        update={"stage": stage, "policy": policy, "seed": seed}
    )


def write_resolved_config(cfg: DatpConfig, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    dest = output_dir / ArtifactFile.RESOLVED_CONFIG
    dest.write_text(yaml.safe_dump(cfg.model_dump(mode="json"), sort_keys=False))
    return dest
