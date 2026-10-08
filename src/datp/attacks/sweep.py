from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import polars as pl
import torch
from joblib import Parallel, delayed

from datp.artifacts import ArtifactLayout, nbaiot_main_manifest_path
from datp.attacks.injection import (
    AurocSet,
    ClientScores,
    InjectionResult,
    MetricEngineInput,
    PoisonedCalibrationSet,
    ReservoirResult,
    ScoreCollection,
    SweepCellSpec,
    ThresholdPairBase,
    assert_bounded_scale_requires_single_client,
    assert_fractions_in_locked_grid,
    assert_no_inplace_mutation,
    assert_reservoir_not_test_or_training,
    assert_valid_source_objective_pair,
    build_reservoir,
    build_score_collection,
    enumerate_bounded_sweep_matrix,
    inject_disjoint_reservoir,
    inject_fixed_budget,
)
from datp.attacks.feature_reservoir import inject_feature_reservoir, score_feature_rows
from datp.attacks.manifests import (
    ArtifactProvenance,
    BoundedSweepManifest,
    BoundedSweepResultRow,
    ProvenanceRecord,
)
from datp.attacks.metrics import (
    BlastRadiusRecord,
    ClusterThresholdPair,
    DeltaTauEntry,
    FleetFprMetrics,
    MetricResult,
    NonVictimDownstreamMetrics,
    SpilloverRecord,
    VictimDownstreamMetrics,
    cluster_size_of,
    cluster_sizes,
    compute_auroc_records,
    compute_blast_radius,
    compute_cluster_pair,
    compute_delta_tau,
    compute_fleet_fpr,
    compute_global_pair,
    compute_local_pair,
    compute_metrics,
    compute_mu_flag_threshold,
    compute_non_victim_downstream,
    compute_spillover,
    compute_victim_downstream_metrics,
    duplicate_rate,
    n_reassigned,
    tau_bound_utilization,
)
from datp.config import (
    FEATURE_TAIL_MASS,
    N_MIN,
    TAIL_MASS,
    THRESHOLD_QUANTILE,
    CalibrationPoisoningConfig,
    ExperimentStage,
    ModelConfig,
)
from datp.core import (
    REPOSITORY_NAME,
    SeedPair,
    SeedRecord,
    TrainingCellId,
    get_logger,
    hash_jsonable,
    make_seed_rng,
)
from datp.data import processed_root
from datp.enums import (
    WorkflowEvent,
    Workflow,
    CheckpointKey,
    AttackerObjective,
    DatasetID,
    FeatureDonorScope,
    ManifestProvenanceSource,
    PoisoningSourceStrategy,
    ReservoirDraw,
    ReservoirStatus,
    ScoringStage,
    ThresholdPolicy,
    is_train_feature_source,
    is_diagnostic_source,
)
from datp.modeling import Autoencoder
from datp.scoring import (
    hash_model_state,
    load_main_cal_errors,
    load_parquets_from_dir,
    validate_scoring_manifest,
)
from datp.types import (
    Ratio,
    ClientId,
    Index,
    ManifestMetricValue,
    PoisonFraction,
    RandomSeed,
    SampleCount,
    ScoreVector,
    SignedCount,
    Threshold,
)

_SOURCES_SORTED = tuple(sorted(PoisoningSourceStrategy))
_OBJECTIVES_SORTED = tuple(sorted(AttackerObjective))


def cell_child_index(
    source: PoisoningSourceStrategy,
    objective: AttackerObjective | None,
    fraction: PoisonFraction,
) -> Index:
    if objective is None:
        return 0
    return (
        (_SOURCES_SORTED.index(source) * len(_OBJECTIVES_SORTED) * 1000)
        + (_OBJECTIVES_SORTED.index(objective) * 1000)
        + round(fraction * 1000)
    )


@dataclass(frozen=True, slots=True)
class InjectionSpec:
    source: PoisoningSourceStrategy
    fraction: PoisonFraction
    seed_pair: SeedPair
    objective: AttackerObjective | None
    scope_idx: Index = 0
    tail_mass: PoisonFraction = TAIL_MASS
    draw: ReservoirDraw = ReservoirDraw.WITH_REPLACEMENT


@dataclass(frozen=True)
class InjectionOutcome:
    victim_id: ClientId
    poisoned_cal_set: PoisonedCalibrationSet
    reservoir: ReservoirResult
    injection: InjectionResult
    reservoir_draw: ReservoirDraw
    donor_feature_unique_fraction: Ratio | None


def _build_poisoned_clients(
    collection: ScoreCollection, victim_cal_map: dict[ClientId, ScoreVector]
) -> dict[ClientId, ScoreVector]:
    return {
        cid: victim_cal_map[cid]
        if cid in victim_cal_map
        else collection.clients[cid].cal.copy()
        for cid in collection.eligible_ids
    }


