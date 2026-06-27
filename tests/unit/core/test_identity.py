"""Tests verifying canonical identity containers and run ID builders."""

from __future__ import annotations
from datp.core.enums import ThresholdPolicy

import pytest

from datp.config.models import ExperimentStage
from datp.core.identity import (
    PolicyRunId,
    TrainingCellId,
    make_run_id,
    seed_segment,
)

_STAGE = ExperimentStage.NBAIOT_MAIN


class TestTrainingCellId:
    """Tests verifying representation and invariants of training cell identifiers."""

    def test_label_includes_stage_and_seed(self) -> None:
        """Verify that training cell label formats stage name and seed correctly."""
        key = TrainingCellId(stage=_STAGE, seed=42)
        label = key.label()
        assert "nbaiot_main" in label
        assert "42" in label

    def test_immutable(self) -> None:
        """Confirm TrainingCellId is frozen and cannot be mutated."""
        key = TrainingCellId(stage=_STAGE, seed=42)
        with pytest.raises((AttributeError, TypeError)):
            setattr(key, "stage", ExperimentStage.NBAIOT_MAIN)

    def test_equality(self) -> None:
        """Verify value-based equality for identical training cell inputs."""
        k1 = TrainingCellId(stage=_STAGE, seed=1)
        k2 = TrainingCellId(stage=_STAGE, seed=1)
        assert k1 == k2

    def test_inequality_different_seed(self) -> None:
        """Verify value-based inequality for training cells with different seeds."""
        k1 = TrainingCellId(stage=_STAGE, seed=1)
        k2 = TrainingCellId(stage=_STAGE, seed=2)
        assert k1 != k2

    def test_hashable(self) -> None:
        """Verify TrainingCellId instances are hashable and can form sets."""
        k1 = TrainingCellId(stage=_STAGE, seed=1)
        k2 = TrainingCellId(stage=_STAGE, seed=2)
        s: set[TrainingCellId] = {k1, k2}
        assert len(s) == 2

    def test_stage_field(self) -> None:
        """Confirm stage property exposes the correct experiment stage enum."""
        key = TrainingCellId(stage=_STAGE, seed=1)
        assert key.stage == _STAGE

    def test_used_as_dict_key(self) -> None:
        """Confirm TrainingCellId is hashable for use as dictionary keys."""
        k1 = TrainingCellId(stage=_STAGE, seed=0)
        k2 = TrainingCellId(stage=_STAGE, seed=0)
        d: dict[TrainingCellId, str] = {k1: "shared"}
        assert d[k2] == "shared"


class TestPolicyRunId:
    """Tests verifying representation and invariants of policy run identifiers."""

    def test_construction_and_properties(self) -> None:
        """Confirm PolicyRunId maps back to its training cell and policy fields."""
        cell = TrainingCellId(stage=_STAGE, seed=42)
        run = PolicyRunId(cell=cell, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        assert run.cell is cell
        assert run.policy == ThresholdPolicy.GLOBAL_THRESHOLD

    def test_equality(self) -> None:
        """Verify value-based equality for identical policy runs."""
        cell = TrainingCellId(stage=_STAGE, seed=1)
        r1 = PolicyRunId(cell=cell, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        r2 = PolicyRunId(cell=cell, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        assert r1 == r2

    def test_inequality_different_policy(self) -> None:
        """Verify value-based inequality for runs under different policies."""
        cell = TrainingCellId(stage=_STAGE, seed=1)
        r1 = PolicyRunId(cell=cell, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        r2 = PolicyRunId(cell=cell, policy=ThresholdPolicy.LOCAL_THRESHOLD)
        assert r1 != r2

    def test_inequality_different_cell(self) -> None:
        """Verify value-based inequality for runs spanning different cells."""
        c1 = TrainingCellId(stage=_STAGE, seed=1)
        c2 = TrainingCellId(stage=_STAGE, seed=2)
        r1 = PolicyRunId(cell=c1, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        r2 = PolicyRunId(cell=c2, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        assert r1 != r2

    def test_immutable(self) -> None:
        """Confirm PolicyRunId is frozen and cannot be mutated."""
        cell = TrainingCellId(stage=_STAGE, seed=42)
        run = PolicyRunId(cell=cell, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        with pytest.raises((AttributeError, TypeError)):
            setattr(run, "policy", ThresholdPolicy.LOCAL_THRESHOLD)

    def test_hashable(self) -> None:
        """Verify PolicyRunId instances are hashable and can form sets."""
        cell = TrainingCellId(stage=_STAGE, seed=1)
        r1 = PolicyRunId(cell=cell, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        r2 = PolicyRunId(cell=cell, policy=ThresholdPolicy.LOCAL_THRESHOLD)
        s: set[PolicyRunId] = {r1, r2}
        assert len(s) == 2

    def test_label_includes_stage_policy_seed(self) -> None:
        """Verify run label formatting embeds stage name, policy string, and seed."""
        cell = TrainingCellId(stage=_STAGE, seed=42)
        run = PolicyRunId(cell=cell, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        label = run.label()
        assert "nbaiot_main" in label
        assert "global_threshold" in label
        assert "42" in label

    def test_audit_id(self) -> None:
        """Verify generated audit ID string matches the canonical format."""
        cell = TrainingCellId(stage=_STAGE, seed=42)
        run = PolicyRunId(cell=cell, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        assert run.audit_id() == "nbaiot_main_global_threshold_seed42"


class TestSeedSegment:
    """Tests verifying seed directory path segments formatting."""

    def test_returns_seed_prefix(self) -> None:
        """Confirm positive seed formatting returns the correct directory segment prefix."""
        assert seed_segment(42) == "seed_42"

    def test_zero_seed(self) -> None:
        """Confirm seed zero directory segment is correctly formatted."""
        assert seed_segment(0) == "seed_0"


class TestMakeRunId:
    """Tests verifying dynamic run ID generator logic."""

    def test_includes_stage_and_seed(self) -> None:
        """Verify generated run ID string contains the stage prefix and seed."""
        rid = make_run_id(_STAGE, seed=42)
        assert rid.startswith("nbaiot_main_seed42_")

    def test_no_alpha_in_run_id(self) -> None:
        """Verify generated run ID does not contain alpha parameter naming by default."""
        rid = make_run_id(_STAGE, seed=42)
        assert "alpha" not in rid

    def test_different_seeds_produce_different_prefixes(self) -> None:
        """Verify different seed inputs generate run IDs with distinct prefixes."""
        r1 = make_run_id(_STAGE, seed=0)
        r2 = make_run_id(_STAGE, seed=1)
        assert r1.startswith("nbaiot_main_seed0_")
        assert r2.startswith("nbaiot_main_seed1_")
