from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from datp.artifacts import ArtifactLayout
from datp.config import (
    CLUSTER_K_NBAIOT,
    CLUSTER_MAX_ITER,
    CLUSTER_N_INIT,
    CLUSTER_RANDOM_STATE,
    N_MIN,
    ExperimentStage,
)
from datp.core import (
    ClientFingerprint,
    ClientThreshold,
    ClusterCountSilhouetteScore,
    ClusterInfo,
    ClusterMetadata,
    MetricsProvenance,
    PolicyRunId,
    ThresholdResult,
    TrainingCellId,
    array_hash,
    get_logger,
    git_commit,
    source_hash,
    utc_timestamp,
)
from datp.enums import (
    ErrorScope,
    POLICY_THRESHOLD_SOURCE,
    THRESHOLD_AGGREGATION_BY_POLICY,
    ClientStatus,
    DatasetID,
    MetricName,
    ProvenanceSentinel,
    RunKind,
    ThresholdAggregationMethod,
    ThresholdPolicy,
    ThresholdSource,
)
from datp.evaluation import ClientEvaluationRecord, EvaluationResult
from datp.types import (
    ClassificationScore,
    ClientCount,
    ClientId,
    ClusterCount,
    ClusterId,
    ClusterIndex,
    ContentHash,
    FalseNegativeRate,
    FalsePositiveRate,
    FeatureMatrix,
    Index,
    IterationCount,
    NarrativeText,
    Quantile,
    RandomSeed,
    Ratio,
    RunId,
    SampleCount,
    SchemaVersion,
    ScoreValue,
    ScoreVector,
    SignedCount,
    Threshold,
    TrueNegativeRate,
    TruePositiveRate,
)
from datp.statistics import (
    floats_of,
    mean_of,
    percentile_of,
    silhouette_of,
    skewness_of,
    std_of,
)

if TYPE_CHECKING:
    from datp.config import ThresholdConfig


def percentile_threshold(errors: ScoreVector, q: Quantile) -> Threshold:
    if errors.size == 0:
        raise ValueError(
            f"[{ErrorScope.THRESHOLDS}] Cannot compute percentile. Expected: non-empty array. Got: empty array."
        )
    if q < 0.0 or q > 100.0:
        raise ValueError(
            f"[{ErrorScope.THRESHOLDS}] Invalid percentile. Expected: 0 <= q <= 100. Got: {q}."
        )
    return percentile_of(errors, q)


def arithmetic_mean_threshold(tau_list: list[Threshold] | ScoreVector) -> Threshold:
    arr = np.asarray(tau_list, dtype=np.float64)
    if arr.size == 0:
        raise ValueError(
            f"[{ErrorScope.THRESHOLDS}] Cannot compute mean. Expected: non-empty threshold list. Got: empty list."
        )
    return mean_of(arr)


@dataclass(frozen=True, slots=True)
class EligibilityResult:
    eligible_ids: tuple[ClientId, ...]
    pending_ids: tuple[ClientId, ...]


@dataclass(frozen=True, slots=True)
class ClientCalibrationErrors:
    client_id: ClientId
    errors: ScoreVector

    def __post_init__(self) -> None:
        object.__setattr__(self, "errors", np.array(self.errors, copy=False))


@dataclass(frozen=True, slots=True)
class CalibrationErrorSet:
    clients: tuple[ClientCalibrationErrors, ...]

    @classmethod
    def from_mapping(
        cls,
        client_errors: Mapping[ClientId, ScoreVector],
    ) -> "CalibrationErrorSet":
        return cls(
            clients=tuple(
                ClientCalibrationErrors(client_id=ClientId(cid), errors=errors)
                for cid, errors in client_errors.items()
            )
        )

    def for_client(self, client_id: ClientId) -> ClientCalibrationErrors:
        for client in self.clients:
            if client.client_id == client_id:
                return client
        raise KeyError(client_id)


@dataclass(frozen=True, slots=True)
class ClientThresholdsCollection(Mapping[ClientId, float]):
    entries: tuple[ClientThreshold, ...]

    @classmethod
    def from_mapping(
        cls,
        thresholds: Mapping[ClientId, Threshold],
        strategy: ThresholdPolicy,
    ) -> "ClientThresholdsCollection":
        return cls(
            entries=tuple(
                ClientThreshold(
                    client_id=ClientId(cid),
                    threshold=tau,
                    status=ClientStatus.ELIGIBLE,
                    strategy=strategy,
                )
                for cid, tau in thresholds.items()
            )
        )

    @property
    def client_ids(self) -> tuple[ClientId, ...]:
        return tuple(entry.client_id for entry in self.entries)

    def __len__(self) -> int:
        return len(self.entries)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Mapping):
            return dict(self.items()) == other
        return super().__eq__(other)

    def __getitem__(self, client_id: ClientId) -> ScoreValue:
        for entry in self.entries:
            if entry.client_id == client_id:
                return entry.threshold
        raise KeyError(client_id)

    def __iter__(self):
        return iter(self.client_ids)