def inject_single_victim(
    collection: ScoreCollection,
    *,
    victim_id: ClientId,
    spec: InjectionSpec,
    feature_reservoir_scores: ScoreVector | None = None,
    feature_row_ids: np.ndarray | None = None,
    feature_tail_mass: PoisonFraction = FEATURE_TAIL_MASS,
) -> InjectionOutcome:
    v_clean = collection.clients[victim_id].cal
    clean_snapshot = v_clean.copy()

    assert_reservoir_not_test_or_training(ScoringStage.CAL)
    if is_diagnostic_source(spec.source):
        raise ValueError(
            f"Source {spec.source!r} is diagnostic-only and must not enter "
            "the bounded/full experiment matrix."
        )
    rng = make_seed_rng(
        SeedRecord(
            pair=spec.seed_pair,
            client_idx=collection.client_index(victim_id),
            scope_idx=spec.scope_idx,
        ),
        child_index=cell_child_index(spec.source, spec.objective, spec.fraction),
    )
    donor_feature_unique_fraction: Ratio | None = None
    reservoir_draw = spec.draw
    if is_train_feature_source(spec.source):
        if feature_reservoir_scores is None or feature_row_ids is None:
            raise ValueError(
                f"Source {spec.source!r} requires scores from the victim's "
                "separate benign training-feature reservoir."
            )
        tail_fraction = (
            feature_tail_mass
            if spec.source is PoisoningSourceStrategy.HIGH_SCORE_TRAIN_FEATURE_BENIGN
            else 1.0
        )
        feature_outcome = inject_feature_reservoir(
            clean_cal=v_clean,
            benign_reservoir_scores=feature_reservoir_scores,
            feature_row_ids=feature_row_ids,
            fraction=spec.fraction,
            tail_fraction=tail_fraction,
            rng=rng,
        )
        inj = feature_outcome.injection
        reservoir_draw = ReservoirDraw.WITHOUT_REPLACEMENT
        donor_feature_unique_fraction = feature_outcome.donor_feature_unique_fraction
        pool = feature_reservoir_scores[feature_outcome.candidate_indices]
        res = ReservoirResult(
            pool=pool,
            status=ReservoirStatus.FEASIBLE,
            source=spec.source,
            n_pool=pool.size,
            n_distinct=len(np.unique(pool)),
        )
    elif spec.draw == ReservoirDraw.DISJOINT_RESERVOIR:
        inj, res = inject_disjoint_reservoir(
            clean_cal=v_clean,
            source=spec.source,
            tail_mass=spec.tail_mass,
            fraction=spec.fraction,
            rng=rng,
        )
    else:
        res = build_reservoir(
            clean_cal=v_clean, source=spec.source, tail_mass=spec.tail_mass
        )
        inj = inject_fixed_budget(
            clean_cal=v_clean,
            reservoir=res,
            fraction=spec.fraction,
            rng=rng,
            draw=spec.draw,
        )
    assert_no_inplace_mutation(clean_snapshot, v_clean, "victim_cal")

    return InjectionOutcome(
        victim_id=victim_id,
        poisoned_cal_set=PoisonedCalibrationSet.from_mapping(
            _build_poisoned_clients(collection, {victim_id: inj.poisoned_cal})
        ),
        reservoir=res,
        injection=inj,
        reservoir_draw=reservoir_draw,
        donor_feature_unique_fraction=donor_feature_unique_fraction,
    )


def recompute_pair(
    collection: ScoreCollection,
    poisoned_cal_set: PoisonedCalibrationSet,
    policy: ThresholdPolicy,
) -> ThresholdPairBase:
    match policy:
        case ThresholdPolicy.GLOBAL_THRESHOLD:
            return compute_global_pair(collection, poisoned_cal_set, THRESHOLD_QUANTILE)
        case ThresholdPolicy.LOCAL_THRESHOLD:
            t = compute_global_pair(
                collection, poisoned_cal_set, THRESHOLD_QUANTILE
            ).tau_global_clean
            return compute_local_pair(
                collection, poisoned_cal_set, THRESHOLD_QUANTILE, t
            )
        case ThresholdPolicy.CLUSTER_THRESHOLD:
            return compute_cluster_pair(
                collection, poisoned_cal_set, THRESHOLD_QUANTILE
            )


def lock_mu_flag_threshold(collection: ScoreCollection) -> Threshold:
    clean_cal_set = PoisonedCalibrationSet.from_mapping(
        {cid: collection.clients[cid].cal.copy() for cid in collection.eligible_ids}
    )
    fprs = [
        compute_metrics(
            MetricEngineInput(
                collection=collection,
                pair=recompute_pair(collection, clean_cal_set, policy),
                mu_flag_threshold=None,
            )
        ).fleet_fpr.mean_fpr
        for policy in (
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        )
    ]
    positive_fprs = [v for v in fprs if v > 0.0]
    return compute_mu_flag_threshold(min(positive_fprs)) if positive_fprs else 0.0


