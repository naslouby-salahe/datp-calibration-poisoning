"""Threshold-policy implementations for the locked policy ladder (GLOBAL, LOCAL, CLUSTER)."""

from __future__ import annotations

from collections import defaultdict
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
    ClientFingerprintTuple,
    ClientSilhouetteScore,
    ClientSilhouetteScoreTuple,
    ClusterInfo,
    ClusterInfoTuple,
    ClusterMetadata,
    ThresholdResult,
)
from datp.thresholding.eligibility import (
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
    """Maps eligible clients to their assigned cluster and per-cluster thresholds."""

    client_cluster: dict[str, int]
    cluster_taus_map: dict[int, list[float]]
    tau_per_cluster: dict[int, float]


@dataclass(frozen=True, slots=True)
class ClusterMetadataInput:
    """Aggregated clustering inputs for building ClusterMetadata."""

    k: int
    client_cluster: dict[str, int]
    tau_per_cluster: dict[int, float]
    silhouette: float
    silhouette_scores: dict[int, float]
    fingerprints: dict[str, np.ndarray]
    eligible_ids: list[str]


@dataclass(frozen=True, slots=True)
class _ClusterComputationRequest:
    client_errors: dict[str, np.ndarray]
    eligible: list[str]
    q: float
    random_state: int
    cluster_k: int
    n_init: int
    max_iter: int


@dataclass(frozen=True, slots=True)
class _ClusterComputationResult:
    eligible_map: dict[str, float]
    metadata: ClusterMetadata


def compute_global(
    client_errors: dict[str, np.ndarray],
    n_min: int,
    q: float,
    run: PolicyRunId,
) -> ThresholdResult:
    """Compute a single global threshold shared by all eligible clients."""
    eligible, pending = identify_eligible(client_errors, n_min=n_min)
    client_taus = compute_client_thresholds(client_errors, eligible, q=q)
    tau_global = compute_tau_global(client_taus)
    eligible_map = dict.fromkeys(eligible, tau_global)

    return build_threshold_result(
        run=run,
        tau_global=tau_global,
        eligible_thresholds=eligible_map,
        pending_clients=pending,
        cluster_metadata=None,
    )


def compute_local(
    client_errors: dict[str, np.ndarray],
    n_min: int,
    tau_global: float,
    q: float,
    run: PolicyRunId,
) -> ThresholdResult:
    """Compute per-client local thresholds without clustering."""
    eligible, pending = identify_eligible(client_errors, n_min=n_min)
    client_taus = compute_client_thresholds(client_errors, eligible, q=q)

    return build_threshold_result(
        run=run,
        tau_global=tau_global,
        eligible_thresholds=client_taus,
        pending_clients=pending,
        cluster_metadata=None,
    )


def compute_fingerprints(
    client_errors: dict[str, np.ndarray],
    eligible: list[str],
    *,
    q: float,
) -> dict[str, np.ndarray]:
    """Compute four-feature statistical fingerprints per eligible client."""
    fingerprints: dict[str, np.ndarray] = {}
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


def _validate_fingerprint_matrix(fingerprint_matrix: np.ndarray) -> None:
    if not np.isfinite(fingerprint_matrix).all():
        raise ValueError(
            f"[{_MODULE}] Invalid fingerprint values. Expected: finite mean/std/skew/p95. Got: NaN or inf."
        )
    unique_rows = np.unique(fingerprint_matrix, axis=0)
    if unique_rows.shape[0] < 2:
        raise ValueError(
            f"[{_MODULE}] Degenerate fingerprints: all eligible clients have identical fingerprints. Expected: at least 2 distinct eligible fingerprints. Got: {str(unique_rows.shape[0])}."
        )


def scaled_fingerprints(
    client_errors: dict[str, np.ndarray],
    eligible_ids: list[str],
    *,
    q: float,
) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """Compute and standard-scale fingerprint vectors for eligible clients."""
    fingerprints = compute_fingerprints(client_errors, eligible_ids, q=q)
    fingerprint_matrix = np.array([fingerprints[cid] for cid in eligible_ids])
    _validate_fingerprint_matrix(fingerprint_matrix)
    fingerprint_scaled = StandardScaler().fit_transform(fingerprint_matrix)
    if not np.isfinite(fingerprint_scaled).all():
        raise ValueError(
            f"[{_MODULE}] Invalid scaled fingerprints. Expected: finite values after scaling. Got: NaN or inf."
        )
    return fingerprints, fingerprint_scaled


def validate_k_candidates(k_candidates: list[int]) -> list[int]:
    """Validate and deduplicate cluster-count candidates, requiring integers >= 2."""
    if not k_candidates:
        raise ValueError(
            f"[{_MODULE}] k_candidates is empty. Expected: at least one integer k. Got: empty list."
        )
    invalid = [k for k in k_candidates if k < 2]
    if invalid:
        raise ValueError(
            f"[{_MODULE}] Invalid k_candidates. Expected: integers >= 2. Got: {str(invalid)}."
        )
    return sorted(set(k_candidates))


def silhouette_scores_by_k(
    x_scaled: np.ndarray,
    k_candidates: list[int],
    random_state: int,
    n_init: int,
    max_iter: int,
) -> dict[int, float]:
    """Compute silhouette scores for each candidate k on scaled fingerprints."""
    scores: dict[int, float] = {}
    for k in k_candidates:
        if k >= x_scaled.shape[0]:
            continue
        kmeans = KMeans(
            n_clusters=k,
            init="k-means++",
            random_state=random_state,
            n_init=int(n_init),  # type: ignore[arg-type]
            max_iter=int(max_iter),
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
    cluster_k: int,
    eligible_count: int,
    silhouette_scores: dict[int, float],
) -> tuple[int, float]:
    """Validate the locked cluster k and retrieve its precomputed silhouette score."""
    if cluster_k <= 0:
        raise ValueError(
            f"[{_MODULE}] Invalid cluster k. Expected: locked fixed K > 0. Got: {str(cluster_k)}."
        )
    if cluster_k >= eligible_count:
        raise ValueError(
            f"[{_MODULE}] Invalid cluster k. Expected: 2 <= k < eligible_count ({eligible_count}). Got: {str(cluster_k)}."
        )
    silhouette = silhouette_scores.get(cluster_k)
    if silhouette is None:
        raise ValueError(
            f"[{_MODULE}] Cluster k has no valid silhouette score. Expected: non-degenerate clustering. Got: {str(cluster_k)}."
        )
    return cluster_k, silhouette


def fit_cluster_labels(
    fingerprint_scaled: np.ndarray,
    *,
    k: int,
    random_state: int,
    n_init: int,
    max_iter: int,
) -> np.ndarray:
    """Run KMeans on scaled fingerprints and return cluster labels."""
    kmeans = KMeans(
        n_clusters=k,
        init="k-means++",
        random_state=random_state,
        n_init=int(n_init),  # type: ignore[arg-type]
        max_iter=int(max_iter),
    )
    return kmeans.fit_predict(fingerprint_scaled)


def final_silhouette(
    fingerprint_scaled: np.ndarray,
    labels: np.ndarray,
    *,
    random_state: int,
) -> float:
    """Compute the silhouette score for the final clustering assignment."""
    if len(set(labels)) <= 1:
        return 0.0
    return float(
        silhouette_score(fingerprint_scaled, labels, random_state=random_state)
    )


def cluster_assignments(
    *,
    eligible_ids: list[str],
    labels: np.ndarray,
    client_taus: dict[str, float],
) -> ClusterAssignments:
    """Build cluster-to-client and cluster-to-tau mappings from KMeans labels."""
    client_cluster = dict(zip(eligible_ids, labels.astype(int), strict=True))
    cluster_taus_map: dict[int, list[float]] = defaultdict(list)
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
    k: int,
    cluster_taus_map: dict[int, list[float]],
    silhouette: float,
) -> None:
    logger.info(
        "CLUSTER clustering complete",
        k=k,
        cluster_sizes=[len(cluster_taus_map[c]) for c in sorted(cluster_taus_map)],
        silhouette=silhouette,
    )


