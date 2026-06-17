"""B4 — Cluster-mean threshold: k-means on eligible [mean, std, skew, p95] fingerprints; Calibration-Pending clients never enter k-means and receive τ_global."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np
from scipy import stats as sp_stats
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from datp.core.enums import B4_FINGERPRINT_FEATURES, Regime
from datp.core.errors import fmt
from datp.core.identity import BaselineRunId
from datp.core.logging import get_logger
from datp.core.regime import enforce_regime
from datp.core.types import B4ClusterInfo, B4Metadata, ThresholdResult
from datp.thresholding.eligibility import (
    build_threshold_result,
    compute_client_thresholds,
    identify_eligible,
)
from datp.thresholding.thresholds import arithmetic_mean_threshold

logger = get_logger(__name__)

_MODULE = "thresholding.b4_cluster"
_MIN_CLUSTER_ELIGIBLE = 2

# Verify B4_FINGERPRINT_FEATURES matches the 4-element fingerprint order.
assert len(B4_FINGERPRINT_FEATURES) == 4, (
    f"B4_FINGERPRINT_FEATURES must have exactly 4 elements, got {len(B4_FINGERPRINT_FEATURES)}"
)


@dataclass(frozen=True, slots=True)
class _B4MetadataInput:
    k: int
    cluster_info: dict[str, B4ClusterInfo]
    silhouette: float
    silhouette_scores: dict[int, float]
    fingerprints: dict[str, np.ndarray]


@dataclass(frozen=True, slots=True)
class _B4ComputationRequest:
    client_errors: dict[str, np.ndarray]
    eligible: list[str]
    q: float
    regime: Regime
    random_state: int
    k_regime_a: int
    k_candidates: list[int]
    n_init: int
    max_iter: int


@dataclass(frozen=True, slots=True)
class _B4ComputationResult:
    eligible_map: dict[str, float]
    metadata: B4Metadata


def compute_fingerprints(
    client_errors: dict[str, np.ndarray],
    eligible: list[str],
    *,
    q: float,
) -> dict[str, np.ndarray]:
    # Calibration-Pending clients must not appear in eligible.
    # Constant/near-constant arrays produce skew=0.0 rather than NaN; single-element arrays also yield std=0.0.
    fingerprints: dict[str, np.ndarray] = {}
    for cid in eligible:
        e = np.asarray(client_errors[cid], dtype=np.float64)
        mean_e = float(np.mean(e))
        # ddof=1 is NaN for n==1; clamp to 0.0
        std_e = float(np.std(e, ddof=1)) if e.size >= 2 else 0.0
        # Constant data (std == 0) has skew = 0 by definition; skip scipy to
        # avoid the RuntimeWarning about catastrophic cancellation.
        raw_skew = float(sp_stats.skew(e)) if (e.size >= 2 and std_e > 0.0) else 0.0
        skew_e = 0.0 if (not np.isfinite(raw_skew)) else raw_skew
        p95_e = float(np.percentile(e, q * 100))
        fingerprints[cid] = np.array([mean_e, std_e, skew_e, p95_e], dtype=np.float64)
    return fingerprints


def _silhouette_scores_by_k(
    x_scaled: np.ndarray,
    k_candidates: list[int],
    random_state: int,
    n_init: int,
    max_iter: int,
) -> dict[int, float]:
    # _validate_k_candidates already guarantees every k >= 2.
    scores: dict[int, float] = {}
    for k in k_candidates:
        if k >= x_scaled.shape[0]:
            continue
        km = KMeans(
            n_clusters=k,
            random_state=random_state,
            n_init=int(n_init),  # type: ignore[arg-type]  # sklearn stubs restrict n_init to str; int is valid
            max_iter=int(max_iter),
        )
        labels = km.fit_predict(x_scaled)
        n_labels = len(set(labels))
        if n_labels < 2 or n_labels >= x_scaled.shape[0]:
            continue
        score = float(silhouette_score(x_scaled, labels, random_state=random_state))
        if not np.isfinite(score):
            continue
        logger.info("B4 silhouette", k=k, score=score)
        scores[k] = score
    return scores


def _select_best_k(scores: dict[int, float]) -> tuple[int, float]:
    if not scores:
        raise ValueError(
            fmt(
                _MODULE,
                "No valid silhouette scores",
                "at least one valid k in [2, K_elig - 1]",
                "none",
            )
        )
    best_k = max(scores, key=lambda k: scores[k])
    return best_k, scores[best_k]


def _validate_k_candidates(k_candidates: list[int]) -> list[int]:
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


def _validate_fingerprint_matrix(fingerprint_matrix: np.ndarray) -> None:
    if not np.isfinite(fingerprint_matrix).all():
        raise ValueError(
            fmt(
                _MODULE,
                "Invalid fingerprint values",
                "finite mean/std/skew/p95",
                "NaN or inf",
            )
        )
    unique_rows = np.unique(fingerprint_matrix, axis=0)
    if unique_rows.shape[0] < 2:
        raise ValueError(
            fmt(
                _MODULE,
                "Degenerate fingerprints — all eligible clients have identical fingerprints",
                "at least 2 distinct eligible fingerprints",
                str(unique_rows.shape[0]),
            )
        )


def _select_regime_a_k(
    *,
    k_regime_a: int,
    eligible_count: int,
    silhouette_scores: dict[int, float],
) -> tuple[int, float]:
    if k_regime_a <= 0:
        return _select_best_k(silhouette_scores)
    if k_regime_a >= eligible_count:
        raise ValueError(
            fmt(
                _MODULE,
                "Invalid Regime A k",
                f"2 <= k < eligible_count ({eligible_count})",
                str(k_regime_a),
            )
        )
    silhouette = silhouette_scores.get(k_regime_a)
    if silhouette is None:
        raise ValueError(
            fmt(
                _MODULE,
                "Regime A k has no valid silhouette score",
                "non-degenerate clustering",
                str(k_regime_a),
            )
        )
    return k_regime_a, silhouette


def _select_b4_k(
    *,
    regime: Regime,
    k_regime_a: int,
    eligible_count: int,
    silhouette_scores: dict[int, float],
) -> tuple[int, float]:
    # @enforce_regime on compute() guarantees regime ∈ {A, B, C}.
    if regime == Regime.A:
        return _select_regime_a_k(
            k_regime_a=k_regime_a,
            eligible_count=eligible_count,
            silhouette_scores=silhouette_scores,
        )
    # Regime B or C: silhouette-based K selection.
    k, silhouette = _select_best_k(silhouette_scores)
    logger.info("B4 selected K", k=k, silhouette=silhouette, regime=regime)
    return k, silhouette


def _scaled_fingerprints(
    client_errors: dict[str, np.ndarray],
    eligible_ids: list[str],
    *,
    q: float,
) -> tuple[dict[str, np.ndarray], np.ndarray]:
    fingerprints = compute_fingerprints(client_errors, eligible_ids, q=q)
    fingerprint_matrix = np.array([fingerprints[cid] for cid in eligible_ids])
    _validate_fingerprint_matrix(fingerprint_matrix)
    fingerprint_scaled = StandardScaler().fit_transform(fingerprint_matrix)
    if not np.isfinite(fingerprint_scaled).all():
        raise ValueError(
            fmt(
                _MODULE,
                "Invalid scaled fingerprints",
                "finite values after scaling",
                "NaN or inf",
            )
        )
    return fingerprints, fingerprint_scaled


def _fit_cluster_labels(
    fingerprint_scaled: np.ndarray,
    *,
    k: int,
    random_state: int,
    n_init: int,
    max_iter: int,
) -> np.ndarray:
    km = KMeans(
        n_clusters=k,
        random_state=random_state,
        n_init=int(n_init),  # type: ignore[arg-type]  # sklearn stubs restrict n_init to str; int is valid
        max_iter=int(max_iter),
    )
    return km.fit_predict(fingerprint_scaled)


def _final_silhouette(
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


def _cluster_thresholds(
    *,
    eligible_ids: list[str],
    labels: np.ndarray,
    client_taus: dict[str, float],
) -> tuple[dict[str, int], dict[int, list[float]], dict[int, float]]:
    client_cluster = dict(zip(eligible_ids, labels.astype(int), strict=True))
    cluster_taus_map: dict[int, list[float]] = defaultdict(list)
    for cid in eligible_ids:
        cluster_taus_map[client_cluster[cid]].append(client_taus[cid])
    tau_per_cluster = {
        cluster: arithmetic_mean_threshold(taus)
        for cluster, taus in cluster_taus_map.items()
    }
    return client_cluster, cluster_taus_map, tau_per_cluster


def _cluster_info(
    *,
    eligible_ids: list[str],
    client_cluster: dict[str, int],
    tau_per_cluster: dict[int, float],
) -> dict[str, B4ClusterInfo]:
    return {
        f"cluster_{cluster}": B4ClusterInfo(
            tau_cluster=tau_per_cluster[cluster],
            members=tuple(
                cid for cid in eligible_ids if client_cluster[cid] == cluster
            ),
        )
        for cluster in sorted(tau_per_cluster)
    }


def _log_clustering(
    *,
    k: int,
    cluster_taus_map: dict[int, list[float]],
    silhouette: float,
) -> None:
    logger.info(
        "B4 clustering complete",
        k=k,
        cluster_sizes=[len(cluster_taus_map[c]) for c in sorted(cluster_taus_map)],
        silhouette=silhouette,
    )


def _b4_metadata(
    metadata_input: _B4MetadataInput, *, eligible_ids: list[str]
) -> B4Metadata:
    return B4Metadata(
        k=metadata_input.k,
        cluster_info=metadata_input.cluster_info,
        silhouette=metadata_input.silhouette,
        silhouette_scores={
            str(k): v for k, v in metadata_input.silhouette_scores.items()
        },
        fingerprints={
            cid: tuple(metadata_input.fingerprints[cid].tolist())
            for cid in eligible_ids
        },
    )


def _build_b4_threshold_result(
    *,
    run: BaselineRunId,
    tau_global: float,
    eligible_map: dict[str, float],
    pending: list[str],
    metadata: B4Metadata,
) -> ThresholdResult:
    return build_threshold_result(
        run=run,
        tau_global=tau_global,
        eligible_thresholds=eligible_map,
        pending_clients=pending,
        b3_metadata=None,
        b4_metadata=metadata,
    )


def _compute_b4_thresholds(request: _B4ComputationRequest) -> _B4ComputationResult:
    valid_k_candidates = _validate_k_candidates(request.k_candidates)
    client_taus = compute_client_thresholds(
        request.client_errors, request.eligible, q=request.q
    )
    eligible_ids = sorted(request.eligible)
    fingerprints, fingerprint_scaled = _scaled_fingerprints(
        request.client_errors,
        eligible_ids,
        q=request.q,
    )
    silhouette_scores = _silhouette_scores_by_k(
        fingerprint_scaled,
        k_candidates=valid_k_candidates,
        random_state=request.random_state,
        n_init=request.n_init,
        max_iter=request.max_iter,
    )
    k, _ = _select_b4_k(
        regime=request.regime,
        k_regime_a=request.k_regime_a,
        eligible_count=len(request.eligible),
        silhouette_scores=silhouette_scores,
    )
    labels = _fit_cluster_labels(
        fingerprint_scaled,
        k=k,
        random_state=request.random_state,
        n_init=request.n_init,
        max_iter=request.max_iter,
    )
    final_silhouette = _final_silhouette(
        fingerprint_scaled,
        labels,
        random_state=request.random_state,
    )
    client_cluster, cluster_taus_map, tau_per_cluster = _cluster_thresholds(
        eligible_ids=eligible_ids,
        labels=labels,
        client_taus=client_taus,
    )
    _log_clustering(
        k=k,
        cluster_taus_map=cluster_taus_map,
        silhouette=final_silhouette,
    )
    return _B4ComputationResult(
        eligible_map={
            cid: tau_per_cluster[client_cluster[cid]] for cid in eligible_ids
        },
        metadata=_b4_metadata(
            _B4MetadataInput(
                k=k,
                cluster_info=_cluster_info(
                    eligible_ids=eligible_ids,
                    client_cluster=client_cluster,
                    tau_per_cluster=tau_per_cluster,
                ),
                silhouette=final_silhouette,
                silhouette_scores=silhouette_scores,
                fingerprints=fingerprints,
            ),
            eligible_ids=eligible_ids,
        ),
    )


@enforce_regime(Regime.A, Regime.B, Regime.C)
def compute(
    client_errors: dict[str, np.ndarray],
    n_min: int,
    tau_global: float,
    q: float,
    random_state: int,
    k_regime_a: int,
    k_candidates: list[int],
    n_init: int,
    max_iter: int,
    run: BaselineRunId,
    *,
    regime: Regime,  # noqa: ARG001 - consumed by @enforce_regime decorator
) -> ThresholdResult:
    # Regime A: K=k_regime_a fixed (or silhouette if k_regime_a=0);
    # Regime B/C: K selected by silhouette.
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

    result = _compute_b4_thresholds(
        _B4ComputationRequest(
            client_errors=client_errors,
            eligible=eligible,
            q=q,
            regime=regime,
            random_state=random_state,
            k_regime_a=k_regime_a,
            k_candidates=k_candidates,
            n_init=n_init,
            max_iter=max_iter,
        )
    )

    return _build_b4_threshold_result(
        run=run,
        tau_global=tau_global,
        eligible_map=result.eligible_map,
        pending=pending,
        metadata=result.metadata,
    )
