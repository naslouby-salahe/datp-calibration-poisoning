"""Unit tests for the bounded N-BaIoT bounded sweep manifest schema ."""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from datp.attacks.bounded_sweep_manifest import (
    BoundedSweepManifest,
    BoundedSweepResultRow,
)
from datp.attacks.run_manifest import ProvenanceRecord
from datp.attacks.enums import (
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ThresholdPolicy,
)
from datp.core.seed_sequence import derive_seed_record
from datp.core.seeds import SeedPair


def _row(training_seed: int = 0, poisoning_seed: int = 100) -> BoundedSweepResultRow:
    seed_record = derive_seed_record(
        SeedPair(training_seed=training_seed, poisoning_seed=poisoning_seed),
        client_idx=0,
        scope_idx=0,
    )
    return BoundedSweepResultRow(
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


def _manifest(**overrides: object) -> BoundedSweepManifest:
    base: dict[str, object] = {
        "generated_at_utc": "2026-06-16T00:00:00+00:00",
        "provenance": ProvenanceRecord(
            local_epochs=1, repository="datp-calibration-poisoning"
        ),
        "policies": (ThresholdPolicy.B1_GLOBAL,),
        "sources": (PoisoningSourceStrategy.RANDOM_BENIGN,),
        "fractions": (0.0,),
        "training_seeds": (0,),
        "poisoning_seeds": (100,),
        "mu_flag_threshold_by_training_seed": {0: 0.005},
        "n_cells": 1,
        "results": (_row(),),
    }
    base.update(overrides)
    return BoundedSweepManifest(**base) # type: ignore[arg-type]


def test_manifest_round_trips_through_json():
    manifest = _manifest()
    restored = BoundedSweepManifest.model_validate_json(manifest.model_dump_json())
    assert restored == manifest


def test_undefined_cv_serializes_as_null_and_round_trips_to_nan():
    """Undefined CV(FPR) (NaN) serializes to JSON null, not 0.0, and reloads as NaN."""
    row = _row()
    undefined = row.model_copy(update={"cv_fpr": math.nan, "mean_fpr": 0.0})
    payload = undefined.model_dump_json()
    assert '"cv_fpr":null' in payload
    restored = BoundedSweepResultRow.model_validate_json(payload)
    assert math.isnan(restored.cv_fpr)
    assert not math.isclose(restored.cv_fpr, 0.0, abs_tol=1e-12)
    assert restored.mean_fpr == pytest.approx(0.0)


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
        manifest.n_cells = 99 # type: ignore[misc]
