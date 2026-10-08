from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import datp.cli as cli_module
import datp.cli as commands
from datp.artifacts import DATA_ROOT, OUTPUTS_DIR, RESULTS_PACKAGE_DIR, ArtifactLayout
from datp.cli import app, get_status
from datp.config import ExperimentStage
from datp.core import PolicyRunId, TrainingCellId
from datp.enums import ArtifactFile, CliCommand, CliExitCode, ThresholdPolicy
from tests.fixtures import valid_metrics_json

_runner = CliRunner()


def test_registered_commands_are_exactly_the_cli_command_enum() -> None:
    result = _runner.invoke(app, ["--help"])

    assert all(command in result.output for command in CliCommand)
    assert len(app.registered_commands) == len(CliCommand)


@pytest.mark.parametrize("command", list(CliCommand))
def test_commands_take_no_arguments(command: CliCommand) -> None:
    result = _runner.invoke(app, [command, "--help"])

    assert result.exit_code == CliExitCode.SUCCESS
    assert "Options" in result.output
    assert "--base-dir" not in result.output
    assert "--stage" not in result.output


class TestPlan:
    def test_plan_lists_every_experiment_grid(self) -> None:
        result = _runner.invoke(app, ["plan"])

        assert result.exit_code == CliExitCode.SUCCESS
        output = result.output.lower()
        assert "baseline" in output
        assert "random_benign" in output
        assert "high_score_benign" in output
        assert "low_score_benign" in output
        assert "threshold_raise" in output
        assert "threshold_lower" in output
        for analysis in (
            "cluster_stability",
            "scale_normalization",
            "draw_variant",
            "trust_boundary",
        ):
            assert analysis in output

    def test_plan_reports_cells_per_victim(self) -> None:
        result = _runner.invoke(app, ["plan"])

        assert "1440" in result.output


