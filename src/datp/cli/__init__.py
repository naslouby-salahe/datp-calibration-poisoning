from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from datp.artifacts import (
    DATA_ROOT,
    OUTPUTS_DIR,
    RESULTS_PACKAGE_DIR,
    ArtifactLayout,
    check_run_state,
)
from datp.attacks.sensitivity import write_sensitivity_manifest
from datp.attacks.sweep import write_nbaiot_main_manifest
from datp.config import (
    BASE_CONFIG,
    CLUSTER_SENSITIVITY_FRACTIONS,
    CLUSTER_SENSITIVITY_K_GRID,
    CLUSTER_SENSITIVITY_N_INIT_GRID,
    CLUSTER_SENSITIVITY_RANDOM_STATES,
    DRAW_VARIANT_FRACTIONS,
    NBAIOT_MAIN_SOURCE_OBJECTIVE_PAIRS,
    CalibrationPoisoningConfig,
    ExperimentStage,
)
from datp.core import PolicyRunId, configure_logging, get_logger
from datp.enums import (
    CONTROLLED_POLICIES,
    ArtifactDir,
    CliCommand,
    CliExitCode,
    RunState,
    StatusColumn,
    StatusScope,
)
from datp.experiments import build_experiment_matrix, run_sweep
from datp.reporting.build import build_report_package
from datp.thresholding import results_exist
from datp.types import NarrativeText, SampleCount, SignedCount

console = Console()


logger = get_logger(__name__)


@dataclass(slots=True)
class _StageReport:
    complete: list[PolicyRunId] = field(default_factory=lambda: list[PolicyRunId]())
    missing: list[PolicyRunId] = field(default_factory=lambda: list[PolicyRunId]())
    aborted: list[PolicyRunId] = field(default_factory=lambda: list[PolicyRunId]())

    @property
    def total(self) -> SampleCount:
        return len(self.complete) + len(self.missing) + len(self.aborted)


@dataclass(frozen=True, slots=True)
class _SummaryRow:
    scope: NarrativeText | StatusScope
    complete: SampleCount
    missing: SignedCount
    aborted: SignedCount
    total: SampleCount


@dataclass(slots=True)
class _StatusReport:
    stage_reports: dict[ExperimentStage, _StageReport] = field(
        default_factory=lambda: dict[ExperimentStage, _StageReport]()
    )

    def summary_rows(self) -> list[_SummaryRow]:
        rows = [
            _SummaryRow(
                scope=f"Stage {stage.name}",
                complete=len(r.complete),
                missing=len(r.missing),
                aborted=len(r.aborted),
                total=r.total,
            )
            for stage, r in sorted(self.stage_reports.items(), key=lambda item: item[0])
        ]

        rows.append(
            _SummaryRow(
                scope=StatusScope.OVERALL,
                complete=sum(row.complete for row in rows),
                missing=sum(row.missing for row in rows),
                aborted=sum(row.aborted for row in rows),
                total=sum(row.total for row in rows),
            )
        )

        return rows

    def render_table(self) -> Table:
        table = Table(title="datp-cp Status", border_style="cyan")

        table.add_column(StatusColumn.SCOPE, justify="left", style="bold")
        table.add_column(StatusColumn.COMPLETE, justify="right", style="green")
        table.add_column(StatusColumn.MISSING, justify="right", style="yellow")
        table.add_column(StatusColumn.ABORTED, justify="right", style="red")
        table.add_column(StatusColumn.TOTAL, justify="right")

        for row in self.summary_rows():
            style = "bold" if row.scope is StatusScope.OVERALL else ""
            table.add_row(
                f"[{style}]{row.scope}[/{style}]" if style else row.scope,
                str(row.complete),
                str(row.missing),
                str(row.aborted),
                str(row.total),
            )

        return table


def get_status(base_dir: Path) -> _StatusReport:
    report = _StatusReport()

    for cell in build_experiment_matrix():
        stage = cell.stage
        rr = report.stage_reports.setdefault(stage, _StageReport())
        result_dir = (
            ArtifactLayout(base_dir=base_dir, stage=stage).policy_run(cell).result_dir
        )

        run_state = check_run_state(result_dir)
        if run_state is RunState.ABORTED:
            rr.aborted.append(cell)
        elif results_exist(cell.policy, cell.stage, cell.seed, base_dir=base_dir):
            rr.complete.append(cell)
        else:
            rr.missing.append(cell)

    return report


