"""NBAIOT main bounded-sweep orchestration: per-cell execution and result assembly."""

from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from joblib import Parallel, delayed

from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.poison_layout import PoisonLayout
from datp.artifacts.poison_names import NBAIOT_MAIN_MANIFEST_SOURCE
from datp.attacks.constants import N_MIN
from datp.attacks.execution.bounded_sweep_cell import (
    SweepCellConfig,
    SweepCellResult,
    lock_mu_flag_threshold,
    run_sweep_cell,
)
from datp.attacks.manifests.bounded_sweep_manifest import (
    BoundedSweepManifest,
    BoundedSweepResultRow,
)
from datp.attacks.manifests.run_manifest import ProvenanceRecord
from datp.attacks.metrics.cluster_stability import (
    cluster_size_of,
    cluster_sizes,
    n_reassigned,
)
from datp.attacks.metrics.delta_tau import DeltaTauEntry, compute_delta_tau
from datp.attacks.metrics.diagnostics import (
    compute_blast_radius,
    compute_spillover,
    duplicate_rate,
    tau_bound_utilization,
)
from datp.attacks.metrics.downstream import compute_non_victim_downstream
from datp.attacks.metrics.fleet_fpr import FleetFprMetrics, compute_fleet_fpr
from datp.attacks.metrics.metric_engine import (
    compute_auroc_records,
    compute_victim_downstream_metrics,
)
from datp.attacks.planning.bounded_sweep_matrix import (
    SweepCellSpec,
    enumerate_bounded_sweep_matrix,
)
from datp.attacks.score_containers import (
    ClientScores,
    ScoreCollection,
    build_score_collection,
)
from datp.attacks.threshold_recomputation.cluster_threshold_recompute import (
    ClusterThresholdPair,
)
from datp.attacks.types import AurocSet, ThresholdPairBase
from datp.config.attack_config import CalibrationPoisoningConfig
from datp.config.models import ExperimentStage
from datp.core.enums import ScoringStage
from datp.core.identity import TrainingCellId
from datp.core.provenance import REPOSITORY_NAME, hash_jsonable
from datp.core.seeds import derive_seed_record
from datp.scoring.loading import load_main_cal_errors, load_parquets_from_dir


def _auroc_invariant(result: SweepCellResult) -> bool:
    """Check that Auroc is invariant under poisoning for all clients."""
    c, p = result.clean_metrics.auroc_records, result.poisoned_metrics.auroc_records
    return all(
        c.for_client(r.client_id).auroc == p.for_client(r.client_id).auroc
        for r in c.values()
    )


def _threshold_pairs(
    entries: Mapping[str, DeltaTauEntry],
) -> dict[str, tuple[float, float]]:
    """Map client IDs to (clean, poisoned) thresholds."""
    return {cid: (e.tau_clean, e.tau_pois) for cid, e in entries.items()}


def _scores_by_client(collection: ScoreCollection) -> dict[str, ClientScores]:
    """Map eligible client IDs to their score arrays."""
    return {cid: collection.for_client(cid) for cid in collection.eligible_ids}


def _fixed_assignment_fields(
    collection: ScoreCollection,
    pair: ClusterThresholdPair,
    clean_fleet: FleetFprMetrics,
    victim_id: str,
) -> dict[str, float]:
    """Compute victim, fleet and non-victim effects when clean cluster assignments stay frozen."""
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
        client_scores=collection.for_client(victim_id),
    )
    nv = compute_non_victim_downstream(
        thresholds=_threshold_pairs(entries),
        scores_by_client=_scores_by_client(collection),
        victim_id=victim_id,
    )
    return {
        "fixed_cluster_victim_delta_tau": victim.delta_tau,
        "fixed_cluster_victim_delta_tpr": ds.delta_tpr,
        "fixed_cluster_victim_delta_fpr": ds.delta_fpr,
        "fixed_cluster_delta_cv_fpr": fleet.cv_fpr - clean_fleet.cv_fpr,
        "fixed_cluster_delta_mean_fpr": fleet.mean_fpr - clean_fleet.mean_fpr,
        "fixed_cluster_nonvictim_mean_delta_tpr": nv.mean_delta_tpr,
        "fixed_cluster_nonvictim_mean_delta_fpr": nv.mean_delta_fpr,
    }


def _cluster_fields(
    collection: ScoreCollection,
    pair: ThresholdPairBase,
    clean_fleet: FleetFprMetrics,
    victim_id: str,
) -> dict[str, Any]:
    """Compute cluster-only row fields; NaN or empty for non-cluster policies."""
    if not isinstance(pair, ClusterThresholdPair):
        return {
            "cluster_delta_tau_agg": math.nan,
            "cluster_delta_tau_churn": math.nan,
            "cluster_delta_tau_frozen_scaler": math.nan,
            "cluster_delta_tau_normalization_gap": math.nan,
            "cluster_victim_effect": math.nan,
            "cluster_non_victim_effect": math.nan,
            "cluster_sizes_clean": (),
            "cluster_sizes_poisoned": (),
            "cluster_victim_size_clean": math.nan,
            "cluster_victim_size_poisoned": math.nan,
            "cluster_n_reassigned": math.nan,
            "cluster_silhouette_clean": math.nan,
            "cluster_silhouette_poisoned": math.nan,
            **dict.fromkeys(_FIXED_CLUSTER_FIELDS, math.nan),
        }
    v = pair.decomposition[victim_id]
    nv = [e.delta_tau_total for k, e in pair.decomposition.items() if k != victim_id]
    return {
        "cluster_delta_tau_agg": v.delta_tau_agg,
        "cluster_delta_tau_churn": v.delta_tau_churn,
        "cluster_delta_tau_frozen_scaler": v.delta_tau_frozen_scaler,
        "cluster_delta_tau_normalization_gap": v.delta_tau_normalization_gap,
        "cluster_victim_effect": v.delta_tau_total,
        "cluster_non_victim_effect": sum(nv) / len(nv) if nv else math.nan,
        "cluster_sizes_clean": cluster_sizes(pair.clean_assignments),
        "cluster_sizes_poisoned": cluster_sizes(pair.poisoned_assignments),
        "cluster_victim_size_clean": cluster_size_of(pair.clean_assignments, victim_id),
        "cluster_victim_size_poisoned": cluster_size_of(
            pair.poisoned_assignments, victim_id
        ),
        "cluster_n_reassigned": n_reassigned(
            pair.clean_assignments, pair.poisoned_assignments
        ),
        "cluster_silhouette_clean": pair.silhouette_clean,
        "cluster_silhouette_poisoned": pair.silhouette_poisoned,
        **_fixed_assignment_fields(collection, pair, clean_fleet, victim_id),
    }


