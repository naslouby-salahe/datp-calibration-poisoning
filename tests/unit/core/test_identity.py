from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

import pytest

from datp.config.stages import ExperimentStage
from datp.core.identity import (
    PolicyRunId,
    TrainingCellId,
    make_run_id,
    seed_segment,
)

_STAGE = ExperimentStage.NBAIOT_MAIN


class TestTrainingCellId:
    def test_label_includes_stage_and_seed(self) -> None:
        key = TrainingCellId(stage=_STAGE, seed=42)
        label = key.label()
        assert "nbaiot_main" in label
        assert "42" in label

    def test_immutable(self) -> None:
        key = TrainingCellId(stage=_STAGE, seed=42)
        with pytest.raises((AttributeError, TypeError)):
            key.stage = ExperimentStage.NBAIOT_MAIN  # type: ignore[misc]

    def test_equality(self) -> None:
        k1 = TrainingCellId(stage=_STAGE, seed=1)
        k2 = TrainingCellId(stage=_STAGE, seed=1)
        assert k1 == k2

    def test_inequality_different_seed(self) -> None:
        k1 = TrainingCellId(stage=_STAGE, seed=1)
        k2 = TrainingCellId(stage=_STAGE, seed=2)
        assert k1 != k2

    def test_hashable(self) -> None:
        k1 = TrainingCellId(stage=_STAGE, seed=1)
        k2 = TrainingCellId(stage=_STAGE, seed=2)
        s: set[TrainingCellId] = {k1, k2}
        assert len(s) == 2

    def test_stage_field(self) -> None:
        key = TrainingCellId(stage=_STAGE, seed=1)
        assert key.stage == _STAGE

    def test_used_as_dict_key(self) -> None:
        k1 = TrainingCellId(stage=_STAGE, seed=0)
        k2 = TrainingCellId(stage=_STAGE, seed=0)
        d: dict[TrainingCellId, str] = {k1: "shared"}
        assert d[k2] == "shared"


class TestPolicyRunId:
    def test_construction_and_properties(self) -> None:
        cell = TrainingCellId(stage=_STAGE, seed=42)
        run = PolicyRunId(cell=cell, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        assert run.cell is cell
        assert run.policy == ThresholdPolicy.GLOBAL_THRESHOLD

    def test_equality(self) -> None:
        cell = TrainingCellId(stage=_STAGE, seed=1)
        r1 = PolicyRunId(cell=cell, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        r2 = PolicyRunId(cell=cell, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        assert r1 == r2

    def test_inequality_different_policy(self) -> None:
        cell = TrainingCellId(stage=_STAGE, seed=1)
        r1 = PolicyRunId(cell=cell, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        r2 = PolicyRunId(cell=cell, policy=ThresholdPolicy.LOCAL_THRESHOLD)
        assert r1 != r2

    def test_inequality_different_cell(self) -> None:
        c1 = TrainingCellId(stage=_STAGE, seed=1)
        c2 = TrainingCellId(stage=_STAGE, seed=2)
        r1 = PolicyRunId(cell=c1, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        r2 = PolicyRunId(cell=c2, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        assert r1 != r2

    def test_immutable(self) -> None:
        cell = TrainingCellId(stage=_STAGE, seed=42)
        run = PolicyRunId(cell=cell, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        with pytest.raises((AttributeError, TypeError)):
            run.policy = ThresholdPolicy.LOCAL_THRESHOLD  # type: ignore[misc]

    def test_hashable(self) -> None:
        cell = TrainingCellId(stage=_STAGE, seed=1)
        r1 = PolicyRunId(cell=cell, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        r2 = PolicyRunId(cell=cell, policy=ThresholdPolicy.LOCAL_THRESHOLD)
        s: set[PolicyRunId] = {r1, r2}
        assert len(s) == 2

    def test_label_includes_stage_policy_seed(self) -> None:
        cell = TrainingCellId(stage=_STAGE, seed=42)
        run = PolicyRunId(cell=cell, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        label = run.label()
        assert "nbaiot_main" in label
        assert "global_threshold" in label
        assert "42" in label

    def test_audit_id(self) -> None:
        cell = TrainingCellId(stage=_STAGE, seed=42)
        run = PolicyRunId(cell=cell, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        assert run.audit_id() == "nbaiot_main_global_threshold_seed42"


class TestSeedSegment:
    def test_returns_seed_prefix(self) -> None:
        assert seed_segment(42) == "seed_42"

    def test_zero_seed(self) -> None:
        assert seed_segment(0) == "seed_0"


class TestMakeRunId:
    def test_includes_stage_and_seed(self) -> None:
        rid = make_run_id(_STAGE, seed=42)
        assert rid.startswith("nbaiot_main_seed42_")

    def test_no_alpha_in_run_id(self) -> None:
        rid = make_run_id(_STAGE, seed=42)
        assert "alpha" not in rid

    def test_different_seeds_produce_different_prefixes(self) -> None:
        r1 = make_run_id(_STAGE, seed=0)
        r2 = make_run_id(_STAGE, seed=1)
        assert r1.startswith("nbaiot_main_seed0_")
        assert r2.startswith("nbaiot_main_seed1_")
