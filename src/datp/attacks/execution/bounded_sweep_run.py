"""NBAIOT main bounded-sweep orchestration: per-cell execution and result assembly."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

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
from datp.attacks.metrics.diagnostics import compute_blast_radius, compute_spillover
from datp.attacks.metrics.metric_engine import (
    compute_auroc_records,
    compute_victim_downstream_metrics,
)
from datp.attacks.planning.bounded_sweep_matrix import (
    SweepCellSpec,
    enumerate_bounded_sweep_matrix,
)
from datp.attacks.score_containers import ScoreCollection, build_score_collection
from datp.attacks.threshold_recomputation.cluster_threshold_recompute import (
    ClusterThresholdPair,
)
from datp.attacks.types import AurocSet
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
    ds = compute_victim_downstream_metrics(
        clean_threshold=entry.tau_clean,
        poisoned_threshold=entry.tau_pois,
        client_scores=collection.for_client(spec.victim_id),
    )

    pair = res.thresholds_under_poisoning
    is_cluster = isinstance(pair, ClusterThresholdPair)
    v = pair.decomposition[spec.victim_id] if is_cluster else None
    nv = (
        [
            e.delta_tau_total
            for k, e in pair.decomposition.items()
            if k != spec.victim_id
        ]
        if is_cluster
        else []
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
        cluster_delta_tau_agg=v.delta_tau_agg if v is not None else math.nan,
        cluster_delta_tau_churn=v.delta_tau_churn if v is not None else math.nan,
        cluster_delta_tau_frozen_scaler=v.delta_tau_frozen_scaler
        if v is not None
        else math.nan,
        cluster_delta_tau_normalization_gap=v.delta_tau_normalization_gap
        if v is not None
        else math.nan,
        cluster_victim_effect=v.delta_tau_total if v is not None else math.nan,
        cluster_non_victim_effect=sum(nv) / len(nv) if nv else math.nan,
    )


def run_nbaiot_main(
    base_dir: Path, config: CalibrationPoisoningConfig
) -> BoundedSweepManifest:
    """Execute the full NBAIOT main bounded sweep and return the manifest."""
    collections, mu_flag_by_seed, auroc_by_seed, victims_by_seed = {}, {}, {}, {}

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
        col = build_score_collection(
            {
                cid: (cal, test_benign[cid], test_attack[cid])
                for cid, cal in cal_errors.items()
            },
            n_min=N_MIN,
        )
        collections[seed] = col
        mu_flag_by_seed[seed] = lock_mu_flag_threshold(col)
        auroc_by_seed[seed] = compute_auroc_records(col)
        victims_by_seed[seed] = col.eligible_ids

    cells = enumerate_bounded_sweep_matrix(victims_by_seed, config)

    rows = cast(
        list[BoundedSweepResultRow],
        Parallel(n_jobs=-1, prefer="threads")(
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
