"""Top-level CLI commands: status table and experiment sweep."""

from dataclasses import dataclass, field
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from datp.artifacts.existence import results_exist
from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactFile
from datp.cli.enums import StatusColumn
from datp.experiments.sweep import build_experiment_matrix, run_sweep

console = Console()


@dataclass(slots=True)
class _StageReport:
    """Per-stage counts of complete, missing, and aborted runs."""

    stage: str
    complete: list = field(default_factory=list)
    missing: list = field(default_factory=list)
    aborted: list = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.complete) + len(self.missing) + len(self.aborted)


@dataclass(slots=True)
class _StatusReport:
    """Aggregate status across all experiment stages."""

    stage_reports: dict[str, _StageReport] = field(default_factory=dict)

    def summary_rows(self) -> list[tuple[str, int, int, int, int]]:
        """Return a list of (label, complete, missing, aborted, total) rows."""
        rows = [
            (
                f"Stage {name.upper()}",
                len(r.complete),
                len(r.missing),
                len(r.aborted),
                r.total,
            )
            for name, r in sorted(self.stage_reports.items())
        ]

        rows.append(
            (
                "Overall",
                sum(r[1] for r in rows),
                sum(r[2] for r in rows),
                sum(r[3] for r in rows),
                sum(r[4] for r in rows),
            )
        )

        return rows

    def render_table(self) -> Table:
        """Render the status report as a Rich table."""
        table = Table(title="datp-cp Status", border_style="cyan")

        table.add_column(StatusColumn.SCOPE.value, justify="left", style="bold")
        table.add_column(StatusColumn.COMPLETE.value, justify="right", style="green")
        table.add_column(StatusColumn.MISSING.value, justify="right", style="yellow")
        table.add_column(StatusColumn.ABORTED.value, justify="right", style="red")
        table.add_column(StatusColumn.TOTAL.value, justify="right")

        for label, complete, missing, aborted, total in self.summary_rows():
            style = "bold" if label == "Overall" else ""
            table.add_row(
                f"[{style}]{label}[/{style}]" if style else label,
                str(complete),
                str(missing),
                str(aborted),
                str(total),
            )

        return table


def get_status(base_dir: Path) -> _StatusReport:
    """Build a StatusReport by scanning artifact directories for all experiment cells."""
    report = _StatusReport()

    for cell in build_experiment_matrix():
        stage_key = cell.stage.value
        if stage_key not in report.stage_reports:
            report.stage_reports[stage_key] = _StageReport(stage=stage_key)

        rr = report.stage_reports[stage_key]
        rp = (
            ArtifactLayout(base_dir=base_dir, stage=cell.stage)
            .policy_run(cell)
            .result_dir
        )

        if (rp / ArtifactFile.RUN_ABORTED).is_file():
            rr.aborted.append(cell)
        elif results_exist(cell.policy, cell.stage, cell.seed, base_dir=base_dir):
            rr.complete.append(cell)
        else:
            rr.missing.append(cell)

    return report


def status(base_dir: Path = typer.Option(...)) -> None:
    """Print the experiment status table."""
    console.print(get_status(base_dir=base_dir).render_table())


def sweep(
    dry_run: bool = typer.Option(False, "--dry-run/--no-dry-run"),
    base_dir: Path = typer.Option(...),
    data_root: Path = typer.Option(Path.cwd()),
) -> None:
    """Run the full experiment sweep."""
    run_sweep(dry_run=dry_run, base_dir=base_dir, data_root=data_root)