@dataclass(frozen=True, slots=True)
class SweepCellConfig:
    collection: ScoreCollection
    mu_flag_threshold: Threshold
    auroc_set: AurocSet | None = None
    feature_reservoir_scores: Mapping[ClientId, ScoreVector] | None = None
    feature_row_ids: Mapping[ClientId, np.ndarray] | None = None
    feature_tail_mass: PoisonFraction = FEATURE_TAIL_MASS


@dataclass(frozen=True, slots=True)
class SweepCellResult:
    thresholds_under_poisoning: ThresholdPairBase
    clean_metrics: MetricResult
    poisoned_metrics: MetricResult
    victim_cal_poisoned: ScoreVector
    n_replaced: SampleCount
    reservoir_draw: ReservoirDraw
    donor_feature_unique_fraction: Ratio | None


def _cell_injection_and_metrics(
    spec: SweepCellSpec,
    config: SweepCellConfig,
    *,
    fraction: PoisonFraction,
    mu_flag_threshold: Threshold | None,
) -> tuple[ThresholdPairBase, MetricResult, InjectionOutcome]:
    outcome = inject_single_victim(
        config.collection,
        victim_id=spec.victim_id,
        spec=InjectionSpec(
            source=spec.source,
            fraction=fraction,
            seed_pair=spec.seed_pair,
            objective=spec.objective,
        ),
        feature_reservoir_scores=(
            config.feature_reservoir_scores.get(spec.victim_id)
            if config.feature_reservoir_scores is not None
            else None
        ),
        feature_row_ids=(
            config.feature_row_ids.get(spec.victim_id)
            if config.feature_row_ids is not None
            else None
        ),
        feature_tail_mass=config.feature_tail_mass,
    )
    pair = recompute_pair(config.collection, outcome.poisoned_cal_set, spec.policy)
    metrics = compute_metrics(
        MetricEngineInput(
            collection=config.collection,
            pair=pair,
            mu_flag_threshold=mu_flag_threshold,
            auroc_set=config.auroc_set,
        )
    )
    return pair, metrics, outcome


def clean_cell_metrics(spec: SweepCellSpec, config: SweepCellConfig) -> MetricResult:
    _, clean_metrics, _ = _cell_injection_and_metrics(
        spec, config, fraction=0.0, mu_flag_threshold=None
    )
    return clean_metrics


def run_sweep_cell(
    spec: SweepCellSpec, *, config: SweepCellConfig, clean_metrics: MetricResult
) -> SweepCellResult:
    assert_fractions_in_locked_grid([spec.fraction])
    assert_bounded_scale_requires_single_client(spec.target_scope)
    assert_valid_source_objective_pair(spec.source, spec.objective)

    poisoned_pair, poisoned_metrics, outcome = _cell_injection_and_metrics(
        spec, config, fraction=spec.fraction, mu_flag_threshold=config.mu_flag_threshold
    )

    return SweepCellResult(
        thresholds_under_poisoning=poisoned_pair,
        clean_metrics=clean_metrics,
        poisoned_metrics=poisoned_metrics,
        victim_cal_poisoned=outcome.poisoned_cal_set[spec.victim_id].cal,
        n_replaced=outcome.injection.n_replaced,
        reservoir_draw=outcome.reservoir_draw,
        donor_feature_unique_fraction=outcome.donor_feature_unique_fraction,
    )


logger = get_logger(__name__)


def _auroc_invariant(result: SweepCellResult) -> bool:
    c, p = result.clean_metrics.auroc_records, result.poisoned_metrics.auroc_records
    return all(c[r.client_id].auroc == p[r.client_id].auroc for r in c.values())


def _threshold_pairs(
    entries: Mapping[ClientId, DeltaTauEntry],
) -> dict[ClientId, tuple[Threshold, Threshold]]:
    return {cid: (e.tau_clean, e.tau_pois) for cid, e in entries.items()}


def _scores_by_client(collection: ScoreCollection) -> dict[ClientId, ClientScores]:
    return {cid: collection.clients[cid] for cid in collection.eligible_ids}


@dataclass(frozen=True, slots=True)
class _FixedAssignmentMetrics:
    victim_delta_tau: ManifestMetricValue
    victim_delta_tpr: ManifestMetricValue
    victim_delta_fpr: ManifestMetricValue
    delta_cv_fpr: ManifestMetricValue
    delta_mean_fpr: ManifestMetricValue
    nonvictim_mean_delta_tpr: ManifestMetricValue
    nonvictim_mean_delta_fpr: ManifestMetricValue


@dataclass(frozen=True, slots=True)
class _ClusterMetrics:
    delta_tau_agg: ManifestMetricValue
    delta_tau_churn: ManifestMetricValue
    delta_tau_frozen_scaler: ManifestMetricValue
    delta_tau_normalization_gap: ManifestMetricValue
    victim_effect: ManifestMetricValue
    non_victim_effect: ManifestMetricValue
    sizes_clean: tuple[SignedCount, ...]
    sizes_poisoned: tuple[SignedCount, ...]
    victim_size_clean: ManifestMetricValue
    victim_size_poisoned: ManifestMetricValue
    n_reassigned: ManifestMetricValue
    silhouette_clean: ManifestMetricValue
    silhouette_poisoned: ManifestMetricValue
    fixed_assignment: _FixedAssignmentMetrics


