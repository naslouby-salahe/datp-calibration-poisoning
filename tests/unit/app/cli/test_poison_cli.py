"""Unit tests for the CLI subcommand."""

from __future__ import annotations

from typer.testing import CliRunner

from datp.app.cli import app
from datp.config.stages import ExperimentStage

_runner = CliRunner()


class TestPreview:
    def test_preview_exits_zero(self) -> None:
        result = _runner.invoke(app, ["poison", "preview", "--stage", "nbaiot_main"])
        assert result.exit_code == 0

    def test_preview_contains_stage_name(self) -> None:
        result = _runner.invoke(app, ["poison", "preview", "--stage", "nbaiot_main"])
        assert "nbaiot_main" in result.output

    def test_preview_contains_scale(self) -> None:
        result = _runner.invoke(
            app, ["poison", "preview", "--stage", "synthetic_smoke"]
        )
        assert "smoke" in result.output.lower()

    def test_preview_gated_stage_exits_zero(self) -> None:
        result = _runner.invoke(
            app, ["poison", "preview", "--stage", "nbaiot_full_optional"]
        )
        assert result.exit_code == 0


class TestDryRun:
    def test_dry_run_exits_zero(self) -> None:
        result = _runner.invoke(app, ["poison", "dry-run", "--stage", "nbaiot_main"])
        assert result.exit_code == 0

    def test_dry_run_contains_stage_info(self) -> None:
        result = _runner.invoke(app, ["poison", "dry-run", "--stage", "nbaiot_main"])
        assert "nbaiot_main" in result.output

    def test_dry_run_blocked_stage_shows_notice(self) -> None:
        result = _runner.invoke(
            app, ["poison", "dry-run", "--stage", "nbaiot_full_optional"]
        )
        # CliRunner mixes stdout+stderr into result.output by default.
        assert "blocked" in result.output.lower()

    def test_dry_run_nbaiot_main_sweep_no_longer_blocked(self) -> None:
        # NBAIOT_MAIN has allow_run=True, so the blocked notice must not appear.
        result = _runner.invoke(app, ["poison", "dry-run", "--stage", "nbaiot_main"])
        assert "blocked" not in result.output.lower()

    def test_dry_run_gated_stage_mentions_gate(self) -> None:
        result = _runner.invoke(
            app, ["poison", "dry-run", "--stage", "nbaiot_full_optional"]
        )
        assert "full_scope_continue_decision" in result.output


class TestSmoke:
    def test_smoke_exits_zero(self) -> None:
        result = _runner.invoke(app, ["poison", "smoke"])
        assert result.exit_code == 0

    def test_smoke_mentions_nbaiot(self) -> None:
        result = _runner.invoke(app, ["poison", "smoke"])
        assert "baiot" in result.output.lower()


class TestStages:
    def test_stages_exits_zero(self) -> None:
        result = _runner.invoke(app, ["poison", "stages"])
        assert result.exit_code == 0

    def test_stages_output_contains_all_stages(self) -> None:
        result = _runner.invoke(app, ["poison", "stages"])
        for stage in ExperimentStage:
            assert str(stage) in result.output, f"Stage {stage!r} missing from output"

    def test_stages_output_contains_blocked(self) -> None:
        result = _runner.invoke(app, ["poison", "stages"])
        assert "BLOCKED" in result.output


class TestDryRunBoundedWiring:
    def test_dry_run_bounded_shows_config_policies(self) -> None:
        result = _runner.invoke(app, ["poison", "dry-run", "--stage", "nbaiot_main"])
        assert result.exit_code == 0
        output = result.output.lower()
        assert "global_threshold" in output
        assert "local_threshold" in output
        assert "cluster_threshold" in output

    def test_dry_run_bounded_shows_config_sources(self) -> None:
        result = _runner.invoke(app, ["poison", "dry-run", "--stage", "nbaiot_main"])
        assert result.exit_code == 0
        output = result.output.lower()
        assert "random_benign" in output
        assert "high_score_benign" in output
        assert "low_score_benign" in output

    def test_dry_run_bounded_shows_cells_per_victim(self) -> None:
        result = _runner.invoke(app, ["poison", "dry-run", "--stage", "nbaiot_main"])
        assert result.exit_code == 0
        assert "180" in result.output

    def test_dry_run_bounded_notes_objective_encoding(self) -> None:
        result = _runner.invoke(app, ["poison", "dry-run", "--stage", "nbaiot_main"])
        assert result.exit_code == 0
        output = result.output.lower()
        assert "threshold_raise" in output
        assert "threshold_lower" in output

    def test_dry_run_non_bounded_stage_still_works(self) -> None:
        result = _runner.invoke(
            app, ["poison", "dry-run", "--stage", "nbaiot_full_optional"]
        )
        assert result.exit_code == 0
        # Non-NBAIOT_MAIN stages must not show config_ lines
        assert "config_policies" not in result.output
        assert "cells/victim" not in result.output
