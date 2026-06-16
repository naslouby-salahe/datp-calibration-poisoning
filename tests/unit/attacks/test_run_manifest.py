"""Tests for run manifest schema."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from datp.attacks.poison_enums import (
    AttackerObjective,
    CalibrationInjectionRule,
    ExperimentScale,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ThresholdPolicy,
)
from datp.attacks.run_manifest import (
    RESERVOIR_MODE,
    SPLIT_SEMANTICS,
    ProvenanceRecord,
    RunManifest,
    SeedRecordModel,
)
from datp.core.seed_sequence import SeedRecord, derive_seed_record


def _valid_provenance(**overrides: object) -> ProvenanceRecord:
    defaults: dict[str, object] = {
        "local_epochs": 1,
        "repository": "/home/user/datp-calibration-poisoning",
    }
    defaults.update(overrides)
    return ProvenanceRecord(**defaults) # type: ignore[arg-type]


def _seed_record_model(
    training_seed: int = 0,
    poisoning_seed: int = 100,
    client_idx: int = 0,
    scope_idx: int = 0,
) -> SeedRecordModel:
    record = derive_seed_record(
        training_seed=training_seed,
        poisoning_seed=poisoning_seed,
        client_idx=client_idx,
        scope_idx=scope_idx,
    )
    return SeedRecordModel.from_record(record)


def _valid_manifest(**overrides: object) -> RunManifest:
    defaults: dict[str, object] = {
        "dataset": "nbaiot",
        "scale": ExperimentScale.BOUNDED,
        "policy": ThresholdPolicy.B1_GLOBAL,
        "objective": AttackerObjective.THRESHOLD_RAISE,
        "source": PoisoningSourceStrategy.RANDOM_BENIGN,
        "fraction": 0.10,
        "target_scope": PoisoningTargetScope.SINGLE_CLIENT,
        "training_seed": 0,
        "poisoning_seed": 100,
        "client_idx": 0,
        "scope_idx": 0,
        "provenance": _valid_provenance(),
        "mu_flag_threshold": None,
        "seed_record": _seed_record_model(),
        "generated_at_utc": "2026-06-16T00:00:00Z",
    }
    defaults.update(overrides)
    return RunManifest(**defaults) # type: ignore[arg-type]


class TestProvenanceRecord:
    def test_e1_accepted(self) -> None:
        prov = _valid_provenance(local_epochs=1)
        assert prov.local_epochs == 1

    def test_e5_rejected(self) -> None:
        with pytest.raises(ValidationError, match="E=5 rejected"):
            _valid_provenance(local_epochs=5)

    def test_e2_rejected(self) -> None:
        with pytest.raises(ValidationError, match="E="):
            _valid_provenance(local_epochs=2)

    def test_default_split_semantics(self) -> None:
        prov = _valid_provenance()
        assert prov.split_semantics == SPLIT_SEMANTICS

    def test_pipeline_generated_true_by_default(self) -> None:
        prov = _valid_provenance()
        assert prov.pipeline_generated is True

    def test_checkpoint_round_optional(self) -> None:
        prov = _valid_provenance(checkpoint_round=42)
        assert prov.checkpoint_round == 42

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            _valid_provenance(bogus=1) # type: ignore[call-arg]


class TestSeedRecordModel:
    def test_from_record_round_trip(self) -> None:
        original = SeedRecord(
            training_seed=1, poisoning_seed=101, client_idx=3, scope_idx=0
        )
        model = SeedRecordModel.from_record(original)
        assert model.training_seed == 1
        assert model.poisoning_seed == 101
        assert model.client_idx == 3
        assert model.scope_idx == 0
        assert model.entropy == (1, 101, 3, 0)

    def test_to_record_restores_seed_record(self) -> None:
        original = SeedRecord(
            training_seed=2, poisoning_seed=102, client_idx=5, scope_idx=1
        )
        model = SeedRecordModel.from_record(original)
        restored = model.to_record()
        assert restored.entropy == original.entropy


class TestRunManifest:
    def test_valid_manifest_constructed(self) -> None:
        m = _valid_manifest()
        assert m.schema_version == "1"
        assert m.dataset == "nbaiot"
        assert m.mu_flag_threshold is None
        assert m.injection_rule == CalibrationInjectionRule.REPLACE_FIXED_BUDGET

    def test_default_reservoir_mode(self) -> None:
        m = _valid_manifest()
        assert m.reservoir_mode == RESERVOIR_MODE
        assert "victim_local" in m.reservoir_mode

    def test_mu_flag_threshold_can_be_set(self) -> None:
        m = _valid_manifest(mu_flag_threshold=0.025)
        assert m.mu_flag_threshold == 0.025

    def test_e5_provenance_rejected(self) -> None:
        with pytest.raises(ValidationError, match="E=5 rejected"):
            _valid_manifest(provenance=_valid_provenance(local_epochs=5))

    def test_seed_record_embedded(self) -> None:
        sr = _seed_record_model(training_seed=3, poisoning_seed=103)
        m = _valid_manifest(seed_record=sr)
        assert m.seed_record.training_seed == 3
        assert m.seed_record.poisoning_seed == 103
        assert m.seed_record.entropy == (3, 103, 0, 0)

    def test_frozen(self) -> None:
        m = _valid_manifest()
        with pytest.raises(ValidationError):
            m.dataset = "other" # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            _valid_manifest(bogus=1) # type: ignore[call-arg]
