"""Cluster-threshold recomputation and client-indexed Δτ decomposition.

Protocol (scientific protocol §5):

1. Clean cluster run → τ_i^{eff,clean}, clean cluster assignments A_clean.
2. Agg component: hold A_clean fixed; recompute per-client τ_i from poisoned cal;
   re-average within frozen clusters → τ_i^{eff,agg}.
   Δτ_i^agg = τ_i^{eff,agg} − τ_i^{eff,clean}.
3. Full poisoned cluster run → τ_i^{eff,pois} (refit scaler, re-run k-means).
   Δτ_i^total = τ_i^{eff,pois} − τ_i^{eff,clean}.
4. Churn = residual: Δτ_i^churn = Δτ_i^total − Δτ_i^agg.
   Identity Δτ_agg + Δτ_churn = Δτ_total holds exactly.

Raw k-means label IDs are never compared across runs.
All deltas are client-indexed (by client_id, not label).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, SupportsIndex, overload

import numpy as np

from datp.artifacts.poison_names import (
    CLUSTER_K_NBAIOT,
    CLUSTER_MAX_ITER,
    CLUSTER_N_INIT,
    N_MIN,
)
from datp.attacks.constants import CLUSTER_RANDOM_STATE
from datp.attacks.score_containers import ScoreCollection
from datp.attacks.types import PoisonedCalibrationSet, ThresholdPairBase
from datp.config.stages import ExperimentStage
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.attacks.enums import ThresholdPolicy
from datp.core.types import ClusterMetadata
from datp.thresholding.eligibility import (
    CalibrationErrorSet,
    ClientThresholdsCollection,
    EligibilityResult,
    compute_client_thresholds,
    compute_tau_global,
)
from datp.thresholding.strategies.cluster_threshold import compute as cluster_compute


@dataclass(frozen=True, slots=True)
class ClusterDecompEntry:
    """Per-client cluster-threshold decomposition for one poisoned condition."""

    client_id: str
    tau_clean: float
    tau_agg: float
    tau_pois: float
    delta_tau_agg: float
    delta_tau_churn: float
    delta_tau_total: float


class ClusterDecomposition(tuple[ClusterDecompEntry, ...]):
    def __new__(cls, entries: Any) -> "ClusterDecomposition":
        return super().__new__(cls, entries)

    @overload
    def __getitem__(self, key: str) -> ClusterDecompEntry: ...

    @overload
    def __getitem__(self, key: SupportsIndex) -> ClusterDecompEntry: ...

    @overload
    def __getitem__(self, key: slice) -> tuple[ClusterDecompEntry, ...]: ...

    def __getitem__(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, key: str | SupportsIndex | slice
    ) -> ClusterDecompEntry | tuple[ClusterDecompEntry, ...]:
        if isinstance(key, str):
            for entry in self:
                if entry.client_id == key:
                    return entry
            raise KeyError(key)
        return super().__getitem__(key)

    def keys(self) -> Iterator[str]:
        return (entry.client_id for entry in self)

    def values(self) -> Iterator[ClusterDecompEntry]:
        return iter(self)

    def items(self) -> Iterator[tuple[str, ClusterDecompEntry]]:
        for entry in self:
            yield entry.client_id, entry


@dataclass(frozen=True, slots=True)
class ClusterThresholdPair(ThresholdPairBase):
    """Cluster-threshold pair with client-indexed Δτ decomposition."""

    decomposition: ClusterDecomposition


def _run_cluster(
    cal_dict: dict[str, np.ndarray],
    q: float,
    tau_global: float,
    n_min: int,
    seed: int,
    k: int,
    n_init: int,
    max_iter: int,
    random_state: int,
) -> tuple[dict[str, float], ClusterMetadata]:
    """Run cluster-threshold and return (eligible_client -> effective_threshold, metadata).

    All hyperparameters are injected; never uses silhouette K selection.
    """
    cell = TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=seed)
    run = PolicyRunId(cell=cell, policy=ThresholdPolicy.CLUSTER_THRESHOLD)

    # k_candidates=[k] so CLUSTER_THRESHOLD never silently deviates to a different K.
    result = cluster_compute(
        cal_dict,
        n_min=n_min,
        tau_global=tau_global,
        q=q,
        random_state=random_state,
        cluster_k=k,
        k_candidates=[k],
        n_init=n_init,
        max_iter=max_iter,
        run=run,
    )

    # Extract eligible-only effective thresholds (pending get tau_global elsewhere).
    eff = {
        ct.client_id: ct.threshold
        for ct in result.client_thresholds
        if not ct.calibration_pending
    }
    assert result.metadata.cluster is not None, "CLUSTER_THRESHOLD metadata must be set after CLUSTER_THRESHOLD run"
    return eff, result.metadata.cluster


def _client_to_cluster_key(metadata: ClusterMetadata) -> dict[str, str]:
    """Build client_id → cluster_key mapping from ClusterMetadata.cluster_info."""
    mapping: dict[str, str] = {}
    for info in metadata.cluster_info:
        cluster_key = info.cluster_id
        for member in info.members:
            mapping[member] = cluster_key
    return mapping


def _agg_thresholds(
    *,
    eligible_ids: list[str],
    pois_per_client_taus: dict[str, float],
    client_to_clean_cluster: dict[str, str],
) -> dict[str, float]:
    """τ_i^{eff,agg}: frozen clean assignments + poisoned per-client taus re-averaged.

    For each cluster (using clean assignments), compute the mean of the poisoned
    per-client taus for all members. τ_i^{eff,agg} = that cluster's new mean.
    """
    cluster_pois_taus: dict[str, list[float]] = defaultdict(list)
    for cid in eligible_ids:
        cluster_key = client_to_clean_cluster[cid]
        cluster_pois_taus[cluster_key].append(pois_per_client_taus[cid])

    tau_agg_per_cluster: dict[str, float] = {
        ck: float(np.mean(taus)) for ck, taus in cluster_pois_taus.items()
    }
    return {
        cid: tau_agg_per_cluster[client_to_clean_cluster[cid]] for cid in eligible_ids
    }


def _build_cal_dicts(
    collection: ScoreCollection,
    poisoned_cal_set: PoisonedCalibrationSet,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Return (clean_full_cal, pois_full_cal) covering all client IDs.

    Eligible clients get their (clean, poisoned) cal from the arguments;
    pending clients always get their clean cal in both dicts.
    """
    clean: dict[str, np.ndarray] = {}
    pois: dict[str, np.ndarray] = {}
    for cid in collection.all_ids:
        if cid in collection.eligible_ids:
            clean[cid] = collection.for_client(cid).cal
            pois[cid] = poisoned_cal_set.for_client(cid).cal
        else:
            clean[cid] = collection.for_client(cid).cal
            pois[cid] = collection.for_client(cid).cal
    return clean, pois