def identify_eligible(
    error_set: CalibrationErrorSet | Mapping[ClientId, ScoreVector],
    n_min: SampleCount,
) -> EligibilityResult:
    if not isinstance(error_set, CalibrationErrorSet):
        error_set = CalibrationErrorSet.from_mapping(error_set)
    eligible: list[ClientId] = []
    pending: list[ClientId] = []
    for client in error_set.clients:
        if client.errors.size >= n_min:
            eligible.append(client.client_id)
        else:
            pending.append(client.client_id)
    return EligibilityResult(eligible_ids=tuple(eligible), pending_ids=tuple(pending))


def compute_client_thresholds(
    error_set: CalibrationErrorSet | Mapping[ClientId, ScoreVector],
    eligibility: EligibilityResult,
    q: Quantile,
) -> ClientThresholdsCollection:
    if not isinstance(error_set, CalibrationErrorSet):
        error_set = CalibrationErrorSet.from_mapping(error_set)
    return ClientThresholdsCollection(
        entries=tuple(
            ClientThreshold(
                client_id=cid,
                threshold=percentile_threshold(error_set.for_client(cid).errors, q=q),
                status=ClientStatus.ELIGIBLE,
                strategy=ThresholdPolicy.LOCAL_THRESHOLD,
            )
            for cid in eligibility.eligible_ids
        )
    )


def compute_tau_global(
    thresholds: ClientThresholdsCollection | Mapping[ClientId, Threshold],
) -> ScoreValue:
    if not thresholds:
        raise ValueError(
            "[eligibility] Cannot compute tau_global: no eligible clients. Expected: at least 1 eligible client. Got: 0."
        )
    return arithmetic_mean_threshold(list(thresholds.values()))


def build_threshold_result(
    run: PolicyRunId,
    tau_global: Threshold,
    eligible_thresholds: ClientThresholdsCollection | Mapping[ClientId, Threshold],
    pending_clients: Sequence[ClientId],
    cluster_metadata: ClusterMetadata | None,
) -> ThresholdResult:
    thresholds: list[ClientThreshold] = [
        ClientThreshold(
            client_id=ClientId(cid),
            threshold=tau,
            status=ClientStatus.ELIGIBLE,
            strategy=run.policy,
        )
        for cid, tau in eligible_thresholds.items()
    ]

    for cid in pending_clients:
        thresholds.append(
            ClientThreshold(
                client_id=ClientId(cid),
                threshold=tau_global,
                status=ClientStatus.CALIBRATION_PENDING,
                strategy=run.policy,
            )
        )

    return ThresholdResult(
        run=run,
        tau_global=tau_global,
        client_thresholds=tuple(thresholds),
        cluster=cluster_metadata,
    )


logger = get_logger(__name__)


_MIN_CLUSTER_ELIGIBLE = 2


@dataclass(frozen=True, slots=True)
class ClusterAssignments:
    client_cluster: dict[ClientId, SignedCount]
    cluster_taus_map: dict[ClusterIndex, list[ScoreValue]]
    tau_per_cluster: dict[ClusterIndex, Threshold]


@dataclass(frozen=True, slots=True)
class ClusterMetadataInput:
    k: ClusterCount
    client_cluster: dict[ClientId, SignedCount]
    tau_per_cluster: dict[ClusterIndex, Threshold]
    silhouette: ClassificationScore
    silhouette_scores: dict[ClusterIndex, ClassificationScore]
    fingerprints: dict[ClientId, FeatureMatrix]
    eligible_ids: list[ClientId]


@dataclass(frozen=True, slots=True)
class _ClusterComputationRequest:
    client_errors: dict[ClientId, ScoreVector]
    eligibility: EligibilityResult
    q: Quantile
    random_state: RandomSeed
    cluster_k: ClusterCount
    n_init: IterationCount
    max_iter: IterationCount


@dataclass(frozen=True, slots=True)
class _ClusterComputationResult:
    eligible_map: dict[ClientId, ScoreValue]
    metadata: ClusterMetadata


