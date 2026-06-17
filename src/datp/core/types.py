"""Core data models and shared types for DATP."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict

from datp.core.enums import (
    B0NormalizationMode,
    Baseline,
    DatasetID,
    NormalizationScope,
    Regime,
    RunKind,
    ThresholdAggregationMethod,
    ThresholdSource,
)
from datp.core.identity import BaselineRunId


class FrozenModel(BaseModel):
    """Strict, immutable Pydantic base for models."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class MetricsProvenance(FrozenModel):
    """Provenance metadata for a metrics artifact."""

    config_identity: str
    split_manifest_identity: str
    model_checkpoint_identity: str
    score_artifact_identity: str
    metric_code_version: str
    threshold_code_version: str
    package_version: str
    generated_at_utc: str


class AnalysisRowBase(FrozenModel):
    """Base class for analysis result rows containing cell coordinates."""

    regime: Regime
    seed: int
    alpha: str | None


@dataclass(frozen=True, slots=True)
class B3FamilyInfo:
    tau_family: float
    eligible_count: int
    members: tuple[str, ...]
    threshold_variance: float
    singleton: bool


@dataclass(frozen=True, slots=True)
class B3Metadata:
    family_info: dict[str, B3FamilyInfo]


@dataclass(frozen=True, slots=True)
class B4ClusterInfo:
    tau_cluster: float
    members: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class B4Metadata:
    cluster_info: dict[str, B4ClusterInfo]
    fingerprints: dict[str, tuple[float, ...]]
    silhouette: float
    silhouette_scores: dict[str, float]
    k: int


@dataclass(frozen=True, slots=True)
class ClientThreshold:
    client_id: str
    threshold: float
    calibration_pending: bool
    strategy: Baseline


@dataclass(frozen=True, slots=True)
class ThresholdMetadata:
    b3: B3Metadata | None
    b4: B4Metadata | None


@dataclass(frozen=True, slots=True)
class ThresholdResult:
    run: BaselineRunId
    tau_global: float
    client_thresholds: tuple[ClientThreshold, ...]
    metadata: ThresholdMetadata

    @property
    def eligible_count(self) -> int:
        return sum(1 for ct in self.client_thresholds if not ct.calibration_pending)

    @property
    def pending_count(self) -> int:
        return sum(1 for ct in self.client_thresholds if ct.calibration_pending)


class ClientEvalResult(FrozenModel):
    fpr: float
    tpr: float
    balanced_accuracy: float
    macro_f1: float
    confusion_matrix: dict[str, int]
    n_benign: int
    n_attack: int
    benign_count: int
    attack_count: int
    calibration_pending: bool
    evaluation_incomplete: bool
    threshold_value: float
    threshold_source: ThresholdSource


class ClientEvalResultWithAuroc(ClientEvalResult):
    auroc: float
    pr_auc: float


class BaselineResult(FrozenModel):
    baseline: Baseline
    regime: Regime
    seed: int
    per_client: dict[str, ClientEvalResult]
    n_clients: int
    calibration_pending_clients: tuple[str, ...]


class B0Result(BaselineResult):
    schema_version: str
    metric_schema_version: str
    threshold_schema_version: str
    run_id: str
    run_kind: RunKind
    dataset: DatasetID
    tau_b0: float
    tau_global: float
    threshold_scope: ThresholdAggregationMethod
    threshold_strategy_name: str
    q: float
    n_min: int
    eligible_ids: tuple[str, ...]
    pending_ids: tuple[str, ...]
    eval_incomplete_ids: tuple[str, ...]
    eligible_count: int
    pending_count: int
    eval_incomplete_count: int
    client_count: int
    coverage_ratio: float
    cv_fpr: float
    mean_fpr: float
    std_fpr: float
    cv_tpr: float
    iqr_fpr: float
    iqr_tpr: float
    max_min_fpr_gap: float
    worst_client_fpr: float
    worst_client_id: str | None
    worst_ba: float
    p10_macro_f1: float
    auroc: float | None
    pr_auc: float | None
    aggregate_metrics: dict[str, float | str | None]
    provenance: MetricsProvenance
    threshold_mode: ThresholdAggregationMethod
    normalization_scope: NormalizationScope
    normalization_mode: B0NormalizationMode
