"""Bounded N-BaIoT execution .

Single owner of the end-to-end bounded run: loads each training seed's
real score collection once, locks ``mu_flag_threshold`` per seed before any
poisoned cell for that seed, sweeps the locked 1620-cell matrix, and
assembles the single ``nbaiot_bounded_sweep_manifest.json`` artifact. This is the only
path that should ever produce that file — diagnostic/ad hoc scripts must not
duplicate this orchestration.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from datp.artifacts.poison_layout import PoisonLayout
from datp.attacks.constants import (
    BOUNDED_SWEEP_FRACTIONS,
    BOUNDED_SWEEP_SOURCES,
    DEFAULT_POLICIES,
    POISONING_SEEDS,
    TRAINING_SEEDS,
)
from datp.attacks.bounded_sweep_cell import (
    SweepCellResult,
    lock_mu_flag_threshold,
    run_sweep_cell,
)
from datp.attacks.bounded_sweep_manifest import (
    BoundedSweepManifest,
    BoundedSweepResultRow,
)
from datp.attacks.bounded_sweep_matrix import (
    SweepCellSpec,
    enumerate_bounded_sweep_matrix,
)
from datp.attacks.diagnostics import compute_blast_radius, compute_spillover
from datp.attacks.metric_engine import compute_auroc_records
from datp.attacks.real_score_loader import load_real_score_collection
from datp.attacks.run_manifest import ProvenanceRecord
from datp.attacks.score_containers import ScoreCollection
from datp.attacks.types import AurocSet
from datp.attacks.enums import objective_for_source
from datp.core.enums import Regime
from datp.config.attack_config import CalibrationPoisoningConfig
from datp.attacks.enums import (
    AttackerObjective,
    PoisoningKnowledge,
    PoisoningTargetScope,
)
from datp.experiments.enums import ExperimentScale
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
) -> BoundedSweepResultRow:
    result = run_sweep_cell(
        spec,
        collection,
        mu_flag_threshold=mu_flag_threshold,
        auroc_set=auroc_set,
    )
    entry = result.poisoned_metrics.delta_tau[spec.victim_id]
    blast = compute_blast_radius(result.poisoned_metrics, victim_id=spec.victim_id)
    spill = compute_spillover(result.poisoned_metrics, victim_id=spec.victim_id)
    seed_record = derive_seed_record(
        spec.seed_pair,
        client_idx=collection.client_index(spec.victim_id),
        scope_idx=0,
    )
    return BoundedSweepResultRow(
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
    )


def run_nbaiot_bounded_sweep(
    base_dir: Path,
    config: CalibrationPoisoningConfig | None = None,
) -> BoundedSweepManifest:
    """Execute the locked bounded matrix and return the assembled manifest.

    Loads one real score collection per training seed, locks
    ``mu_flag_threshold`` from that seed's clean B1 fleet FPR before any
    poisoned cell, and reuses it unmodified across every cell for that seed.
    Does not write to disk; callers persist via ``write_nbaiot_bounded_sweep_manifest``.
    """
    # Guard: validates all locked grid parameters against the scientific protocol
    # via CalibrationPoisoningConfig validators. Any drift in locked constants
    # (fractions out of [0,1], B4 k≠3, seed-pool mismatch, wrong injection rule)
    # raises here before any score data is loaded.
    if config is None:
        config = CalibrationPoisoningConfig(
            policy=DEFAULT_POLICIES[0],
            objective=AttackerObjective.THRESHOLD_RAISE,
            source=BOUNDED_SWEEP_SOURCES[0],
            knowledge=PoisoningKnowledge.GRAY_BOX_SCORE_ACCESS,
            target_scope=PoisoningTargetScope.SINGLE_CLIENT,
            scale=ExperimentScale.BOUNDED,
        )
    collections: dict[int, ScoreCollection] = {}
    mu_flag_by_seed: dict[int, float] = {}
    auroc_by_seed: dict[int, AurocSet] = {}
    victims_by_seed: dict[int, Sequence[str]] = {}

    for training_seed in config.seeds.training:
        collection = load_real_score_collection(
            regime=Regime.A, seed=training_seed, base_dir=base_dir
        )
        collections[training_seed] = collection
        mu_flag_by_seed[training_seed] = lock_mu_flag_threshold(collection)
        auroc_by_seed[training_seed] = compute_auroc_records(collection)
        victims_by_seed[training_seed] = collection.eligible_ids

    cells = enumerate_bounded_sweep_matrix(victims_by_seed)
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
        policies=DEFAULT_POLICIES,
        sources=BOUNDED_SWEEP_SOURCES,
        fractions=BOUNDED_SWEEP_FRACTIONS,
        training_seeds=TRAINING_SEEDS,
        poisoning_seeds=POISONING_SEEDS,
        mu_flag_threshold_by_training_seed=mu_flag_by_seed,
        n_cells=len(rows),
        results=tuple(rows),
    )


def write_nbaiot_bounded_sweep_manifest(base_dir: Path) -> Path:
    """Run the bounded sweep and write the manifest to its canonical path.

    Returns the path written (``PoisonLayout.nbaiot_bounded_sweep_manifest()``).
    """
    manifest = run_nbaiot_bounded_sweep(base_dir=base_dir)
    layout = PoisonLayout(base_dir=base_dir)
    out_path = layout.nbaiot_bounded_sweep_manifest()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return out_path
