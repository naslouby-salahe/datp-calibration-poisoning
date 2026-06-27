"""Tests verifying BoundedSweepManifest schemas, round-tripping, NaN serialization, and validation constraints."""

from __future__ import annotations

import math
from typing import Any

import pytest
from pydantic import ValidationError

from datp.attacks.enums import (
    AttackerObjective,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
)
from datp.attacks.manifests.bounded_sweep_manifest import (
    BoundedSweepManifest,
    BoundedSweepResultRow,
)
from datp.attacks.manifests.run_manifest import ProvenanceRecord
from datp.core.enums import ThresholdPolicy
from datp.core.provenance import REPOSITORY_NAME
from datp.core.seeds import SeedPair, derive_seed_record


def _row(training_seed: int = 0, poisoning_seed: int = 100) -> BoundedSweepResultRow:
    """Helper to build a complete BoundedSweepResultRow mock instance."""
    seed_record = derive_seed_record(
        SeedPair(training_seed=training_seed, poisoning_seed=poisoning_seed),
        client_idx=0,
        scope_idx=0,
    )
    return BoundedSweepResultRow(
        policy=ThresholdPolicy.GLOBAL_THRESHOLD,
        source=PoisoningSourceStrategy.RANDOM_BENIGN,
        objective=AttackerObjective.THRESHOLD_RAISE,
        fraction=0.0,
        target_scope=PoisoningTargetScope.SINGLE_CLIENT,
        victim_id="c0",
        training_seed=training_seed,
        poisoning_seed=poisoning_seed,
        seed_record=seed_record,
        delta_tau=0.0,
        delta_tau_rel=0.0,
        is_victim_significant=False,
        cv_fpr_clean=0.1,
        cv_fpr_poisoned=0.1,
        delta_cv_fpr=0.0,
        mean_fpr_clean=0.01,
        mean_fpr_poisoned=0.01,
        delta_mean_fpr=0.0,
        iqr_fpr_clean=0.02,
        iqr_fpr_poisoned=0.02,
        delta_iqr_fpr=0.0,
        max_min_fpr_clean=0.03,
        max_min_fpr_poisoned=0.03,
        delta_max_min_fpr=0.0,
        worst_client_fpr_clean=0.04,
        worst_client_fpr_poisoned=0.04,
        delta_worst_client_fpr=0.0,
        coverage_ratio=1.0,
        n_eligible=9,
        mu_flag_triggered=False,
        auroc_invariant=True,
        blast_fraction=0.0,
        n_blast_significant=0,
        n_spillover=0,
        n_non_victims=8,
        victim_tpr_clean=0.95,
        victim_tpr_poisoned=0.95,
        victim_delta_tpr=0.0,
        victim_ba_clean=0.9,
        victim_ba_poisoned=0.9,
        victim_delta_ba=0.0,
        victim_macro_f1_clean=0.92,
        victim_macro_f1_poisoned=0.92,
        victim_delta_macro_f1=0.0,
        cluster_delta_tau_agg=math.nan,
        cluster_delta_tau_churn=math.nan,
        cluster_delta_tau_frozen_scaler=math.nan,
        cluster_delta_tau_normalization_gap=math.nan,
        cluster_victim_effect=math.nan,
        cluster_non_victim_effect=math.nan,
    )


def _manifest(**overrides: Any) -> BoundedSweepManifest:
    """Helper to build BoundedSweepManifest mock instance configurations."""
    base: dict[str, Any] = {
        "generated_at_utc": "2026-06-16T00:00:00+00:00",
        "provenance": ProvenanceRecord(local_epochs=1, repository=REPOSITORY_NAME),
        "policies": (ThresholdPolicy.GLOBAL_THRESHOLD,),
        "sources": (PoisoningSourceStrategy.RANDOM_BENIGN,),
        "source_objective_pairs": ("random_benign+threshold_raise",),
        "fractions": (0.0,),
        "training_seeds": tuple(range(10)),
        "poisoning_seeds": tuple(range(100, 110)),
        "analysis_seeds": tuple(range(300, 310)),
        "config_hash": "config-hash",
        "artifact_provenance": {"source": "test"},
        "mu_flag_threshold_by_training_seed": dict.fromkeys(range(10), 0.005),
        "n_cells": 1,
        "results": (_row(),),
    }
    base.update(overrides)
    return BoundedSweepManifest(**base)


def test_manifest_round_trips_through_json() -> None:
    """Verify that BoundedSweepManifest parses successfully from serialized JSON output."""
    manifest = _manifest()
    restored = BoundedSweepManifest.model_validate_json(manifest.model_dump_json())
    assert restored == manifest


