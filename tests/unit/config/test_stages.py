"""Unit tests for CP2 stage configuration layout."""

from __future__ import annotations

import pytest

from datp.attacks.poison_enums import ExperimentScale
from datp.config.stages import (
    Cp2Stage,
    Cp2StageConfig,
    all_stage_configs,
    get_stage_config,
)


class TestCp2Stage:
    def test_all_expected_stages_present(self) -> None:
        stages = set(Cp2Stage)
        assert Cp2Stage.COMMON in stages
        assert Cp2Stage.AUDIT_READONLY in stages
        assert Cp2Stage.NBAIOT_SMOKE in stages
        assert Cp2Stage.NBAIOT_MVP in stages
        assert Cp2Stage.NBAIOT_FULL in stages
        assert Cp2Stage.CICIOT2023_STRETCH in stages
        assert Cp2Stage.PAPER_FIGURES in stages

    def test_stage_values_are_strings(self) -> None:
        for stage in Cp2Stage:
            assert isinstance(str(stage), str)


class TestGetStageConfig:
    def test_common_has_no_scale(self) -> None:
        cfg = get_stage_config(Cp2Stage.COMMON)
        assert cfg.scale is None

    def test_nbaiot_smoke_scale_is_smoke(self) -> None:
        cfg = get_stage_config(Cp2Stage.NBAIOT_SMOKE)
        assert cfg.scale == ExperimentScale.SMOKE

    def test_nbaiot_mvp_scale_is_mvp(self) -> None:
        cfg = get_stage_config(Cp2Stage.NBAIOT_MVP)
        assert cfg.scale == ExperimentScale.MVP

    def test_nbaiot_full_scale_is_full(self) -> None:
        cfg = get_stage_config(Cp2Stage.NBAIOT_FULL)
        assert cfg.scale == ExperimentScale.FULL

    def test_ciciot_stretch_scale_is_stretch(self) -> None:
        cfg = get_stage_config(Cp2Stage.CICIOT2023_STRETCH)
        assert cfg.scale == ExperimentScale.STRETCH

    def test_paper_figures_has_no_scale(self) -> None:
        cfg = get_stage_config(Cp2Stage.PAPER_FIGURES)
        assert cfg.scale is None

    def test_nbaiot_stages_dataset_is_nbaiot(self) -> None:
        for stage in (
            Cp2Stage.NBAIOT_SMOKE,
            Cp2Stage.NBAIOT_MVP,
            Cp2Stage.NBAIOT_FULL,
        ):
            assert get_stage_config(stage).dataset == "nbaiot"

    def test_ciciot_stage_dataset_is_ciciot2023(self) -> None:
        assert get_stage_config(Cp2Stage.CICIOT2023_STRETCH).dataset == "ciciot2023"

    def test_edge_iiotset_not_present(self) -> None:
        for cfg in all_stage_configs():
            assert cfg.dataset != "edge_iiotset", (
                "Edge-IIoTset is forbidden for CP2"
            )


class TestAllowRun:
    def test_no_stage_allows_run_in_phase_b(self) -> None:
        # All stages must have allow_run=False in Phase B.
        for cfg in all_stage_configs():
            assert not cfg.allow_run, (
                f"Stage {cfg.stage!r} has allow_run=True; "
                "no stage should run experiments until CP2-T056"
            )


class TestGateRequirements:
    def test_nbaiot_full_gated_by_fb3(self) -> None:
        cfg = get_stage_config(Cp2Stage.NBAIOT_FULL)
        assert cfg.gate == "FB3"

    def test_ciciot_stretch_gated_by_fb4(self) -> None:
        cfg = get_stage_config(Cp2Stage.CICIOT2023_STRETCH)
        assert cfg.gate == "FB4"

    def test_common_has_no_gate(self) -> None:
        assert get_stage_config(Cp2Stage.COMMON).gate is None

    def test_audit_readonly_has_no_gate(self) -> None:
        assert get_stage_config(Cp2Stage.AUDIT_READONLY).gate is None


class TestAllStageConfigs:
    def test_returns_all_stages(self) -> None:
        cfgs = all_stage_configs()
        assert len(cfgs) == len(Cp2Stage)

    def test_each_config_is_cp2_stage_config(self) -> None:
        for cfg in all_stage_configs():
            assert isinstance(cfg, Cp2StageConfig)

    def test_each_stage_appears_once(self) -> None:
        stages_seen = [cfg.stage for cfg in all_stage_configs()]
        assert len(stages_seen) == len(set(stages_seen))

    def test_frozen_immutable(self) -> None:
        cfg = get_stage_config(Cp2Stage.NBAIOT_MVP)
        with pytest.raises(Exception):
            cfg.allow_run = True  # type: ignore[misc]
