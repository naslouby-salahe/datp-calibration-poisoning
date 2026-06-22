"""CLUSTER_THRESHOLD policy orchestration."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from datp.core.errors import fmt
from datp.core.identity import PolicyRunId
from datp.core.types import (
    ClusterMetadata,
    ThresholdResult,
)
from datp.thresholding.eligibility import (
    build_threshold_result,
    compute_client_thresholds,
    identify_eligible,
)
from datp.thresholding.policies.cluster_metadata import (
    ClusterMetadataInput,
    build_cluster_metadata,
)
from datp.thresholding.policies.clustering import (
    cluster_assignments,
    final_silhouette,
    fit_cluster_labels,
    log_clustering,
    select_cluster_k,
    silhouette_scores_by_k,
    validate_k_candidates,
)
from datp.thresholding.policies.fingerprints import (
    compute_fingerprints,
    scaled_fingerprints,
)

__all__ = ["compute", "compute_fingerprints"]

_MODULE = "thresholding.cluster_threshold"
_MIN_CLUSTER_ELIGIBLE = 2

@dataclass(frozen=True, slots=True)
class _ClusterComputationRequest:
    client_errors: dict[str, np.ndarray]
    eligible: list[str]
    q: float
    random_state: int
    cluster_k: int
    k_candidates: list[int]
    n_init: int
    max_iter: int


@dataclass(frozen=True, slots=True)
class _ClusterComputationResult:
    eligible_map: dict[str, float]
    metadata: ClusterMetadata


def _build_cluster_threshold_result(
    *,
    run: PolicyRunId,
    tau_global: float,
    eligible_map: dict[str, float],
    pending: list[str],
    metadata: ClusterMetadata,
) -> ThresholdResult:
    return build_threshold_result(
        run=run,
        tau_global=tau_global,
        eligible_thresholds=eligible_map,
        pending_clients=pending,
        cluster_metadata=metadata,
    )


def _compute_cluster_thresholds(
    request: _ClusterComputationRequest,
) -> _ClusterComputationResult:
    valid_k_candidates = validate_k_candidates(request.k_candidates)
    client_taus = compute_client_thresholds(
        request.client_errors, request.eligible, q=request.q
    )
    eligible_ids = sorted(request.eligible)
    fingerprints, fingerprint_scaled = scaled_fingerprints(
        request.client_errors,
        eligible_ids,
        q=request.q,
    )
    silhouette_scores = silhouette_scores_by_k(
        fingerprint_scaled,
        k_candidates=valid_k_candidates,
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
    log_clustering(
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


def compute(
    client_errors: dict[str, np.ndarray],
    n_min: int,
    tau_global: float,
    q: float,
    random_state: int,
    cluster_k: int,
    k_candidates: list[int],
    n_init: int,
    max_iter: int,
    run: PolicyRunId,
) -> ThresholdResult:
    # cluster_k > 0: fixed K; cluster_k == 0: silhouette-based K selection.
    # Calibration-Pending clients receive tau_global unconditionally.
    eligible, pending = identify_eligible(client_errors, n_min=n_min)

    if len(eligible) < _MIN_CLUSTER_ELIGIBLE:
        raise ValueError(
            fmt(
                _MODULE,
                "Cannot cluster",
                f"at least {_MIN_CLUSTER_ELIGIBLE} eligible clients",
                str(len(eligible)),
            )
        )

    result = _compute_cluster_thresholds(
        _ClusterComputationRequest(
            client_errors=client_errors,
            eligible=eligible,
            q=q,
            random_state=random_state,
            cluster_k=cluster_k,
            k_candidates=k_candidates,
            n_init=n_init,
            max_iter=max_iter,
        )
    )

    return _build_cluster_threshold_result(
        run=run,
        tau_global=tau_global,
        eligible_map=result.eligible_map,
        pending=pending,
        metadata=result.metadata,
    )
