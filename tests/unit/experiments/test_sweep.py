from __future__ import annotations

from pathlib import Path

from datp.core.enums import Baseline, Regime
from datp.core.identity import BaselineRunId
from datp.experiments.sweep import (
    SweepResult,
    _cell_is_done,
    build_experiment_matrix,
    run_sweep,
)
from datp.experiments.validator import validate_sweep
from tests.fixtures.payloads import valid_metrics_json

_TOTAL_CELLS = 135
_REGIME_A_CELLS = 25
_REGIME_B_CELLS = 20
_REGIME_C_CELLS = 90


class TestBuildExperimentMatrix:
    def test_total_count(self):
        cells = build_experiment_matrix()
        assert len(cells) == _TOTAL_CELLS

    def test_regime_a_count(self):
        cells = build_experiment_matrix()
        regime_a = [c for c in cells if c.regime == Regime.A]
        assert len(regime_a) == _REGIME_A_CELLS

    def test_regime_b_count(self):
        cells = build_experiment_matrix()
        regime_b = [c for c in cells if c.regime == Regime.B]
        assert len(regime_b) == _REGIME_B_CELLS

    def test_regime_c_count(self):
        cells = build_experiment_matrix()
        regime_c = [c for c in cells if c.regime == Regime.C]
        assert len(regime_c) == _REGIME_C_CELLS

    def test_b3_only_regime_a(self):
        cells = build_experiment_matrix()
        b3_cells = [c for c in cells if c.baseline == Baseline.B3]
        assert all(c.regime == Regime.A for c in b3_cells)
        assert len(b3_cells) > 0

    def test_b0_in_non_dirichlet_regimes_only(self):
        cells = build_experiment_matrix()
        b0_cells = [c for c in cells if c.baseline == Baseline.B0]
        assert all(c.regime in (Regime.A, Regime.B) for c in b0_cells)
        assert len(b0_cells) > 0

    def test_b0_not_in_regime_c(self):
        cells = build_experiment_matrix()
        regime_c = [c for c in cells if c.regime == Regime.C]
        assert all(c.baseline != Baseline.B0 for c in regime_c)

    def test_cells_are_experiment_cell_instances(self):
        cells = build_experiment_matrix()
        assert all(isinstance(c, BaselineRunId) for c in cells)


class TestValidateSweep:
    def test_all_valid(self):
        cells = build_experiment_matrix()
        errors, configs = validate_sweep(cells)
        assert errors == []
        assert len(configs) == len(cells)

    def test_configs_keyed_by_baseline_run_id(self):
        cells = build_experiment_matrix()
        _, configs = validate_sweep(cells)
        for cell in cells:
            assert cell in configs
            assert configs[cell] is not None

    def test_empty_cells_returns_empty(self):
        errors, configs = validate_sweep([])
        assert errors == []
        assert configs == {}

    def test_invalid_cell_reports_error(self):
        """B3 with Regime.B should fail compose_config (B3 only valid for Regime.A)."""
        from datp.core.identity import TrainingCellId

        bad_cell = BaselineRunId(
            cell=TrainingCellId(regime=Regime.B, seed=0, alpha=None),
            baseline=Baseline.B3,
        )
        errors, configs = validate_sweep([bad_cell])
        assert len(errors) == 1
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
        from datp.core.identity import TrainingCellId

        protocol = BASE_CONFIG.checkpoint_protocol
        if protocol is None:
            pytest.skip("checkpoint protocol not configured in base YAML")
            return
        run = BaselineRunId(
            cell=TrainingCellId(regime=Regime.A, seed=0, alpha=None),
            baseline=Baseline.B1,
        )
        legacy_dir = (
            ArtifactLayout(base_dir=tmp_path, regime=Regime.A)
            .baseline_run(run)
            .result_dir
        )
        legacy_dir.mkdir(parents=True, exist_ok=True)
        (legacy_dir / "metrics.json").write_text(valid_metrics_json("b1", "a", 0))

        assert _cell_is_done(run, tmp_path) is False

    def test_shared_baseline_done_requires_all_checkpoint_rounds(self, tmp_path: Path):
        import pytest

        from datp.artifacts.layout import ArtifactLayout
        from datp.config.compose import BASE_CONFIG
        from datp.core.identity import TrainingCellId

        protocol = BASE_CONFIG.checkpoint_protocol
        if protocol is None:
            pytest.skip("checkpoint protocol not configured in base YAML")
            return
        run = BaselineRunId(
            cell=TrainingCellId(regime=Regime.A, seed=0, alpha=None),
            baseline=Baseline.B1,
        )
        layout = ArtifactLayout(base_dir=tmp_path, regime=Regime.A)
        for checkpoint_round in protocol.milestones:
            result_dir = layout.baseline_run_for_round(run, checkpoint_round).result_dir
            result_dir.mkdir(parents=True, exist_ok=True)
            (result_dir / "metrics.json").write_text(valid_metrics_json("b1", "a", 0))

        assert _cell_is_done(run, tmp_path) is True


class TestRunSweep:
    def test_dry_run_exits_cleanly(self, tmp_path: Path):
        result = run_sweep(dry_run=True, base_dir=tmp_path, regime=None)
        assert isinstance(result, SweepResult)
        assert result.total == _TOTAL_CELLS
        assert result.completed == 0
        assert result.failed == 0

    def test_skips_completed_runs(self, tmp_path: Path):
        from unittest.mock import patch

        baseline, regime, seed = Baseline.B0, Regime.A, 0

        from datp.artifacts.layout import ArtifactLayout
        from datp.core.identity import TrainingCellId

        run = BaselineRunId(
            cell=TrainingCellId(regime=regime, seed=seed, alpha=None),
            baseline=baseline,
        )
        rp = (
            ArtifactLayout(base_dir=tmp_path, regime=regime)
            .baseline_run(run)
            .result_dir
        )
        rp.mkdir(parents=True, exist_ok=True)
        (rp / "metrics.json").write_text(valid_metrics_json("b1", "a", 0))

        _fail = RuntimeError("no data — mocked for unit test")
        # Patch the executor methods used by run_sweep's new architecture.
        with (
            patch(
                "datp.experiments.executor.SharedTrainingExecutor.build_context",
                side_effect=_fail,
            ),
            patch(
                "datp.experiments.executor.IsolatedBaselineExecutor.run",
                side_effect=_fail,
            ),
        ):
            result = run_sweep(dry_run=False, base_dir=tmp_path, regime=Regime.A)

        assert result.skipped >= 1
        assert result.failed == result.total - result.skipped

    def test_regime_filter_limits_cells(self, tmp_path: Path):
        result = run_sweep(dry_run=True, base_dir=tmp_path, regime=Regime.A)
        assert result.total == _REGIME_A_CELLS

    def test_data_root_passed_through(self, tmp_path: Path):
        """data_root parameter is accepted without error in dry-run mode."""
        result = run_sweep(
            dry_run=True, base_dir=tmp_path, regime=Regime.A, data_root=tmp_path
        )
        assert result.total == _REGIME_A_CELLS