def _fixed_assignment_fields(
    collection: ScoreCollection,
    pair: ClusterThresholdPair,
    clean_fleet: FleetFprMetrics,
    victim_id: ClientId,
) -> _FixedAssignmentMetrics:
    fixed_pair = ThresholdPairBase(
        policy=pair.policy,
        tau_global_clean=pair.tau_global_clean,
        tau_global_pois=pair.tau_global_pois,
        thresholds_clean=pair.thresholds_clean,
        thresholds_pois=pair.fixed_assignment_thresholds,
    )
    entries = compute_delta_tau(collection, fixed_pair)
    fleet = compute_fleet_fpr(collection, fixed_pair, None)
    victim = entries[victim_id]
    ds = compute_victim_downstream_metrics(
        clean_threshold=victim.tau_clean,
        poisoned_threshold=victim.tau_pois,
        client_scores=collection.clients[victim_id],
    )
    nv = compute_non_victim_downstream(
        thresholds=_threshold_pairs(entries),
        scores_by_client=_scores_by_client(collection),
        victim_id=victim_id,
    )
    return _FixedAssignmentMetrics(
        victim.delta_tau,
        ds.delta_tpr,
        ds.delta_fpr,
        fleet.cv_fpr - clean_fleet.cv_fpr,
        fleet.mean_fpr - clean_fleet.mean_fpr,
        nv.mean_delta_tpr,
        nv.mean_delta_fpr,
    )


def _cluster_fields(
    collection: ScoreCollection,
    pair: ThresholdPairBase,
    clean_fleet: FleetFprMetrics,
    victim_id: ClientId,
) -> _ClusterMetrics:
    if not isinstance(pair, ClusterThresholdPair):
        return _ClusterMetrics(
            math.nan,
            math.nan,
            math.nan,
            math.nan,
            math.nan,
            math.nan,
            (),
            (),
            math.nan,
            math.nan,
            math.nan,
            math.nan,
            math.nan,
            _FixedAssignmentMetrics(
                math.nan,
                math.nan,
                math.nan,
                math.nan,
                math.nan,
                math.nan,
                math.nan,
            ),
        )
    v = pair.decomposition[victim_id]
    nv = [e.delta_tau_total for k, e in pair.decomposition.items() if k != victim_id]
    return _ClusterMetrics(
        v.delta_tau_agg,
        v.delta_tau_churn,
        v.delta_tau_frozen_scaler,
        v.delta_tau_normalization_gap,
        v.delta_tau_total,
        sum(nv) / len(nv) if nv else math.nan,
        cluster_sizes(pair.clean_assignments),
        cluster_sizes(pair.poisoned_assignments),
        cluster_size_of(pair.clean_assignments, victim_id),
        cluster_size_of(pair.poisoned_assignments, victim_id),
        n_reassigned(pair.clean_assignments, pair.poisoned_assignments),
        pair.silhouette_clean,
        pair.silhouette_poisoned,
        _fixed_assignment_fields(collection, pair, clean_fleet, victim_id),
    )


def _rows_for_group(
    collection: ScoreCollection,
    specs: tuple[SweepCellSpec, ...],
    mu_flag_threshold: Threshold,
    auroc_set: AurocSet,
    feature_reservoir_scores: Mapping[ClientId, ScoreVector] | None = None,
    feature_row_ids: Mapping[ClientId, np.ndarray] | None = None,
    feature_tail_mass: PoisonFraction = FEATURE_TAIL_MASS,
) -> list[BoundedSweepResultRow]:
    config = SweepCellConfig(
        collection=collection,
        mu_flag_threshold=mu_flag_threshold,
        auroc_set=auroc_set,
        feature_reservoir_scores=feature_reservoir_scores,
        feature_row_ids=feature_row_ids,
        feature_tail_mass=feature_tail_mass,
    )
    clean_metrics = clean_cell_metrics(specs[0], config)
    return [_row_for_cell(collection, spec, config, clean_metrics) for spec in specs]


@dataclass(frozen=True, slots=True)
class _CellEvidence:
    res: SweepCellResult
    entry: DeltaTauEntry
    blast: BlastRadiusRecord
    spill: SpilloverRecord
    cf: FleetFprMetrics
    pf: FleetFprMetrics
    victim_scores: ClientScores
    ds: VictimDownstreamMetrics
    nv: NonVictimDownstreamMetrics
    cluster: _ClusterMetrics


