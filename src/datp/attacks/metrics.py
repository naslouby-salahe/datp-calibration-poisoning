from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TypeVar

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from datp.attacks.injection import (
    AurocRecord,
    AurocSet,
    ClientScores,
    MetricEngineInput,
    PoisonedCalibrationSet,
    ScoreCollection,
    ThresholdPairBase,
)
from datp.config import (
    CLUSTER_K_NBAIOT,
    CLUSTER_MAX_ITER,
    CLUSTER_N_INIT,
    CLUSTER_RANDOM_STATE,
    EPS_NUM,
    IQR_FLOOR_FACTOR,
    MATERIALITY_FACTOR,
    MU_FLAG_DIVISOR,
    N_MIN,
    ExperimentStage,
)
from datp.core import (
    ClientThreshold,
    ClusterMetadata,
    PolicyRunId,
    ThresholdResult,
    TrainingCellId,
)
from datp.enums import AttackerObjective, ClientStatus, ThresholdPolicy
from datp.evaluation import (
    BinaryMetrics,
    compute_binary_ranking_metrics,
    recompute_binary_metrics,
)
from datp.statistics import compute_fpr_fleet_stats, iqr
from datp.thresholding import (
    CalibrationErrorSet,
    ClientCalibrationErrors,
    ClientThresholdsCollection,
    EligibilityResult,
    compute_client_thresholds,
    compute_cluster,
    compute_fingerprints,
    compute_tau_global,
)
from datp.types import (
    ClassificationScore,
    ClientId,
    ClusterCount,
    ClusterId,
    ClusterIndex,
    FalsePositiveRate,
    FeatureMatrix,
    IterationCount,
    NarrativeText,
    PoisonFraction,
    Quantile,
    RandomSeed,
    Ratio,
    SampleCount,
    ScoreValue,
    ScoreVector,
    SignedCount,
    SignedDelta,
    Threshold,
    TruePositiveRate,
)


def compute_auroc_records(collection: ScoreCollection) -> AurocSet:
    records: list[AurocRecord] = []
    for cid in collection.eligible_ids:
        c = collection.clients[cid]
        records.append(
            AurocRecord(
                client_id=cid,
                auroc=compute_binary_ranking_metrics(
                    c.test_benign, c.test_attack
                ).auroc,
            )
        )
    return AurocSet.from_records(records)


def compute_mu_flag_threshold(mean_clean_fpr: FalsePositiveRate) -> Threshold:
    """``mu_flag_threshold = mean_clean_fpr / MU_FLAG_DIVISOR``.

    The locked protocol formula divides by MU_FLAG_DIVISOR exactly. No
    significant-figure rounding is applied: any rounding would silently
    alter the locked CV(FPR) instability gate and could flip a stability
    flag near the boundary.
    """
    return mean_clean_fpr / MU_FLAG_DIVISOR


@dataclass(frozen=True, slots=True)
class FleetFprMetrics:
    policy: ThresholdPolicy
    cv_fpr: FalsePositiveRate
    mean_fpr: FalsePositiveRate
    std_fpr: FalsePositiveRate
    iqr_fpr: FalsePositiveRate
    max_min_fpr_gap: FalsePositiveRate
    worst_client_fpr: FalsePositiveRate
    worst_client_id: ClientId | None
    coverage_ratio: Ratio
    n_eligible: SampleCount
    n_total: SampleCount
    mu_flag_triggered: bool


def compute_fleet_fpr(
    collection: ScoreCollection,
    pair: ThresholdPairBase,
    mu_flag_threshold: Threshold | None,
) -> FleetFprMetrics:
    eligible = list(collection.eligible_ids)

    client_fprs = [
        (cid, float(np.mean(tb > pair.thresholds_pois[cid])))
        for cid in eligible
        if (tb := collection.clients[cid].test_benign).size > 0
    ]

    n_valid = len(client_fprs)
    fpr_arr = np.array([f for _, f in client_fprs]) if n_valid else np.array([])
    stats = compute_fpr_fleet_stats(fpr_arr)
    worst_id: NarrativeText | None = (
        max(client_fprs, key=lambda x: x[1])[0] if client_fprs else None
    )

    return FleetFprMetrics(
        policy=pair.policy,
        cv_fpr=stats.cv,
        mean_fpr=stats.mean,
        std_fpr=stats.std,
        iqr_fpr=stats.iqr,
        max_min_fpr_gap=stats.max_min_gap,
        worst_client_fpr=stats.worst_value,
        worst_client_id=worst_id,
        coverage_ratio=collection.coverage_ratio,
        n_eligible=len(eligible),
        n_total=len(collection.clients),
        mu_flag_triggered=bool(
            n_valid and mu_flag_threshold is not None and stats.mean < mu_flag_threshold
        ),
    )