def _build_cluster_decomposition(
    eligible_ids: list[str],
    eff_clean: dict[str, float],
    tau_agg: dict[str, float],
    eff_pois: dict[str, float],
) -> ClusterDecomposition:
    """Build the per-client cluster-threshold decomposition from the three threshold maps."""
    entries = []
    for cid in eligible_ids:
        tc = eff_clean[cid]
        ta = tau_agg[cid]
        tp = eff_pois[cid]
        entries.append(
            ClusterDecompEntry(
                client_id=cid,
                tau_clean=tc,
                tau_agg=ta,
                tau_pois=tp,
                delta_tau_agg=ta - tc,
                delta_tau_churn=(tp - tc) - (ta - tc),
                delta_tau_total=tp - tc,
            )
        )
    return ClusterDecomposition(entries)


def _eligible_taus_and_global(
    cal_dict: dict[str, np.ndarray],
    eligible_ids: list[str],
    q: float,
) -> tuple[ClientThresholdsCollection, float]:
    eligibility = EligibilityResult(eligible_ids=tuple(eligible_ids), pending_ids=())
    per_client_taus = compute_client_thresholds(
        CalibrationErrorSet.from_mapping({cid: cal_dict[cid] for cid in eligible_ids}),
        eligibility,
        q=q,
    )
    tau_global = compute_tau_global(per_client_taus)
    return per_client_taus, tau_global


def _cluster_run_with_hyperparams(
    cal_dict: dict[str, np.ndarray],
    q: float,
    tau_global: float,
    *,
    n_min: int,
    seed: int,
    k: int,
    n_init: int,
    max_iter: int,
    random_state: int,
) -> tuple[dict[str, float], ClusterMetadata]:
    return _run_cluster(
        cal_dict, q, tau_global, n_min, seed, k, n_init, max_iter, random_state
    )


def compute_cluster_pair(
    collection: ScoreCollection,
    poisoned_cal_set: PoisonedCalibrationSet | dict[str, np.ndarray],
    q: float,
    *,
    k: int = CLUSTER_K_NBAIOT,
    n_init: int = CLUSTER_N_INIT,
    max_iter: int = CLUSTER_MAX_ITER,
    random_state: int = CLUSTER_RANDOM_STATE,
    n_min: int = N_MIN,
    seed: int = 0,
) -> ClusterThresholdPair:
    """Compute cluster-threshold pair and client-indexed Δτ decomposition.

    poisoned_cal must contain entries for all eligible clients. Pending clients
    are supplied their clean cal for the cluster run (they never enter clustering).
    """
    if not isinstance(poisoned_cal_set, PoisonedCalibrationSet):
        poisoned_cal_set = PoisonedCalibrationSet.from_mapping(poisoned_cal_set)
    eligible_ids = list(collection.eligible_ids)

    clean_full_cal, pois_full_cal = _build_cal_dicts(collection, poisoned_cal_set)

    hyperparams = {
        "n_min": n_min,
        "seed": seed,
        "k": k,
        "n_init": n_init,
        "max_iter": max_iter,
        "random_state": random_state,
    }

    _, tau_global_clean = _eligible_taus_and_global(clean_full_cal, eligible_ids, q)
    eff_clean, clean_meta = _cluster_run_with_hyperparams(
        clean_full_cal, q, tau_global_clean, **hyperparams
    )

    pois_per_client_taus, tau_global_pois = _eligible_taus_and_global(
        pois_full_cal, eligible_ids, q
    )
    client_to_clean_cluster = _client_to_cluster_key(clean_meta)
    tau_agg = _agg_thresholds(
        eligible_ids=eligible_ids,
        pois_per_client_taus=dict(pois_per_client_taus.items()),
        client_to_clean_cluster=client_to_clean_cluster,
    )

    eff_pois, _ = _cluster_run_with_hyperparams(
        pois_full_cal, q, tau_global_pois, **hyperparams
    )

    decomposition = _build_cluster_decomposition(eligible_ids, eff_clean, tau_agg, eff_pois)

    return ClusterThresholdPair(
        policy=ThresholdPolicy.CLUSTER_THRESHOLD,
        tau_global_clean=tau_global_clean,
        tau_global_pois=tau_global_pois,
        thresholds_clean=ClientThresholdsCollection.from_mapping(
            eff_clean, ThresholdPolicy.CLUSTER_THRESHOLD
        ),
        thresholds_pois=ClientThresholdsCollection.from_mapping(eff_pois, ThresholdPolicy.CLUSTER_THRESHOLD),
        decomposition=decomposition,
    )