def _cell_evidence(
    collection: ScoreCollection,
    spec: SweepCellSpec,
    config: SweepCellConfig,
    clean_metrics: MetricResult,
) -> _CellEvidence:
    res = run_sweep_cell(spec, config=config, clean_metrics=clean_metrics)
    entry = res.poisoned_metrics.delta_tau[spec.victim_id]
    cf, pf = res.clean_metrics.fleet_fpr, res.poisoned_metrics.fleet_fpr
    return _CellEvidence(
        res=res,
        entry=entry,
        blast=compute_blast_radius(res.poisoned_metrics, victim_id=spec.victim_id),
        spill=compute_spillover(
            res.poisoned_metrics,
            collection=collection,
            victim_id=spec.victim_id,
            objective=spec.objective,
        ),
        cf=cf,
        pf=pf,
        victim_scores=collection.clients[spec.victim_id],
        ds=compute_victim_downstream_metrics(
            clean_threshold=entry.tau_clean,
            poisoned_threshold=entry.tau_pois,
            client_scores=collection.clients[spec.victim_id],
        ),
        nv=compute_non_victim_downstream(
            thresholds=_threshold_pairs(res.poisoned_metrics.delta_tau),
            scores_by_client=_scores_by_client(collection),
            victim_id=spec.victim_id,
        ),
        cluster=_cluster_fields(
            collection, res.thresholds_under_poisoning, cf, spec.victim_id
        ),
    )


