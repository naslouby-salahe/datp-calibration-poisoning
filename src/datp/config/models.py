from __future__ import annotations

from datp.types import (
    BatchSize,
    BinCount,
    BootstrapCount,
    ByteCount,
    DurationSeconds,
    EpochCount,
    ExperimentName,
    FeatureCount,
    GpuShare,
    IntervalBound,
    IterationCount,
    LearningRate,
    MemoryAmount,
    NarrativeText,
    Patience,
    PoisonFraction,
    RandomSeed,
    RoundCount,
    SampleCount,
    ScoreValue,
    SignedCount,
    SignificanceLevel,
    Threshold,
    Tolerance,
    TrackingUri,
    WorkerCount,
)


import enum
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from datp.checkpointing.enums import (
    CheckpointArtifactPathMode,
    CheckpointConvergenceMode,
    CheckpointProtocolMode,
    PrimaryCheckpointSelectionRule,
)
from datp.core.enums import (
    Activation,
    DatasetID,
    LogLevel,
    ThresholdPolicy,
    NBaIoTBalancePolicy,
)


class ExperimentStage(enum.StrEnum):

    FINAL_AUDIT = "final_audit"
    SYNTHETIC_SMOKE = "synthetic_smoke"
    NBAIOT_MAIN = "nbaiot_main"
    NBAIOT_FULL_OPTIONAL = "nbaiot_full_optional"
    STRETCH_DIAGNOSTIC_ONLY = "stretch_diagnostic_only"


@dataclass(frozen=True, slots=True)
class ExperimentStageConfig:

    stage: ExperimentStage
    dataset: DatasetID | None
    allow_run: bool
    gate: ExperimentGate | None
    description: NarrativeText


class ExperimentGate(StrEnum):

    FINAL_AUDIT_PASS = "final_audit_pass"
    SMOKE_DIAGNOSTICS_SIGNOFF = "smoke_diagnostics_signoff"
    NBAIOT_MAIN_RUN_LOCK = "nbaiot_main_run_lock"
    FULL_SCOPE_CONTINUE_DECISION = "full_scope_continue_decision"
    STRETCH_DIAGNOSTIC_SIGNOFF = "stretch_diagnostic_signoff"


_STAGE_CONFIGS: dict[ExperimentStage, ExperimentStageConfig] = {
    ExperimentStage.FINAL_AUDIT: ExperimentStageConfig(
        stage=ExperimentStage.FINAL_AUDIT,
        dataset=None,
        allow_run=False,
        gate=ExperimentGate.FINAL_AUDIT_PASS,
        description="Protocol audit and provenance validation before execution.",
    ),
    ExperimentStage.SYNTHETIC_SMOKE: ExperimentStageConfig(
        stage=ExperimentStage.SYNTHETIC_SMOKE,
        dataset=None,
        allow_run=True,
        gate=ExperimentGate.SMOKE_DIAGNOSTICS_SIGNOFF,
        description="Synthetic invariant validation; must pass before N-BaIoT main.",
    ),
    ExperimentStage.NBAIOT_MAIN: ExperimentStageConfig(
        stage=ExperimentStage.NBAIOT_MAIN,
        dataset=DatasetID.NBAIOT,
        allow_run=True,
        gate=ExperimentGate.NBAIOT_MAIN_RUN_LOCK,
        description="Primary N-BaIoT single-client calibration-poisoning experiment.",
    ),
    ExperimentStage.NBAIOT_FULL_OPTIONAL: ExperimentStageConfig(
        stage=ExperimentStage.NBAIOT_FULL_OPTIONAL,
        dataset=DatasetID.NBAIOT,
        allow_run=False,
        gate=ExperimentGate.FULL_SCOPE_CONTINUE_DECISION,
        description="Optional multi-client extension (pairs and triples).",
    ),
    ExperimentStage.STRETCH_DIAGNOSTIC_ONLY: ExperimentStageConfig(
        stage=ExperimentStage.STRETCH_DIAGNOSTIC_ONLY,
        dataset=None,
        allow_run=False,
        gate=ExperimentGate.STRETCH_DIAGNOSTIC_SIGNOFF,
        description="Diagnostic-only stretch contrast; cannot support main claims.",
    ),
}