def compute_global(
    client_errors: dict[ClientId, ScoreVector],
    n_min: SampleCount,
    q: Quantile,
    run: PolicyRunId,
) -> ThresholdResult:
    eligibility = identify_eligible(client_errors, n_min=n_min)
    client_taus = compute_client_thresholds(client_errors, eligibility, q=q)
    tau_global = compute_tau_global(client_taus)
    eligible_map = dict.fromkeys(eligibility.eligible_ids, tau_global)

    return build_threshold_result(
        run=run,
        tau_global=tau_global,
        eligible_thresholds=eligible_map,
        pending_clients=eligibility.pending_ids,
        cluster_metadata=None,
    )


def compute_local(
    client_errors: dict[ClientId, ScoreVector],
    n_min: SampleCount,
    tau_global: Threshold,
    q: Quantile,
    run: PolicyRunId,
) -> ThresholdResult:
    eligibility = identify_eligible(client_errors, n_min=n_min)
    client_taus = compute_client_thresholds(client_errors, eligibility, q=q)

    return build_threshold_result(
        run=run,
        tau_global=tau_global,
        eligible_thresholds=client_taus,
        pending_clients=eligibility.pending_ids,
        cluster_metadata=None,
    )


def compute_fingerprints(
    client_errors: dict[ClientId, ScoreVector],
    eligible: Sequence[ClientId],
    *,
    q: Quantile,
) -> dict[ClientId, FeatureMatrix]:
    fingerprints: dict[ClientId, FeatureMatrix] = {}
    for cid in eligible:
        errors = np.asarray(client_errors[cid], dtype=np.float64)
        mean_error = mean_of(errors)
        std_error = std_of(errors, ddof=1) if errors.size >= 2 else 0.0
        raw_skew = skewness_of(errors) if errors.size >= 2 and std_error > 0.0 else 0.0
        skew_error = raw_skew if np.isfinite(raw_skew) else 0.0
        p95_error = percentile_of(errors, q)
        fingerprints[cid] = np.array(
            [mean_error, std_error, skew_error, p95_error],
            dtype=np.float64,
        )
    return fingerprints


def _validate_fingerprint_matrix(fingerprint_matrix: FeatureMatrix) -> None:
    if not np.isfinite(fingerprint_matrix).all():
        raise ValueError(
            f"[{ErrorScope.THRESHOLD_POLICIES}] Invalid fingerprint values. Expected: finite mean/std/skew/p95. Got: NaN or inf."
        )
    unique_rows = np.unique(fingerprint_matrix, axis=0)
    if unique_rows.shape[0] < 2:
        raise ValueError(
            f"[{ErrorScope.THRESHOLD_POLICIES}] Degenerate fingerprints: all eligible clients have identical fingerprints. Expected: at least 2 distinct eligible fingerprints. Got: {unique_rows.shape[0]}."
        )


def scaled_fingerprints(
    client_errors: dict[ClientId, ScoreVector],
    eligible_ids: list[ClientId],
    *,
    q: Quantile,
) -> tuple[dict[ClientId, FeatureMatrix], FeatureMatrix]:
    fingerprints = compute_fingerprints(client_errors, eligible_ids, q=q)
    fingerprint_matrix = np.array([fingerprints[cid] for cid in eligible_ids])
    _validate_fingerprint_matrix(fingerprint_matrix)
    fingerprint_scaled = StandardScaler().fit_transform(fingerprint_matrix)
    if not np.isfinite(fingerprint_scaled).all():
        raise ValueError(
            f"[{ErrorScope.THRESHOLD_POLICIES}] Invalid scaled fingerprints. Expected: finite values after scaling. Got: NaN or inf."
        )
    return fingerprints, fingerprint_scaled


def silhouette_scores_by_k(
    x_scaled: ScoreVector,
    k_candidates: list[SignedCount],
    random_state: RandomSeed,
    n_init: IterationCount,
    max_iter: IterationCount,
) -> dict[Index, ClassificationScore]:
    scores: dict[Index, ScoreValue] = {}
    for k in k_candidates:
        if k >= x_scaled.shape[0]:
            continue
        kmeans = KMeans(
            n_clusters=k,
            init="k-means++",
            random_state=random_state,
            n_init=n_init,
            max_iter=max_iter,
        )
        labels = kmeans.fit_predict(x_scaled)
        n_labels = len(set(labels))
        if n_labels < 2 or n_labels >= x_scaled.shape[0]:
            continue
        score = silhouette_of(x_scaled, labels, random_state)
        if not np.isfinite(score):
            continue
        logger.info("CLUSTER silhouette", k=k, score=score)
        scores[k] = score
    return scores


