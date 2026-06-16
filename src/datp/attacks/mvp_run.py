"""Bounded N-BaIoT MVP execution (CP2-T044-authorized matrix, CP2-T045 run path).

Single owner of the end-to-end bounded-MVP run: loads each training seed's
real score collection once, locks ``mu_flag_threshold`` per seed before any
poisoned cell for that seed, sweeps the locked 1620-cell matrix, and
assembles the single ``nbaiot_mvp_manifest.json`` artifact. This is the only
path that should ever produce that file — diagnostic/ad hoc scripts must not
duplicate this orchestration.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from datp.artifacts.poison_layout import Cp2Layout
from datp.artifacts.poison_names import CP2_POISONING_SEEDS, CP2_TRAINING_SEEDS
from datp.attacks.diagnostics import compute_blast_radius, compute_spillover
from datp.attacks.metric_engine import Cp2AurocRecord, compute_auroc_records
from datp.attacks.mvp_manifest import Cp2MvpManifest, Cp2MvpResultRow
from datp.attacks.mvp_matrix import Cp2MvpCellSpec, enumerate_mvp_matrix
from datp.attacks.mvp_runner import MvpCellResult, lock_mu_flag_threshold, run_mvp_cell
from datp.attacks.poison_enums import CP2_DEFAULT_POLICIES, CP2_MVP_FRACTIONS, CP2_MVP_SOURCES
from datp.attacks.real_score_loader import load_real_score_collection
from datp.attacks.run_manifest import Cp2ProvenanceRecord, Cp2SeedRecordModel
from datp.attacks.score_containers import Cp2ScoreCollection
from datp.attacks.source_strategies import objective_for_source
from datp.core.enums import Regime
from datp.core.seed_sequence import derive_cp2_seed_record

_REPOSITORY_NAME: str = "datp-calibration-poisoning"


def _client_idx(collection: Cp2ScoreCollection, client_id: str) -> int:
    return collection.all_ids.index(client_id)


def _auroc_invariant(result: MvpCellResult) -> bool:
    clean = result.clean_metrics.auroc_records
    poisoned = result.poisoned_metrics.auroc_records
    return all(clean[cid].auroc == poisoned[cid].auroc for cid in clean)


def _row_for_cell(
    collection: Cp2ScoreCollection,
    spec: Cp2MvpCellSpec,
    *,
    mu_flag_threshold: float,
    auroc_records: dict[str, Cp2AurocRecord],
) -> Cp2MvpResultRow:
    result = run_mvp_cell(
        collection,
        victim_id=spec.victim_id,
        policy=spec.policy,
        source=spec.source,
        fraction=spec.fraction,
        training_seed=spec.training_seed,
        poisoning_seed=spec.poisoning_seed,
        mu_flag_threshold=mu_flag_threshold,
        auroc_records=auroc_records,
    )
    entry = result.poisoned_metrics.delta_tau[spec.victim_id]
    blast = compute_blast_radius(result.poisoned_metrics, victim_id=spec.victim_id)
    spill = compute_spillover(result.poisoned_metrics, victim_id=spec.victim_id)
    seed_record = Cp2SeedRecordModel.from_record(
        derive_cp2_seed_record(
            training_seed=spec.training_seed,
            poisoning_seed=spec.poisoning_seed,
            client_idx=_client_idx(collection, spec.victim_id),
            scope_idx=0,
        )
    )
    return Cp2MvpResultRow(
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


def run_nbaiot_mvp(*, base_dir: Path) -> Cp2MvpManifest:
    """Execute the locked bounded-MVP matrix and return the assembled manifest.

    Loads one real score collection per training seed, locks
    ``mu_flag_threshold`` from that seed's clean B1 fleet FPR before any
    poisoned cell, and reuses it unmodified across every cell for that seed.
    Does not write to disk; callers persist via ``write_nbaiot_mvp_manifest``.
    """
    collections: dict[int, Cp2ScoreCollection] = {}
    mu_flag_by_seed: dict[int, float] = {}
    auroc_by_seed: dict[int, dict[str, Cp2AurocRecord]] = {}
    victims_by_seed: dict[int, Sequence[str]] = {}

    for training_seed in CP2_TRAINING_SEEDS:
        collection = load_real_score_collection(
            regime=Regime.A, seed=training_seed, base_dir=base_dir
        )
        collections[training_seed] = collection
        mu_flag_by_seed[training_seed] = lock_mu_flag_threshold(collection)
        auroc_by_seed[training_seed] = compute_auroc_records(collection)
        victims_by_seed[training_seed] = collection.eligible_ids

    cells = enumerate_mvp_matrix(victims_by_seed)
    rows = [
        _row_for_cell(
            collections[spec.training_seed],
            spec,
            mu_flag_threshold=mu_flag_by_seed[spec.training_seed],
            auroc_records=auroc_by_seed[spec.training_seed],
        )
        for spec in cells
    ]

    provenance = Cp2ProvenanceRecord(local_epochs=1, repository=_REPOSITORY_NAME)
    return Cp2MvpManifest(
        generated_at_utc=datetime.now(UTC).isoformat(),
        provenance=provenance,
        policies=CP2_DEFAULT_POLICIES,
        sources=CP2_MVP_SOURCES,
        fractions=CP2_MVP_FRACTIONS,
        training_seeds=CP2_TRAINING_SEEDS,
        poisoning_seeds=CP2_POISONING_SEEDS,
        mu_flag_threshold_by_training_seed=mu_flag_by_seed,
        n_cells=len(rows),
        results=tuple(rows),
    )


def write_nbaiot_mvp_manifest(base_dir: Path) -> Path:
    """Run the bounded MVP and write the manifest to its canonical path.

    Returns the path written (``Cp2Layout.nbaiot_mvp_manifest()``).
    """
    manifest = run_nbaiot_mvp(base_dir=base_dir)
    layout = Cp2Layout(base_dir=base_dir)
    out_path = layout.nbaiot_mvp_manifest()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return out_path
