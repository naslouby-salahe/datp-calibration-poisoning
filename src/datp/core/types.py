"""Core domain value objects: fingerprints, clusters, thresholds, and evaluation results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, SupportsIndex, TypeVar

from pydantic import BaseModel, ConfigDict

from datp.config.models import ExperimentStage
from datp.core.enums import ThresholdPolicy, ThresholdSource
from datp.core.identity import PolicyRunId

T = TypeVar("T")


class FrozenModel(BaseModel):
    """Pydantic base model with extra fields forbidden and immutability enabled."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class MetricsProvenance(FrozenModel):
    """Provenance metadata for config, data, model, and scoring artifacts used in a metrics run."""

    config_identity: str
    split_manifest_identity: str
    model_checkpoint_identity: str
    score_artifact_identity: str
    metric_code_version: str
    threshold_code_version: str
    package_version: str
    generated_at_utc: str


class AnalysisRowBase(FrozenModel):
    """Base row for analysis results carrying experiment stage and random seed."""

    stage: ExperimentStage
    seed: int


@dataclass(frozen=True, slots=True)
class ClusterInfo:
    """Summary of a cluster: identifier, tau threshold, and member client IDs."""

    cluster_id: str
    tau_cluster: float
    members: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ClientFingerprint:
    """Statistical fingerprint of a client's calibration scores (mean, std, skewness, p95)."""

    client_id: str
    mean: float
    std: float
    skewness: float
    p95: float

    def as_tuple(self) -> tuple[float, float, float, float]:
        """Return fingerprint features as a 4-tuple (mean, std, skewness, p95)."""
        return (self.mean, self.std, self.skewness, self.p95)


@dataclass(frozen=True, slots=True)
class ClientSilhouetteScore:
    """Silhouette score assigned to a single client within its cluster."""

    client_id: str
    score: float


class _DictLikeTuple(tuple[T, ...]):
    """A tuple subclass that supports string-keyed dictionary lookup over its entries."""

    _key_attr: str = ""

    def __init__(self, entries: Any) -> None:
        """Build an internal lookup index keyed by the '_key_attr' of each entry."""
        super().__init__()
        self._lookup = {getattr(e, self.__class__._key_attr): e for e in self}

    def __getitem__(self, key: str | slice | SupportsIndex) -> Any:
        """Allow lookup by string key or integer index."""
        if isinstance(key, str):
            return self._lookup[key]
        return super().__getitem__(key)

    def __contains__(self, key: object) -> bool:
        """Check containment by string key or integer index."""
        return (
            key in self._lookup if isinstance(key, str) else super().__contains__(key)
        )

    def keys(self) -> Any:
        """Return the lookup keys."""
        return self._lookup.keys()

    def values(self) -> Any:
        """Return the lookup values."""
        return self._lookup.values()

    def items(self) -> Any:
        """Return (key, value) pairs."""
        return self._lookup.items()


class ClusterInfoTuple(_DictLikeTuple[ClusterInfo]):
    """An indexable collection of ClusterInfo entries keyed by cluster_id."""

    _key_attr = "cluster_id"


class ClientFingerprintTuple(_DictLikeTuple[ClientFingerprint]):
    """An indexable collection of ClientFingerprint entries keyed by client_id."""

    _key_attr = "client_id"

    def get(self, key: str, default=None):
        """Return the fingerprint as a 4-tuple, or default if not found."""
        return self._lookup[key].as_tuple() if key in self._lookup else default


class ClientSilhouetteScoreTuple(_DictLikeTuple[ClientSilhouetteScore]):
    """An indexable collection of ClientSilhouetteScore entries keyed by client_id."""

    _key_attr = "client_id"

    def items(self):
        """Return (client_id, score) pairs."""
        return ((k, v.score) for k, v in self._lookup.items())


@dataclass(frozen=True, slots=True)
class ClusterMetadata:
    """Aggregated metadata for a clustering result: clusters, fingerprints, and silhouette scores."""

    cluster_info: ClusterInfoTuple
    fingerprints: ClientFingerprintTuple
    silhouette: float
    silhouette_scores: ClientSilhouetteScoreTuple
    k: int

    def __post_init__(self) -> None:
        """Coerce raw inputs into typed tuple wrappers."""
        c_in: Any = self.cluster_info
        if not isinstance(c_in, ClusterInfoTuple):
            object.__setattr__(
                self,
                "cluster_info",
                ClusterInfoTuple(c_in.values() if hasattr(c_in, "values") else c_in),
            )

        f_in: Any = self.fingerprints
        if not isinstance(f_in, ClientFingerprintTuple):
            if hasattr(f_in, "items"):
                f_in = [
                    ClientFingerprint(k, *[float(x) for x in v])
                    for k, v in f_in.items()
                ]
            object.__setattr__(self, "fingerprints", ClientFingerprintTuple(f_in))

        s_in: Any = self.silhouette_scores
        if not isinstance(s_in, ClientSilhouetteScoreTuple):
            if hasattr(s_in, "items"):
                s_in = [
                    ClientSilhouetteScore(str(k), float(v)) for k, v in s_in.items()
                ]
            object.__setattr__(
                self, "silhouette_scores", ClientSilhouetteScoreTuple(s_in)
            )

    def cluster_for(self, cluster_id: str) -> ClusterInfo:
        """Look up a cluster by its identifier."""
        return self.cluster_info[cluster_id]

    def fingerprint_for(self, client_id: str) -> ClientFingerprint:
        """Look up a client fingerprint by client identifier."""
        return self.fingerprints[client_id]


@dataclass(frozen=True, slots=True)
class ClientThreshold:
    """Per-client threshold value with eligibility status and threshold policy."""

    client_id: str
    threshold: float
    calibration_pending: bool
    strategy: ThresholdPolicy


@dataclass(frozen=True, slots=True)
class ThresholdMetadata:
    """Optional cluster metadata attached to a threshold result."""

    cluster: ClusterMetadata | None


@dataclass(frozen=True, slots=True)
class ThresholdResult:
    """Output of a threshold policy run: global tau, per-client thresholds, and metadata."""

    run: PolicyRunId
    tau_global: float
    client_thresholds: tuple[ClientThreshold, ...]
    metadata: ThresholdMetadata

    @property
    def eligible_count(self) -> int:
        """Return the number of clients with resolved thresholds."""
        return sum(1 for ct in self.client_thresholds if not ct.calibration_pending)

    @property
    def pending_count(self) -> int:
        """Return the number of clients still awaiting calibration."""
        return sum(1 for ct in self.client_thresholds if ct.calibration_pending)

    def for_client(self, client_id: str) -> ClientThreshold:
        """Return the ClientThreshold for a client, raising KeyError if absent."""
        for threshold in self.client_thresholds:
            if threshold.client_id == client_id:
                return threshold
        raise KeyError(client_id)


class ClientEvalResult(FrozenModel):
    """Evaluation metrics for one client: FPR, TPR, accuracy, confusion matrix, and threshold info."""

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
    """Client evaluation result extended with AUROC and PR AUC scores."""

    auroc: float
    pr_auc: float


class PolicyResult(FrozenModel):
    """Aggregate result for a threshold policy across all clients in a given stage and seed."""

    policy: ThresholdPolicy
    stage: ExperimentStage
    seed: int
    per_client: dict[str, ClientEvalResult]
    n_clients: int
    calibration_pending_clients: tuple[str, ...]