def cluster_info(
    *,
    eligible_ids: list[str],
    client_cluster: dict[str, int],
    tau_per_cluster: dict[int, float],
) -> dict[str, ClusterInfo]:
    """Build per-cluster metadata dicts keyed by cluster identifier string."""
    return {
        f"cluster_{cluster}": ClusterInfo(
            cluster_id=f"cluster_{cluster}",
            tau_cluster=tau_per_cluster[cluster],
            members=tuple(
                cid for cid in eligible_ids if client_cluster[cid] == cluster
            ),
        )
        for cluster in sorted(tau_per_cluster)
    }


def build_cluster_metadata(metadata_input: ClusterMetadataInput) -> ClusterMetadata:
    """Assemble a ClusterMetadata object from fingerprint, silhouette, and assignment inputs."""
    info = cluster_info(
        eligible_ids=metadata_input.eligible_ids,
        client_cluster=metadata_input.client_cluster,
        tau_per_cluster=metadata_input.tau_per_cluster,
    )
    return ClusterMetadata(
        k=metadata_input.k,
        cluster_info=ClusterInfoTuple(info.values()),
        silhouette=metadata_input.silhouette,
        silhouette_scores=ClientSilhouetteScoreTuple(
            ClientSilhouetteScore(client_id=str(k), score=v)
            for k, v in metadata_input.silhouette_scores.items()
        ),
        fingerprints=ClientFingerprintTuple(
            ClientFingerprint(
                client_id=cid,
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
        request.eligible,
        q=request.q,
    )
    eligible_ids = sorted(request.eligible)
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
        eligible_count=len(request.eligible),
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
    client_errors: dict[str, np.ndarray],
    n_min: int,
    tau_global: float,
    q: float,
    random_state: int,
    cluster_k: int,
    n_init: int,
    max_iter: int,
    run: PolicyRunId,
) -> ThresholdResult:
    """Compute per-cluster thresholds via KMeans on four-feature client fingerprints."""
    if cluster_k <= 0:
        raise ValueError(
            f"[{_MODULE}] Invalid cluster k. Expected: locked fixed K > 0. Got: {str(cluster_k)}."
        )
    eligible, pending = identify_eligible(client_errors, n_min=n_min)

    if len(eligible) < _MIN_CLUSTER_ELIGIBLE:
        raise ValueError(
            f"[{_MODULE}] Cannot cluster. Expected: at least {_MIN_CLUSTER_ELIGIBLE} eligible clients. Got: {str(len(eligible))}."
        )

    result = _compute_cluster_thresholds(
        _ClusterComputationRequest(
            client_errors=client_errors,
            eligible=eligible,
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
        pending_clients=pending,
        cluster_metadata=result.metadata,
    )
