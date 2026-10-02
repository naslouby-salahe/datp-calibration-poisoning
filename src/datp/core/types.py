from __future__ import annotations

from datp.types import (
    ClassificationScore,
    ClientId,
    ClusterCount,
    ClusterId,
    ContentHash,
    NarrativeText,
    SampleCount,
    SchemaVersion,
    ScoreValue,
    Threshold,
)


from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict

from datp.core.enums import ClientStatus, ThresholdPolicy
from datp.core.identity import PolicyRunId

class FrozenModel(BaseModel):

    model_config = ConfigDict(extra="forbid", frozen=True)


class MetricsProvenance(FrozenModel):

    config_identity: ContentHash
    split_manifest_identity: ContentHash
    model_checkpoint_identity: ContentHash
    score_artifact_identity: ContentHash
    metric_code_version: SchemaVersion
    threshold_code_version: SchemaVersion
    package_version: SchemaVersion
    generated_at_utc: NarrativeText


@dataclass(frozen=True, slots=True)
class ClusterInfo:
    cluster_id: ClusterId
    tau_cluster: Threshold
    members: tuple[ClientId, ...]


@dataclass(frozen=True, slots=True)
class ClientFingerprint:

    client_id: ClientId
    mean: ScoreValue
    std: ScoreValue
    skewness: ScoreValue
    p95: ScoreValue

@dataclass(frozen=True, slots=True)
class ClusterCountSilhouetteScore:

    cluster_count: SampleCount
    score: ScoreValue


@dataclass(frozen=True, slots=True)
class ClusterMetadata:
    cluster_info: tuple[ClusterInfo, ...]
    fingerprints: tuple[ClientFingerprint, ...]
    silhouette: ClassificationScore
    silhouette_scores: tuple[ClusterCountSilhouetteScore, ...]
    k: ClusterCount

    def fingerprint_for(self, client_id: ClientId) -> ClientFingerprint:
        for fingerprint in self.fingerprints:
            if fingerprint.client_id == client_id:
                return fingerprint
        raise KeyError(client_id)


@dataclass(frozen=True, slots=True)
class ClientThreshold:

    client_id: ClientId
    threshold: Threshold
    status: ClientStatus
    strategy: ThresholdPolicy


@dataclass(frozen=True, slots=True)
class ThresholdResult:

    run: PolicyRunId
    tau_global: Threshold
    client_thresholds: tuple[ClientThreshold, ...]
    cluster: ClusterMetadata | None

    @property
    def eligible_count(self) -> SampleCount:
        return sum(1 for ct in self.client_thresholds if ct.status is ClientStatus.ELIGIBLE)

    @property
    def pending_count(self) -> SampleCount:
        return sum(
            1
            for ct in self.client_thresholds
            if ct.status is ClientStatus.CALIBRATION_PENDING
        )