def select_cluster_k(
    *,
    cluster_k: ClusterCount,
    eligible_count: SampleCount,
    silhouette_scores: dict[ClusterIndex, ClassificationScore],
) -> tuple[ClusterCount, ScoreValue]:
    if cluster_k <= 0:
        raise ValueError(
            f"[{ErrorScope.THRESHOLD_POLICIES}] Invalid cluster k. Expected: locked fixed K > 0. Got: {cluster_k}."
        )
    if cluster_k >= eligible_count:
        raise ValueError(
            f"[{ErrorScope.THRESHOLD_POLICIES}] Invalid cluster k. Expected: 2 <= k < eligible_count ({eligible_count}). Got: {cluster_k}."
        )
    silhouette = silhouette_scores.get(cluster_k)
    if silhouette is None:
        raise ValueError(
            f"[{ErrorScope.THRESHOLD_POLICIES}] Cluster k has no valid silhouette score. Expected: non-degenerate clustering. Got: {cluster_k}."
        )
    return cluster_k, silhouette


def fit_cluster_labels(
    fingerprint_scaled: FeatureMatrix,
    *,
    k: ClusterCount,
    random_state: RandomSeed,
    n_init: IterationCount,
    max_iter: IterationCount,
) -> ScoreVector:
    kmeans = KMeans(
        n_clusters=k,
        init="k-means++",
        random_state=random_state,
        n_init=n_init,
        max_iter=max_iter,
    )
    return kmeans.fit_predict(fingerprint_scaled)


def final_silhouette(
    fingerprint_scaled: FeatureMatrix,
    labels: ScoreVector,
    *,
    random_state: RandomSeed,
) -> ClassificationScore:
    if len(set(labels)) <= 1:
        return 0.0
    return silhouette_of(fingerprint_scaled, labels, random_state)


def cluster_assignments(
    *,
    eligible_ids: list[ClientId],
    labels: ScoreVector,
    client_taus: dict[ClientId, ScoreValue],
) -> ClusterAssignments:
    client_cluster = dict(zip(eligible_ids, labels.astype(int), strict=True))
    cluster_taus_map: dict[ClusterIndex, list[ScoreValue]] = defaultdict(list)
    for cid in eligible_ids:
        cluster_taus_map[client_cluster[cid]].append(client_taus[cid])
    tau_per_cluster = {
        cluster: arithmetic_mean_threshold(taus)
        for cluster, taus in cluster_taus_map.items()
    }
    return ClusterAssignments(
        client_cluster=client_cluster,
        cluster_taus_map=cluster_taus_map,
        tau_per_cluster=tau_per_cluster,
    )


def _log_clustering(
    *,
    k: ClusterCount,
    cluster_taus_map: dict[ClusterIndex, list[ScoreValue]],
    silhouette: ClassificationScore,
) -> None:
    logger.info(
        "CLUSTER clustering complete",
        k=k,
        cluster_sizes=[len(cluster_taus_map[c]) for c in sorted(cluster_taus_map)],
        silhouette=silhouette,
    )


def cluster_info(
    *,
    eligible_ids: list[ClientId],
    client_cluster: dict[ClientId, SignedCount],
    tau_per_cluster: dict[ClusterIndex, Threshold],
) -> tuple[ClusterInfo, ...]:
    return tuple(
        ClusterInfo(
            cluster_id=ClusterId(f"cluster_{cluster}"),
            tau_cluster=tau_per_cluster[cluster],
            members=tuple(
                ClientId(cid) for cid in eligible_ids if client_cluster[cid] == cluster
            ),
        )
        for cluster in sorted(tau_per_cluster)
    )


def build_cluster_metadata(metadata_input: ClusterMetadataInput) -> ClusterMetadata:
    info = cluster_info(
        eligible_ids=metadata_input.eligible_ids,
        client_cluster=metadata_input.client_cluster,
        tau_per_cluster=metadata_input.tau_per_cluster,
    )
    fingerprint_values = {
        cid: floats_of(metadata_input.fingerprints[cid])
        for cid in metadata_input.eligible_ids
    }
    return ClusterMetadata(
        k=metadata_input.k,
        cluster_info=info,
        silhouette=metadata_input.silhouette,
        silhouette_scores=tuple(
            ClusterCountSilhouetteScore(cluster_count=k, score=v)
            for k, v in metadata_input.silhouette_scores.items()
        ),
        fingerprints=tuple(
            ClientFingerprint(
                client_id=ClientId(cid),
                mean=fingerprint_values[cid][0],
                std=fingerprint_values[cid][1],
                skewness=fingerprint_values[cid][2],
                p95=fingerprint_values[cid][3],
            )
            for cid in metadata_input.eligible_ids
        ),
    )