def test_undefined_cv_serializes_as_null_and_round_trips_to_nan() -> None:
    """Verify that NaN float values serialize to JSON null and round-trip back to NaN."""
    row = _row()
    undefined = row.model_copy(
        update={"cv_fpr_poisoned": math.nan, "mean_fpr_poisoned": 0.0}
    )
    payload = undefined.model_dump_json()
    assert '"cv_fpr_poisoned":null' in payload
    restored = BoundedSweepResultRow.model_validate_json(payload)
    assert math.isnan(restored.cv_fpr_poisoned)
    assert not math.isclose(restored.cv_fpr_poisoned, 0.0, abs_tol=1e-12)
    assert restored.mean_fpr_poisoned == pytest.approx(0.0)


def test_manifest_rejects_n_cells_mismatch() -> None:
    """Verify that manifest validation fails if n_cells differs from actual results length."""
    with pytest.raises(ValidationError):
        _manifest(n_cells=2)


def test_manifest_rejects_unpaired_seed_pools() -> None:
    """Verify validation fails if training and poisoning seed pool lengths mismatch."""
    with pytest.raises(ValidationError):
        _manifest(training_seeds=(0, 1), poisoning_seeds=(100,))


def test_manifest_rejects_five_seed_pools() -> None:
    """Verify validation fails if seed pools contain fewer than 10 required items."""
    with pytest.raises(ValidationError, match="0..9"):
        _manifest(
            training_seeds=tuple(range(5)),
            poisoning_seeds=tuple(range(100, 105)),
            analysis_seeds=tuple(range(300, 305)),
            mu_flag_threshold_by_training_seed=dict.fromkeys(range(5), 0.005),
        )


def test_manifest_rejects_missing_mu_flag_entry() -> None:
    """Verify validation fails if training seed mu thresholds map is missing keys."""
    with pytest.raises(ValidationError):
        _manifest(mu_flag_threshold_by_training_seed={})


def test_manifest_is_frozen() -> None:
    """Verify that BoundedSweepManifest models behave as frozen/read-only once built."""
    manifest = _manifest()
    with pytest.raises(ValidationError):
        manifest.n_cells = 99


def test_result_row_has_victim_tpr_fields() -> None:
    """Verify that BoundedSweepResultRow defines all expected victim True Positive Rate metrics."""
    row = _row()
    assert hasattr(row, "victim_tpr_clean")
    assert hasattr(row, "victim_tpr_poisoned")
    assert hasattr(row, "victim_delta_tpr")


def test_result_row_has_victim_ba_fields() -> None:
    """Verify that BoundedSweepResultRow defines all expected victim Balanced Accuracy metrics."""
    row = _row()
    assert hasattr(row, "victim_ba_clean")
    assert hasattr(row, "victim_ba_poisoned")
    assert hasattr(row, "victim_delta_ba")


def test_result_row_has_victim_macro_f1_fields() -> None:
    """Verify that BoundedSweepResultRow defines all expected victim Macro F1 metrics."""
    row = _row()
    assert hasattr(row, "victim_macro_f1_clean")
    assert hasattr(row, "victim_macro_f1_poisoned")
    assert hasattr(row, "victim_delta_macro_f1")


def test_victim_tpr_fields_are_floats() -> None:
    """Verify that TPR metrics fields are float-typed attributes."""
    row = _row()
    assert isinstance(row.victim_tpr_clean, float)
    assert isinstance(row.victim_tpr_poisoned, float)
    assert isinstance(row.victim_delta_tpr, float)


def test_victim_downstream_zero_fraction_deltas_are_zero() -> None:
    """Verify that a zero poisoning fraction yields downstream metric deltas of exactly 0.0."""
    row = _row()
    assert math.isclose(row.fraction, 0.0)
    assert row.victim_delta_tpr == pytest.approx(0.0)
    assert row.victim_delta_ba == pytest.approx(0.0)
    if not math.isnan(row.victim_delta_macro_f1):
        assert row.victim_delta_macro_f1 == pytest.approx(0.0)


def test_manifest_round_trips_victim_fields() -> None:
    """Verify that victim accuracy metric deltas round-trip correctly through JSON serialization."""
    manifest = _manifest()
    restored = BoundedSweepManifest.model_validate_json(manifest.model_dump_json())
    row = manifest.results[0]
    r_row = restored.results[0]
    assert row.victim_tpr_clean == pytest.approx(r_row.victim_tpr_clean)
    assert row.victim_ba_clean == pytest.approx(r_row.victim_ba_clean)
    assert row.victim_delta_tpr == pytest.approx(r_row.victim_delta_tpr)