def _row_for_cell(
    collection: ScoreCollection,
    spec: SweepCellSpec,
    config: SweepCellConfig,
    clean_metrics: MetricResult,
) -> BoundedSweepResultRow:
    ev = _cell_evidence(collection, spec, config, clean_metrics)
    return BoundedSweepResultRow(
        policy=spec.policy,
        source=spec.source,
        objective=spec.objective,
        fraction=spec.fraction,
        target_scope=spec.target_scope,
        victim_id=spec.victim_id,
        training_seed=spec.training_seed,
        poisoning_seed=spec.poisoning_seed,
        seed_record=SeedRecord(
            pair=spec.seed_pair,
            client_idx=collection.client_index(spec.victim_id),
            scope_idx=0,
        ),
        delta_tau=ev.entry.delta_tau,
        delta_tau_rel=ev.entry.delta_tau_rel,
        is_victim_significant=ev.entry.is_significant,
        cv_fpr_clean=ev.cf.cv_fpr,
        cv_fpr_poisoned=ev.pf.cv_fpr,
        delta_cv_fpr=ev.pf.cv_fpr - ev.cf.cv_fpr,
        mean_fpr_clean=ev.cf.mean_fpr,
        mean_fpr_poisoned=ev.pf.mean_fpr,
        delta_mean_fpr=ev.pf.mean_fpr - ev.cf.mean_fpr,
        iqr_fpr_clean=ev.cf.iqr_fpr,
        iqr_fpr_poisoned=ev.pf.iqr_fpr,
        delta_iqr_fpr=ev.pf.iqr_fpr - ev.cf.iqr_fpr,
        max_min_fpr_clean=ev.cf.max_min_fpr_gap,
        max_min_fpr_poisoned=ev.pf.max_min_fpr_gap,
        delta_max_min_fpr=ev.pf.max_min_fpr_gap - ev.cf.max_min_fpr_gap,
        worst_client_fpr_clean=ev.cf.worst_client_fpr,
        worst_client_fpr_poisoned=ev.pf.worst_client_fpr,
        delta_worst_client_fpr=ev.pf.worst_client_fpr - ev.cf.worst_client_fpr,
        coverage_ratio=ev.pf.coverage_ratio,
        n_eligible=ev.pf.n_eligible,
        mu_flag_triggered=ev.pf.mu_flag_triggered,
        auroc_invariant=_auroc_invariant(ev.res),
        blast_fraction=ev.blast.blast_fraction,
        n_blast_significant=ev.blast.n_significant,
        n_spillover=ev.spill.n_spillover,
        n_non_victims=ev.spill.n_non_victims,
        victim_tpr_clean=ev.ds.tpr_clean,
        victim_tpr_poisoned=ev.ds.tpr_poisoned,
        victim_delta_tpr=ev.ds.delta_tpr,
        victim_ba_clean=ev.ds.ba_clean,
        victim_ba_poisoned=ev.ds.ba_poisoned,
        victim_delta_ba=ev.ds.delta_ba,
        victim_macro_f1_clean=ev.ds.macro_f1_clean,
        victim_macro_f1_poisoned=ev.ds.macro_f1_poisoned,
        victim_delta_macro_f1=ev.ds.delta_macro_f1,
        cluster_delta_tau_agg=ev.cluster.delta_tau_agg,
        cluster_delta_tau_churn=ev.cluster.delta_tau_churn,
        cluster_delta_tau_frozen_scaler=ev.cluster.delta_tau_frozen_scaler,
        cluster_delta_tau_normalization_gap=ev.cluster.delta_tau_normalization_gap,
        cluster_victim_effect=ev.cluster.victim_effect,
        cluster_non_victim_effect=ev.cluster.non_victim_effect,
        victim_fpr_clean=ev.ds.fpr_clean,
        victim_fpr_poisoned=ev.ds.fpr_poisoned,
        victim_delta_fpr=ev.ds.delta_fpr,
        victim_fp_clean=ev.ds.fp_clean,
        victim_fp_poisoned=ev.ds.fp_poisoned,
        victim_fn_clean=ev.ds.fn_clean,
        victim_fn_poisoned=ev.ds.fn_poisoned,
        victim_n_test_benign=ev.ds.n_test_benign,
        victim_n_test_attack=ev.ds.n_test_attack,
        nonvictim_mean_tpr_clean=ev.nv.mean_tpr_clean,
        nonvictim_mean_tpr_poisoned=ev.nv.mean_tpr_poisoned,
        nonvictim_mean_delta_tpr=ev.nv.mean_delta_tpr,
        nonvictim_worst_delta_tpr=ev.nv.worst_delta_tpr,
        nonvictim_mean_fpr_clean=ev.nv.mean_fpr_clean,
        nonvictim_mean_fpr_poisoned=ev.nv.mean_fpr_poisoned,
        nonvictim_mean_delta_fpr=ev.nv.mean_delta_fpr,
        nonvictim_worst_delta_fpr=ev.nv.worst_delta_fpr,
        nonvictim_mean_delta_ba=ev.nv.mean_delta_ba,
        nonvictim_mean_delta_macro_f1=ev.nv.mean_delta_macro_f1,
        nonvictim_delta_fp_total=ev.nv.delta_fp_total,
        nonvictim_delta_fn_total=ev.nv.delta_fn_total,
        victim_delta_tau_scale_base=ev.entry.scale_base,
        iqr_median_clean=ev.entry.iqr_median,
        delta_tau_bound_utilization=tau_bound_utilization(
            clean_cal=ev.victim_scores.cal,
            tau_clean=ev.entry.tau_clean,
            tau_pois=ev.entry.tau_pois,
            objective=spec.objective,
        ),
        n_replaced=ev.res.n_replaced,
        reservoir_draw=ev.res.reservoir_draw,
        donor_feature_unique_fraction=ev.res.donor_feature_unique_fraction,
        cal_duplicate_rate_clean=duplicate_rate(ev.victim_scores.cal),
        cal_duplicate_rate_poisoned=duplicate_rate(ev.res.victim_cal_poisoned),
        cluster_sizes_clean=ev.cluster.sizes_clean,
        cluster_sizes_poisoned=ev.cluster.sizes_poisoned,
        cluster_victim_size_clean=ev.cluster.victim_size_clean,
        cluster_victim_size_poisoned=ev.cluster.victim_size_poisoned,
        cluster_n_reassigned=ev.cluster.n_reassigned,
        cluster_silhouette_clean=ev.cluster.silhouette_clean,
        cluster_silhouette_poisoned=ev.cluster.silhouette_poisoned,
        fixed_cluster_victim_delta_tau=ev.cluster.fixed_assignment.victim_delta_tau,
        fixed_cluster_victim_delta_tpr=ev.cluster.fixed_assignment.victim_delta_tpr,
        fixed_cluster_victim_delta_fpr=ev.cluster.fixed_assignment.victim_delta_fpr,
        fixed_cluster_delta_cv_fpr=ev.cluster.fixed_assignment.delta_cv_fpr,
        fixed_cluster_delta_mean_fpr=ev.cluster.fixed_assignment.delta_mean_fpr,
        fixed_cluster_nonvictim_mean_delta_tpr=(
            ev.cluster.fixed_assignment.nonvictim_mean_delta_tpr
        ),
        fixed_cluster_nonvictim_mean_delta_fpr=(
            ev.cluster.fixed_assignment.nonvictim_mean_delta_fpr
        ),
    )


def load_seed_collections(
    base_dir: Path, config: CalibrationPoisoningConfig
) -> dict[RandomSeed, ScoreCollection]:
    logger.info(
        "poisoning score collection load started",
        stage=ExperimentStage.NBAIOT_MAIN,
        seed_count=len(config.seeds.training),
    )
    collections: dict[RandomSeed, ScoreCollection] = {}
    for seed in config.seeds.training:
        try:
            cal_errors = load_main_cal_errors(
                ExperimentStage.NBAIOT_MAIN, seed, base_dir
            )
            layout = ArtifactLayout(
                base_dir=base_dir, stage=ExperimentStage.NBAIOT_MAIN
            )
            score_dir = layout.score_cell(
                TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=RandomSeed(seed))
            ).score_dir
            test_benign = load_parquets_from_dir(
                score_dir / ScoringStage.TEST_BENIGN, allow_empty=False
            )
            test_attack = load_parquets_from_dir(
                score_dir / ScoringStage.TEST_ATTACK, allow_empty=False
            )
            collections[seed] = build_score_collection(
                {
                    cid: (cal, test_benign[cid], test_attack[cid])
                    for cid, cal in cal_errors.items()
                },
                n_min=N_MIN,
            )
        except Exception:
            logger.exception(
                "poisoning score collection load failed",
                stage=ExperimentStage.NBAIOT_MAIN,
                seed=seed,
            )
            raise
    logger.info(
        "poisoning score collection load completed",
        stage=ExperimentStage.NBAIOT_MAIN,
        seed_count=len(collections),
        eligible_client_count=sum(
            len(collection.eligible_ids) for collection in collections.values()
        ),
    )
    return collections


