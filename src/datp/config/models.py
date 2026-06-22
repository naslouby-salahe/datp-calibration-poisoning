"""Pydantic v2 config models — single source of truth for all scientific defaults.

Every scientific parameter lives here. No module-level constants for
scientific parameters downstream.
"""

from __future__ import annotations
from datp.core.enums import ThresholdPolicy

from pydantic import BaseModel, ConfigDict, Field, model_validator

from datp.checkpointing.enums import (
    CheckpointArtifactPathMode,
    CheckpointConvergenceMode,
    CheckpointProtocolMode,
    PrimaryCheckpointSelectionRule,
)
from datp.config.stages import ExperimentStage
from datp.core.enums import (
    Activation,
)


class SafetyBounds(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    max_batch_size_train: int


class ConvergenceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    rounds_initial: int
    rounds_max: int
    relative_threshold: float
    window: int
    round_timeout_s: float


class ModelConfig(BaseModel):
    """Autoencoder architecture config.

    ``encoder_dims`` is the canonical layer-width spec: the encoder path's
    hidden-layer dimensions including the bottleneck. The decoder is built
    as the mirror of the encoder inside ``Autoencoder``. There is no full
    symmetric ``layer_widths`` — that dual representation was removed to
    eliminate drift.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    input_dim: int
    encoder_dims: list[int]
    lr: float
    epochs: int
    patience: int
    activation: Activation
    use_bn: bool


class DatasetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    feature_count: int
    n_min: int
    cap: int
    attack_reserve_fraction: float
    nbaiot_balanced_test: bool


class MachineConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
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


class FederationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    convergence: ConvergenceConfig
    local_epochs: int


def _validate_milestone_ordering(milestones: tuple[int, ...]) -> None:
    if not milestones:
        raise ValueError("checkpoint milestones must not be empty")
    if len(set(milestones)) != len(milestones):
        raise ValueError("checkpoint milestones must not contain duplicates")
    if tuple(sorted(milestones)) != milestones:
        raise ValueError("checkpoint milestones must be sorted ascending")
    if any(round_count <= 0 for round_count in milestones):
        raise ValueError("checkpoint milestones must be positive")


def _validate_checkpoint_milestones(
    milestones: tuple[int, ...],
    max_rounds: int,
) -> None:
    _validate_milestone_ordering(milestones)
    if max(milestones) > max_rounds:
        raise ValueError("checkpoint milestone cannot exceed max_rounds")


def _validate_checkpoint_selection(
    rule: PrimaryCheckpointSelectionRule,
) -> None:
    if (
        rule
        != PrimaryCheckpointSelectionRule.GLOBAL_LOWER_TAIL_TRADEOFF_FROM_NBAIOT_MAIN
    ):
        raise ValueError("unsupported primary checkpoint selection rule")


def _validate_checkpoint_modes(
    convergence_mode: CheckpointConvergenceMode,
    artifact_path_mode: CheckpointArtifactPathMode,
) -> None:
    if convergence_mode not in (
        CheckpointConvergenceMode.LOG_ONLY,
        CheckpointConvergenceMode.EARLY_STOP,
    ):
        raise ValueError("unsupported checkpoint convergence mode")
    if artifact_path_mode != CheckpointArtifactPathMode.ROUND_AWARE:
        raise ValueError("checkpoint protocol requires round-aware artifact paths")


class CheckpointProtocolConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    mode: CheckpointProtocolMode
    max_rounds: int = Field(gt=0)
    milestones: tuple[int, ...]
    convergence_mode: CheckpointConvergenceMode
    primary_selection_rule: PrimaryCheckpointSelectionRule
    artifact_path_mode: CheckpointArtifactPathMode

    @model_validator(mode="after")
    def validate_checkpoint_protocol(self) -> "CheckpointProtocolConfig":
        _validate_checkpoint_milestones(self.milestones, self.max_rounds)
        _validate_checkpoint_selection(self.primary_selection_rule)
        _validate_checkpoint_modes(self.convergence_mode, self.artifact_path_mode)
        return self

    @property
    def enabled(self) -> bool:
        return self.mode == CheckpointProtocolMode.ENABLED


class ThresholdConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    n_min: int
    q: float
    cluster_k_nbaiot: int
    cluster_k_candidates: list[int]
    cluster_n_init: int
    cluster_max_iter: int
    cluster_random_state: int


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    seeds: list[int]


class StatisticsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    n_bootstrap: int
    ci_level: float
    bootstrap_seed: int
    significance_alpha: float
    # Preliminary single-seed GO threshold for CV(FPR)[GLOBAL_THRESHOLD, NBAIOT_MAIN].
    dispersion_threshold: float


class QualityGateConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    ciciot_homogeneity_threshold: float
    js_divergence_n_bins: int


class StyleConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    dpi: int
    font_size: int
    figsize_single_col: tuple[float, float]
    figsize_double_col: tuple[float, float]
    policy_colors: dict[ThresholdPolicy, str]
    policy_labels: dict[ThresholdPolicy, str]


class LoggingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    level: str
    json_format: bool
    max_bytes: int
    backup_count: int
    training_progress_interval: int


class RuntimeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    lock_timeout_seconds: float
    ray_memory_threshold: float


class TrackingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    experiment_name: str
    tracking_uri: str


class ReportingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    figure2_max_points: int
    figure2_rng_seed: int
    metric_tol: float
    style: StyleConfig


class DatpConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, protected_namespaces=())

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
    def check_input_dim_matches_features(self) -> "DatpConfig":
        if self.model.input_dim != self.dataset.feature_count:
            raise ValueError(
                f"model.input_dim ({self.model.input_dim}) != "
                f"dataset.feature_count ({self.dataset.feature_count})"
            )
        return self

    @model_validator(mode="after")
    def check_n_min_consistent(self) -> "DatpConfig":
        if self.dataset.n_min != self.threshold.n_min:
            raise ValueError(
                f"dataset.n_min ({self.dataset.n_min}) != "
                f"threshold.n_min ({self.threshold.n_min})"
            )
        return self

    @model_validator(mode="after")
    def check_batch_size_within_bounds(self) -> "DatpConfig":
        if (
            self.machine.batch_size_train
            > self.machine.safety_bounds.max_batch_size_train
        ):
            raise ValueError(
                f"machine.batch_size_train ({self.machine.batch_size_train}) exceeds "
                f"machine.safety_bounds.max_batch_size_train "
                f"({self.machine.safety_bounds.max_batch_size_train})"
            )
        return self