@dataclass(frozen=True, slots=True)
class DeltaTauEntry:
    client_id: ClientId
    policy: ThresholdPolicy
    tau_clean: Threshold
    tau_pois: Threshold
    delta_tau: SignedDelta
    delta_tau_rel: SignedDelta
    delta_tau_scale: SignedDelta
    scale_base: ScoreValue
    iqr_median: ScoreValue
    is_significant: bool


def per_client_scale_base(clean_cal: ScoreVector, iqr: ScoreValue) -> ScoreValue:
    if iqr > 0.0:
        return iqr

    mad = float(np.median(np.abs(clean_cal - np.median(clean_cal))))
    if mad > 0.0:
        return mad

    diffs = np.diff(np.unique(clean_cal))
    pos_diffs = diffs[diffs > 0.0]
    if pos_diffs.size > 0:
        return float(pos_diffs.min())

    return math.nan


def materiality_scale(
    scale_base: ScoreValue,
    iqr_median: ScoreValue,
    factor: ScoreValue,
    floor_factor: ScoreValue,
) -> ScoreValue:
    if math.isnan(scale_base):
        return math.nan
    return max(factor * scale_base, floor_factor * iqr_median)


def compute_delta_tau(
    collection: ScoreCollection,
    pair: ThresholdPairBase,
) -> dict[ClientId, DeltaTauEntry]:
    bases: dict[ClientId, ScoreValue] = {}
    iqrs: list[ScoreValue] = []

    for cid in collection.eligible_ids:
        clean_cal = collection.clients[cid].cal
        iqr_val = iqr(clean_cal)
        iqrs.append(iqr_val)
        bases[cid] = per_client_scale_base(clean_cal, iqr_val)

    iqr_median = float(np.median(iqrs)) if iqrs else 0.0
    result: dict[ClientId, DeltaTauEntry] = {}

    for cid in collection.eligible_ids:
        tc = pair.thresholds_clean[cid]
        tp = pair.thresholds_pois[cid]
        dt = tp - tc
        base = bases[cid]
        scale = materiality_scale(
            base, iqr_median, MATERIALITY_FACTOR, IQR_FLOOR_FACTOR
        )
        is_sig = not math.isnan(scale) and abs(dt) >= scale

        result[cid] = DeltaTauEntry(
            client_id=cid,
            policy=pair.policy,
            tau_clean=tc,
            tau_pois=tp,
            delta_tau=dt,
            delta_tau_rel=dt / max(abs(tc), EPS_NUM),
            delta_tau_scale=scale,
            scale_base=base,
            iqr_median=iqr_median,
            is_significant=is_sig,
        )

    return result


def cluster_sizes(assignments: Mapping[ClientId, ClusterId]) -> tuple[SignedCount, ...]:
    return tuple(sorted(Counter(assignments.values()).values(), reverse=True))


def cluster_size_of(
    assignments: Mapping[ClientId, ClusterId], client_id: ClientId
) -> SignedCount:
    own = assignments[client_id]
    return sum(1 for label in assignments.values() if label == own)


def _mates(
    assignments: Mapping[ClientId, ClusterId], client_id: ClientId
) -> frozenset[ClientId]:
    own = assignments[client_id]
    return frozenset(c for c, label in assignments.items() if label == own)


def n_reassigned(
    clean: Mapping[ClientId, ClusterId], poisoned: Mapping[ClientId, ClusterId]
) -> SampleCount:
    return sum(1 for cid in clean if _mates(clean, cid) != _mates(poisoned, cid))


@dataclass(frozen=True, slots=True)
class BlastRadiusRecord:
    policy: ThresholdPolicy
    victim_id: ClientId | None
    n_significant: SampleCount
    n_eligible: SampleCount
    blast_fraction: PoisonFraction


