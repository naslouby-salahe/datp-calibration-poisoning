from datp.types import (
    NarrativeText,
    SampleCount,
    SignedCount,
)

from dataclasses import dataclass, field
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from datp.artifacts.existence import results_exist
from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.lifecycle import check_run_state
from datp.artifacts.names import RunState
from datp.cli.enums import StatusColumn, StatusScope
from datp.config.models import ExperimentStage
from datp.core.logging import get_logger
from datp.core.identity import PolicyRunId
from datp.experiments.sweep import build_experiment_matrix, run_sweep

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
            for stage, r in sorted(
                self.stage_reports.items(), key=lambda item: item[0]
            )
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
        if stage not in report.stage_reports:
            report.stage_reports[stage] = _StageReport()

        rr = report.stage_reports[stage]
        rp = (
            ArtifactLayout(base_dir=base_dir, stage=cell.stage)
            .policy_run(cell)
            .result_dir
        )

        run_state = check_run_state(rp)
        if run_state is RunState.ABORTED:
            rr.aborted.append(cell)
        elif results_exist(cell.policy, cell.stage, cell.seed, base_dir=base_dir):
            rr.complete.append(cell)
        else:
            rr.missing.append(cell)

    return report


def status(base_dir: Path = typer.Option(...)) -> None:
    """Print the experiment status table."""
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


def sweep(
    dry_run: bool = typer.Option(False, "--dry-run/--no-dry-run"),
    base_dir: Path = typer.Option(...),
    data_root: Path = typer.Option(Path.cwd()),
) -> None:
    """Run the full experiment sweep."""
    run_sweep(dry_run=dry_run, base_dir=base_dir, data_root=data_root)
