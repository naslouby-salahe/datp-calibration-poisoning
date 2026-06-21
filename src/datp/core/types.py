"""Core data models and shared types for DATP."""

from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

from dataclasses import dataclass
from typing import Any, SupportsIndex, overload

from pydantic import BaseModel, ConfigDict

from datp.config.stages import ExperimentStage
from datp.core.enums import ThresholdSource
from datp.core.identity import PolicyRunId


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

    stage: ExperimentStage
    seed: int


@dataclass(frozen=True, slots=True)
class ClusterInfo:
    cluster_id: str
    tau_cluster: float
    members: tuple[str, ...]


class ClusterInfoTuple(tuple[ClusterInfo, ...]):
    def __new__(cls, entries: Any) -> "ClusterInfoTuple":
        return super().__new__(cls, entries)

    @overload
    def __getitem__(self, key: str) -> ClusterInfo: ...

    @overload
    def __getitem__(self, key: SupportsIndex) -> ClusterInfo: ...

    @overload
    def __getitem__(self, key: slice) -> tuple[ClusterInfo, ...]: ...

    def __getitem__(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, key: str | SupportsIndex | slice
    ) -> ClusterInfo | tuple[ClusterInfo, ...]:
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
class ClusterMetadata:
    cluster_info: ClusterInfoTuple
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
        object.__setattr__(self, "cluster_info", ClusterInfoTuple(cluster_info))
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

    def cluster_for(self, cluster_id: str) -> ClusterInfo:
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
    strategy: ThresholdPolicy


@dataclass(frozen=True, slots=True)
class ThresholdMetadata:
    cluster: ClusterMetadata | None


@dataclass(frozen=True, slots=True)
class ThresholdResult:
    run: PolicyRunId
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


class PolicyResult(FrozenModel):
    policy: ThresholdPolicy
    stage: ExperimentStage
    seed: int
    per_client: dict[str, ClientEvalResult]
    n_clients: int
    calibration_pending_clients: tuple[str, ...]

