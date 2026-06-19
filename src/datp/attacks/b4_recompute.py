"""B4 threshold recomputation and client-indexed Δτ decomposition.

Protocol (scientific protocol §5):

1. Clean B4 run → τ_i^{eff,clean}, clean cluster assignments A_clean.
2. Agg component: hold A_clean fixed; recompute per-client τ_i from poisoned cal;
   re-average within frozen clusters → τ_i^{eff,agg}.
   Δτ_i^agg = τ_i^{eff,agg} − τ_i^{eff,clean}.
3. Full poisoned B4 run → τ_i^{eff,pois} (refit scaler, re-run k-means).
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
    B4_K,
    B4_MAX_ITER,
    B4_N_INIT,
    N_MIN,
)
from datp.attacks.constants import B4_RANDOM_STATE
from datp.attacks.score_containers import ScoreCollection
from datp.attacks.types import PoisonedCalibrationSet, ThresholdPairBase
from datp.core.enums import Baseline, Regime
from datp.core.identity import BaselineRunId, TrainingCellId
from datp.attacks.enums import ThresholdPolicy
from datp.core.types import B4Metadata
from datp.thresholding.eligibility import (
    CalibrationErrorSet,
    ClientThresholdsCollection,
    EligibilityResult,
    compute_client_thresholds,
    compute_tau_global,
)
from datp.thresholding.strategies.b4_cluster import compute as b4_compute


@dataclass(frozen=True, slots=True)
class B4DecompEntry:
    """Per-client B4 decomposition for one poisoned condition."""

    client_id: str
    tau_clean: float
    tau_agg: float
    tau_pois: float
    delta_tau_agg: float
    delta_tau_churn: float
    delta_tau_total: float


class B4Decomposition(tuple[B4DecompEntry, ...]):
    def __new__(cls, entries: Any) -> "B4Decomposition":
        return super().__new__(cls, entries)

    @overload
    def __getitem__(self, key: str) -> B4DecompEntry: ...

    @overload
    def __getitem__(self, key: SupportsIndex) -> B4DecompEntry: ...

    @overload
    def __getitem__(self, key: slice) -> tuple[B4DecompEntry, ...]: ...

    def __getitem__(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, key: str | SupportsIndex | slice
    ) -> B4DecompEntry | tuple[B4DecompEntry, ...]:
        if isinstance(key, str):
            for entry in self:
                if entry.client_id == key:
                    return entry
            raise KeyError(key)
        return super().__getitem__(key)

    def keys(self) -> Iterator[str]:
        return (entry.client_id for entry in self)

    def values(self) -> Iterator[B4DecompEntry]:
        return iter(self)

    def items(self) -> Iterator[tuple[str, B4DecompEntry]]:
        for entry in self:
            yield entry.client_id, entry


@dataclass(frozen=True, slots=True)
class B4ThresholdPair(ThresholdPairBase):
    """B4 threshold pair with client-indexed Δτ decomposition."""

    decomposition: B4Decomposition


def _run_b4(
    cal_dict: dict[str, np.ndarray],
    q: float,
    tau_global: float,
    n_min: int,
    seed: int,
    k: int,
    n_init: int,
    max_iter: int,
    random_state: int,
) -> tuple[dict[str, float], B4Metadata]:
    """Run B4 and return (eligible_client -> effective_threshold, metadata).

    All hyperparameters are injected; never uses silhouette K selection.
    """
    cell = TrainingCellId(regime=Regime.A, seed=seed, alpha=None)
    run = BaselineRunId(cell=cell, baseline=Baseline.B4)

    # k_candidates=[k] so B4 never silently deviates to a different K.
    result = b4_compute(
        cal_dict,
        n_min=n_min,
        tau_global=tau_global,
        q=q,
        random_state=random_state,
        k_regime_a=k,
        k_candidates=[k],
        n_init=n_init,
        max_iter=max_iter,
        run=run,
        regime=Regime.A,
    )

    # Extract eligible-only effective thresholds (pending get tau_global elsewhere).
    eff = {
        ct.client_id: ct.threshold
        for ct in result.client_thresholds
        if not ct.calibration_pending
    }
    assert result.metadata.b4 is not None, "B4 metadata must be set after B4 run"
    return eff, result.metadata.b4


def _client_to_cluster_key(metadata: B4Metadata) -> dict[str, str]:
    """Build client_id → cluster_key mapping from B4Metadata.cluster_info."""
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


def compute_b4_pair(
    collection: ScoreCollection,
    poisoned_cal_set: PoisonedCalibrationSet | dict[str, np.ndarray],
    q: float,
    *,
    k: int = B4_K,
    n_init: int = B4_N_INIT,
    max_iter: int = B4_MAX_ITER,
    random_state: int = B4_RANDOM_STATE,
    n_min: int = N_MIN,
    seed: int = 0,
) -> B4ThresholdPair:
    """Compute B4 threshold pair and client-indexed Δτ decomposition.

    poisoned_cal must contain entries for all eligible clients. Pending clients
    are supplied their clean cal for the B4 run (they never enter clustering).
    """
    if not isinstance(poisoned_cal_set, PoisonedCalibrationSet):
        poisoned_cal_set = PoisonedCalibrationSet.from_mapping(poisoned_cal_set)
    eligible_ids = list(collection.eligible_ids)
    eligibility = EligibilityResult(eligible_ids=tuple(eligible_ids), pending_ids=())

    # Build full cal dicts: eligible → from arg; pending → always clean.
    clean_full_cal = collection.cal_dict()
    pois_full_cal: dict[str, np.ndarray] = {}
    for cid in collection.all_ids:
        if cid in collection.eligible_ids:
            pois_full_cal[cid] = poisoned_cal_set.for_client(cid).cal
        else:
            pois_full_cal[cid] = collection.for_client(cid).cal

    # Clean B4 run.
    clean_per_client_taus = compute_client_thresholds(
        CalibrationErrorSet.from_mapping({cid: clean_full_cal[cid] for cid in eligible_ids}),
        eligibility,
        q=q,
    )
    tau_global_clean = compute_tau_global(clean_per_client_taus)
    eff_clean, clean_meta = _run_b4(
        clean_full_cal,
        q,
        tau_global_clean,
        n_min,
        seed,
        k,
        n_init,
        max_iter,
        random_state,
    )

    # Poisoned per-client taus (no re-clustering yet).
    pois_per_client_taus = compute_client_thresholds(
        CalibrationErrorSet.from_mapping({cid: pois_full_cal[cid] for cid in eligible_ids}),
        eligibility,
        q=q,
    )
    tau_global_pois = compute_tau_global(pois_per_client_taus)

    # Agg component: frozen clean assignments + poisoned per-client taus.
    client_to_clean_cluster = _client_to_cluster_key(clean_meta)
    tau_agg = _agg_thresholds(
        eligible_ids=eligible_ids,
        pois_per_client_taus=dict(pois_per_client_taus.items()),
        client_to_clean_cluster=client_to_clean_cluster,
    )

    # Full poisoned B4 run (refit scaler, re-run k-means).
    eff_pois, _ = _run_b4(
        pois_full_cal,
        q,
        tau_global_pois,
        n_min,
        seed,
        k,
        n_init,
        max_iter,
        random_state,
    )

    # Decomposition.
    decomposition = []
    for cid in eligible_ids:
        tc = eff_clean[cid]
        ta = tau_agg[cid]
        tp = eff_pois[cid]
        d_agg = ta - tc
        d_total = tp - tc
        d_churn = d_total - d_agg
        decomposition.append(B4DecompEntry(
            client_id=cid,
            tau_clean=tc,
            tau_agg=ta,
            tau_pois=tp,
            delta_tau_agg=d_agg,
            delta_tau_churn=d_churn,
            delta_tau_total=d_total,
        ))

    return B4ThresholdPair(
        policy=ThresholdPolicy.B4_CLUSTER,
        tau_global_clean=tau_global_clean,
        tau_global_pois=tau_global_pois,
        thresholds_clean=ClientThresholdsCollection.from_mapping(eff_clean, Baseline.B4),
        thresholds_pois=ClientThresholdsCollection.from_mapping(eff_pois, Baseline.B4),
        decomposition=B4Decomposition(decomposition),
    )
