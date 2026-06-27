"""Tests verifying RunManifest schema structures, seed derivation, and validation constraints."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from datp.attacks.enums import (
    AttackerObjective,
    CalibrationInjectionRule,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
)
from datp.attacks.manifests.run_manifest import (
    RESERVOIR_MODE,
    SPLIT_SEMANTICS,
    ProvenanceRecord,
    RunManifest,
)
from datp.config.models import ExperimentStage
from datp.core.enums import ThresholdPolicy
from datp.core.seeds import SeedPair, SeedRecord, derive_seed_record


def _valid_provenance(**overrides: Any) -> ProvenanceRecord:
    """Helper to build a valid ProvenanceRecord instance."""
    defaults: dict[str, Any] = {
        "local_epochs": 1,
        "repository": "/home/user/datp-calibration-poisoning",
    }
    defaults.update(overrides)
    return ProvenanceRecord(**defaults)


def _seed_record_model(
    training_seed: int = 0,
    poisoning_seed: int = 100,
    client_idx: int = 0,
    scope_idx: int = 0,
) -> SeedRecord:
    """Helper to build standard SeedRecord instances."""
    return derive_seed_record(
        SeedPair(training_seed=training_seed, poisoning_seed=poisoning_seed),
        client_idx=client_idx,
        scope_idx=scope_idx,
    )


def _valid_manifest(**overrides: Any) -> RunManifest:
    """Helper to build a valid RunManifest mock instance."""
    defaults: dict[str, Any] = {
        "dataset": "nbaiot",
        "stage": ExperimentStage.NBAIOT_MAIN,
        "policy": ThresholdPolicy.GLOBAL_THRESHOLD,
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
    return RunManifest(**defaults)


class TestProvenanceRecord:
    """Tests verifying constraints and default fields of ProvenanceRecord."""

    def test_e1_accepted(self) -> None:
        """Verify that local_epochs=1 is successfully accepted."""
        prov = _valid_provenance(local_epochs=1)
        assert prov.local_epochs == 1

    def test_e5_rejected(self) -> None:
        """Verify that local_epochs values greater than 1 raise ValidationError."""
        with pytest.raises(ValidationError, match="E=5 rejected"):
            _valid_provenance(local_epochs=5)

    def test_e2_rejected(self) -> None:
        """Verify that local_epochs=2 raises ValidationError."""
        with pytest.raises(ValidationError, match="E=2 rejected"):
            _valid_provenance(local_epochs=2)

    def test_default_split_semantics(self) -> None:
        """Verify default split_semantics defaults matches the global constant SPLIT_SEMANTICS."""
        prov = _valid_provenance()
        assert prov.split_semantics == SPLIT_SEMANTICS

    def test_pipeline_generated_true_by_default(self) -> None:
        """Verify that pipeline_generated is True by default."""
        prov = _valid_provenance()
        assert prov.pipeline_generated is True

    def test_checkpoint_round_optional(self) -> None:
        """Verify that optional checkpoint_round is correctly initialized."""
        prov = _valid_provenance(checkpoint_round=42)
        assert prov.checkpoint_round == 42

    def test_extra_fields_forbidden(self) -> None:
        """Verify that passing undefined fields to the model raises ValidationError."""
        with pytest.raises(ValidationError, match="extra"):
            _valid_provenance(bogus=1)


class TestSeedRecord:
    """Tests verifying properties of SeedRecord fields."""

    def test_fields_and_entropy(self) -> None:
        """Verify fields initialization and derived seed entropy tuple."""
        original = SeedRecord(
            pair=SeedPair(training_seed=1, poisoning_seed=101),
            client_idx=3,
            scope_idx=0,
        )
        assert original.training_seed == 1
        assert original.poisoning_seed == 101
        assert original.client_idx == 3
        assert original.scope_idx == 0
        assert original.entropy == (1, 101, 3, 0)


class TestRunManifest:
    """Tests verifying schemas, validation checks, and default parameters of RunManifest."""

    def test_valid_manifest_constructed(self) -> None:
        """Verify that a valid RunManifest initializes schema_version and default injection rules correctly."""
        m = _valid_manifest()
        assert m.schema_version == "1"
        assert m.dataset == "nbaiot"
        assert m.mu_flag_threshold is None
        assert m.injection_rule == CalibrationInjectionRule.REPLACE_FIXED_BUDGET

    def test_default_reservoir_mode(self) -> None:
        """Verify that reservoir_mode maps to the expected global setting."""
        m = _valid_manifest()
        assert m.reservoir_mode == RESERVOIR_MODE
        assert "victim_local" in m.reservoir_mode

    def test_mu_flag_threshold_can_be_set(self) -> None:
        """Verify that float-valued mu_flag_threshold can be set and accessed."""
        m = _valid_manifest(mu_flag_threshold=0.025)
        assert m.mu_flag_threshold == pytest.approx(0.025)

    def test_e5_provenance_rejected(self) -> None:
        """Verify that validation rejects nested provenance objects failing local_epochs checks."""
        with pytest.raises(ValidationError, match="E=5 rejected"):
            _valid_manifest(provenance=_valid_provenance(local_epochs=5))

    def test_seed_record_embedded(self) -> None:
        """Verify that the embedded seed_record contains derived entropy values."""
        sr = _seed_record_model(training_seed=3, poisoning_seed=103)
        m = _valid_manifest(seed_record=sr)
        assert m.seed_record.training_seed == 3
        assert m.seed_record.poisoning_seed == 103
        assert m.seed_record.entropy == (3, 103, 0, 0)

    def test_frozen(self) -> None:
        """Verify that RunManifest models are frozen and raise ValidationError on attribute assignment."""
        m = _valid_manifest()
        with pytest.raises(ValidationError):
            m.dataset = "other"

    def test_extra_fields_forbidden(self) -> None:
        """Verify that passing undefined fields to RunManifest raises ValidationError."""
        with pytest.raises(ValidationError, match="extra"):
            _valid_manifest(bogus=1)
