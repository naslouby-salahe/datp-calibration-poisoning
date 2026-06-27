"""Cluster-threshold recomputation with decomposition into agg, churn, and frozen-scaler effects."""

from __future__ import annotations

from collections import UserDict
from dataclasses import dataclass

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from datp.attacks.constants import (
    CLUSTER_K_NBAIOT,
    CLUSTER_MAX_ITER,
    CLUSTER_N_INIT,
    CLUSTER_RANDOM_STATE,
    N_MIN,
)
from datp.attacks.score_containers import ScoreCollection
from datp.attacks.types import PoisonedCalibrationSet, ThresholdPairBase
from datp.config.models import ExperimentStage
from datp.core.enums import ThresholdPolicy
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.thresholding.eligibility import (
    CalibrationErrorSet,
    ClientThresholdsCollection,
    EligibilityResult,
    compute_client_thresholds,
    compute_tau_global,
)
from datp.thresholding.policies import compute_cluster, compute_fingerprints


@dataclass(frozen=True, slots=True)
class ClusterHyperparams:
    """KMeans hyperparameters for cluster-threshold computation."""

    k: int = CLUSTER_K_NBAIOT
    n_init: int = CLUSTER_N_INIT
    max_iter: int = CLUSTER_MAX_ITER
    random_state: int = CLUSTER_RANDOM_STATE
    n_min: int = N_MIN
    seed: int = 0


@dataclass(frozen=True, slots=True)
class ClusterDecompEntry:
    """Per-client decomposition of total delta-tau into agg, churn, frozen-scaler, and gap components."""

    client_id: str
    tau_clean: float
    tau_agg: float
    tau_pois: float
    tau_frozen_scaler: float
    delta_tau_agg: float
    delta_tau_churn: float
    delta_tau_total: float
    delta_tau_frozen_scaler: float
    delta_tau_normalization_gap: float


class ClusterDecomposition(UserDict):
    """Client-ID-keyed collection of ClusterDecompEntry records."""

    def __init__(self, entries: tuple[ClusterDecompEntry, ...]):
        """Initialize from a tuple of ClusterDecompEntry records."""
        super().__init__({e.client_id: e for e in entries})


@dataclass(frozen=True, slots=True)
class ClusterThresholdPair(ThresholdPairBase):
    """Threshold pair with cluster-decomposition metadata."""

    decomposition: ClusterDecomposition