def print_status(base_dir: Path) -> None:
    logger.info("status report started", base_dir=base_dir.as_posix())
    report: _StatusReport = get_status(base_dir=base_dir)
    stage_reports: tuple[_StageReport, ...] = tuple(report.stage_reports.values())
    run_count: SampleCount = 0
    for stage_report in stage_reports:
        run_count += stage_report.total
    console.print(report.render_table())
    logger.info(
        "status report completed",
        stage_count=len(report.stage_reports),
        run_count=run_count,
    )


def baseline() -> None:
    """Train, score and evaluate the clean N-BaIoT baseline."""
    run_sweep(base_dir=OUTPUTS_DIR, data_root=DATA_ROOT)


def plan() -> None:
    """Print the baseline, poisoning and sensitivity grids without running them."""
    config = CalibrationPoisoningConfig.for_bounded_sweep()
    console.print(
        f"[bold]baseline[/bold]: {len(build_experiment_matrix())} policy runs "
        f"({len(CONTROLLED_POLICIES)} policies x {len(BASE_CONFIG.experiment.seeds)} seeds)"
    )
    console.print("[bold]poison[/bold]")
    console.print(f" policies  : {list(config.policies)}")
    console.print(f" pairs     : {list(NBAIOT_MAIN_SOURCE_OBJECTIVE_PAIRS)}")
    console.print(f" fractions : {list(config.fractions)}")
    console.print(f" seeds     : {len(config.seeds.training)} paired seeds")
    cells_per_victim = (
        len(config.policies)
        * len(NBAIOT_MAIN_SOURCE_OBJECTIVE_PAIRS)
        * len(config.fractions)
        * len(config.seeds.training)
    )
    console.print(f" cells/victim: {cells_per_victim}")
    console.print("[bold]sensitivity[/bold]")
    console.print(
        f" CLUSTER_STABILITY: k={list(CLUSTER_SENSITIVITY_K_GRID)} "
        f"n_init={list(CLUSTER_SENSITIVITY_N_INIT_GRID)} "
        f"random_states={len(CLUSTER_SENSITIVITY_RANDOM_STATES)} "
        f"fractions={list(CLUSTER_SENSITIVITY_FRACTIONS)}"
    )
    console.print(" SCALE_NORMALIZATION")
    console.print(f" DRAW_VARIANT: fractions={list(DRAW_VARIANT_FRACTIONS)}")
    console.print(" TRUST_BOUNDARY")


def poison() -> None:
    """Run the bounded calibration-poisoning sweep and write its manifest."""
    out_path = write_nbaiot_main_manifest(OUTPUTS_DIR)
    console.print(f"[bold green]Wrote bounded-sweep manifest:[/bold green] {out_path}")


def sensitivity() -> None:
    """Run the sensitivity analyses and write their manifest."""
    out_path = write_sensitivity_manifest(OUTPUTS_DIR)
    console.print(f"[bold green]Wrote sensitivity manifest:[/bold green] {out_path}")


def status() -> None:
    """Print the experiment status table."""
    print_status(OUTPUTS_DIR)


def report() -> None:
    """Audit results, build every report output and package them into results/."""
    try:
        paths = build_report_package(
            base_dir=OUTPUTS_DIR,
            results_dir=RESULTS_PACKAGE_DIR,
            data_root=DATA_ROOT,
            cfg=BASE_CONFIG,
        )
    except (FileNotFoundError, ValueError) as exc:
        logger.exception("report failed")
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=CliExitCode.ERROR) from exc
    for path in paths:
        console.print(f"[green]wrote[/green] {path}")


def _main_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(code=CliExitCode.ERROR)


app = typer.Typer(
    name="datp",
    invoke_without_command=True,
    callback=_main_callback,
    add_completion=False,
)

app.command(CliCommand.BASELINE)(baseline)
app.command(CliCommand.PLAN)(plan)
app.command(CliCommand.POISON)(poison)
app.command(CliCommand.SENSITIVITY)(sensitivity)
app.command(CliCommand.STATUS)(status)
app.command(CliCommand.REPORT)(report)


def cli_entry() -> None:
    """Configure logging and run the CLI app."""
    configure_logging(
        BASE_CONFIG.logging,
        log_dir=Path.cwd() / ArtifactDir.OUTPUTS / ArtifactDir.LOGS,
    )
    command = CliCommand.resolve(sys.argv[1:])
    logger.info("CLI invocation started", command=command)
    try:
        app()
    except SystemExit as exc:
        if exc.code is None or exc.code == CliExitCode.SUCCESS:
            logger.info("CLI invocation completed", command=command)
        else:
            logger.error(
                "CLI invocation failed",
                command=command,
                outcome=CliExitCode.ERROR,
            )
        raise
    except Exception:
        logger.exception("CLI invocation failed", command=command)
        raise
    logger.info("CLI invocation completed", command=command)