def get_stage_config(stage: ExperimentStage) -> ExperimentStageConfig:
    return _STAGE_CONFIGS[stage]


def all_stage_configs() -> list[ExperimentStageConfig]:
    return list(_STAGE_CONFIGS.values())


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
    patience: Patience
    activation: Activation
    use_bn: bool


class DatasetConfig(StrictModel):

    feature_count: FeatureCount
    n_min: SampleCount
    cap: SignedCount
    attack_reserve_fraction: PoisonFraction
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
    cache_maxsize: SignedCount = Field(gt=0)
    safety_bounds: SafetyBounds


class FederationConfig(StrictModel):

    convergence: ConvergenceConfig
    local_epochs: RoundCount


class CheckpointProtocolConfig(StrictModel):

    mode: CheckpointProtocolMode
    max_rounds: RoundCount = Field(gt=0)
    milestones: tuple[SignedCount, ...]
    convergence_mode: Literal[
        CheckpointConvergenceMode.LOG_ONLY, CheckpointConvergenceMode.EARLY_STOP
    ]
    primary_selection_rule: Literal[
        PrimaryCheckpointSelectionRule.GLOBAL_LOWER_TAIL_TRADEOFF_FROM_NBAIOT_MAIN
    ]
    artifact_path_mode: Literal[CheckpointArtifactPathMode.ROUND_AWARE]

    @field_validator("milestones")
    @classmethod
    def validate_milestones(
        cls, v: tuple[SignedCount, ...]
    ) -> tuple[SignedCount, ...]:
        if not v:
            raise ValueError("milestones must not be empty")
        if tuple(sorted(v)) != v or len(set(v)) != len(v):
            raise ValueError("milestones must be sorted and unique")
        if any(m <= 0 for m in v):
            raise ValueError("milestones must be positive")
        return v

    @model_validator(mode="after")
    def validate_max_rounds(self) -> "CheckpointProtocolConfig":
        if max(self.milestones) > self.max_rounds:
            raise ValueError("milestones cannot exceed max_rounds")
        return self

    @property
    def enabled(self) -> bool:
        if self.mode is CheckpointProtocolMode.ENABLED:
            return True
        if self.mode is CheckpointProtocolMode.DISABLED:
            return False
        raise ValueError(f"Unsupported checkpoint protocol mode: {self.mode!r}")


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
    ci_level: IntervalBound
    bootstrap_seed: RandomSeed
    significance_alpha: SignificanceLevel
    dispersion_threshold: Threshold


class QualityGateConfig(StrictModel):

    js_divergence_n_bins: BinCount


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
    training_progress_interval: SignedCount


class RuntimeConfig(StrictModel):

    lock_timeout_seconds: DurationSeconds
    ray_memory_threshold: Threshold


class TrackingConfig(StrictModel):

    experiment_name: ExperimentName
    tracking_uri: TrackingUri


class ReportingConfig(StrictModel):

    figure2_max_points: SignedCount
    figure2_rng_seed: RandomSeed
    metric_tol: Tolerance
    style: StyleConfig


class DatpConfig(StrictModel):

    model: ModelConfig
    dataset: DatasetConfig
    machine: MachineConfig
    federation: FederationConfig
    checkpoint_protocol: CheckpointProtocolConfig | None = None
    threshold: ThresholdConfig
    experiment: ExperimentConfig
    statistics: StatisticsConfig
    quality_gates: QualityGateConfig
    reporting: ReportingConfig
    runtime: RuntimeConfig
    logging: LoggingConfig
    tracking: TrackingConfig

    stage: ExperimentStage | None = None
    policy: ThresholdPolicy | None = None
    seed: RandomSeed | None = None

    @model_validator(mode="after")
    def cross_field_validations(self) -> "DatpConfig":
        if self.model.input_dim != self.dataset.feature_count:
            raise ValueError(
                f"model.input_dim ({self.model.input_dim}) != dataset.feature_count"
            )
        if self.dataset.n_min != self.threshold.n_min:
            raise ValueError(f"dataset.n_min ({self.dataset.n_min}) != threshold.n_min")
        if (
            self.machine.batch_size_train
            > self.machine.safety_bounds.max_batch_size_train
        ):
            raise ValueError("batch_size_train exceeds safety limits")
        return self
