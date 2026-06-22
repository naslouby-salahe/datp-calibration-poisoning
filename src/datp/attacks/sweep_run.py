"""Bounded N-BaIoT execution .

Single owner of the end-to-end bounded run: loads each training seed's
real score collection once, locks ``mu_flag_threshold`` per seed before any
poisoned cell for that seed, sweeps the locked 1620-cell matrix, and
assembles the single ``nbaiot_main_manifest.json`` artifact. This is the only
path that should ever produce that file — diagnostic/ad hoc scripts must not
duplicate this orchestration.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from datp.artifacts.poison_layout import PoisonLayout
from datp.attacks.sweep_cell import (
    SweepCellConfig,
    SweepCellResult,
    lock_mu_flag_threshold,
    run_sweep_cell,
)
from datp.attacks.bounded_manifest import (
    BoundedSweepManifest,
    SweepResultRow,
)
from datp.attacks.sweep_matrix import (
    SweepCellSpec,
    enumerate_sweep_cells,
)
from datp.attacks.diagnostics import compute_blast_radius, compute_spillover
from datp.attacks.metrics import (
    compute_auroc_records,
    compute_victim_downstream_metrics,
)
from datp.attacks.score_loader import load_real_score_collection
from datp.attacks.run_manifest import ProvenanceRecord
from datp.attacks.score_containers import ScoreCollection
from datp.attacks.types import AurocSet
from datp.attacks.enums import objective_for_source
from datp.config.attack_config import CalibrationPoisoningConfig
from datp.config.stages import ExperimentStage
from datp.core.seed_sequence import derive_seed_record

_REPOSITORY_NAME: str = "datp-calibration-poisoning"


def _auroc_invariant(result: SweepCellResult) -> bool:
    clean = result.clean_metrics.auroc_records
    poisoned = result.poisoned_metrics.auroc_records
    return all(
        clean.for_client(record.client_id).auroc
        == poisoned.for_client(record.client_id).auroc
        for record in clean.records
    )


def _row_for_cell(
    collection: ScoreCollection,
    spec: SweepCellSpec,
    *,
    mu_flag_threshold: float,
    auroc_set: AurocSet,
) -> SweepResultRow:
    result = run_sweep_cell(
        spec,
        config=SweepCellConfig(
            collection=collection,
            mu_flag_threshold=mu_flag_threshold,
            auroc_set=auroc_set,
        ),
    )
    entry = result.poisoned_metrics.delta_tau[spec.victim_id]
    blast = compute_blast_radius(result.poisoned_metrics, victim_id=spec.victim_id)
    spill = compute_spillover(result.poisoned_metrics, victim_id=spec.victim_id)
    seed_record = derive_seed_record(
        spec.seed_pair,
        client_idx=collection.client_index(spec.victim_id),
        scope_idx=0,
    )
    victim_scores = collection.for_client(spec.victim_id)
    # entry.tau_clean and entry.tau_pois come from ThresholdPairBase.thresholds_clean
    # and thresholds_pois respectively — derived from clean and poisoned calibration sets.
    downstream = compute_victim_downstream_metrics(
        clean_threshold=entry.tau_clean,
        poisoned_threshold=entry.tau_pois,
        client_scores=victim_scores,
    )
    return SweepResultRow(
        policy=spec.policy,
        source=spec.source,
        objective=objective_for_source(spec.source),
        fraction=spec.fraction,
        target_scope=spec.target_scope,
        victim_id=spec.victim_id,
        training_seed=spec.training_seed,
        poisoning_seed=spec.poisoning_seed,
        seed_record=seed_record,
        delta_tau=entry.delta_tau,
        delta_tau_rel=entry.delta_tau_rel,
        is_victim_significant=entry.is_significant,
        cv_fpr=result.poisoned_metrics.fleet_fpr.cv_fpr,
        mean_fpr=result.poisoned_metrics.fleet_fpr.mean_fpr,
        coverage_ratio=result.poisoned_metrics.fleet_fpr.coverage_ratio,
        n_eligible=result.poisoned_metrics.fleet_fpr.n_eligible,
        mu_flag_triggered=result.poisoned_metrics.fleet_fpr.mu_flag_triggered,
        auroc_invariant=_auroc_invariant(result),
        blast_fraction=blast.blast_fraction,
        n_blast_significant=blast.n_significant,
        n_spillover=spill.n_spillover,
        n_non_victims=spill.n_non_victims,
        victim_tpr_clean=downstream.tpr_clean,
        victim_tpr_poisoned=downstream.tpr_poisoned,
        victim_delta_tpr=downstream.delta_tpr,
        victim_ba_clean=downstream.ba_clean,
        victim_ba_poisoned=downstream.ba_poisoned,
        victim_delta_ba=downstream.delta_ba,
        victim_macro_f1_clean=downstream.macro_f1_clean,
        victim_macro_f1_poisoned=downstream.macro_f1_poisoned,
        victim_delta_macro_f1=downstream.delta_macro_f1,
    )


def execute_bounded_sweep(
    base_dir: Path,
    config: CalibrationPoisoningConfig,
) -> BoundedSweepManifest:
    """Execute the locked bounded matrix and return the assembled manifest.

    Loads one real score collection per training seed, locks
    ``mu_flag_threshold`` from that seed's clean GLOBAL_THRESHOLD fleet FPR before any
    poisoned cell, and reuses it unmodified across every cell for that seed.
    Does not write to disk; callers persist via ``write_bounded_sweep_manifest``.
    """
    collections: dict[int, ScoreCollection] = {}
    mu_flag_by_seed: dict[int, float] = {}
    auroc_by_seed: dict[int, AurocSet] = {}
    victims_by_seed: dict[int, Sequence[str]] = {}

    for training_seed in config.seeds.training:
        collection = load_real_score_collection(
            stage=ExperimentStage.NBAIOT_MAIN, seed=training_seed, base_dir=base_dir
        )
        collections[training_seed] = collection
        mu_flag_by_seed[training_seed] = lock_mu_flag_threshold(collection)
        auroc_by_seed[training_seed] = compute_auroc_records(collection)
        victims_by_seed[training_seed] = collection.eligible_ids

    cells = enumerate_sweep_cells(victims_by_seed, config)
    rows = [
        _row_for_cell(
            collections[spec.training_seed],
            spec,
            mu_flag_threshold=mu_flag_by_seed[spec.training_seed],
            auroc_set=auroc_by_seed[spec.training_seed],
        )
        for spec in cells
    ]

    provenance = ProvenanceRecord(local_epochs=1, repository=_REPOSITORY_NAME)
    return BoundedSweepManifest(
        generated_at_utc=datetime.now(UTC).isoformat(),
        provenance=provenance,
        policies=config.policies,
        sources=config.sources,
        fractions=config.fractions,
        training_seeds=config.seeds.training,
        poisoning_seeds=config.seeds.poisoning,
        mu_flag_threshold_by_training_seed=mu_flag_by_seed,
        n_cells=len(rows),
        results=tuple(rows),
    )


def write_bounded_sweep_manifest(base_dir: Path) -> Path:
    """Run the bounded sweep and write the manifest to its canonical path.

    Returns the path written (``PoisonLayout.nbaiot_main_manifest()``).
    """
    config = CalibrationPoisoningConfig.for_bounded_sweep()
    manifest = execute_bounded_sweep(base_dir=base_dir, config=config)
    layout = PoisonLayout(base_dir=base_dir)
    out_path = layout.nbaiot_main_manifest()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return out_path
