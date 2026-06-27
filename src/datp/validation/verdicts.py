"""Cell-level reuse verdicts: manifest checks + metric reproduction → safe/blocked."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from datp.artifacts.io import write_json_atomic
from datp.artifacts.names import ArtifactDir
from datp.config.models import DatpConfig
from datp.config.models import ExperimentStage
from datp.validation.discovery import iter_score_cells
from datp.validation.enums import AuditArtifact, AuditStatus, ReuseVerdict
from datp.validation.metric_reproducer import (
    CellReproductionResult,
    reproduce_cell_metrics,
)
from datp.validation.schemas import (
    CellVerdict,
    ScoreCellVerification,
    ValidationCheck,
    VerdictSummary,
    VerdictTable,
)
from datp.validation.score_manifest import (
    verify_score_cell,
)

REASON_ALL_PASS = "all checks passed"
MANIFEST_PREFIX = "manifest"
REPRODUCTION_PREFIX = "reproduction"


def failing_manifest_entries(
    manifest_report: ScoreCellVerification,
) -> list[ValidationCheck]:
    """Extract manifest checks that did not pass from a score-cell verification report."""
    return [
        ValidationCheck(
            code=f"{MANIFEST_PREFIX}:{check.code}",
            status=check.status,
            detail=check.detail,
        )
        for check in manifest_report.checks
        if check.status != AuditStatus.PASS
    ]


def failing_reproduction_entries(
    reproduction_result: CellReproductionResult,
) -> list[ValidationCheck]:
    """Extract reproduction checks that did not pass, including missing-policy entries."""
    entries = [
        ValidationCheck(
            code=f"{REPRODUCTION_PREFIX}:{policy_result.policy.value}.{check.code}",
            status=check.status,
            detail=check.detail,
        )
        for policy_result in reproduction_result.policies
        for check in policy_result.checks
        if check.status != AuditStatus.PASS
    ]
    entries.extend(
        [
            ValidationCheck(
                code=f"{REPRODUCTION_PREFIX}:{missing_policy.value}.metrics_json_missing",
                status=AuditStatus.MISSING,
                detail=f"metrics.json absent for policy {missing_policy.value}",
            )
            for missing_policy in reproduction_result.missing_policies
        ]
    )
    return entries


def summarize_reason(failed_checks: list[ValidationCheck]) -> str:
    """Condense a list of failed checks into a short human-readable reason string."""
    if not failed_checks:
        return REASON_ALL_PASS
    codes = [f"{entry.code}({entry.status.value})" for entry in failed_checks]
    return (
        "; ".join(codes)
        if len(codes) <= 5
        else f"{'; '.join(codes[:5])}; +{len(codes) - 5} more"
    )


def compute_reuse_verdict(
    manifest_report: ScoreCellVerification, reproduction_result: CellReproductionResult
) -> CellVerdict:
    """Combine manifest and reproduction results into a single reuse-verdict for a score cell."""
    if manifest_report.cell != reproduction_result.cell:
        raise ValueError(
            f"verdict inputs disagree on cell: manifest={manifest_report.cell!r}, reproduction={reproduction_result.cell!r}"
        )

    manifest_status, reproduction_status = (
        manifest_report.overall_status,
        reproduction_result.overall_status,
    )
    failed = failing_manifest_entries(manifest_report) + failing_reproduction_entries(
        reproduction_result
    )

    return CellVerdict(
        cell=manifest_report.cell,
        verdict=ReuseVerdict.VERIFIED_REUSE_SAFE
        if manifest_status == AuditStatus.PASS
        and reproduction_status == AuditStatus.PASS
        else ReuseVerdict.REUSE_BLOCKED_RERUN_REQUIRED,
        manifest_status=manifest_status,
        reproduction_status=reproduction_status,
        reason=summarize_reason(failed),
        failed_checks=failed,
    )


def summarize_verdicts(cells: list[CellVerdict]) -> VerdictSummary:
    """Aggregate cell-level verdicts into a summary with per-stage breakdowns."""
    by_stage: dict[ExperimentStage, dict[ReuseVerdict, int]] = {}
    safe, blocked = 0, 0

    for cell in cells:
        if cell.cell.stage not in by_stage:
            by_stage[cell.cell.stage] = dict.fromkeys(ReuseVerdict, 0)
        by_stage[cell.cell.stage][cell.verdict] += 1

        if cell.verdict == ReuseVerdict.VERIFIED_REUSE_SAFE:
            safe += 1
        else:
            blocked += 1

    return VerdictSummary(
        total=len(cells),
        verified_reuse_safe=safe,
        reuse_blocked_rerun_required=blocked,
        by_stage=by_stage,
    )


def compute_all_verdicts(
    base_dir: Path,
    *,
    data_root: Path | None = None,
    config: DatpConfig | None = None,
    write_reports: bool = False,
) -> VerdictTable:
    """Compute reuse verdicts for all score cells under base_dir, optionally writing reports."""
    resolved_base = base_dir.resolve()
    resolved_data_root = (data_root or resolved_base.parent).resolve()

    def process_location(location):
        manifest_report = verify_score_cell(
            location.cell_dir, resolved_base, data_root=resolved_data_root
        )
        reproduction_result = reproduce_cell_metrics(
            location.cell_dir, resolved_base, config=config
        )
        return location, compute_reuse_verdict(manifest_report, reproduction_result)

    with ThreadPoolExecutor() as executor:
        results = list(executor.map(process_location, iter_score_cells(resolved_base)))

    cells = [res[1] for res in results]
    table = VerdictTable(cells=cells, summary=summarize_verdicts(cells))

    if write_reports:
        for loc, cell_verdict in results:
            write_json_atomic(
                loc.cell_dir / AuditArtifact.CELL_VERDICT,
                cell_verdict.model_dump(mode="json"),
            )
        write_json_atomic(
            resolved_base / ArtifactDir.SCORES / AuditArtifact.CELL_VERDICTS,
            table.model_dump(mode="json"),
        )

    return table
