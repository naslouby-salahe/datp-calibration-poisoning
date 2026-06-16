"""Unit tests for the CP2 CLI subcommand."""

from __future__ import annotations

from datp.app.cli import app
from datp.config.stages import Cp2Stage

from typer.testing import CliRunner

_runner = CliRunner()


class TestCp2Preview:
    def test_preview_exits_zero(self) -> None:
        result = _runner.invoke(app, ["cp2", "preview", "--stage", "nbaiot_mvp"])
        assert result.exit_code == 0

    def test_preview_contains_stage_name(self) -> None:
        result = _runner.invoke(app, ["cp2", "preview", "--stage", "nbaiot_mvp"])
        assert "nbaiot_mvp" in result.output

    def test_preview_contains_scale(self) -> None:
        result = _runner.invoke(app, ["cp2", "preview", "--stage", "nbaiot_smoke"])
        assert "smoke" in result.output.lower()

    def test_preview_gated_stage_exits_zero(self) -> None:
        result = _runner.invoke(app, ["cp2", "preview", "--stage", "nbaiot_full"])
        assert result.exit_code == 0


class TestCp2DryRun:
    def test_dry_run_exits_zero(self) -> None:
        result = _runner.invoke(app, ["cp2", "dry-run", "--stage", "nbaiot_mvp"])
        assert result.exit_code == 0

    def test_dry_run_contains_stage_info(self) -> None:
        result = _runner.invoke(app, ["cp2", "dry-run", "--stage", "nbaiot_mvp"])
        assert "nbaiot_mvp" in result.output

    def test_dry_run_phase_b_notice_present(self) -> None:
        result = _runner.invoke(app, ["cp2", "dry-run", "--stage", "nbaiot_mvp"])
        # CliRunner mixes stdout+stderr into result.output by default.
        assert "blocked" in result.output.lower() or "CP2-T056" in result.output

    def test_dry_run_gated_stage_mentions_gate(self) -> None:
        result = _runner.invoke(app, ["cp2", "dry-run", "--stage", "nbaiot_full"])
        assert "FB3" in result.output


class TestCp2Smoke:
    def test_smoke_exits_zero(self) -> None:
        result = _runner.invoke(app, ["cp2", "smoke"])
        assert result.exit_code == 0

    def test_smoke_mentions_nbaiot(self) -> None:
        result = _runner.invoke(app, ["cp2", "smoke"])
        assert "nbaiot" in result.output.lower()


class TestCp2Stages:
    def test_stages_exits_zero(self) -> None:
        result = _runner.invoke(app, ["cp2", "stages"])
        assert result.exit_code == 0

    def test_stages_output_contains_all_stages(self) -> None:
        result = _runner.invoke(app, ["cp2", "stages"])
        for stage in Cp2Stage:
            assert str(stage) in result.output, f"Stage {stage!r} missing from output"

    def test_stages_output_contains_blocked(self) -> None:
        result = _runner.invoke(app, ["cp2", "stages"])
        assert "BLOCKED" in result.output
