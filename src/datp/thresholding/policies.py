from __future__ import annotations

from datp.types import (
    ClassificationScore,
    ClientId,
    ClusterCount,
    ClusterId,
    ClusterIndex,
    FeatureMatrix,
    Index,
    IterationCount,
    Quantile,
    RandomSeed,
    SampleCount,
    ScoreValue,
    ScoreVector,
    SignedCount,
    Threshold,
)


from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy import stats as sp_stats
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from datp.core.enums import CLUSTER_FINGERPRINT_FEATURES
from datp.core.identity import PolicyRunId
from datp.core.logging import get_logger
from datp.core.types import (
    ClientFingerprint,
    ClusterCountSilhouetteScore,
    ClusterInfo,
    ClusterMetadata,
    ThresholdResult,
)
from datp.thresholding.eligibility import (
    EligibilityResult,
    build_threshold_result,
    compute_client_thresholds,
    compute_tau_global,
    identify_eligible,
)
from datp.thresholding.thresholds import arithmetic_mean_threshold

__all__ = [
    "ClusterAssignments",
    "ClusterMetadataInput",
    "build_cluster_metadata",
    "cluster_assignments",
    "cluster_info",
    "compute_cluster",
    "compute_fingerprints",
    "compute_global",
    "compute_local",
    "final_silhouette",
    "fit_cluster_labels",
    "scaled_fingerprints",
    "select_cluster_k",
    "silhouette_scores_by_k",
    "validate_k_candidates",
]

logger = get_logger(__name__)

_MODULE = "thresholding.policies"
_MIN_CLUSTER_ELIGIBLE = 2

if len(CLUSTER_FINGERPRINT_FEATURES) != 4:
    raise ValueError(
        "CLUSTER_FINGERPRINT_FEATURES must have exactly 4 elements, got "
        f"{len(CLUSTER_FINGERPRINT_FEATURES)}"
    )


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
        mean_error = float(np.mean(errors))
        std_error = float(np.std(errors, ddof=1)) if errors.size >= 2 else 0.0
        raw_skew = (
            float(sp_stats.skew(errors))
            if errors.size >= 2 and std_error > 0.0
            else 0.0
        )
        skew_error = raw_skew if np.isfinite(raw_skew) else 0.0
        p95_error = float(np.percentile(errors, q))
        fingerprints[cid] = np.array(
            [mean_error, std_error, skew_error, p95_error],
            dtype=np.float64,
        )
    return fingerprints


def _validate_fingerprint_matrix(fingerprint_matrix: FeatureMatrix) -> None:
    if not np.isfinite(fingerprint_matrix).all():
        raise ValueError(
            f"[{_MODULE}] Invalid fingerprint values. Expected: finite mean/std/skew/p95. Got: NaN or inf."
        )
    unique_rows = np.unique(fingerprint_matrix, axis=0)
    if unique_rows.shape[0] < 2:
        raise ValueError(
            f"[{_MODULE}] Degenerate fingerprints: all eligible clients have identical fingerprints. Expected: at least 2 distinct eligible fingerprints. Got: {unique_rows.shape[0]}."
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
            f"[{_MODULE}] Invalid scaled fingerprints. Expected: finite values after scaling. Got: NaN or inf."
        )
    return fingerprints, fingerprint_scaled


def validate_k_candidates(k_candidates: list[SignedCount]) -> list[SignedCount]:
    if not k_candidates:
        raise ValueError(
            f"[{_MODULE}] k_candidates is empty. Expected: at least one integer k. Got: empty list."
        )
    invalid = [k for k in k_candidates if k < 2]
    if invalid:
        raise ValueError(
            f"[{_MODULE}] Invalid k_candidates. Expected: integers >= 2. Got: {invalid}."
        )
    return sorted(set(k_candidates))


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
        score = float(silhouette_score(x_scaled, labels, random_state=random_state))
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
            f"[{_MODULE}] Invalid cluster k. Expected: locked fixed K > 0. Got: {cluster_k}."
        )
    if cluster_k >= eligible_count:
        raise ValueError(
            f"[{_MODULE}] Invalid cluster k. Expected: 2 <= k < eligible_count ({eligible_count}). Got: {cluster_k}."
        )
    silhouette = silhouette_scores.get(cluster_k)
    if silhouette is None:
        raise ValueError(
            f"[{_MODULE}] Cluster k has no valid silhouette score. Expected: non-degenerate clustering. Got: {cluster_k}."
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
    return float(
        silhouette_score(fingerprint_scaled, labels, random_state=random_state)
    )


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
                ClientId(cid)
                for cid in eligible_ids
                if client_cluster[cid] == cluster
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
                mean=float(metadata_input.fingerprints[cid][0]),
                std=float(metadata_input.fingerprints[cid][1]),
                skewness=float(metadata_input.fingerprints[cid][2]),
                p95=float(metadata_input.fingerprints[cid][3]),
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


def compute_cluster(
    client_errors: dict[ClientId, ScoreVector],
    n_min: SampleCount,
    tau_global: Threshold,
    q: Quantile,
    random_state: RandomSeed,
    cluster_k: ClusterCount,
    n_init: IterationCount,
    max_iter: IterationCount,
    run: PolicyRunId,
) -> ThresholdResult:
    if cluster_k <= 0:
        raise ValueError(
            f"[{_MODULE}] Invalid cluster k. Expected: locked fixed K > 0. Got: {cluster_k}."
        )
    eligibility = identify_eligible(client_errors, n_min=n_min)

    if len(eligibility.eligible_ids) < _MIN_CLUSTER_ELIGIBLE:
        raise ValueError(
            f"[{_MODULE}] Cannot cluster. Expected: at least {_MIN_CLUSTER_ELIGIBLE} eligible clients. Got: {len(eligibility.eligible_ids)}."
        )

    result = _compute_cluster_thresholds(
        _ClusterComputationRequest(
            client_errors=client_errors,
            eligibility=eligibility,
            q=q,
            random_state=random_state,
            cluster_k=cluster_k,
            n_init=n_init,
            max_iter=max_iter,
        )
    )

    return build_threshold_result(
        run=run,
        tau_global=tau_global,
        eligible_thresholds=result.eligible_map,
        pending_clients=eligibility.pending_ids,
        cluster_metadata=result.metadata,
    )
