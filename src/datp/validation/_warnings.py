"""Warning emission functions for the results audit."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from datp.core.enums import Baseline, Regime
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


def emit_worst_client_stability_warnings(
    worst_client_records: list[WorstClientRecord],
    warnings: list[WarningRecord],
) -> None:
    """Warn when the same client is worst across seeds, indicating a likely encoder-quality limitation."""
    grouped: dict[
        tuple[Regime, str | None, Baseline, MetricName], list[tuple[int, str | None]]
    ] = defaultdict(list)
    for record in worst_client_records:
        if record.worst_client_id is None:
            continue
        grouped[(record.regime, record.alpha, record.baseline, record.metric)].append(
            (record.seed, record.worst_client_id)
        )
    for (regime, alpha_text, baseline, metric), entries in sorted(grouped.items()):
        if len(entries) < WORST_CLIENT_STABLE_MIN_SEEDS:
            continue
        ids = sorted({cid for _, cid in entries if cid is not None})
        if len(ids) == 1:
            warnings.append(
                WarningRecord(
                    severity=AuditSeverity.WARNING,
                    code=WarningCode.WORST_CLIENT_STABLE,
                    message=(
                        f"{regime}/{baseline}/alpha={alpha_text} worst client on {metric} is "
                        f"{ids[0]} across all {len(entries)} seeds; treat as encoder-quality "
                        "limitation, not threshold-strategy effect."
                    ),
                )
            )
        else:
            warnings.append(
                WarningRecord(
                    severity=AuditSeverity.INFO,
                    code=WarningCode.WORST_CLIENT_VARIES,
                    message=(
                        f"{regime}/{baseline}/alpha={alpha_text} worst client on {metric} "
                        f"varies across {len(entries)} seeds: {ids}."
                    ),
                )
            )


def emit_ciciot_homogeneity_warnings(
    homogeneity_records: list[CICIoTHomogeneityRecord],
    warnings: list[WarningRecord],
    *,
    homogeneity_threshold: float,
) -> None:
    """Emit CICIoT2023 homogeneity warnings based on pairwise JS divergence."""
    for record in homogeneity_records:
        cell = f"regime={record.regime}/seed={record.seed}/baseline={record.baseline}"
        if record.homogeneity_verdict == HomogeneityVerdict.HOMOGENEOUS:
            warnings.append(
                WarningRecord(
                    severity=AuditSeverity.INFO,
                    code=WarningCode.CICIOT_HOMOGENEITY_VERIFIED,
                    message=(
                        f"{cell} pairwise JS mean "
                        f"{record.pairwise_js_mean:.4g} < {homogeneity_threshold}; "
                        "reported claims may describe CICIoT2023 clients as homogeneous."
                    ),
                )
            )
        elif record.homogeneity_verdict == HomogeneityVerdict.HETEROGENEOUS:
            warnings.append(
                WarningRecord(
                    severity=AuditSeverity.WARNING,
                    code=WarningCode.CICIOT_NOT_HOMOGENEOUS,
                    message=(
                        f"{cell} pairwise JS mean "
                        f"{record.pairwise_js_mean:.4g} \u2265 {homogeneity_threshold}; "
                        "reported claims must not describe CICIoT2023 clients as homogeneous."
                    ),
                )
            )
        else:
            warnings.append(
                WarningRecord(
                    severity=AuditSeverity.BLOCKED_PENDING_RUN,
                    code=WarningCode.CICIOT_HOMOGENEITY_INCOMPLETE,
                    message=f"{cell} pairwise homogeneity could not be computed (insufficient client data).",
                    exact_command=BLOCKED_RESUME_COMMAND,
                )
            )


def emit_flat_cv_tpr_warnings(
    cell_panel: "dict[tuple[Regime, int, str | None, Baseline], _CellPanel]",
    warnings: list[WarningRecord],
) -> None:
    """Warn when CV(TPR) is suspiciously identical across baselines in a cell."""
    by_cell: dict[tuple[Regime, int, str | None], list[float]] = defaultdict(list)
    for (regime, seed, alpha_text, _), panel in cell_panel.items():
        if panel.cv_tpr is not None:
            by_cell[(regime, seed, alpha_text)].append(float(panel.cv_tpr))
    for key, values in by_cell.items():
        if len(values) < 2:
            continue
        spread = max(values) - min(values)
        if spread < FLAT_CV_TPR_EPSILON:
            regime, seed, alpha_text = key
            warnings.append(
                WarningRecord(
                    severity=AuditSeverity.WARNING,
                    code=WarningCode.FLAT_CV_TPR_SUSPICIOUS,
                    message=(
                        f"{regime}_seed{seed}_alpha{alpha_text} CV(TPR) is identical across "
                        f"{len(values)} baselines (spread {spread:.2e}); investigate denominator, "
                        "NaN fill, or zero-attack-client aggregation."
                    ),
                )
            )


def check_b2_utility_tradeoff(
    regime: Regime,
    seed: int,
    alpha_text: str | None,
    b1: "_CellPanel",
    b2: "_CellPanel",
    warnings: list[WarningRecord],
) -> None:
    """Warn when B2 improves CV(FPR) but worsens utility metrics relative to B1."""
    if b1.cv_fpr is None or b2.cv_fpr is None or b2.cv_fpr >= b1.cv_fpr:
        return
    worsened: list[MetricName] = []
    if (
        b1.macro_f1_mean is not None
        and b2.macro_f1_mean is not None
        and b2.macro_f1_mean < b1.macro_f1_mean
    ):
        worsened.append(MetricName.MACRO_F1)
    if (
        b1.pr_auc_mean is not None
        and b2.pr_auc_mean is not None
        and b2.pr_auc_mean < b1.pr_auc_mean
    ):
        worsened.append(MetricName.PR_AUC)
    if (
        b1.auroc_mean is not None
        and b2.auroc_mean is not None
        and b2.auroc_mean < b1.auroc_mean
    ):
        worsened.append(MetricName.AUROC)
    if b1.cv_tpr is not None and b2.cv_tpr is not None and b2.cv_tpr < b1.cv_tpr:
        worsened.append(MetricName.CV_TPR)
    if worsened:
        warnings.append(
            WarningRecord(
                severity=AuditSeverity.WARNING,
                code=WarningCode.B2_UTILITY_TRADEOFF,
                message=f"{regime}_seed{seed}_alpha{alpha_text} B2 improves CV(FPR) but worsens {', '.join(worsened)} relative to B1.",
            )
        )