@dataclass(frozen=True, slots=True)
class SpilloverRecord:
    policy: ThresholdPolicy
    victim_id: ClientId
    spillover_client_ids: tuple[ClientId, ...]
    n_spillover: SampleCount
    n_non_victims: SampleCount


def compute_blast_radius(
    result: MetricResult, *, victim_id: ClientId | None = None
) -> BlastRadiusRecord:
    entries = result.delta_tau
    n_sig = sum(e.is_significant for cid, e in entries.items() if cid != victim_id)
    n_elig = len(entries) - (1 if victim_id in entries else 0)

    return BlastRadiusRecord(
        policy=result.policy,
        victim_id=victim_id,
        n_significant=n_sig,
        n_eligible=n_elig,
        blast_fraction=n_sig / n_elig if n_elig else 0.0,
    )


def compute_spillover(
    result: MetricResult,
    *,
    collection: ScoreCollection,
    victim_id: ClientId,
    objective: AttackerObjective,
) -> SpilloverRecord:
    entries = result.delta_tau
    non_victim_ids = tuple(cid for cid in entries if cid != victim_id)
    spill = tuple(
        sorted(
            cid
            for cid in non_victim_ids
            if _has_downstream_degradation(
                collection=collection,
                result=result,
                client_id=cid,
                objective=objective,
            )
        )
    )

    return SpilloverRecord(
        policy=result.policy,
        victim_id=victim_id,
        spillover_client_ids=spill,
        n_spillover=len(spill),
        n_non_victims=len(non_victim_ids),
    )


def _has_downstream_degradation(
    *,
    collection: ScoreCollection,
    result: MetricResult,
    client_id: ClientId,
    objective: AttackerObjective,
) -> bool:
    entry = result.delta_tau[client_id]
    client_scores = collection.clients[client_id]

    if objective == AttackerObjective.THRESHOLD_RAISE:
        metrics = compute_victim_downstream_metrics(
            clean_threshold=entry.tau_clean,
            poisoned_threshold=entry.tau_pois,
            client_scores=client_scores,
        )
        return (
            metrics.delta_tpr < 0.0
            or metrics.delta_ba < 0.0
            or metrics.delta_macro_f1 < 0.0
        )

    clean_fpr = _fpr(client_scores.test_benign, entry.tau_clean)
    poisoned_fpr = _fpr(client_scores.test_benign, entry.tau_pois)
    return poisoned_fpr > clean_fpr


def _fpr(test_benign: ScoreVector, threshold: Threshold) -> FalsePositiveRate:
    if test_benign.size == 0:
        return math.nan
    return float(np.mean(test_benign > threshold))


def duplicate_rate(values: ScoreVector) -> ScoreValue:
    return 1.0 - len(np.unique(values)) / values.size if values.size else math.nan


def tau_bound_utilization(
    *,
    clean_cal: ScoreVector,
    tau_clean: Threshold,
    tau_pois: Threshold,
    objective: AttackerObjective,
) -> Threshold:
    if objective == AttackerObjective.THRESHOLD_RAISE:
        reachable = float(clean_cal.max()) - tau_clean
        shift = tau_pois - tau_clean
    else:
        reachable = tau_clean - float(clean_cal.min())
        shift = tau_clean - tau_pois
    return shift / reachable if reachable > 0.0 else math.nan


@dataclass(frozen=True, slots=True)
class VictimDownstreamMetrics:
    tpr_clean: TruePositiveRate
    tpr_poisoned: TruePositiveRate
    delta_tpr: SignedDelta
    fpr_clean: FalsePositiveRate
    fpr_poisoned: FalsePositiveRate
    delta_fpr: SignedDelta
    ba_clean: ScoreValue
    ba_poisoned: ScoreValue
    delta_ba: SignedDelta
    macro_f1_clean: ClassificationScore
    macro_f1_poisoned: ClassificationScore
    delta_macro_f1: SignedDelta
    fp_clean: SignedCount
    fp_poisoned: SignedCount
    fn_clean: SignedCount
    fn_poisoned: SignedCount
    n_test_benign: SampleCount
    n_test_attack: SampleCount


