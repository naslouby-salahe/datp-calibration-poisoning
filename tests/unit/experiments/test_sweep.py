from __future__ import annotations

from pathlib import Path

from datp.attacks.enums import ThresholdPolicy
from datp.config.stages import ExperimentStage
from datp.core.enums import CONTROLLED_POLICIES
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.experiments.sweep import (
    SweepResult,
    _cell_is_done,
    build_experiment_matrix,
    run_sweep,
)
from datp.experiments.validator import validate_sweep
from tests.fixtures.payloads import valid_metrics_json

_STAGE = ExperimentStage.NBAIOT_MAIN
_TOTAL_CELLS = 15  # 3 policies × 5 seeds


class TestBuildExperimentMatrix:
    def test_total_count(self):
        cells = build_experiment_matrix()
        assert len(cells) == _TOTAL_CELLS

    def test_all_nbaiot_main_stage(self):
        cells = build_experiment_matrix()
        assert all(c.stage == _STAGE for c in cells)

    def test_only_controlled_policies(self):
        cells = build_experiment_matrix()
        assert {c.policy for c in cells} == set(CONTROLLED_POLICIES)

    def test_cells_are_policy_run_id_instances(self):
        cells = build_experiment_matrix()
        assert all(isinstance(c, PolicyRunId) for c in cells)

    def test_each_policy_has_five_seeds(self):
        cells = build_experiment_matrix()
        for policy in CONTROLLED_POLICIES:
            policy_cells = [c for c in cells if c.policy == policy]
            assert len(policy_cells) == 5


class TestValidateSweep:
    def test_all_valid(self):
        cells = build_experiment_matrix()
        errors, configs = validate_sweep(cells)
        assert errors == []
        assert len(configs) == len(cells)

    def test_configs_keyed_by_policy_run_id(self):
        cells = build_experiment_matrix()
        _, configs = validate_sweep(cells)
        for cell in cells:
            assert cell in configs
            assert configs[cell] is not None

    def test_empty_cells_returns_empty(self):
        errors, configs = validate_sweep([])
        assert errors == []
        assert configs == {}


class TestSweepResult:
    def test_defaults(self):
        r = SweepResult()
        assert r.total == 0
        assert r.completed == 0
        assert r.skipped == 0
        assert r.failed == 0

    def test_explicit_total(self):
        r = SweepResult(total=42)
        assert r.total == 42
        assert r.completed == 0


class TestCheckpointProtocolCompletion:
    def test_shared_baseline_ignores_legacy_non_round_metrics(self, tmp_path: Path):
        import pytest

        from datp.artifacts.layout import ArtifactLayout
        from datp.config.compose import BASE_CONFIG

        protocol = BASE_CONFIG.checkpoint_protocol
        if protocol is None:
            pytest.skip("checkpoint protocol not configured in base YAML")
            return
        run = PolicyRunId(
            cell=TrainingCellId(stage=_STAGE, seed=0),
            policy=ThresholdPolicy.GLOBAL_THRESHOLD,
        )
        legacy_dir = (
            ArtifactLayout(base_dir=tmp_path, stage=_STAGE)
            .policy_run(run)
            .result_dir
        )
        legacy_dir.mkdir(parents=True, exist_ok=True)
        (legacy_dir / "metrics.json").write_text(
            valid_metrics_json("global_threshold", "nbaiot_main", 0)
        )

        assert _cell_is_done(run, tmp_path) is False

    def test_shared_baseline_done_requires_all_checkpoint_rounds(self, tmp_path: Path):
        import pytest

        from datp.artifacts.layout import ArtifactLayout
        from datp.config.compose import BASE_CONFIG

        protocol = BASE_CONFIG.checkpoint_protocol
        if protocol is None:
            pytest.skip("checkpoint protocol not configured in base YAML")
            return
        run = PolicyRunId(
            cell=TrainingCellId(stage=_STAGE, seed=0),
            policy=ThresholdPolicy.GLOBAL_THRESHOLD,
        )
        layout = ArtifactLayout(base_dir=tmp_path, stage=_STAGE)
        for checkpoint_round in protocol.milestones:
            result_dir = layout.policy_run_for_round(run, checkpoint_round).result_dir
            result_dir.mkdir(parents=True, exist_ok=True)
            (result_dir / "metrics.json").write_text(
                valid_metrics_json("global_threshold", "nbaiot_main", 0)
            )

        assert _cell_is_done(run, tmp_path) is True


class TestRunSweep:
    def test_dry_run_exits_cleanly(self, tmp_path: Path):
        result = run_sweep(dry_run=True, base_dir=tmp_path)
        assert isinstance(result, SweepResult)
        assert result.total == _TOTAL_CELLS
        assert result.completed == 0
        assert result.failed == 0

    def test_skips_completed_runs(self, tmp_path: Path):
        from unittest.mock import patch

        from datp.artifacts.layout import ArtifactLayout
        from tests.fixtures.payloads import valid_metrics_dict
        import json

        run = PolicyRunId(
            cell=TrainingCellId(stage=_STAGE, seed=0),
            policy=ThresholdPolicy.GLOBAL_THRESHOLD,
        )
        metrics_path = (
            ArtifactLayout(base_dir=tmp_path, stage=_STAGE)
            .policy_run(run)
            .metrics_path
        )
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_path.write_text(json.dumps(valid_metrics_dict("global_threshold", "nbaiot_main", 0)))

        _fail = RuntimeError("no data — mocked for unit test")
        with (
            patch(
                "datp.experiments.executor.SharedTrainingExecutor.build_context",
                side_effect=_fail,
            )
        ):
            result = run_sweep(dry_run=False, base_dir=tmp_path)

        assert result.skipped >= 1
        assert result.failed == result.total - result.skipped

    def test_data_root_passed_through(self, tmp_path: Path):
        """data_root parameter is accepted without error in dry-run mode."""
        result = run_sweep(
            dry_run=True, base_dir=tmp_path, data_root=tmp_path
        )
        assert result.total == _TOTAL_CELLS
