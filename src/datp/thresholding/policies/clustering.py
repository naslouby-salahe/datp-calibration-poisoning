from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from datp.core.errors import fmt
from datp.core.logging import get_logger
from datp.thresholding.thresholds import arithmetic_mean_threshold

logger = get_logger(__name__)

_MODULE = "thresholding.cluster_threshold.clustering"


@dataclass(frozen=True, slots=True)
class ClusterAssignments:
    client_cluster: dict[str, int]
    cluster_taus_map: dict[int, list[float]]
    tau_per_cluster: dict[int, float]


def validate_k_candidates(k_candidates: list[int]) -> list[int]:
    if not k_candidates:
        raise ValueError(
            fmt(
                _MODULE, "k_candidates is empty", "at least one integer k", "empty list"
            )
        )
    invalid = [k for k in k_candidates if k < 2]
    if invalid:
        raise ValueError(
            fmt(_MODULE, "Invalid k_candidates", "integers >= 2", str(invalid))
        )
    return sorted(set(k_candidates))


def silhouette_scores_by_k(
    x_scaled: np.ndarray,
    k_candidates: list[int],
    random_state: int,
    n_init: int,
    max_iter: int,
) -> dict[int, float]:
    scores: dict[int, float] = {}
    for k in k_candidates:
        if k >= x_scaled.shape[0]:
            continue
        km = KMeans(
            n_clusters=k,
            init="k-means++",
            random_state=random_state,
            n_init=int(n_init),  # type: ignore[arg-type]
            max_iter=int(max_iter),
        )
        labels = km.fit_predict(x_scaled)
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
    if cluster_k <= 0:
        if not silhouette_scores:
            raise ValueError(
                fmt(
                    _MODULE,
                    "No valid silhouette scores",
                    "at least one valid k in [2, K_elig - 1]",
                    "none",
                )
            )
        best_k = max(silhouette_scores, key=lambda k: silhouette_scores[k])
        return best_k, silhouette_scores[best_k]
    if cluster_k >= eligible_count:
        raise ValueError(
            fmt(
                _MODULE,
                "Invalid cluster k",
                f"2 <= k < eligible_count ({eligible_count})",
                str(cluster_k),
            )
        )
    silhouette = silhouette_scores.get(cluster_k)
    if silhouette is None:
        raise ValueError(
            fmt(
                _MODULE,
                "Cluster k has no valid silhouette score",
                "non-degenerate clustering",
                str(cluster_k),
            )
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
    km = KMeans(
        n_clusters=k,
        init="k-means++",
        random_state=random_state,
        n_init=int(n_init),  # type: ignore[arg-type]
        max_iter=int(max_iter),
    )
    return km.fit_predict(fingerprint_scaled)


def final_silhouette(
    fingerprint_scaled: np.ndarray,
    labels: np.ndarray,
    *,
    random_state: int,
) -> float:
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


def log_clustering(
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
