from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

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
from datp.attacks.manifests import (
    ArtifactProvenance,
    BoundedSweepManifest,
    BoundedSweepResultRow,
    ProvenanceRecord,
)
from datp.attacks.metrics import (
    ClusterThresholdPair,
    DeltaTauEntry,
    FleetFprMetrics,
    MetricResult,
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
    N_MIN,
    TAIL_MASS,
    THRESHOLD_QUANTILE,
    CalibrationPoisoningConfig,
    ExperimentStage,
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
from datp.enums import (
    AttackerObjective,
    ManifestProvenanceSource,
    PoisoningSourceStrategy,
    ReservoirDraw,
    ScoringStage,
    ThresholdPolicy,
    is_diagnostic_source,
)
from datp.scoring import load_main_cal_errors, load_parquets_from_dir
from datp.types import (
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
    collection: ScoreCollection, *, victim_id: ClientId, spec: InjectionSpec
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
    if spec.draw == ReservoirDraw.DISJOINT_RESERVOIR:
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


@dataclass(frozen=True, slots=True)
class SweepCellResult:

    thresholds_under_poisoning: ThresholdPairBase
    clean_metrics: MetricResult
    poisoned_metrics: MetricResult
    victim_cal_poisoned: ScoreVector
    n_replaced: SampleCount


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


def run_sweep_cell(spec: SweepCellSpec, *, config: SweepCellConfig) -> SweepCellResult:
    assert_fractions_in_locked_grid([spec.fraction])
    assert_bounded_scale_requires_single_client(spec.target_scope)
    assert_valid_source_objective_pair(spec.source, spec.objective)

    _, clean_metrics, _ = _cell_injection_and_metrics(
        spec, config, fraction=0.0, mu_flag_threshold=None
    )
    poisoned_pair, poisoned_metrics, outcome = _cell_injection_and_metrics(
        spec, config, fraction=spec.fraction, mu_flag_threshold=config.mu_flag_threshold
    )

    return SweepCellResult(
        thresholds_under_poisoning=poisoned_pair,
        clean_metrics=clean_metrics,
        poisoned_metrics=poisoned_metrics,
        victim_cal_poisoned=outcome.poisoned_cal_set[spec.victim_id].cal,
        n_replaced=outcome.injection.n_replaced,
    )


logger = get_logger(__name__)


def _auroc_invariant(result: SweepCellResult) -> bool:
    c, p = result.clean_metrics.auroc_records, result.poisoned_metrics.auroc_records
    return all(
        c[r.client_id].auroc == p[r.client_id].auroc
        for r in c.values()
    )


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


def _row_for_cell(
    collection: ScoreCollection,
    spec: SweepCellSpec,
    mu_flag_threshold: Threshold,
    auroc_set: AurocSet,
) -> BoundedSweepResultRow:
    res = run_sweep_cell(
        spec,
        config=SweepCellConfig(
            collection=collection,
            mu_flag_threshold=mu_flag_threshold,
            auroc_set=auroc_set,
        ),
    )
    entry = res.poisoned_metrics.delta_tau[spec.victim_id]
    blast = compute_blast_radius(res.poisoned_metrics, victim_id=spec.victim_id)
    spill = compute_spillover(
        res.poisoned_metrics,
        collection=collection,
        victim_id=spec.victim_id,
        objective=spec.objective,
    )
    cf, pf = res.clean_metrics.fleet_fpr, res.poisoned_metrics.fleet_fpr
    victim_scores = collection.clients[spec.victim_id]
    ds = compute_victim_downstream_metrics(
        clean_threshold=entry.tau_clean,
        poisoned_threshold=entry.tau_pois,
        client_scores=victim_scores,
    )
    nv = compute_non_victim_downstream(
        thresholds=_threshold_pairs(res.poisoned_metrics.delta_tau),
        scores_by_client=_scores_by_client(collection),
        victim_id=spec.victim_id,
    )

    cluster = _cluster_fields(
        collection, res.thresholds_under_poisoning, cf, spec.victim_id
    )

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
        delta_tau=entry.delta_tau,
        delta_tau_rel=entry.delta_tau_rel,
        is_victim_significant=entry.is_significant,
        cv_fpr_clean=cf.cv_fpr,
        cv_fpr_poisoned=pf.cv_fpr,
        delta_cv_fpr=pf.cv_fpr - cf.cv_fpr,
        mean_fpr_clean=cf.mean_fpr,
        mean_fpr_poisoned=pf.mean_fpr,
        delta_mean_fpr=pf.mean_fpr - cf.mean_fpr,
        iqr_fpr_clean=cf.iqr_fpr,
        iqr_fpr_poisoned=pf.iqr_fpr,
        delta_iqr_fpr=pf.iqr_fpr - cf.iqr_fpr,
        max_min_fpr_clean=cf.max_min_fpr_gap,
        max_min_fpr_poisoned=pf.max_min_fpr_gap,
        delta_max_min_fpr=pf.max_min_fpr_gap - cf.max_min_fpr_gap,
        worst_client_fpr_clean=cf.worst_client_fpr,
        worst_client_fpr_poisoned=pf.worst_client_fpr,
        delta_worst_client_fpr=pf.worst_client_fpr - cf.worst_client_fpr,
        coverage_ratio=pf.coverage_ratio,
        n_eligible=pf.n_eligible,
        mu_flag_triggered=pf.mu_flag_triggered,
        auroc_invariant=_auroc_invariant(res),
        blast_fraction=blast.blast_fraction,
        n_blast_significant=blast.n_significant,
        n_spillover=spill.n_spillover,
        n_non_victims=spill.n_non_victims,
        victim_tpr_clean=ds.tpr_clean,
        victim_tpr_poisoned=ds.tpr_poisoned,
        victim_delta_tpr=ds.delta_tpr,
        victim_ba_clean=ds.ba_clean,
        victim_ba_poisoned=ds.ba_poisoned,
        victim_delta_ba=ds.delta_ba,
        victim_macro_f1_clean=ds.macro_f1_clean,
        victim_macro_f1_poisoned=ds.macro_f1_poisoned,
        victim_delta_macro_f1=ds.delta_macro_f1,
        cluster_delta_tau_agg=cluster.delta_tau_agg,
        cluster_delta_tau_churn=cluster.delta_tau_churn,
        cluster_delta_tau_frozen_scaler=cluster.delta_tau_frozen_scaler,
        cluster_delta_tau_normalization_gap=cluster.delta_tau_normalization_gap,
        cluster_victim_effect=cluster.victim_effect,
        cluster_non_victim_effect=cluster.non_victim_effect,
        victim_fpr_clean=ds.fpr_clean,
        victim_fpr_poisoned=ds.fpr_poisoned,
        victim_delta_fpr=ds.delta_fpr,
        victim_fp_clean=ds.fp_clean,
        victim_fp_poisoned=ds.fp_poisoned,
        victim_fn_clean=ds.fn_clean,
        victim_fn_poisoned=ds.fn_poisoned,
        victim_n_test_benign=ds.n_test_benign,
        victim_n_test_attack=ds.n_test_attack,
        nonvictim_mean_tpr_clean=nv.mean_tpr_clean,
        nonvictim_mean_tpr_poisoned=nv.mean_tpr_poisoned,
        nonvictim_mean_delta_tpr=nv.mean_delta_tpr,
        nonvictim_worst_delta_tpr=nv.worst_delta_tpr,
        nonvictim_mean_fpr_clean=nv.mean_fpr_clean,
        nonvictim_mean_fpr_poisoned=nv.mean_fpr_poisoned,
        nonvictim_mean_delta_fpr=nv.mean_delta_fpr,
        nonvictim_worst_delta_fpr=nv.worst_delta_fpr,
        nonvictim_mean_delta_ba=nv.mean_delta_ba,
        nonvictim_mean_delta_macro_f1=nv.mean_delta_macro_f1,
        nonvictim_delta_fp_total=nv.delta_fp_total,
        nonvictim_delta_fn_total=nv.delta_fn_total,
        victim_delta_tau_scale_base=entry.scale_base,
        iqr_median_clean=entry.iqr_median,
        delta_tau_bound_utilization=tau_bound_utilization(
            clean_cal=victim_scores.cal,
            tau_clean=entry.tau_clean,
            tau_pois=entry.tau_pois,
            objective=spec.objective,
        ),
        n_replaced=res.n_replaced,
        cal_duplicate_rate_clean=duplicate_rate(victim_scores.cal),
        cal_duplicate_rate_poisoned=duplicate_rate(res.victim_cal_poisoned),
        cluster_sizes_clean=cluster.sizes_clean,
        cluster_sizes_poisoned=cluster.sizes_poisoned,
        cluster_victim_size_clean=cluster.victim_size_clean,
        cluster_victim_size_poisoned=cluster.victim_size_poisoned,
        cluster_n_reassigned=cluster.n_reassigned,
        cluster_silhouette_clean=cluster.silhouette_clean,
        cluster_silhouette_poisoned=cluster.silhouette_poisoned,
        fixed_cluster_victim_delta_tau=cluster.fixed_assignment.victim_delta_tau,
        fixed_cluster_victim_delta_tpr=cluster.fixed_assignment.victim_delta_tpr,
        fixed_cluster_victim_delta_fpr=cluster.fixed_assignment.victim_delta_fpr,
        fixed_cluster_delta_cv_fpr=cluster.fixed_assignment.delta_cv_fpr,
        fixed_cluster_delta_mean_fpr=cluster.fixed_assignment.delta_mean_fpr,
        fixed_cluster_nonvictim_mean_delta_tpr=(
            cluster.fixed_assignment.nonvictim_mean_delta_tpr
        ),
        fixed_cluster_nonvictim_mean_delta_fpr=(
            cluster.fixed_assignment.nonvictim_mean_delta_fpr
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
                TrainingCellId(
                    stage=ExperimentStage.NBAIOT_MAIN, seed=RandomSeed(seed)
                )
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


def run_nbaiot_main(
    base_dir: Path, config: CalibrationPoisoningConfig
) -> BoundedSweepManifest:
    logger.info(
        "bounded sweep started",
        stage=ExperimentStage.NBAIOT_MAIN,
        training_seed_count=len(config.seeds.training),
        poisoning_seed_count=len(config.seeds.poisoning),
        analysis_seed_count=len(config.seeds.analysis),
    )
    collections = load_seed_collections(base_dir, config)
    mu_flag_by_seed: dict[RandomSeed, Threshold] = {}
    auroc_by_seed: dict[RandomSeed, AurocSet] = {}
    victims_by_seed: dict[RandomSeed, tuple[ClientId, ...]] = {}

    for seed, col in collections.items():
        mu_flag_by_seed[seed] = lock_mu_flag_threshold(col)
        auroc_by_seed[seed] = compute_auroc_records(col)
        victims_by_seed[seed] = col.eligible_ids

    cells = enumerate_bounded_sweep_matrix(victims_by_seed, config)
    logger.info(
        "bounded sweep matrix planned",
        cell_count=len(cells),
        training_seed_count=len(collections),
        eligible_client_count=sum(len(ids) for ids in victims_by_seed.values()),
    )

    try:
        rows = Parallel(n_jobs=-1)(
            delayed(_row_for_cell)(
                collections[spec.training_seed],
                spec,
                mu_flag_by_seed[spec.training_seed],
                auroc_by_seed[spec.training_seed],
            )
            for spec in cells
        )
    except Exception:
        logger.exception("bounded sweep cell execution failed", cell_count=len(cells))
        raise

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


def write_nbaiot_main_manifest(base_dir: Path) -> Path:
    out_path = nbaiot_main_manifest_path(base_dir)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        run_nbaiot_main(
            base_dir, CalibrationPoisoningConfig.for_bounded_sweep()
        ).model_dump_json(indent=2)
    )
    logger.info("bounded sweep manifest written", path=out_path)
    return out_path