@dataclass(frozen=True, slots=True)
class NonVictimDownstreamMetrics:
    n_clients: SampleCount
    mean_tpr_clean: TruePositiveRate
    mean_tpr_poisoned: TruePositiveRate
    mean_delta_tpr: SignedDelta
    worst_delta_tpr: SignedDelta
    mean_fpr_clean: FalsePositiveRate
    mean_fpr_poisoned: FalsePositiveRate
    mean_delta_fpr: SignedDelta
    worst_delta_fpr: SignedDelta
    mean_delta_ba: SignedDelta
    mean_delta_macro_f1: SignedDelta
    delta_fp_total: SignedCount
    delta_fn_total: SignedCount


def _counts(scores: ScoreVector, threshold: Threshold) -> SignedCount:
    return int(np.sum(scores > threshold))


def compute_victim_downstream_metrics(
    *,
    clean_threshold: Threshold,
    poisoned_threshold: Threshold,
    client_scores: ClientScores,
) -> VictimDownstreamMetrics:
    benign = client_scores.test_benign
    attack = client_scores.test_attack
    n_benign, n_attack = len(benign), len(attack)

    def _metrics_at(
        thresh: ScoreValue,
    ) -> tuple[BinaryMetrics, SignedCount, SignedCount]:
        tp = _counts(attack, thresh)
        fp = _counts(benign, thresh)
        return (
            recompute_binary_metrics(tp, fp, n_benign - fp, n_attack - tp),
            fp,
            n_attack - tp,
        )

    m_clean, fp_clean, fn_clean = _metrics_at(clean_threshold)
    m_pois, fp_pois, fn_pois = _metrics_at(poisoned_threshold)

    return VictimDownstreamMetrics(
        tpr_clean=m_clean.tpr,
        tpr_poisoned=m_pois.tpr,
        delta_tpr=m_pois.tpr - m_clean.tpr,
        fpr_clean=m_clean.fpr,
        fpr_poisoned=m_pois.fpr,
        delta_fpr=m_pois.fpr - m_clean.fpr,
        ba_clean=m_clean.balanced_accuracy,
        ba_poisoned=m_pois.balanced_accuracy,
        delta_ba=m_pois.balanced_accuracy - m_clean.balanced_accuracy,
        macro_f1_clean=m_clean.macro_f1,
        macro_f1_poisoned=m_pois.macro_f1,
        delta_macro_f1=m_pois.macro_f1 - m_clean.macro_f1,
        fp_clean=fp_clean,
        fp_poisoned=fp_pois,
        fn_clean=fn_clean,
        fn_poisoned=fn_pois,
        n_test_benign=n_benign,
        n_test_attack=n_attack,
    )


def _finite_mean(values: Iterable[ScoreValue]) -> ScoreValue:
    finite = [v for v in values if math.isfinite(v)]
    return float(np.mean(finite)) if finite else math.nan


def aggregate_non_victim_metrics(
    per_client: Mapping[ClientId, VictimDownstreamMetrics],
) -> NonVictimDownstreamMetrics:
    items = list(per_client.values())
    d_tpr = [m.delta_tpr for m in items if math.isfinite(m.delta_tpr)]
    d_fpr = [m.delta_fpr for m in items if math.isfinite(m.delta_fpr)]
    return NonVictimDownstreamMetrics(
        n_clients=len(items),
        mean_tpr_clean=_finite_mean(m.tpr_clean for m in items),
        mean_tpr_poisoned=_finite_mean(m.tpr_poisoned for m in items),
        mean_delta_tpr=_finite_mean(d_tpr),
        worst_delta_tpr=min(d_tpr) if d_tpr else math.nan,
        mean_fpr_clean=_finite_mean(m.fpr_clean for m in items),
        mean_fpr_poisoned=_finite_mean(m.fpr_poisoned for m in items),
        mean_delta_fpr=_finite_mean(d_fpr),
        worst_delta_fpr=max(d_fpr) if d_fpr else math.nan,
        mean_delta_ba=_finite_mean(m.delta_ba for m in items),
        mean_delta_macro_f1=_finite_mean(m.delta_macro_f1 for m in items),
        delta_fp_total=sum(m.fp_poisoned - m.fp_clean for m in items),
        delta_fn_total=sum(m.fn_poisoned - m.fn_clean for m in items),
    )