def _seed_statics(collection: ScoreCollection) -> tuple[Threshold, AurocSet]:
    return lock_mu_flag_threshold(collection), compute_auroc_records(collection)


def _read_train_features(feature_root: Path, client_id: ClientId) -> np.ndarray:
    train_path = feature_root / client_id / "train.parquet"
    if not train_path.is_file():
        raise FileNotFoundError(f"Missing benign training feature split: {train_path}")
    return pl.read_parquet(train_path).to_numpy().astype(np.float32, copy=False)


def _global_row_ids(
    features_by_client: Mapping[ClientId, np.ndarray],
) -> dict[ClientId, np.ndarray]:
    if not features_by_client:
        return {}
    _, inverse = np.unique(
        np.concatenate(list(features_by_client.values())),
        axis=0,
        return_inverse=True,
    )
    inverse = inverse.reshape(-1).astype(np.int64, copy=False)
    bounds = np.cumsum([0, *(len(f) for f in features_by_client.values())])
    return {
        client_id: inverse[start:stop]
        for client_id, start, stop in zip(
            features_by_client, bounds[:-1], bounds[1:], strict=True
        )
    }


def load_train_feature_reservoirs(
    base_dir: Path,
    collections: Mapping[RandomSeed, ScoreCollection],
    *,
    data_root: Path = Path("."),
    donor_scope: FeatureDonorScope,
) -> tuple[
    dict[RandomSeed, dict[ClientId, ScoreVector]],
    dict[RandomSeed, dict[ClientId, np.ndarray]],
]:
    logger.info(WorkflowEvent.STARTED, workflow=Workflow.FEATURE_RESERVOIR_LOAD)
    feature_root = processed_root(DatasetID.NBAIOT, base_dir=data_root)
    score_by_seed: dict[RandomSeed, dict[ClientId, ScoreVector]] = {}
    row_ids_by_seed: dict[RandomSeed, dict[ClientId, np.ndarray]] = {}
    layout = ArtifactLayout(base_dir=base_dir, stage=ExperimentStage.NBAIOT_MAIN)
    client_ids = next(iter(collections.values())).eligible_ids
    features_by_client = {
        client_id: _read_train_features(feature_root, client_id)
        for client_id in client_ids
    }
    row_ids_by_client = _global_row_ids(features_by_client)

    for seed, collection in collections.items():
        cell = TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=seed)
        checkpoint_path = layout.model_checkpoint(cell)
        if not checkpoint_path.is_file():
            raise FileNotFoundError(
                f"Missing federated model checkpoint {checkpoint_path}. "
                "Rerun the baseline with the current code before running the sweep."
            )
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        model_config = ModelConfig.model_validate(
            checkpoint[CheckpointKey.MODEL_CONFIG]
        )
        model = Autoencoder(
            input_dim=model_config.input_dim,
            hidden_dims=model_config.encoder_dims,
            activation=model_config.activation,
            use_bn=model_config.use_bn,
        )
        model.load_state_dict(checkpoint[CheckpointKey.STATE_DICT])
        model.eval()

        score_dir = layout.score_cell(cell).score_dir
        manifest = validate_scoring_manifest(score_dir)
        if hash_model_state(model) != manifest.model_hash:
            raise ValueError(
                f"Checkpoint {checkpoint_path} does not match its score manifest."
            )

        own_scores: dict[ClientId, ScoreVector] = {}
        for client_id in collection.eligible_ids:
            features = features_by_client[client_id]
            if features.shape[1] != model_config.input_dim:
                raise ValueError(
                    f"Feature dimension mismatch for {client_id}: expected "
                    f"{model_config.input_dim}, got {features.shape[1]}"
                )
            own_scores[client_id] = score_feature_rows(model, features)
        scores_for_clients: dict[ClientId, ScoreVector] = {}
        row_ids_for_clients: dict[ClientId, np.ndarray] = {}
        for client_id in collection.eligible_ids:
            donors = (
                (client_id,)
                if donor_scope is FeatureDonorScope.OWN_DEVICE
                else tuple(c for c in collection.eligible_ids if c != client_id)
            )
            scores_for_clients[client_id] = np.concatenate(
                [own_scores[c] for c in donors]
            )
            row_ids_for_clients[client_id] = np.concatenate(
                [row_ids_by_client[c] for c in donors]
            )

        score_by_seed[seed] = scores_for_clients
        row_ids_by_seed[seed] = row_ids_for_clients
    workflow_result = score_by_seed, row_ids_by_seed
    logger.info(WorkflowEvent.COMPLETED, workflow=Workflow.FEATURE_RESERVOIR_LOAD)
    return workflow_result