def compute_cluster_pair(
    collection: ScoreCollection,
    poisoned_cal_set: PoisonedCalibrationSet | dict[str, np.ndarray],
    q: float,
    params: ClusterHyperparams = ClusterHyperparams(),
) -> ClusterThresholdPair:
    """Recompute cluster thresholds and decompose effects into agg, churn, and frozen-scaler components."""
    if not isinstance(poisoned_cal_set, PoisonedCalibrationSet):
        poisoned_cal_set = PoisonedCalibrationSet.from_mapping(poisoned_cal_set)

    eligible_ids = list(collection.eligible_ids)
    eligibility = EligibilityResult(eligible_ids=tuple(eligible_ids), pending_ids=())

    clean_cal = {cid: collection.for_client(cid).cal for cid in collection.all_ids}
    pois_cal = {
        cid: poisoned_cal_set.for_client(cid).cal
        if cid in collection.eligible_ids
        else clean_cal[cid]
        for cid in collection.all_ids
    }

    tau_clean_col = compute_client_thresholds(
        CalibrationErrorSet.from_mapping({cid: clean_cal[cid] for cid in eligible_ids}),
        eligibility,
        q=q,
    )
    tau_pois_col = compute_client_thresholds(
        CalibrationErrorSet.from_mapping({cid: pois_cal[cid] for cid in eligible_ids}),
        eligibility,
        q=q,
    )

    tau_global_clean = compute_tau_global(tau_clean_col)
    tau_global_pois = compute_tau_global(tau_pois_col)

    run_id = PolicyRunId(
        cell=TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=params.seed),
        policy=ThresholdPolicy.CLUSTER_THRESHOLD,
    )

    clean_res = compute_cluster(
        clean_cal,
        n_min=params.n_min,
        tau_global=tau_global_clean,
        q=q,
        random_state=params.random_state,
        cluster_k=params.k,
        n_init=params.n_init,
        max_iter=params.max_iter,
        run=run_id,
    )
    eff_clean = {
        ct.client_id: ct.threshold
        for ct in clean_res.client_thresholds
        if not ct.calibration_pending
    }

    pois_res = compute_cluster(
        pois_cal,
        n_min=params.n_min,
        tau_global=tau_global_pois,
        q=q,
        random_state=params.random_state,
        cluster_k=params.k,
        n_init=params.n_init,
        max_iter=params.max_iter,
        run=run_id,
    )
    eff_pois = {
        ct.client_id: ct.threshold
        for ct in pois_res.client_thresholds
        if not ct.calibration_pending
    }

    assert clean_res.metadata.cluster is not None, (
        "CLUSTER_THRESHOLD metadata must be set after compute_cluster run"
    )

    tau_pois_map = dict(tau_pois_col.items())
    client_to_clean_cluster = {
        member: info.cluster_id
        for info in clean_res.metadata.cluster.cluster_info
        for member in info.members
    }

    clean_fp = compute_fingerprints(clean_cal, eligible_ids, q=q)
    pois_fp = compute_fingerprints(pois_cal, eligible_ids, q=q)
    clean_fp_mat = np.array([clean_fp[cid] for cid in eligible_ids], dtype=np.float64)
    pois_fp_mat = np.array([pois_fp[cid] for cid in eligible_ids], dtype=np.float64)

    fs_labels: list[int] = (
        KMeans(
            n_clusters=params.k,
            n_init=params.n_init,  # type: ignore[arg-type]
            max_iter=params.max_iter,
            random_state=params.random_state,
        )
        .fit_predict(StandardScaler().fit(clean_fp_mat).transform(pois_fp_mat))
        .tolist()
    )

    # tau_agg: frozen clean-cluster assignments re-averaged over poisoned per-client quantile taus.
    cluster_groups: dict[str, list[str]] = {}
    for cid in eligible_ids:
        cluster_groups.setdefault(client_to_clean_cluster[cid], []).append(cid)
    tau_agg_per_cluster = {
        ck: float(np.mean([tau_pois_map[c] for c in cids]))
        for ck, cids in cluster_groups.items()
    }
    tau_agg_map = {
        cid: tau_agg_per_cluster[client_to_clean_cluster[cid]] for cid in eligible_ids
    }

    # tau_fs: frozen-scaler diagnostic — clean scaler on poisoned fingerprints, re-averaged.
    fs_groups: dict[int, list[str]] = {}
    for cid, lbl in zip(eligible_ids, fs_labels):
        fs_groups.setdefault(lbl, []).append(cid)
    tau_fs_per_label = {
        lbl: float(np.mean([tau_pois_map[c] for c in cids]))
        for lbl, cids in fs_groups.items()
    }
    tau_fs_map = {
        cid: tau_fs_per_label[lbl] for cid, lbl in zip(eligible_ids, fs_labels)
    }

    entries = []
    for cid in eligible_ids:
        tc = eff_clean[cid]
        ta = tau_agg_map[cid]
        tp = eff_pois[cid]
        tfs = tau_fs_map[cid]
        dta = ta - tc
        dtt = tp - tc
        dtfs = tfs - tc
        entries.append(
            ClusterDecompEntry(
                client_id=cid,
                tau_clean=tc,
                tau_agg=ta,
                tau_pois=tp,
                tau_frozen_scaler=tfs,
                delta_tau_agg=dta,
                delta_tau_churn=dtt - dta,
                delta_tau_total=dtt,
                delta_tau_frozen_scaler=dtfs,
                delta_tau_normalization_gap=dtt - dtfs,
            )
        )
    decomposition = ClusterDecomposition(tuple(entries))

    return ClusterThresholdPair(
        policy=ThresholdPolicy.CLUSTER_THRESHOLD,
        tau_global_clean=tau_global_clean,
        tau_global_pois=tau_global_pois,
        thresholds_clean=ClientThresholdsCollection.from_mapping(
            eff_clean, ThresholdPolicy.CLUSTER_THRESHOLD
        ),
        thresholds_pois=ClientThresholdsCollection.from_mapping(
            eff_pois, ThresholdPolicy.CLUSTER_THRESHOLD
        ),
        decomposition=decomposition,
    )