def _compute_cluster_thresholds(
    request: _ClusterComputationRequest,
) -> _ClusterComputationResult:
    client_taus = compute_client_thresholds(
        request.client_errors,
        request.eligibility,
        q=request.q,
    )
    eligible_ids = sorted(request.eligibility.eligible_ids)
    fingerprints, fingerprint_scaled = scaled_fingerprints(
        request.client_errors,
        eligible_ids,
        q=request.q,
    )
    silhouette_scores = silhouette_scores_by_k(
        fingerprint_scaled,
        k_candidates=[request.cluster_k],
        random_state=request.random_state,
        n_init=request.n_init,
        max_iter=request.max_iter,
    )
    k, _ = select_cluster_k(
        cluster_k=request.cluster_k,
        eligible_count=len(request.eligibility.eligible_ids),
        silhouette_scores=silhouette_scores,
    )
    labels = fit_cluster_labels(
        fingerprint_scaled,
        k=k,
        random_state=request.random_state,
        n_init=request.n_init,
        max_iter=request.max_iter,
    )
    final_score = final_silhouette(
        fingerprint_scaled,
        labels,
        random_state=request.random_state,
    )
    assignments = cluster_assignments(
        eligible_ids=eligible_ids,
        labels=labels,
        client_taus=dict(client_taus.items()),
    )
    _log_clustering(
        k=k,
        cluster_taus_map=assignments.cluster_taus_map,
        silhouette=final_score,
    )
    return _ClusterComputationResult(
        eligible_map={
            cid: assignments.tau_per_cluster[assignments.client_cluster[cid]]
            for cid in eligible_ids
        },
        metadata=build_cluster_metadata(
            ClusterMetadataInput(
                k=k,
                client_cluster=assignments.client_cluster,
                tau_per_cluster=assignments.tau_per_cluster,
                silhouette=final_score,
                silhouette_scores=silhouette_scores,
                fingerprints=fingerprints,
                eligible_ids=eligible_ids,
            ),
        ),
    )


@dataclass(frozen=True, slots=True)
class ClusterHyperparams:
    k: ClusterCount = CLUSTER_K_NBAIOT
    n_init: IterationCount = CLUSTER_N_INIT
    max_iter: IterationCount = CLUSTER_MAX_ITER
    random_state: RandomSeed = CLUSTER_RANDOM_STATE
    n_min: SampleCount = N_MIN


_CLUSTER_CACHE_LIMIT = 256
_CLUSTER_CACHE: dict[
    tuple[
        tuple[tuple[ClientId, ContentHash], ...],
        Threshold,
        Quantile,
        ClusterHyperparams,
        PolicyRunId,
    ],
    ThresholdResult,
] = {}


def compute_cluster(
    client_errors: dict[ClientId, ScoreVector],
    tau_global: Threshold,
    q: Quantile,
    params: ClusterHyperparams,
    run: PolicyRunId,
) -> ThresholdResult:
    if params.k <= 0:
        raise ValueError(
            f"[{ErrorScope.THRESHOLD_POLICIES}] Invalid cluster k. Expected: locked fixed K > 0. Got: {params.k}."
        )
    cache_key = (
        tuple(
            sorted((cid, array_hash(errors)) for cid, errors in client_errors.items())
        ),
        tau_global,
        q,
        params,
        run,
    )
    if (cached := _CLUSTER_CACHE.get(cache_key)) is not None:
        return cached
    eligibility = identify_eligible(client_errors, n_min=params.n_min)

    if len(eligibility.eligible_ids) < _MIN_CLUSTER_ELIGIBLE:
        raise ValueError(
            f"[{ErrorScope.THRESHOLD_POLICIES}] Cannot cluster. Expected: at least {_MIN_CLUSTER_ELIGIBLE} eligible clients. Got: {len(eligibility.eligible_ids)}."
        )

    result = _compute_cluster_thresholds(
        _ClusterComputationRequest(
            client_errors=client_errors,
            eligibility=eligibility,
            q=q,
            random_state=params.random_state,
            cluster_k=params.k,
            n_init=params.n_init,
            max_iter=params.max_iter,
        )
    )

    threshold_result = build_threshold_result(
        run=run,
        tau_global=tau_global,
        eligible_thresholds=result.eligible_map,
        pending_clients=eligibility.pending_ids,
        cluster_metadata=result.metadata,
    )
    if len(_CLUSTER_CACHE) >= _CLUSTER_CACHE_LIMIT:
        _CLUSTER_CACHE.clear()
    _CLUSTER_CACHE[cache_key] = threshold_result
    return threshold_result


