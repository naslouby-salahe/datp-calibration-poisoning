"""Core data models and shared types for DATP."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, SupportsIndex, overload

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
    family_name: str
    tau_family: float
    eligible_count: int
    members: tuple[str, ...]
    threshold_variance: float
    singleton: bool


class B3FamilyInfoTuple(tuple[B3FamilyInfo, ...]):
    def __new__(cls, entries: Any) -> "B3FamilyInfoTuple":
        return super().__new__(cls, entries)

    @overload
    def __getitem__(self, key: str) -> B3FamilyInfo: ...

    @overload
    def __getitem__(self, key: SupportsIndex) -> B3FamilyInfo: ...

    @overload
    def __getitem__(self, key: slice) -> tuple[B3FamilyInfo, ...]: ...

    def __getitem__(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, key: str | SupportsIndex | slice
    ) -> B3FamilyInfo | tuple[B3FamilyInfo, ...]:
        if isinstance(key, str):
            for entry in self:
                if entry.family_name == key:
                    return entry
            raise KeyError(key)
        return super().__getitem__(key)

    def __contains__(self, key: object) -> bool:
        if isinstance(key, str):
            return any(entry.family_name == key for entry in self)
        return super().__contains__(key)

    def keys(self):
        return (entry.family_name for entry in self)

    def values(self):
        return iter(self)

    def items(self):
        for entry in self:
            yield entry.family_name, entry


@dataclass(frozen=True, slots=True)
class B3Metadata:
    family_info: B3FamilyInfoTuple

    def __post_init__(self) -> None:
        family_info_input: Any = self.family_info
        if hasattr(family_info_input, "values"):
            family_info = tuple(family_info_input.values())
        else:
            family_info = tuple(family_info_input)
        object.__setattr__(self, "family_info", B3FamilyInfoTuple(family_info))

    def for_family(self, family_name: str) -> B3FamilyInfo:
        for info in self.family_info:
            if info.family_name == family_name:
                return info
        raise KeyError(family_name)


@dataclass(frozen=True, slots=True)
class B4ClusterInfo:
    cluster_id: str
    tau_cluster: float
    members: tuple[str, ...]


class B4ClusterInfoTuple(tuple[B4ClusterInfo, ...]):
    def __new__(cls, entries: Any) -> "B4ClusterInfoTuple":
        return super().__new__(cls, entries)

    @overload
    def __getitem__(self, key: str) -> B4ClusterInfo: ...

    @overload
    def __getitem__(self, key: SupportsIndex) -> B4ClusterInfo: ...

    @overload
    def __getitem__(self, key: slice) -> tuple[B4ClusterInfo, ...]: ...

    def __getitem__(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, key: str | SupportsIndex | slice
    ) -> B4ClusterInfo | tuple[B4ClusterInfo, ...]:
        if isinstance(key, str):
            for entry in self:
                if entry.cluster_id == key:
                    return entry
            raise KeyError(key)
        return super().__getitem__(key)

    def __contains__(self, key: object) -> bool:
        if isinstance(key, str):
            return any(entry.cluster_id == key for entry in self)
        return super().__contains__(key)

    def keys(self):
        return (entry.cluster_id for entry in self)

    def values(self):
        return iter(self)

    def items(self):
        for entry in self:
            yield entry.cluster_id, entry


@dataclass(frozen=True, slots=True)
class ClientFingerprint:
    client_id: str
    mean: float
    variance: float
    skewness: float
    p95: float

    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.mean, self.variance, self.skewness, self.p95)


class ClientFingerprintTuple(tuple[ClientFingerprint, ...]):
    def __new__(cls, entries: Any) -> "ClientFingerprintTuple":
        return super().__new__(cls, entries)

    @overload
    def __getitem__(self, key: str) -> ClientFingerprint: ...

    @overload
    def __getitem__(self, key: SupportsIndex) -> ClientFingerprint: ...

    @overload
    def __getitem__(self, key: slice) -> tuple[ClientFingerprint, ...]: ...

    def __getitem__(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, key: str | SupportsIndex | slice
    ) -> ClientFingerprint | tuple[ClientFingerprint, ...]:
        if isinstance(key, str):
            for entry in self:
                if entry.client_id == key:
                    return entry
            raise KeyError(key)
        return super().__getitem__(key)

    def get(self, key: str, default=None):
        try:
            return self[key].as_tuple()
        except KeyError:
            return default

    def keys(self):
        return (entry.client_id for entry in self)

    def values(self):
        return iter(self)

    def items(self):
        for entry in self:
            yield entry.client_id, entry


@dataclass(frozen=True, slots=True)
class ClientSilhouetteScore:
    client_id: str
    score: float


class ClientSilhouetteScoreTuple(tuple[ClientSilhouetteScore, ...]):
    def __new__(cls, entries: Any) -> "ClientSilhouetteScoreTuple":
        return super().__new__(cls, entries)

    def items(self):
        for entry in self:
            yield entry.client_id, entry.score


@dataclass(frozen=True, slots=True)
class B4Metadata:
    cluster_info: B4ClusterInfoTuple
    fingerprints: ClientFingerprintTuple
    silhouette: float
    silhouette_scores: ClientSilhouetteScoreTuple
    k: int

    def __post_init__(self) -> None:
        cluster_info_input: Any = self.cluster_info
        if hasattr(cluster_info_input, "values"):
            cluster_info = tuple(cluster_info_input.values())
        else:
            cluster_info = tuple(cluster_info_input)
        object.__setattr__(self, "cluster_info", B4ClusterInfoTuple(cluster_info))
        fingerprints_input: Any = self.fingerprints
        if isinstance(fingerprints_input, ClientFingerprintTuple):
            fingerprints = tuple(fingerprints_input)
        elif hasattr(fingerprints_input, "items"):
            fingerprints = tuple(
                ClientFingerprint(
                    client_id=client_id,
                    mean=float(values[0]),
                    variance=float(values[1]),
                    skewness=float(values[2]),
                    p95=float(values[3]),
                )
                for client_id, values in fingerprints_input.items()
            )
        else:
            fingerprints = tuple(fingerprints_input)
        object.__setattr__(self, "fingerprints", ClientFingerprintTuple(fingerprints))
        scores_input: Any = self.silhouette_scores
        if hasattr(scores_input, "items"):
            silhouette_scores = tuple(
                ClientSilhouetteScore(client_id=str(client_id), score=float(score))
                for client_id, score in scores_input.items()
            )
        else:
            silhouette_scores = tuple(scores_input)
        object.__setattr__(
            self, "silhouette_scores", ClientSilhouetteScoreTuple(silhouette_scores)
        )

    def cluster_for(self, cluster_id: str) -> B4ClusterInfo:
        for info in self.cluster_info:
            if info.cluster_id == cluster_id:
                return info
        raise KeyError(cluster_id)

    def fingerprint_for(self, client_id: str) -> ClientFingerprint:
        for fingerprint in self.fingerprints:
            if fingerprint.client_id == client_id:
                return fingerprint
        raise KeyError(client_id)


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

    def for_client(self, client_id: str) -> ClientThreshold:
        for threshold in self.client_thresholds:
            if threshold.client_id == client_id:
                return threshold
        raise KeyError(client_id)


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
