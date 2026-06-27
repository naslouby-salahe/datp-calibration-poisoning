"""CLI smoke tests for the `poison` subcommand (preview, dry-run, smoke, stages)."""

from __future__ import annotations

from typer.testing import CliRunner

from datp.cli import app
from datp.config.models import ExperimentStage

_runner = CliRunner()


class TestPreview:
    """Verify `poison preview` output for various stages."""

    """Verify `poison preview` output for various stages."""

    def test_preview_exits_zero(self) -> None:
        """Preview of nbaiot_main exits with code 0."""
        result = _runner.invoke(app, ["poison", "preview", "--stage", "nbaiot_main"])
        assert result.exit_code == 0

    def test_preview_contains_stage_name(self) -> None:
        """Preview output includes the requested stage name."""
        result = _runner.invoke(app, ["poison", "preview", "--stage", "nbaiot_main"])
        assert "nbaiot_main" in result.output

    def test_preview_contains_scale(self) -> None:
        """Preview output mentions the scale (smoke) for synthetic_smoke."""
        result = _runner.invoke(
            app, ["poison", "preview", "--stage", "synthetic_smoke"]
        )
        assert "smoke" in result.output.lower()

    def test_preview_gated_stage_exits_zero(self) -> None:
        """Preview of a gated stage exits with code 0."""
        result = _runner.invoke(
            app, ["poison", "preview", "--stage", "nbaiot_full_optional"]
        )
        assert result.exit_code == 0


class TestDryRun:
    """Verify `poison dry-run` output for various stages."""

    """Verify `poison dry-run` output for various stages."""

    def test_dry_run_exits_zero(self) -> None:
        """Dry-run of nbaiot_main exits with code 0."""
        result = _runner.invoke(app, ["poison", "dry-run", "--stage", "nbaiot_main"])
        assert result.exit_code == 0

    def test_dry_run_contains_stage_info(self) -> None:
        """Dry-run output includes the requested stage name."""
        result = _runner.invoke(app, ["poison", "dry-run", "--stage", "nbaiot_main"])
        assert "nbaiot_main" in result.output

    def test_dry_run_blocked_stage_shows_notice(self) -> None:
        """Dry-run of a blocked stage shows the blocked notice."""
        result = _runner.invoke(
            app, ["poison", "dry-run", "--stage", "nbaiot_full_optional"]
        )

        assert "blocked" in result.output.lower()

    def test_dry_run_nbaiot_main_sweep_no_longer_blocked(self) -> None:
        """Dry-run of nbaiot_main does not show blocked (unlike gated stages)."""
        result = _runner.invoke(app, ["poison", "dry-run", "--stage", "nbaiot_main"])
        assert "blocked" not in result.output.lower()

    def test_dry_run_gated_stage_mentions_gate(self) -> None:
        """Dry-run of a gated stage mentions the gate decision key."""
        result = _runner.invoke(
            app, ["poison", "dry-run", "--stage", "nbaiot_full_optional"]
        )
        assert "full_scope_continue_decision" in result.output


class TestSmoke:
    """Verify `poison smoke` CLI integration."""

    """Verify `poison smoke` CLI integration."""

    def test_smoke_exits_zero(self) -> None:
        """Smoke subcommand exits with code 0."""
        result = _runner.invoke(app, ["poison", "smoke"])
        assert result.exit_code == 0

    def test_smoke_mentions_nbaiot(self) -> None:
        """Smoke output mentions the nbaiot dataset."""
        result = _runner.invoke(app, ["poison", "smoke"])
        assert "baiot" in result.output.lower()


class TestStages:
    """Verify `poison stages` enumeration."""

    """Verify `poison stages` enumeration."""

    def test_stages_exits_zero(self) -> None:
        """Stages subcommand exits with code 0."""
        result = _runner.invoke(app, ["poison", "stages"])
        assert result.exit_code == 0

    def test_stages_output_contains_all_stages(self) -> None:
        """Output lists every ExperimentStage enum member."""
        result = _runner.invoke(app, ["poison", "stages"])
        for stage in ExperimentStage:
            assert str(stage) in result.output, f"Stage {stage!r} missing from output"

    def test_stages_output_contains_blocked(self) -> None:
        """Output includes blocked gate status."""
        result = _runner.invoke(app, ["poison", "stages"])
        assert "BLOCKED" in result.output


class TestDryRunBoundedWiring:
    """Verify bounded-sweep config wiring in dry-run output."""

    """Verify bounded-sweep config wiring in dry-run output."""

    def test_dry_run_bounded_shows_config_policies(self) -> None:
        """Dry-run output includes all three threshold policies."""
        result = _runner.invoke(app, ["poison", "dry-run", "--stage", "nbaiot_main"])
        assert result.exit_code == 0
        output = result.output.lower()
        assert "global_threshold" in output
        assert "local_threshold" in output
        assert "cluster_threshold" in output

    def test_dry_run_bounded_shows_config_sources(self) -> None:
        """Dry-run output includes poisoning source strategies."""
        result = _runner.invoke(app, ["poison", "dry-run", "--stage", "nbaiot_main"])
        assert result.exit_code == 0
        output = result.output.lower()
        assert "random_benign" in output
        assert "high_score_benign" in output
        assert "low_score_benign" in output

    def test_dry_run_bounded_shows_cells_per_victim(self) -> None:
        result = _runner.invoke(app, ["poison", "dry-run", "--stage", "nbaiot_main"])
        assert result.exit_code == 0
        assert "480" in result.output

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

        assert "config_policies" not in result.output
        assert "cells/victim" not in result.output