@dataclass(frozen=True, slots=True)
class ThresholdDerivation:
    policy: ThresholdPolicy
    client_errors: dict[ClientId, ScoreVector]
    n_min: SampleCount
    q: Quantile
    tau_global: Threshold
    threshold_cfg: ThresholdConfig
    seed: RandomSeed = RandomSeed(0)


def derive_threshold(inputs: ThresholdDerivation) -> ThresholdResult:
    run = PolicyRunId(
        cell=TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=inputs.seed),
        policy=inputs.policy,
    )

    if inputs.policy is ThresholdPolicy.GLOBAL_THRESHOLD:
        return compute_global(
            inputs.client_errors,
            inputs.n_min,
            q=inputs.q,
            run=run,
        )
    if inputs.policy is ThresholdPolicy.LOCAL_THRESHOLD:
        return compute_local(
            inputs.client_errors,
            inputs.n_min,
            inputs.tau_global,
            q=inputs.q,
            run=run,
        )
    if inputs.policy is ThresholdPolicy.CLUSTER_THRESHOLD:
        return compute_cluster(
            inputs.client_errors,
            inputs.tau_global,
            inputs.q,
            ClusterHyperparams(
                k=inputs.threshold_cfg.cluster_k_nbaiot,
                n_init=inputs.threshold_cfg.cluster_n_init,
                max_iter=inputs.threshold_cfg.cluster_max_iter,
                random_state=RandomSeed(inputs.threshold_cfg.cluster_random_state),
                n_min=inputs.n_min,
            ),
            run,
        )

    raise ValueError(
        f"[{ErrorScope.THRESHOLD_DERIVATION}] Unknown policy for threshold derivation. Expected: GLOBAL_THRESHOLD/LOCAL_THRESHOLD/CLUSTER_THRESHOLD. Got: {inputs.policy!r}."
    )


METRIC_SCHEMA_VERSION: SchemaVersion = "2"


THRESHOLD_SCHEMA_VERSION: SchemaVersion = "1"


@dataclass(frozen=True, slots=True)
class MetricsBuildRequest:
    eval_result: EvaluationResult
    threshold_result: ThresholdResult
    config_identity: ContentHash
    split_manifest_identity: ContentHash
    model_identity: ContentHash
    score_artifact_identity: ContentHash


