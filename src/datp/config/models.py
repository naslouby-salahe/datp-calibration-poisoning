"""Pydantic models for experiment configuration: stages, dataset, model, federation, and thresholds."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from datp.checkpointing.enums import (
    CheckpointArtifactPathMode,
    CheckpointConvergenceMode,
    CheckpointProtocolMode,
    PrimaryCheckpointSelectionRule,
)
from datp.core.enums import Activation, DatasetID, ThresholdPolicy


class ExperimentStage(enum.StrEnum):
    """Execution stages, ordered lightest to heaviest."""

    FINAL_AUDIT = "final_audit"
    SYNTHETIC_SMOKE = "synthetic_smoke"
    NBAIOT_MAIN = "nbaiot_main"
    NBAIOT_FULL_OPTIONAL = "nbaiot_full_optional"
    STRETCH_DIAGNOSTIC_ONLY = "stretch_diagnostic_only"


@dataclass(frozen=True, slots=True)
class ExperimentStageConfig:
    """Metadata for an experiment stage: dataset, run gate, and description."""

    stage: ExperimentStage
    dataset: DatasetID | None
    allow_run: bool
    gate: str | None
    description: str


_STAGE_CONFIGS: dict[ExperimentStage, ExperimentStageConfig] = {
    ExperimentStage.FINAL_AUDIT: ExperimentStageConfig(
        stage=ExperimentStage.FINAL_AUDIT,
        dataset=None,
        allow_run=False,
        gate="final_audit_pass",
        description="Protocol audit and provenance validation before execution.",
    ),
    ExperimentStage.SYNTHETIC_SMOKE: ExperimentStageConfig(
        stage=ExperimentStage.SYNTHETIC_SMOKE,
        dataset=None,
        allow_run=True,
        gate="smoke_diagnostics_signoff",
        description="Synthetic invariant validation; must pass before N-BaIoT main.",
    ),
    ExperimentStage.NBAIOT_MAIN: ExperimentStageConfig(
        stage=ExperimentStage.NBAIOT_MAIN,
        dataset=DatasetID.NBAIOT,
        allow_run=True,
        gate="nbaiot_main_run_lock",
        description="Primary N-BaIoT single-client calibration-poisoning experiment.",
    ),
    ExperimentStage.NBAIOT_FULL_OPTIONAL: ExperimentStageConfig(
        stage=ExperimentStage.NBAIOT_FULL_OPTIONAL,
        dataset=DatasetID.NBAIOT,
        allow_run=False,
        gate="full_scope_continue_decision",
        description="Optional multi-client extension (pairs and triples).",
    ),
    ExperimentStage.STRETCH_DIAGNOSTIC_ONLY: ExperimentStageConfig(
        stage=ExperimentStage.STRETCH_DIAGNOSTIC_ONLY,
        dataset=None,
        allow_run=False,
        gate="stretch_diagnostic_signoff",
        description="Diagnostic-only stretch contrast; cannot support main claims.",
    ),
}


def get_stage_config(stage: ExperimentStage) -> ExperimentStageConfig:
    """Return the ExperimentStageConfig for a given stage."""
    return _STAGE_CONFIGS[stage]


def all_stage_configs() -> list[ExperimentStageConfig]:
    """Return all experiment stage configs."""
    return list(_STAGE_CONFIGS.values())


class StrictModel(BaseModel):
    """Base Pydantic model with extra fields forbidden, frozen, and protected namespaces off."""

    model_config = ConfigDict(extra="forbid", frozen=True, protected_namespaces=())


class SafetyBounds(StrictModel):
    """Safety limits for batch sizes."""

    max_batch_size_train: int


class ConvergenceConfig(StrictModel):
    """Convergence detection parameters for federated training."""

    rounds_initial: int
    rounds_max: int
    relative_threshold: float
    window: int
    round_timeout_s: float


class ModelConfig(StrictModel):
    """Autoencoder model architecture and training hyperparameters."""

    input_dim: int
    encoder_dims: list[int]
    lr: float
    epochs: int
    patience: int
    activation: Activation
    use_bn: bool


class DatasetConfig(StrictModel):
    """Dataset dimensions, caps, and attack-reserve fraction."""

    feature_count: int
    n_min: int
    cap: int
    attack_reserve_fraction: float
    nbaiot_balanced_test: bool


class MachineConfig(StrictModel):
    """Compute resource configuration: batch sizes, CUDA, Ray, RAM, and caching."""

    batch_size_train: int = Field(gt=0)
    scoring_batch_size: int = Field(default=256, gt=0)
    require_cuda: bool = False
    ray_num_gpus_per_client: float = Field(default=0.0, ge=0)
    per_client_ram_gb: float = Field(gt=0)
    reserve_ram_gb: float = Field(ge=0)
    max_concurrent_override: int | None = Field(gt=0, default=None)
    ray_object_store_mb: int = Field(gt=0)
    cache_maxsize: int = Field(gt=0)
    safety_bounds: SafetyBounds


class FederationConfig(StrictModel):
    """Federated learning configuration: convergence and local epochs."""

    convergence: ConvergenceConfig
    local_epochs: int


class CheckpointProtocolConfig(StrictModel):
    """Configuration for the checkpoint protocol: mode, milestones, and selection rule."""

    mode: CheckpointProtocolMode
    max_rounds: int = Field(gt=0)
    milestones: tuple[int, ...]
    convergence_mode: Literal[
        CheckpointConvergenceMode.LOG_ONLY, CheckpointConvergenceMode.EARLY_STOP
    ]
    primary_selection_rule: Literal[
        PrimaryCheckpointSelectionRule.GLOBAL_LOWER_TAIL_TRADEOFF_FROM_NBAIOT_MAIN
    ]
    artifact_path_mode: Literal[CheckpointArtifactPathMode.ROUND_AWARE]

    @field_validator("milestones")
    @classmethod
    def validate_milestones(cls, v: tuple[int, ...]) -> tuple[int, ...]:
        """Validate milestones are sorted, unique, and positive."""
        if not v:
            raise ValueError("milestones must not be empty")
        if tuple(sorted(v)) != v or len(set(v)) != len(v):
            raise ValueError("milestones must be sorted and unique")
        if any(m <= 0 for m in v):
            raise ValueError("milestones must be positive")
        return v

    @model_validator(mode="after")
    def validate_max_rounds(self) -> "CheckpointProtocolConfig":
        """Validate that no milestone exceeds max_rounds."""
        if max(self.milestones) > self.max_rounds:
            raise ValueError("milestones cannot exceed max_rounds")
        return self

    @property
    def enabled(self) -> bool:
        """True when the checkpoint protocol mode is ENABLED."""
        return self.mode == CheckpointProtocolMode.ENABLED


class ThresholdConfig(StrictModel):
    """Threshold configuration: n_min, quantile, and clustering parameters."""

    n_min: int
    q: Literal[95]
    cluster_k_nbaiot: Literal[3]
    cluster_n_init: int
    cluster_max_iter: int
    cluster_random_state: Literal[42]


class ExperimentConfig(StrictModel):
    """Experiment-level configuration: seed list."""

    seeds: list[int]


class StatisticsConfig(StrictModel):
    """Statistical testing and bootstrap configuration."""

    n_bootstrap: int
    ci_level: float
    bootstrap_seed: int
    significance_alpha: float
    dispersion_threshold: float


class QualityGateConfig(StrictModel):
    """Quality gate parameters including JS divergence bins."""

    js_divergence_n_bins: int


class StyleConfig(StrictModel):
    """Figure and table styling: DPI, font size, and policy colors/labels."""

    dpi: int
    font_size: int
    figsize_single_col: tuple[float, float]
    figsize_double_col: tuple[float, float]
    policy_colors: dict[ThresholdPolicy, str]
    policy_labels: dict[ThresholdPolicy, str]


class LoggingConfig(StrictModel):
    """Logging configuration: level, format, rotation, and training progress interval."""

    level: str
    json_format: bool
    max_bytes: int
    backup_count: int
    training_progress_interval: int


class RuntimeConfig(StrictModel):
    """Runtime configuration: lock timeout and Ray memory threshold."""

    lock_timeout_seconds: float
    ray_memory_threshold: float


class TrackingConfig(StrictModel):
    """MLflow tracking configuration."""

    experiment_name: str
    tracking_uri: str


class ReportingConfig(StrictModel):
    """Reporting configuration: figure limits, metric tolerance, and styling."""

    figure2_max_points: int
    figure2_rng_seed: int
    metric_tol: float
    style: StyleConfig


class DatpConfig(StrictModel):
    """Top-level validated configuration composing all sub-configs."""

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
    seed: int | None = None

    @model_validator(mode="after")
    def cross_field_validations(self) -> "DatpConfig":
        """Validate consistency between model, dataset, threshold, and machine configs."""
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