def run_nbaiot_main(
    base_dir: Path,
    config: CalibrationPoisoningConfig,
    *,
    data_root: Path = Path("."),
) -> BoundedSweepManifest:
    logger.info(
        "bounded sweep started",
        stage=ExperimentStage.NBAIOT_MAIN,
        training_seed_count=len(config.seeds.training),
        poisoning_seed_count=len(config.seeds.poisoning),
        analysis_seed_count=len(config.seeds.analysis),
    )
    collections = load_seed_collections(base_dir, config)
    feature_scores_by_seed: dict[RandomSeed, dict[ClientId, ScoreVector]] = {}
    feature_row_ids_by_seed: dict[RandomSeed, dict[ClientId, np.ndarray]] = {}
    if any(is_train_feature_source(source) for source in config.sources):
        feature_scores_by_seed, feature_row_ids_by_seed = load_train_feature_reservoirs(
            base_dir,
            collections,
            data_root=data_root,
            donor_scope=config.feature_donor_scope,
        )
    mu_flag_by_seed: dict[RandomSeed, Threshold] = {}
    auroc_by_seed: dict[RandomSeed, AurocSet] = {}
    victims_by_seed: dict[RandomSeed, tuple[ClientId, ...]] = {}

    seed_statics = Parallel(n_jobs=-1)(
        delayed(_seed_statics)(col) for col in collections.values()
    )
    for (seed, col), (mu_flag, auroc_records) in zip(
        collections.items(), seed_statics, strict=True
    ):
        mu_flag_by_seed[seed] = mu_flag
        auroc_by_seed[seed] = auroc_records
        victims_by_seed[seed] = col.eligible_ids

    cells = enumerate_bounded_sweep_matrix(victims_by_seed, config)
    logger.info(
        "bounded sweep matrix planned",
        cell_count=len(cells),
        training_seed_count=len(collections),
        eligible_client_count=sum(len(ids) for ids in victims_by_seed.values()),
    )

    groups: dict[
        tuple[RandomSeed, RandomSeed, ThresholdPolicy, ClientId], list[Index]
    ] = defaultdict(list)
    for index, spec in enumerate(cells):
        groups[
            (spec.training_seed, spec.poisoning_seed, spec.policy, spec.victim_id)
        ].append(index)
    try:
        grouped_rows = Parallel(n_jobs=-1)(
            delayed(_rows_for_group)(
                collections[key[0]],
                tuple(cells[i] for i in indices),
                mu_flag_by_seed[key[0]],
                auroc_by_seed[key[0]],
                feature_scores_by_seed.get(key[0]),
                feature_row_ids_by_seed.get(key[0]),
                config.feature_tail_mass,
            )
            for key, indices in groups.items()
        )
    except Exception:
        logger.exception("bounded sweep cell execution failed", cell_count=len(cells))
        raise

    ordered: list[BoundedSweepResultRow | None] = [None] * len(cells)
    for indices, group_rows in zip(groups.values(), grouped_rows, strict=True):
        for index, row in zip(indices, group_rows, strict=True):
            ordered[index] = row
    rows = [row for row in ordered if row is not None]

    manifest = BoundedSweepManifest(
        generated_at_utc=datetime.now(UTC).isoformat(),
        provenance=ProvenanceRecord(local_epochs=1, repository=REPOSITORY_NAME),
        config_hash=hash_jsonable(config.model_dump(mode="json")),
        artifact_provenance=ArtifactProvenance(
            source=ManifestProvenanceSource.NBAIOT_MAIN_SWEEP
        ),
        policies=config.policies,
        sources=config.sources,
        source_objective_pairs=tuple(
            sorted({f"{r.source}+{r.objective}" for r in rows})
        ),
        fractions=config.fractions,
        training_seeds=config.seeds.training,
        poisoning_seeds=config.seeds.poisoning,
        analysis_seeds=config.seeds.analysis,
        mu_flag_threshold_by_training_seed=mu_flag_by_seed,
        n_cells=len(rows),
        results=tuple(rows),
    )
    logger.info("bounded sweep completed", result_count=len(manifest.results))
    return manifest


def write_nbaiot_main_manifest(base_dir: Path, data_root: Path = Path(".")) -> Path:
    out_path = nbaiot_main_manifest_path(base_dir)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        run_nbaiot_main(
            base_dir,
            CalibrationPoisoningConfig.for_bounded_sweep(),
            data_root=data_root,
        ).model_dump_json(indent=2)
    )
    logger.info("bounded sweep manifest written", path=out_path)
    return out_path
