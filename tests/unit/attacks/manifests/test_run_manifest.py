"""Tests verifying RunManifest schema structures, seed derivation, and validation constraints."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from datp.attacks.enums import SplitSemantics
from datp.attacks.manifests.run_manifest import ProvenanceRecord
from datp.core.seeds import SeedPair, SeedRecord


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
    return SeedRecord(
        pair=SeedPair(training_seed=training_seed, poisoning_seed=poisoning_seed),
        client_idx=client_idx,
        scope_idx=scope_idx,
    )


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
        """Verify the default split semantics use the canonical enum."""
        prov = _valid_provenance()
        assert (
            prov.split_semantics
            is SplitSemantics.CHRONOLOGICAL_BENIGN_ONLY_60_1_20_1_18
        )

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