class ConfusionMatrix(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    tp: SampleCount
    fp: SampleCount
    tn: SampleCount
    fn: SampleCount


class MetricsClientDetail(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    client_id: ClientId
    fpr: FalsePositiveRate
    tpr: TruePositiveRate
    tnr: TrueNegativeRate
    fnr: FalseNegativeRate
    precision: ClassificationScore
    recall: ClassificationScore
    balanced_accuracy: ClassificationScore
    macro_f1: ClassificationScore
    confusion_matrix: ConfusionMatrix
    n_benign: SampleCount
    n_attack: SampleCount
    calibration_pending: bool
    evaluation_incomplete: bool
    threshold_value: Threshold
    threshold_source: ThresholdSource


class SweepMetrics(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: SchemaVersion
    metric_schema_version: SchemaVersion
    threshold_schema_version: SchemaVersion
    run_id: RunId
    run_kind: RunKind
    policy: ThresholdPolicy
    stage: ExperimentStage
    seed: RandomSeed
    dataset: DatasetID
    threshold_scope: ThresholdAggregationMethod
    threshold_strategy_name: NarrativeText
    tau_global: Threshold
    eligible_ids: tuple[ClientId, ...]
    pending_ids: tuple[ClientId, ...]
    eval_incomplete_ids: tuple[ClientId, ...]
    eligible_count: ClientCount
    pending_count: ClientCount
    eval_incomplete_count: ClientCount
    client_count: ClientCount
    coverage_ratio: Ratio
    cv_fpr: FalsePositiveRate
    mean_fpr: FalsePositiveRate | None = None
    std_fpr: FalsePositiveRate | None = None
    cv_tpr: TruePositiveRate
    iqr_fpr: FalsePositiveRate
    iqr_tpr: TruePositiveRate
    worst_client_fpr: FalsePositiveRate
    worst_client_id: ClientId | None
    worst_ba: ScoreValue
    p10_macro_f1: ClassificationScore
    aggregate_metrics: dict[MetricName, ScoreValue | ClientId | None]
    provenance: MetricsProvenance
    per_client: tuple[MetricsClientDetail, ...]

    @model_validator(mode="after")
    def validate_partition(self) -> "SweepMetrics":
        client_ids = tuple(client.client_id for client in self.per_client)
        client_id_set = set(client_ids)
        eligible = set(self.eligible_ids)
        pending = set(self.pending_ids)
        incomplete = set(self.eval_incomplete_ids)
        _validate_client_membership(
            self, client_ids, client_id_set, eligible, pending, incomplete
        )
        _validate_client_states(self, pending, incomplete)
        _validate_provenance(self.provenance)
        return self


def _validate_client_membership(
    metrics: SweepMetrics,
    client_ids: tuple[ClientId, ...],
    client_id_set: set[ClientId],
    eligible: set[ClientId],
    pending: set[ClientId],
    incomplete: set[ClientId],
) -> None:
    if len(client_id_set) != len(client_ids):
        raise ValueError("per_client contains duplicate client IDs")
    if overlap := eligible & pending:
        raise ValueError(f"eligible_ids overlap pending_ids: {sorted(overlap)}")
    if missing := (eligible | pending | incomplete) - client_id_set:
        raise ValueError(f"eligibility IDs missing per_client rows: {sorted(missing)}")
    if metrics.eligible_count != len(eligible):
        raise ValueError("eligible_count does not match eligible_ids")
    if metrics.pending_count != len(pending):
        raise ValueError("pending_count does not match pending_ids")
    if metrics.eval_incomplete_count != len(incomplete):
        raise ValueError("eval_incomplete_count does not match eval_incomplete_ids")
    if metrics.client_count != len(client_id_set):
        raise ValueError("client_count does not match per_client rows")
    if not 0.0 <= metrics.coverage_ratio <= 1.0:
        raise ValueError("coverage_ratio must be within [0, 1]")


def _validate_client_states(
    metrics: SweepMetrics,
    pending: set[ClientId],
    incomplete: set[ClientId],
) -> None:
    for client in metrics.per_client:
        if client.client_id in pending and not client.calibration_pending:
            raise ValueError(
                f"pending client {client.client_id} missing calibration_pending=true"
            )
        if client.client_id in incomplete and not client.evaluation_incomplete:
            raise ValueError(
                f"eval-incomplete client {client.client_id} missing evaluation_incomplete=true"
            )


def _validate_provenance(provenance: MetricsProvenance) -> None:
    values = (
        provenance.config_identity,
        provenance.split_manifest_identity,
        provenance.model_identity,
        provenance.score_artifact_identity,
        provenance.metric_code_version,
        provenance.threshold_code_version,
        provenance.package_version,
        provenance.generated_at_utc,
    )
    if any(
        value
        in {
            ProvenanceSentinel.UNKNOWN,
            ProvenanceSentinel.UNKNOWN_LOWERCASE,
        }
        for value in values
    ):
        raise ValueError("provenance contains a vague UNKNOWN value")
    identities = (
        provenance.config_identity,
        provenance.split_manifest_identity,
        provenance.model_identity,
        provenance.score_artifact_identity,
    )
    if any(value == ProvenanceSentinel.MISSING_MANIFEST_HASH for value in identities):
        raise ValueError("provenance contains an unresolved MISSING_* identity")


def _to_client_detail(
    record: ClientEvaluationRecord, default_source: ThresholdSource
) -> MetricsClientDetail:
    return MetricsClientDetail(
        client_id=record.client_id,
        fpr=record.metrics.fpr,
        tpr=record.metrics.tpr,
        tnr=record.metrics.tnr,
        fnr=record.metrics.fnr,
        precision=record.metrics.precision,
        recall=record.metrics.recall,
        balanced_accuracy=record.metrics.balanced_accuracy,
        macro_f1=record.metrics.macro_f1,
        confusion_matrix=ConfusionMatrix(
            tp=record.confusion.tp,
            fp=record.confusion.fp,
            tn=record.confusion.tn,
            fn=record.confusion.fn,
        ),
        n_benign=record.n_benign,
        n_attack=record.n_attack,
        calibration_pending=record.threshold.status is ClientStatus.CALIBRATION_PENDING,
        evaluation_incomplete=record.evaluation_incomplete,
        threshold_value=record.threshold.threshold,
        threshold_source=ThresholdSource.TAU_GLOBAL_FALLBACK
        if record.threshold.status is ClientStatus.CALIBRATION_PENDING
        else default_source,
    )


def build_metrics_dict(req: MetricsBuildRequest) -> SweepMetrics:
    er = req.eval_result
    tr = req.threshold_result

    aggregate_metrics = {
        MetricName.CV_FPR: er.dispersion.cv_fpr,
        MetricName.MEAN_FPR: er.dispersion.mean_fpr,
        MetricName.STD_FPR: er.dispersion.std_fpr,
        MetricName.CV_TPR: er.dispersion.cv_tpr,
        MetricName.IQR_FPR: er.dispersion.iqr_fpr,
        MetricName.IQR_TPR: er.dispersion.iqr_tpr,
        MetricName.MAX_MIN_FPR_GAP: er.dispersion.max_min_fpr_gap,
        MetricName.WORST_CLIENT_FPR: er.dispersion.worst_client_fpr,
        MetricName.WORST_CLIENT_ID: er.dispersion.worst_client_id,
        MetricName.WORST_BA: er.dispersion.worst_ba,
        MetricName.P10_MACRO_F1: er.dispersion.p10_macro_f1,
    }

    provenance = MetricsProvenance(
        config_identity=req.config_identity,
        split_manifest_identity=req.split_manifest_identity,
        model_identity=req.model_identity,
        score_artifact_identity=req.score_artifact_identity,
        metric_code_version=source_hash([Path(__file__)]),
        threshold_code_version=git_commit(),
        package_version=git_commit(),
        generated_at_utc=utc_timestamp(),
    )

    return SweepMetrics(
        schema_version=METRIC_SCHEMA_VERSION,
        metric_schema_version=METRIC_SCHEMA_VERSION,
        threshold_schema_version=THRESHOLD_SCHEMA_VERSION,
        run_id=RunId(f"{er.run.stage}_{er.run.policy}_seed{er.run.seed}"),
        run_kind=RunKind.CORE_LADDER,
        policy=er.run.policy,
        stage=er.run.stage,
        seed=er.run.seed,
        dataset=er.dataset,
        threshold_scope=THRESHOLD_AGGREGATION_BY_POLICY[er.run.policy],
        threshold_strategy_name=tr.run.policy,
        tau_global=tr.tau_global,
        eligible_ids=er.eligible_ids,
        pending_ids=er.pending_ids,
        eval_incomplete_ids=er.incomplete_ids,
        eligible_count=tr.eligible_count,
        pending_count=tr.pending_count,
        eval_incomplete_count=len(er.incomplete_ids),
        client_count=er.dispersion.client_count,
        coverage_ratio=er.coverage_ratio,
        cv_fpr=er.dispersion.cv_fpr,
        mean_fpr=er.dispersion.mean_fpr,
        std_fpr=er.dispersion.std_fpr,
        cv_tpr=er.dispersion.cv_tpr,
        iqr_fpr=er.dispersion.iqr_fpr,
        iqr_tpr=er.dispersion.iqr_tpr,
        worst_client_fpr=er.dispersion.worst_client_fpr,
        worst_client_id=er.dispersion.worst_client_id,
        worst_ba=er.dispersion.worst_ba,
        p10_macro_f1=er.dispersion.p10_macro_f1,
        aggregate_metrics=aggregate_metrics,
        provenance=provenance,
        per_client=tuple(
            _to_client_detail(c, POLICY_THRESHOLD_SOURCE[er.run.policy])
            for c in er.clients
        ),
    )


def results_exist(
    policy: ThresholdPolicy,
    stage: ExperimentStage,
    seed: RandomSeed,
    *,
    base_dir: Path,
) -> bool:
    run = PolicyRunId(
        cell=TrainingCellId(stage=stage, seed=RandomSeed(seed)), policy=policy
    )
    path = ArtifactLayout(base_dir=base_dir, stage=stage).policy_run(run).metrics_path

    if not path.is_file() or path.stat().st_size == 0:
        return False

    try:
        SweepMetrics.model_validate_json(path.read_text())
    except ValidationError as exc:
        logger.warning("metrics file failed validation", path=path, error=exc)
        return False
    return True
