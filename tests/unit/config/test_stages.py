"""Unit tests for experiment stage definitions and gate logic."""

from __future__ import annotations

from datp.config.models import (
    ExperimentStage,
    ExperimentStageConfig,
    all_stage_configs,
    get_stage_config,
)
from datp.core.enums import DatasetID


class TestExperimentStage:
    """ExperimentStage enum values and properties."""

    def test_all_expected_stages_present(self) -> None:
        assert set(ExperimentStage) == {
            ExperimentStage.FINAL_AUDIT,
            ExperimentStage.SYNTHETIC_SMOKE,
            ExperimentStage.NBAIOT_MAIN,
            ExperimentStage.NBAIOT_FULL_OPTIONAL,
            ExperimentStage.STRETCH_DIAGNOSTIC_ONLY,
        }


class TestGetStageConfig:
    """Stage config lookup by name."""

    def test_final_audit_config(self) -> None:
        cfg = get_stage_config(ExperimentStage.FINAL_AUDIT)
        assert cfg.dataset is None
        assert cfg.allow_run is False
        assert cfg.gate == "final_audit_pass"

    def test_synthetic_smoke_config(self) -> None:
        cfg = get_stage_config(ExperimentStage.SYNTHETIC_SMOKE)
        assert cfg.dataset is None
        assert cfg.allow_run is True

    def test_nbaiot_main_config(self) -> None:
        cfg = get_stage_config(ExperimentStage.NBAIOT_MAIN)
        assert cfg.dataset == DatasetID.NBAIOT
        assert cfg.allow_run is True

    def test_nbaiot_full_optional_config(self) -> None:
        cfg = get_stage_config(ExperimentStage.NBAIOT_FULL_OPTIONAL)
        assert cfg.dataset == DatasetID.NBAIOT
        assert cfg.allow_run is False
        assert cfg.gate == "full_scope_continue_decision"

    def test_stretch_diagnostic_only_config(self) -> None:
        cfg = get_stage_config(ExperimentStage.STRETCH_DIAGNOSTIC_ONLY)
        assert cfg.dataset is None
        assert cfg.allow_run is False
        assert cfg.gate == "stretch_diagnostic_signoff"

    def test_edge_iiotset_not_present(self) -> None:
        for cfg in all_stage_configs():
            assert cfg.dataset != "edge_iiotset", "Edge-IIoTset is forbidden"


class TestAllStageConfigs:
    """All stage configs are well-formed."""

    def test_returns_all_stages(self) -> None:
        cfgs = all_stage_configs()
        assert len(cfgs) == len(ExperimentStage)

    def test_each_config_is_stage_config(self) -> None:
        for cfg in all_stage_configs():
            assert isinstance(cfg, ExperimentStageConfig)

    def test_each_stage_appears_once(self) -> None:
        stages_seen = [cfg.stage for cfg in all_stage_configs()]
        assert len(stages_seen) == len(set(stages_seen))
