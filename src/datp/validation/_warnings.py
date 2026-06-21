"""Warning emission functions for the results audit."""

from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

from collections import defaultdict
from typing import TYPE_CHECKING

from datp.config.stages import ExperimentStage
from datp.core.metric_enums import MetricName
from datp.validation.constants import (
    BLOCKED_RESUME_COMMAND,
    FLAT_CV_TPR_EPSILON,
    WORST_CLIENT_STABLE_MIN_SEEDS,
)
from datp.validation.enums import (
    AuditSeverity,
    HomogeneityVerdict,
    WarningCode,
)
from datp.validation.schemas import (
    CICIoTHomogeneityRecord,
    WarningRecord,
    WorstClientRecord,
)

if TYPE_CHECKING:
    from datp.validation._audit_types import _CellPanel


def _is_worsened(global_val: float | None, local_val: float | None) -> bool:
    return global_val is not None and local_val is not None and local_val < global_val


def _emit_worst_client_group_warning(
    key: tuple[ExperimentStage, ThresholdPolicy, MetricName],
    entries: list[tuple[int, str | None]],
    warnings: list[WarningRecord],
) -> None:
    stage, policy, metric = key
    ids = sorted({cid for _, cid in entries if cid is not None})
    if len(ids) == 1:
        warnings.append(
            WarningRecord(
                severity=AuditSeverity.WARNING,
                code=WarningCode.WORST_CLIENT_STABLE,
                message=(
                    f"{stage}/{policy} worst client on {metric} is "
                    f"{ids[0]} across all {len(entries)} seeds; treat as encoder-quality "
                    "limitation, not threshold-strategy effect."
                ),
            )
        )
    elif len(ids) > 1:
        warnings.append(
            WarningRecord(
                severity=AuditSeverity.WARNING,
                code=WarningCode.WORST_CLIENT_VARIES,
                message=(
                    f"{stage}/{policy} worst client on {metric} rotates among "
                    f"{ids} across {len(entries)} seeds; verify encoder stability."
                ),
            )
        )


def emit_worst_client_stability_warnings(
    worst_client_records: list[WorstClientRecord],
    warnings: list[WarningRecord],
) -> None:
    grouped: dict[
        tuple[ExperimentStage, ThresholdPolicy, MetricName], list[tuple[int, str | None]]
    ] = defaultdict(list)
    for record in worst_client_records:
        grouped[(record.stage, record.policy, record.metric)].append(
            (record.seed, record.worst_client_id)
        )
    for key, entries in grouped.items():
        if len(entries) >= WORST_CLIENT_STABLE_MIN_SEEDS:
            cell = f"stage={entries[0][0] if entries else '?'}/policy={key[1]}"
            _ = cell  # suppress unused warning; message built in group warning
            _emit_worst_client_group_warning(key, entries, warnings)


def _emit_flat_cv_tpr_cell_warning(
    cell_key: tuple[ExperimentStage, int],
    tpr_values: list[float],
    warnings: list[WarningRecord],
) -> None:
    stage, seed = cell_key
    if len(set(tpr_values)) == 1:
        warnings.append(
            WarningRecord(
                severity=AuditSeverity.WARNING,
                code=WarningCode.FLAT_CV_TPR_SUSPICIOUS,
                message=f"{stage}_seed{seed} CV(TPR) is identical across "
                f"all policies ({tpr_values[0]:.4f}); verify threshold attribution.",
            )
        )
    elif all(abs(v - tpr_values[0]) < FLAT_CV_TPR_EPSILON for v in tpr_values):
        warnings.append(
            WarningRecord(
                severity=AuditSeverity.WARNING,
                code=WarningCode.FLAT_CV_TPR_SUSPICIOUS,
                message=f"{stage}_seed{seed} CV(TPR) is nearly identical across "
                f"all policies (range < {FLAT_CV_TPR_EPSILON}); verify threshold attribution.",
            )
        )


def emit_flat_cv_tpr_warnings(
    cell_panel: "dict[tuple[ExperimentStage, int, ThresholdPolicy], _CellPanel]",
    warnings: list[WarningRecord],
) -> None:
    by_cell: dict[tuple[ExperimentStage, int], list[float]] = defaultdict(list)
    for (stage, seed, _), panel in cell_panel.items():
        if panel.cv_tpr is not None:
            by_cell[(stage, seed)].append(float(panel.cv_tpr))
    for cell_key, tpr_values in by_cell.items():
        if len(tpr_values) >= 2:
            _emit_flat_cv_tpr_cell_warning(cell_key, tpr_values, warnings)


def _emit_local_utility_warning(
    cell_key: tuple[ExperimentStage, int],
    b1: "_CellPanel",
    b2: "_CellPanel",
    warnings: list[WarningRecord],
) -> None:
    stage, seed = cell_key
    worsened: list[str] = []
    if _is_worsened(b1.macro_f1_mean, b2.macro_f1_mean):
        worsened.append("macro_f1_mean")
    if _is_worsened(b1.auroc_mean, b2.auroc_mean):
        worsened.append("auroc_mean")
    if _is_worsened(b1.pr_auc_mean, b2.pr_auc_mean):
        worsened.append("pr_auc_mean")
    if worsened:
        warnings.append(
            WarningRecord(
                severity=AuditSeverity.WARNING,
                code=WarningCode.LOCAL_UTILITY_TRADEOFF,
                message=f"{stage}_seed{seed} LOCAL_THRESHOLD improves CV(FPR) but worsens {', '.join(worsened)} relative to GLOBAL_THRESHOLD.",
            )
        )


def check_local_threshold_utility_tradeoff(
    cell_key: tuple[ExperimentStage, int],
    b1: "_CellPanel",
    b2: "_CellPanel",
    warnings: list[WarningRecord],
) -> None:
    _emit_local_utility_warning(cell_key, b1, b2, warnings)


def emit_ciciot_homogeneity_warnings(
    homogeneity_records: list[CICIoTHomogeneityRecord],
    warnings: list[WarningRecord],
    *,
    homogeneity_threshold: float,
) -> None:
    for record in homogeneity_records:
        if record.homogeneity_verdict == HomogeneityVerdict.HOMOGENEOUS:
            warnings.append(
                WarningRecord(
                    severity=AuditSeverity.INFO,
                    code=WarningCode.CICIOT_HOMOGENEITY_VERIFIED,
                    message=(
                        f"CICIoT2023 clients are homogeneous "
                        f"(JS mean={record.pairwise_js_mean:.4f} < {homogeneity_threshold})."
                    ),
                )
            )
        elif record.homogeneity_verdict == HomogeneityVerdict.HETEROGENEOUS:
            warnings.append(
                WarningRecord(
                    severity=AuditSeverity.WARNING,
                    code=WarningCode.CICIOT_NOT_HOMOGENEOUS,
                    message=(
                        f"CICIoT2023 clients are heterogeneous "
                        f"(JS mean={record.pairwise_js_mean:.4f} >= {homogeneity_threshold}); "
                        "claims of homogeneous CICIoT2023 behavior are not supported."
                    ),
                )
            )
        elif record.homogeneity_verdict == HomogeneityVerdict.BLOCKED_PENDING_RUN:
            warnings.append(
                WarningRecord(
                    severity=AuditSeverity.BLOCKED_PENDING_RUN,
                    code=WarningCode.CICIOT_HOMOGENEITY_INCOMPLETE,
                    message="CICIoT2023 homogeneity verdict is BLOCKED_PENDING_RUN; "
                    "cannot confirm or deny homogeneity claims.",
                    exact_command=BLOCKED_RESUME_COMMAND,
                )
            )
