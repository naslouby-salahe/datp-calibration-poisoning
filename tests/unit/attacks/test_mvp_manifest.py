"""Unit tests for the bounded N-BaIoT MVP manifest schema (CP2-T045)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from datp.attacks.mvp_manifest import Cp2MvpManifest, Cp2MvpResultRow
from datp.attacks.poison_enums import (
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ThresholdPolicy,
)
from datp.attacks.run_manifest import Cp2ProvenanceRecord, Cp2SeedRecordModel
from datp.core.seed_sequence import derive_cp2_seed_record


def _row(training_seed: int = 0, poisoning_seed: int = 100) -> Cp2MvpResultRow:
    seed_record = Cp2SeedRecordModel.from_record(
        derive_cp2_seed_record(
            training_seed=training_seed,
            poisoning_seed=poisoning_seed,
            client_idx=0,
            scope_idx=0,
        )
    )
    return Cp2MvpResultRow(
        policy=ThresholdPolicy.B1_GLOBAL,
        source=PoisoningSourceStrategy.RANDOM_BENIGN,
        objective=None,
        fraction=0.0,
        target_scope=PoisoningTargetScope.SINGLE_CLIENT,
        victim_id="c0",
        training_seed=training_seed,
        poisoning_seed=poisoning_seed,
        seed_record=seed_record,
        delta_tau=0.0,
        delta_tau_rel=0.0,
        is_victim_significant=False,
        cv_fpr=0.1,
        mean_fpr=0.01,
        coverage_ratio=1.0,
        n_eligible=9,
        mu_flag_triggered=False,
        auroc_invariant=True,
        blast_fraction=0.0,
        n_blast_significant=0,
        n_spillover=0,
        n_non_victims=8,
    )


def _manifest(**overrides: object) -> Cp2MvpManifest:
    base: dict[str, object] = dict(
        generated_at_utc="2026-06-16T00:00:00+00:00",
        provenance=Cp2ProvenanceRecord(
            local_epochs=1, repository="datp-calibration-poisoning"
        ),
        policies=(ThresholdPolicy.B1_GLOBAL,),
        sources=(PoisoningSourceStrategy.RANDOM_BENIGN,),
        fractions=(0.0,),
        training_seeds=(0,),
        poisoning_seeds=(100,),
        mu_flag_threshold_by_training_seed={0: 0.005},
        n_cells=1,
        results=(_row(),),
    )
    base.update(overrides)
    return Cp2MvpManifest(**base)  # type: ignore[arg-type]


def test_manifest_round_trips_through_json():
    manifest = _manifest()
    restored = Cp2MvpManifest.model_validate_json(manifest.model_dump_json())
    assert restored == manifest


def test_manifest_rejects_n_cells_mismatch():
    with pytest.raises(ValidationError):
        _manifest(n_cells=2)


def test_manifest_rejects_unpaired_seed_pools():
    with pytest.raises(ValidationError):
        _manifest(training_seeds=(0, 1), poisoning_seeds=(100,))


def test_manifest_rejects_missing_mu_flag_entry():
    with pytest.raises(ValidationError):
        _manifest(mu_flag_threshold_by_training_seed={})


def test_manifest_is_frozen():
    manifest = _manifest()
    with pytest.raises(ValidationError):
        manifest.n_cells = 99  # type: ignore[misc]