def compute_non_victim_downstream(
    *,
    thresholds: Mapping[ClientId, tuple[Threshold, Threshold]],
    scores_by_client: Mapping[ClientId, ClientScores],
    victim_id: ClientId,
) -> NonVictimDownstreamMetrics:
    return aggregate_non_victim_metrics(
        {
            cid: compute_victim_downstream_metrics(
                clean_threshold=clean,
                poisoned_threshold=pois,
                client_scores=scores_by_client[cid],
            )
            for cid, (clean, pois) in thresholds.items()
            if cid != victim_id
        }
    )


@dataclass(frozen=True, slots=True)
class MetricResult:
    policy: ThresholdPolicy
    delta_tau: dict[ClientId, DeltaTauEntry]
    fleet_fpr: FleetFprMetrics
    auroc_records: AurocSet
    mu_flag_threshold: Threshold | None


def compute_metrics(inputs: MetricEngineInput) -> MetricResult:
    return MetricResult(
        policy=inputs.pair.policy,
        delta_tau=compute_delta_tau(inputs.collection, inputs.pair),
        fleet_fpr=compute_fleet_fpr(
            inputs.collection, inputs.pair, inputs.mu_flag_threshold
        ),
        auroc_records=inputs.auroc_set or compute_auroc_records(inputs.collection),
        mu_flag_threshold=inputs.mu_flag_threshold,
    )


def get_threshold_data(
    collection: ScoreCollection,
    poisoned_cal: PoisonedCalibrationSet,
    q: Quantile,
) -> tuple[
    ClientThresholdsCollection, ClientThresholdsCollection, tuple[ClientId, ...]
]:
    eligible_ids = collection.eligible_ids
    eligibility = EligibilityResult(eligible_ids=eligible_ids, pending_ids=())

    taus_clean = compute_client_thresholds(
        collection.eligible_calibration_errors,
        eligibility,
        q=q,
    )
    taus_pois = compute_client_thresholds(
        CalibrationErrorSet(
            tuple(
                ClientCalibrationErrors(cid, poisoned_cal[cid].cal)
                for cid in eligible_ids
            )
        ),
        eligibility,
        q=q,
    )
    return taus_clean, taus_pois, eligible_ids


def build_uniform_collection(
    eligible_ids: tuple[ClientId, ...], tau: Threshold
) -> ClientThresholdsCollection:
    return ClientThresholdsCollection(
        entries=tuple(
            ClientThreshold(
                client_id=cid,
                threshold=tau,
                status=ClientStatus.ELIGIBLE,
                strategy=ThresholdPolicy.GLOBAL_THRESHOLD,
            )
            for cid in eligible_ids
        )
    )


def compute_global_pair(
    collection: ScoreCollection,
    poisoned_cal_set: PoisonedCalibrationSet,
    q: Quantile,
) -> ThresholdPairBase:
    taus_clean, taus_pois, eligible_ids = get_threshold_data(
        collection, poisoned_cal_set, q
    )

    tau_global_clean = compute_tau_global(taus_clean)
    tau_global_pois = compute_tau_global(taus_pois)

    return ThresholdPairBase(
        policy=ThresholdPolicy.GLOBAL_THRESHOLD,
        tau_global_clean=tau_global_clean,
        tau_global_pois=tau_global_pois,
        thresholds_clean=build_uniform_collection(eligible_ids, tau_global_clean),
        thresholds_pois=build_uniform_collection(eligible_ids, tau_global_pois),
    )


def compute_local_pair(
    collection: ScoreCollection,
    poisoned_cal_set: PoisonedCalibrationSet,
    q: Quantile,
    tau_global_clean: Threshold,
) -> ThresholdPairBase:
    taus_clean, taus_pois, _ = get_threshold_data(collection, poisoned_cal_set, q)

    return ThresholdPairBase(
        policy=ThresholdPolicy.LOCAL_THRESHOLD,
        tau_global_clean=tau_global_clean,
        tau_global_pois=compute_tau_global(taus_pois),
        thresholds_clean=taus_clean,
        thresholds_pois=taus_pois,
    )


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
    return {client_id: int(label) for client_id, label in zip(eligible_ids, labels)}


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
