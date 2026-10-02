from __future__ import annotations

from datp.types import (
    ClassificationScore,
    ClientId,
    ClusterCount,
    ClusterId,
    ClusterIndex,
    FeatureMatrix,
    IterationCount,
    Quantile,
    RandomSeed,
    SampleCount,
    SignedDelta,
    Threshold,
)


from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TypeVar

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
from datp.core.enums import ClientStatus, ThresholdPolicy
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.core.types import (
    ClusterMetadata,
    ThresholdResult,
)
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

    k: ClusterCount = CLUSTER_K_NBAIOT
    n_init: IterationCount = CLUSTER_N_INIT
    max_iter: IterationCount = CLUSTER_MAX_ITER
    random_state: RandomSeed = CLUSTER_RANDOM_STATE
    n_min: SampleCount = N_MIN
    seed: RandomSeed = RandomSeed(0)


@dataclass(frozen=True, slots=True)
class ClusterDecompEntry:

    client_id: ClientId
    tau_clean: Threshold
    tau_agg: Threshold
    tau_pois: Threshold
    tau_frozen_scaler: Threshold
    delta_tau_agg: SignedDelta
    delta_tau_churn: SignedDelta
    delta_tau_total: SignedDelta
    delta_tau_frozen_scaler: SignedDelta
    delta_tau_normalization_gap: SignedDelta


@dataclass(frozen=True, slots=True)
class ClusterThresholdPair(ThresholdPairBase):

    decomposition: Mapping[ClientId, ClusterDecompEntry]
    fixed_assignment_thresholds: ClientThresholdsCollection
    clean_assignments: Mapping[ClientId, ClusterId]
    poisoned_assignments: Mapping[ClientId, ClusterId]
    silhouette_clean: ClassificationScore
    silhouette_poisoned: ClassificationScore


def compute_cluster_pair(
    collection: ScoreCollection,
    poisoned_cal_set: PoisonedCalibrationSet,
    q: Quantile,
    params: ClusterHyperparams = ClusterHyperparams(),
) -> ClusterThresholdPair:
    eligible_ids = list(collection.eligible_ids)
    eligibility = EligibilityResult(eligible_ids=tuple(eligible_ids), pending_ids=())

    clean_cal = {cid: collection.clients[cid].cal for cid in collection.all_ids}
    pois_cal = {
        cid: poisoned_cal_set[cid].cal
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
        cell=TrainingCellId(
            stage=ExperimentStage.NBAIOT_MAIN, seed=RandomSeed(params.seed)
        ),
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
    eff_clean = _resolved_thresholds(clean_res)
    eff_pois = _resolved_thresholds(pois_res)

    assert clean_res.cluster is not None, (
        "CLUSTER_THRESHOLD metadata must be set after compute_cluster run"
    )

    assert pois_res.cluster is not None
    client_to_clean_cluster = _cluster_assignments(clean_res.cluster)
    client_to_pois_cluster = _cluster_assignments(pois_res.cluster)

    clean_fp = compute_fingerprints(clean_cal, eligible_ids, q=q)
    pois_fp = compute_fingerprints(pois_cal, eligible_ids, q=q)
    clean_fp_mat = np.array([clean_fp[cid] for cid in eligible_ids], dtype=np.float64)
    pois_fp_mat = np.array([pois_fp[cid] for cid in eligible_ids], dtype=np.float64)

    frozen_scaler_assignments = _frozen_scaler_assignments(
        eligible_ids, clean_fp_mat, pois_fp_mat, params
    )
    tau_pois_map = dict(tau_pois_col.items())
    tau_agg_map = _aggregate_thresholds_by_assignment(
        client_to_clean_cluster, tau_pois_map
    )
    tau_fs_map = _aggregate_thresholds_by_assignment(
        frozen_scaler_assignments, tau_pois_map
    )
    decomposition = _build_decomposition(
        eligible_ids, eff_clean, tau_agg_map, eff_pois, tau_fs_map
    )

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
        fixed_assignment_thresholds=ClientThresholdsCollection.from_mapping(
            tau_agg_map, ThresholdPolicy.CLUSTER_THRESHOLD
        ),
        clean_assignments=MappingProxyType(client_to_clean_cluster),
        poisoned_assignments=MappingProxyType(client_to_pois_cluster),
        silhouette_clean=clean_res.cluster.silhouette,
        silhouette_poisoned=pois_res.cluster.silhouette,
    )




def _resolved_thresholds(result: ThresholdResult) -> dict[ClientId, Threshold]:
    return {
        item.client_id: item.threshold
        for item in result.client_thresholds
        if item.status is ClientStatus.ELIGIBLE
    }


def _cluster_assignments(metadata: ClusterMetadata) -> dict[ClientId, ClusterId]:
    return {
        client_id: cluster.cluster_id
        for cluster in metadata.cluster_info
        for client_id in cluster.members
    }


def _frozen_scaler_assignments(
    eligible_ids: list[ClientId],
    clean_fingerprints: FeatureMatrix,
    poisoned_fingerprints: FeatureMatrix,
    params: ClusterHyperparams,
) -> dict[ClientId, ClusterIndex]:
    labels = KMeans(
        n_clusters=params.k,
        n_init=params.n_init,
        max_iter=params.max_iter,
        random_state=params.random_state,
    ).fit_predict(
        StandardScaler().fit(clean_fingerprints).transform(poisoned_fingerprints)
    )
    return {
        client_id: int(label)
        for client_id, label in zip(eligible_ids, labels)
    }


_ClusterAssignment = TypeVar("_ClusterAssignment", ClusterId, ClusterIndex)


def _aggregate_thresholds_by_assignment(
    assignments: Mapping[ClientId, _ClusterAssignment],
    thresholds: Mapping[ClientId, Threshold],
) -> dict[ClientId, Threshold]:
    groups: dict[_ClusterAssignment, list[ClientId]] = {}
    for client_id, label in assignments.items():
        groups.setdefault(label, []).append(client_id)
    averages = {
        label: float(np.mean([thresholds[client_id] for client_id in members]))
        for label, members in groups.items()
    }
    return {client_id: averages[label] for client_id, label in assignments.items()}


def _build_decomposition(
    eligible_ids: list[ClientId],
    clean_thresholds: Mapping[ClientId, Threshold],
    aggregate_thresholds: Mapping[ClientId, Threshold],
    poisoned_thresholds: Mapping[ClientId, Threshold],
    frozen_scaler_thresholds: Mapping[ClientId, Threshold],
) -> dict[ClientId, ClusterDecompEntry]:
    entries: dict[ClientId, ClusterDecompEntry] = {}
    for client_id in eligible_ids:
        tau_clean = clean_thresholds[client_id]
        tau_agg = aggregate_thresholds[client_id]
        tau_pois = poisoned_thresholds[client_id]
        tau_frozen = frozen_scaler_thresholds[client_id]
        delta_agg = tau_agg - tau_clean
        delta_total = tau_pois - tau_clean
        delta_frozen = tau_frozen - tau_clean
        entries[client_id] = ClusterDecompEntry(
            client_id=client_id,
            tau_clean=tau_clean,
            tau_agg=tau_agg,
            tau_pois=tau_pois,
            tau_frozen_scaler=tau_frozen,
            delta_tau_agg=delta_agg,
            delta_tau_churn=delta_total - delta_agg,
            delta_tau_total=delta_total,
            delta_tau_frozen_scaler=delta_frozen,
            delta_tau_normalization_gap=delta_total - delta_frozen,
        )
    return entries