class TestDispatch:
    def test_baseline_runs_sweep_on_fixed_directories(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[dict[str, Path]] = []
        monkeypatch.setattr(
            commands, "run_sweep", lambda **kwargs: calls.append(kwargs)
        )

        result = _runner.invoke(app, ["baseline"])

        assert result.exit_code == CliExitCode.SUCCESS
        assert calls == [{"base_dir": OUTPUTS_DIR, "data_root": DATA_ROOT}]

    def test_poison_writes_the_bounded_sweep_manifest(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: list[dict[str, Path]] = []

        def write(base_dir: Path, *, data_root: Path) -> Path:
            seen.append({"base_dir": base_dir, "data_root": data_root})
            return base_dir / "nbaiot_main_manifest.json"

        monkeypatch.setattr(commands, "write_nbaiot_main_manifest", write)

        result = _runner.invoke(app, ["poison"])

        assert result.exit_code == CliExitCode.SUCCESS
        assert seen == [{"base_dir": OUTPUTS_DIR, "data_root": DATA_ROOT}]

    def test_sensitivity_writes_the_sensitivity_manifest(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: list[dict[str, Path]] = []

        def write(base_dir: Path, *, data_root: Path) -> Path:
            seen.append({"base_dir": base_dir, "data_root": data_root})
            return base_dir / "sensitivity_manifest.json"

        monkeypatch.setattr(commands, "write_sensitivity_manifest", write)

        result = _runner.invoke(app, ["sensitivity"])

        assert result.exit_code == CliExitCode.SUCCESS
        assert seen == [{"base_dir": OUTPUTS_DIR, "data_root": DATA_ROOT}]

    def test_status_prints_the_status_table(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: list[Path] = []
        monkeypatch.setattr(commands, "print_status", seen.append)

        result = _runner.invoke(app, ["status"])

        assert result.exit_code == CliExitCode.SUCCESS
        assert seen == [OUTPUTS_DIR]


class TestReport:
    def test_report_packages_into_the_results_directory(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: list[dict[str, Path]] = []

        def package(**kwargs: Path) -> tuple[Path, ...]:
            seen.append({key: value for key, value in kwargs.items() if key != "cfg"})
            return (RESULTS_PACKAGE_DIR / "tables" / "table3_nbaiot.csv",)

        monkeypatch.setattr(commands, "build_report_package", package)

        result = _runner.invoke(app, ["report"])

        assert result.exit_code == CliExitCode.SUCCESS
        assert seen == [
            {
                "base_dir": OUTPUTS_DIR,
                "results_dir": RESULTS_PACKAGE_DIR,
            }
        ]
        assert "table3_nbaiot.csv" in result.output

    def test_report_failure_exits_with_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def package(**_kwargs: Path) -> tuple[Path, ...]:
            raise FileNotFoundError("Missing sensitivity manifest")

        monkeypatch.setattr(commands, "build_report_package", package)

        result = _runner.invoke(app, ["report"])

        assert result.exit_code == CliExitCode.ERROR
        assert "Missing sensitivity manifest" in result.output


class _LogRecorder:
    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict[str, Any]]] = []

    def info(self, event: str, **fields: Any) -> None:
        self.events.append(("info", event, fields))

    def error(self, event: str, **fields: Any) -> None:
        self.events.append(("error", event, fields))

    def exception(self, event: str, **fields: Any) -> None:
        self.events.append(("exception", event, fields))


def test_cli_command_resolution_uses_the_registered_command_enum() -> None:
    assert CliCommand.resolve(["report"]) is CliCommand.REPORT
    assert CliCommand.resolve(["poison"]) is CliCommand.POISON
    assert CliCommand.resolve(["--help"]) is None
    assert CliCommand.resolve(["unregistered", "value"]) is None


def test_cli_entry_logs_start_and_success(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder = _LogRecorder()
    monkeypatch.setattr(cli_module, "logger", recorder)
    monkeypatch.setattr(cli_module, "configure_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli_module, "app", lambda: sys.exit(0))
    monkeypatch.setattr(sys, "argv", ["datp", "plan"])

    with pytest.raises(SystemExit) as exit_info:
        cli_module.cli_entry()

    assert exit_info.value.code == 0
    assert [event for _, event, _ in recorder.events] == [
        "CLI invocation started",
        "CLI invocation completed",
    ]
    assert all(fields["command"] is CliCommand.PLAN for _, _, fields in recorder.events)


def test_cli_entry_logs_failure_and_preserves_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = _LogRecorder()
    failure = RuntimeError("command failed")
    monkeypatch.setattr(cli_module, "logger", recorder)
    monkeypatch.setattr(cli_module, "configure_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli_module, "app", lambda: (_ for _ in ()).throw(failure))
    monkeypatch.setattr(sys, "argv", ["datp", "baseline"])

    with pytest.raises(RuntimeError, match="command failed"):
        cli_module.cli_entry()

    assert [event for _, event, _ in recorder.events] == [
        "CLI invocation started",
        "CLI invocation failed",
    ]
    assert recorder.events[-1][0] == "exception"


_TOTAL_CELLS = 60


_NBAIOT_MAIN_CELLS = 60


class TestAllMissingFreshDir:
    """All cells are missing when the base directory is empty."""

    """All cells are missing when the base directory is empty."""

    def test_all_missing_fresh_dir(self, tmp_path):
        """Empty base directory reports all cells as missing and none complete or aborted."""
        report = get_status(base_dir=tmp_path)
        total_missing = sum(len(rr.missing) for rr in report.stage_reports.values())
        total_complete = sum(len(rr.complete) for rr in report.stage_reports.values())
        total_aborted = sum(len(rr.aborted) for rr in report.stage_reports.values())

        assert total_missing == _TOTAL_CELLS
        assert total_complete == 0
        assert total_aborted == 0


class TestCompleteDetected:
    """A completed metrics.json file is counted as complete."""

    def test_complete_detected(self, tmp_path):
        """Writing a valid metrics.json for one policy-run marks it complete."""
        stage = ExperimentStage.NBAIOT_MAIN
        run = PolicyRunId(
            cell=TrainingCellId(stage=stage, seed=0),
            policy=ThresholdPolicy.GLOBAL_THRESHOLD,
        )
        rp = ArtifactLayout(base_dir=tmp_path, stage=stage).policy_run(run).result_dir
        rp.mkdir(parents=True, exist_ok=True)
        (rp / "metrics.json").write_text(
            valid_metrics_json("global_threshold", "nbaiot_main", 0)
        )

        report = get_status(base_dir=tmp_path)
        rr = report.stage_reports[ExperimentStage.NBAIOT_MAIN]

        assert len(rr.complete) == 1
        assert len(rr.missing) == _NBAIOT_MAIN_CELLS - 1
        assert len(rr.aborted) == 0


class TestAbortedDetected:
    """An aborted marker file is counted as aborted."""

    def test_aborted_detected(self, tmp_path):
        """Writing a run-aborted marker for one policy-run marks it aborted."""
        stage = ExperimentStage.NBAIOT_MAIN
        run = PolicyRunId(
            cell=TrainingCellId(stage=stage, seed=1),
            policy=ThresholdPolicy.LOCAL_THRESHOLD,
        )
        rp = ArtifactLayout(base_dir=tmp_path, stage=stage).policy_run(run).result_dir
        rp.mkdir(parents=True, exist_ok=True)
        (rp / ArtifactFile.RUN_ABORTED).write_text("OOM error")

        report = get_status(base_dir=tmp_path)
        rr = report.stage_reports[ExperimentStage.NBAIOT_MAIN]

        assert len(rr.aborted) == 1
        assert len(rr.missing) == _NBAIOT_MAIN_CELLS - 1
        assert len(rr.complete) == 0


class TestSummaryRows:
    """Summary rows aggregate per-stage and total counts."""

    def test_summary_rows_counts(self, tmp_path):
        """Summary contains two rows: nbaiot_main and total."""
        report = get_status(base_dir=tmp_path)
        rows = report.summary_rows()

        assert len(rows) == 2

        assert rows[0].total == _NBAIOT_MAIN_CELLS
        assert rows[1].total == _TOTAL_CELLS


ROOT = Path(__file__).resolve().parents[2]


def _makefile_text() -> str:
    """Helper to read the top-level project Makefile content."""
    return (ROOT / "Makefile").read_text()


def _registered_root_commands() -> set[str]:
    """Helper to extract registered subcommand names from CLI entrypoints."""
    cli_text = (ROOT / "src/datp/cli/__init__.py").read_text()
    members = re.findall(r"app\.command\(CliCommand\.([A-Z_]+)\)", cli_text)
    return {CliCommand[member].value for member in members}


def test_makefile_cli_commands_are_registered() -> None:
    """Verify that all DATP_CLI commands invoked in the Makefile are actually registered subcommands."""
    makefile_commands = set(
        re.findall(r"\$\(DATP_CLI\)\s+([A-Za-z0-9_.-]+)", _makefile_text())
    )
    assert makefile_commands - _registered_root_commands() == set()


def test_removed_diagnostic_cli_targets_do_not_return() -> None:
    """Verify that legacy diagnostics CLI targets remain removed from the Makefile."""
    makefile = _makefile_text()
    assert "$(DATP_CLI) diagnostic" not in makefile
    assert "diagnostic-regime-" not in makefile