_FIXED_CLUSTER_FIELDS = (
    "fixed_cluster_victim_delta_tau",
    "fixed_cluster_victim_delta_tpr",
    "fixed_cluster_victim_delta_fpr",
    "fixed_cluster_delta_cv_fpr",
    "fixed_cluster_delta_mean_fpr",
    "fixed_cluster_nonvictim_mean_delta_tpr",
    "fixed_cluster_nonvictim_mean_delta_fpr",
)


def _row_for_cell(
    collection: ScoreCollection,
    spec: SweepCellSpec,
    mu_flag_threshold: float,
    auroc_set: AurocSet,
) -> BoundedSweepResultRow:
    """Execute one sweep cell and assemble its result row."""
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
    victim_scores = collection.for_client(spec.victim_id)
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

    return BoundedSweepResultRow(
        policy=spec.policy,
        source=spec.source,
        objective=spec.objective,
        fraction=spec.fraction,
        target_scope=spec.target_scope,
        victim_id=spec.victim_id,
        training_seed=spec.training_seed,
        poisoning_seed=spec.poisoning_seed,
        seed_record=derive_seed_record(
            spec.seed_pair,
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
        **_cluster_fields(
            collection, res.thresholds_under_poisoning, cf, spec.victim_id
        ),
    )


def load_seed_collections(
    base_dir: Path, config: CalibrationPoisoningConfig
) -> dict[int, ScoreCollection]:
    """Load the clean score collection for every training seed."""
    collections: dict[int, ScoreCollection] = {}
    for seed in config.seeds.training:
        cal_errors = load_main_cal_errors(
            ExperimentStage.NBAIOT_MAIN, seed, base_dir, None
        )
        layout = ArtifactLayout(base_dir=base_dir, stage=ExperimentStage.NBAIOT_MAIN)
        score_dir = layout.score_cell(
            TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=seed)
        ).score_dir
        test_benign = load_parquets_from_dir(
            score_dir / ScoringStage.TEST_BENIGN.value, allow_empty=False
        )
        test_attack = load_parquets_from_dir(
            score_dir / ScoringStage.TEST_ATTACK.value, allow_empty=False
        )
        collections[seed] = build_score_collection(
            {
                cid: (cal, test_benign[cid], test_attack[cid])
                for cid, cal in cal_errors.items()
            },
            n_min=N_MIN,
        )
    return collections


def run_nbaiot_main(
    base_dir: Path, config: CalibrationPoisoningConfig
) -> BoundedSweepManifest:
    """Execute the full NBAIOT main bounded sweep and return the manifest."""
    collections = load_seed_collections(base_dir, config)
    mu_flag_by_seed, auroc_by_seed, victims_by_seed = {}, {}, {}

    for seed, col in collections.items():
        mu_flag_by_seed[seed] = lock_mu_flag_threshold(col)
        auroc_by_seed[seed] = compute_auroc_records(col)
        victims_by_seed[seed] = col.eligible_ids

    cells = enumerate_bounded_sweep_matrix(victims_by_seed, config)

    rows = cast(
        list[BoundedSweepResultRow],
        Parallel(n_jobs=-1)(
            delayed(_row_for_cell)(
                collections[spec.training_seed],
                spec,
                mu_flag_by_seed[spec.training_seed],
                auroc_by_seed[spec.training_seed],
            )
            for spec in cells
        ),
    )

    return BoundedSweepManifest(
        generated_at_utc=datetime.now(UTC).isoformat(),
        provenance=ProvenanceRecord(local_epochs=1, repository=REPOSITORY_NAME),
        config_hash=hash_jsonable(config.model_dump(mode="json")),
        artifact_provenance={"source": NBAIOT_MAIN_MANIFEST_SOURCE},
        policies=config.policies,
        sources=config.sources,
        source_objective_pairs=tuple(
            sorted({f"{r.source.value}+{r.objective.value}" for r in rows})
        ),
        fractions=config.fractions,
        training_seeds=config.seeds.training,
        poisoning_seeds=config.seeds.poisoning,
        analysis_seeds=config.seeds.analysis,
        mu_flag_threshold_by_training_seed=mu_flag_by_seed,
        n_cells=len(rows),
        results=tuple(rows),
    )


def write_nbaiot_main_manifest(base_dir: Path) -> Path:
    """Run the NBAIOT main sweep and write the manifest JSON to disk."""
    out_path = PoisonLayout(base_dir=base_dir).nbaiot_main_manifest()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        run_nbaiot_main(
            base_dir, CalibrationPoisoningConfig.for_bounded_sweep()
        ).model_dump_json(indent=2)
    )
    return out_path
