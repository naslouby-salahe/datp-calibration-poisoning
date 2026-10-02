
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from datp.cli.enums import AuditColumn, AuditCommand
from datp.config.compose import BASE_CONFIG
from datp.core.logging import get_logger
from datp.validation.results import AuditOutputPaths, run_results_audit
from datp.validation.verdicts import compute_all_verdicts

app = typer.Typer()
console = Console()
logger = get_logger(__name__)


@app.command(AuditCommand.RESULTS)
def results(
    base_dir: Path = typer.Option(...),
    audit_dir: Path | None = typer.Option(None),
    data_root: Path = typer.Option(Path(".")),
) -> None:
    """Run the results audit and print a table of generated artifact paths."""
    from datp.config.compose import BASE_CONFIG
    from datp.validation.enums import AuditDir

    paths: AuditOutputPaths = run_results_audit(
        base_dir=base_dir,
        audit_dir=audit_dir or (Path("artifacts") / AuditDir.AUDIT),
        cfg=BASE_CONFIG,
        data_root=data_root,
    )

    table = Table(title="datp-cp Results Audit", border_style="cyan")
    table.add_column(AuditColumn.ARTIFACT, style="bold")
    table.add_column(AuditColumn.PATH)

    for name, path in paths.items():
        table.add_row(name, str(path))

    console.print(table)


@app.command(AuditCommand.REUSE)
def reuse(
    base_dir: Path = typer.Option(...),
    data_root: Path | None = typer.Option(None),
) -> None:
    verdicts = compute_all_verdicts(
        base_dir,
        data_root=data_root,
        config=BASE_CONFIG,
        write_reports=True,
    )
    table = Table(title="datp-cp Reuse Audit", border_style="cyan")
    table.add_column("Stage")
    table.add_column("Seed", justify="right")
    table.add_column("Verdict")
    table.add_column("Reason")
    for cell in verdicts.cells:
        table.add_row(
            cell.cell.stage,
            str(cell.cell.seed),
            cell.verdict,
            cell.reason,
        )
    console.print(table)
    logger.info(
        "reuse audit completed",
        cell_count=verdicts.summary.total,
        reuse_safe=verdicts.summary.verified_reuse_safe,
        rerun_required=verdicts.summary.reuse_blocked_rerun_required,
        base_dir=base_dir.as_posix(),
    )
