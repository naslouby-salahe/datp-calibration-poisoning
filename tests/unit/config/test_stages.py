"""Unit tests for stage configuration layout."""

from __future__ import annotations

import pytest

from datp.config.stages import (
    ExperimentStage,
    ExperimentStageConfig,
    all_stage_configs,
    get_stage_config,
)
from datp.core.poison_enums import ExperimentScale
from datp.data.catalog import DatasetID


class TestExperimentStage:
    def test_all_expected_stages_present(self) -> None:
        stages = set(ExperimentStage)
        assert ExperimentStage.COMMON in stages
        assert ExperimentStage.AUDIT_READONLY in stages
        assert ExperimentStage.NBAIOT_SMOKE in stages
        assert ExperimentStage.NBAIOT_BOUNDED in stages
        assert ExperimentStage.NBAIOT_FULL in stages
        assert ExperimentStage.CICIOT2023_STRETCH in stages
        assert ExperimentStage.PAPER_FIGURES in stages

    def test_stage_values_are_strings(self) -> None:
        for stage in ExperimentStage:
            assert isinstance(str(stage), str)


class TestGetStageConfig:
    def test_common_has_no_scale(self) -> None:
        cfg = get_stage_config(ExperimentStage.COMMON)
        assert cfg.scale is None

    def test_nbaiot_smoke_scale_is_smoke(self) -> None:
        cfg = get_stage_config(ExperimentStage.NBAIOT_SMOKE)
        assert cfg.scale == ExperimentScale.SMOKE

    def test_nbaiot_bounded_scale_is_bounded(self) -> None:
        cfg = get_stage_config(ExperimentStage.NBAIOT_BOUNDED)
        assert cfg.scale == ExperimentScale.BOUNDED

    def test_nbaiot_full_scale_is_full(self) -> None:
        cfg = get_stage_config(ExperimentStage.NBAIOT_FULL)
        assert cfg.scale == ExperimentScale.FULL

    def test_ciciot_stretch_scale_is_stretch(self) -> None:
        cfg = get_stage_config(ExperimentStage.CICIOT2023_STRETCH)
        assert cfg.scale == ExperimentScale.STRETCH

    def test_paper_figures_has_no_scale(self) -> None:
        cfg = get_stage_config(ExperimentStage.PAPER_FIGURES)
        assert cfg.scale is None

    def test_nbaiot_stages_dataset_is_nbaiot(self) -> None:
        for stage in (
            ExperimentStage.NBAIOT_SMOKE,
            ExperimentStage.NBAIOT_BOUNDED,
            ExperimentStage.NBAIOT_FULL,
        ):
            assert get_stage_config(stage).dataset == DatasetID.NBAIOT

    def test_ciciot_stage_dataset_is_ciciot2023(self) -> None:
        assert (
            get_stage_config(ExperimentStage.CICIOT2023_STRETCH).dataset
            == DatasetID.CICIOT2023
        )

    def test_edge_iiotset_not_present(self) -> None:
        for cfg in all_stage_configs():
            assert cfg.dataset != "edge_iiotset", "Edge-IIoTset is forbidden"


class TestAllowRun:
    def test_only_stages_with_a_completed_gate_allow_run(self) -> None:
        # NBAIOT_SMOKE and NBAIOT_BOUNDED gates are recorded as satisfied,
        # so those two stages allow_run=True. Every other stage's gate
        # is not yet satisfied and must stay blocked.
        # final/full experiments are not gated by any stage here.
        expected_runnable = {
            ExperimentStage.NBAIOT_SMOKE,
            ExperimentStage.NBAIOT_BOUNDED,
        }
        for cfg in all_stage_configs():
            if cfg.stage in expected_runnable:
                assert cfg.allow_run, f"Stage {cfg.stage!r} should allow_run=True"
            else:
                assert not cfg.allow_run, (
                    f"Stage {cfg.stage!r} has allow_run=True but its gate "
                    "is not recorded as satisfied"
                )


class TestGateRequirements:
    def test_nbaiot_full_gated_by_full_scope_decision(self) -> None:
        cfg = get_stage_config(ExperimentStage.NBAIOT_FULL)
        assert cfg.gate == "full_scope_continue_decision"

    def test_ciciot_stretch_gated_by_feasibility_decision(self) -> None:
        cfg = get_stage_config(ExperimentStage.CICIOT2023_STRETCH)
        assert cfg.gate == "ciciot_feasibility_decision"

    def test_common_has_no_gate(self) -> None:
        assert get_stage_config(ExperimentStage.COMMON).gate is None

    def test_audit_readonly_has_no_gate(self) -> None:
        assert get_stage_config(ExperimentStage.AUDIT_READONLY).gate is None


class TestAllStageConfigs:
    def test_returns_all_stages(self) -> None:
        cfgs = all_stage_configs()
        assert len(cfgs) == len(ExperimentStage)

    def test_each_config_is_stage_config(self) -> None:
        for cfg in all_stage_configs():
            assert isinstance(cfg, ExperimentStageConfig)

    def test_each_stage_appears_once(self) -> None:
        stages_seen = [cfg.stage for cfg in all_stage_configs()]
        assert len(stages_seen) == len(set(stages_seen))

    def test_frozen_immutable(self) -> None:
        cfg = get_stage_config(ExperimentStage.NBAIOT_BOUNDED)
        with pytest.raises(Exception):
            cfg.allow_run = True  # type: ignore[misc]
