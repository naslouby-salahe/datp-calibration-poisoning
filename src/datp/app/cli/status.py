from dataclasses import dataclass, field
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from datp.artifacts.existence import results_exist
from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactFile
from datp.experiments.sweep import build_experiment_matrix

console = Console()


@dataclass(slots=True)
class _StageReport:
    """Internal accumulator — mutable during construction in get_status()."""

    stage: str
    complete: list = field(default_factory=list)
    missing: list = field(default_factory=list)
    aborted: list = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.complete) + len(self.missing) + len(self.aborted)

    @property
    def complete_count(self) -> int:
        return len(self.complete)

    @property
    def missing_count(self) -> int:
        return len(self.missing)

    @property
    def aborted_count(self) -> int:
        return len(self.aborted)


@dataclass(slots=True)
class _StatusReport:
    """Internal accumulator — mutable during construction in get_status()."""

    stage_reports: dict[str, _StageReport] = field(default_factory=dict)

    def summary_rows(self) -> list[tuple[str, int, int, int, int]]:
        rows: list[tuple[str, int, int, int, int]] = []
        total_complete = 0
        total_missing = 0
        total_aborted = 0
        total_all = 0

        for name in sorted(self.stage_reports):
            report = self.stage_reports[name]
            rows.append(
                (
                    f"Stage {name.upper()}",
                    report.complete_count,
                    report.missing_count,
                    report.aborted_count,
                    report.total,
                )
            )
            total_complete += report.complete_count
            total_missing += report.missing_count
            total_aborted += report.aborted_count
            total_all += report.total

        rows.append(
            ("Overall", total_complete, total_missing, total_aborted, total_all)
        )
        return rows

    def summary_lines(self) -> list[str]:
        lines: list[str] = []
        for label, complete, missing, aborted, total in self.summary_rows():
            lines.append(
                f"{label}: complete={complete} "
                f"missing={missing} "
                f"aborted={aborted} "
                f"(total={total})"
            )
        return lines

    def render_table(self) -> Table:
        table = Table(title="DATP Status", border_style="cyan")
        table.add_column("Scope", style="bold")
        table.add_column("Complete", justify="right", style="green")
        table.add_column("Missing", justify="right", style="yellow")
        table.add_column("Aborted", justify="right", style="red")
        table.add_column("Total", justify="right")

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
    cells = build_experiment_matrix()
    report = _StatusReport()

    for cell in cells:
        stage_key = cell.stage.value
        if stage_key not in report.stage_reports:
            report.stage_reports[stage_key] = _StageReport(stage=stage_key)

        rr = report.stage_reports[stage_key]

        rp = (
            ArtifactLayout(base_dir=base_dir, stage=cell.stage)
            .policy_run(cell)
            .result_dir
        )

        aborted_file = rp / ArtifactFile.RUN_ABORTED
        if aborted_file.is_file():
            rr.aborted.append(cell)
        elif results_exist(cell.policy, cell.stage, cell.seed, base_dir=base_dir):
            rr.complete.append(cell)
        else:
            rr.missing.append(cell)

    return report


def status(
    base_dir: Path = typer.Option(..., help="Root output directory"),
) -> None:
    """Report experiment cell completion status."""
    report = get_status(base_dir=base_dir)
    console.print(report.render_table())
