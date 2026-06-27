"""Tests verifying audit validation warnings, utility tradeoff diagnostics, and worst-client stability alerts."""

from __future__ import annotations

from collections.abc import Callable

from datp.config.models import ExperimentStage
from datp.core.enums import MetricName, ThresholdPolicy
from datp.validation.enums import WarningCode, WorstDirection
from datp.validation.results import (
    CellPanel,
    check_local_threshold_utility_tradeoff,
    emit_flat_cv_tpr_warnings,
    emit_worst_client_stability_warnings,
)
from datp.validation.schemas import (
    WarningRecord,
    WorstClientRecord,
)

_STAGE = ExperimentStage.NBAIOT_MAIN


def test_flat_cv_tpr_warning_emitted() -> None:
    """Verify FLAT_CV_TPR_SUSPICIOUS warning is emitted when all policies yield identical CV TPR."""
    warnings_out: list[WarningRecord] = []
    cell_panel: dict[tuple[ExperimentStage, int, ThresholdPolicy], CellPanel] = {
        (_STAGE, 0, ThresholdPolicy.GLOBAL_THRESHOLD): CellPanel(cv_tpr=0.5),
        (_STAGE, 0, ThresholdPolicy.LOCAL_THRESHOLD): CellPanel(cv_tpr=0.5),
        (_STAGE, 0, ThresholdPolicy.CLUSTER_THRESHOLD): CellPanel(cv_tpr=0.5),
    }
    emit_flat_cv_tpr_warnings(cell_panel, warnings_out)
    assert any(w.code == "FLAT_CV_TPR_SUSPICIOUS" for w in warnings_out)


def test_no_flat_cv_tpr_warning_when_different() -> None:
    """Verify no FLAT_CV_TPR_SUSPICIOUS warning is emitted when policies yield differing CV TPR."""
    warnings_out: list[WarningRecord] = []
    cell_panel: dict[tuple[ExperimentStage, int, ThresholdPolicy], CellPanel] = {
        (_STAGE, 0, ThresholdPolicy.GLOBAL_THRESHOLD): CellPanel(cv_tpr=0.3),
        (_STAGE, 0, ThresholdPolicy.LOCAL_THRESHOLD): CellPanel(cv_tpr=0.6),
        (_STAGE, 0, ThresholdPolicy.CLUSTER_THRESHOLD): CellPanel(cv_tpr=0.4),
    }
    emit_flat_cv_tpr_warnings(cell_panel, warnings_out)
    assert not any(w.code == "FLAT_CV_TPR_SUSPICIOUS" for w in warnings_out)


def _worst_client_records(
    client_id_fn: Callable[[int], str],
) -> list[WorstClientRecord]:
    """Helper to build list of WorstClientRecord instances."""
    return [
        WorstClientRecord(
            run_id=f"nbaiot_main_global_seed{s}",
            seed=s,
            stage=_STAGE,
            policy=ThresholdPolicy.GLOBAL_THRESHOLD,
            metric=MetricName.FPR,
            direction=WorstDirection.MAX_IS_WORST,
            worst_client_id=client_id_fn(s),
            worst_value=0.9,
            eligible_pool_size=4,
        )
        for s in range(5)
    ]


def test_worst_client_stability_warning_when_always_same() -> None:
    """Verify WORST_CLIENT_STABLE warning is emitted when the worst client is identical across runs."""
    warnings_out: list[WarningRecord] = []
    emit_worst_client_stability_warnings(
        _worst_client_records(lambda _: "Danmini_Doorbell"), warnings_out
    )
    assert "WORST_CLIENT_STABLE" in [w.code for w in warnings_out]


def test_worst_client_varies_info_when_different() -> None:
    """Verify WORST_CLIENT_VARIES info is emitted when the worst client varies across runs."""
    warnings_out: list[WarningRecord] = []
    emit_worst_client_stability_warnings(
        _worst_client_records(lambda s: f"Client_{s}"), warnings_out
    )
    codes = [w.code for w in warnings_out]
    assert "WORST_CLIENT_VARIES" in codes
    assert "WORST_CLIENT_STABLE" not in codes


def test_check_local_threshold_utility_tradeoff_warns_when_local_improves_cv_fpr_but_worsens_utility() -> (
    None
):
    """Verify local utility tradeoff warnings are emitted when local threshold improves CV FPR but degrades macro F1 or PR-AUC."""
    warnings_out: list[WarningRecord] = []
    global_panel = CellPanel(
        cv_fpr=0.3, macro_f1_mean=0.85, pr_auc_mean=0.90, auroc_mean=0.92, cv_tpr=0.80
    )
    local_panel = CellPanel(
        cv_fpr=0.2, macro_f1_mean=0.80, pr_auc_mean=0.88, auroc_mean=0.91, cv_tpr=0.78
    )
    check_local_threshold_utility_tradeoff(
        (_STAGE, 0), global_panel, local_panel, warnings_out
    )
    codes = [w.code for w in warnings_out]
    assert WarningCode.LOCAL_UTILITY_TRADEOFF in codes
    msg = warnings_out[0].message
    assert "macro_f1" in msg
    assert "pr_auc" in msg


def test_check_local_threshold_utility_tradeoff_no_warning_when_cv_fpr_not_improved() -> (
    None
):
    """Verify no local utility tradeoff warning is emitted if local threshold does not improve CV FPR."""
    warnings_out: list[WarningRecord] = []
    global_panel = CellPanel(cv_fpr=0.2, macro_f1_mean=0.80)
    local_panel = CellPanel(cv_fpr=0.3, macro_f1_mean=0.85)
    check_local_threshold_utility_tradeoff(
        (_STAGE, 0), global_panel, local_panel, warnings_out
    )
    assert len(warnings_out) == 0


def test_check_local_threshold_utility_tradeoff_no_warning_when_no_utility_worsened() -> (
    None
):
    """Verify no local utility tradeoff warning is emitted if no utility metrics degrade."""
    warnings_out: list[WarningRecord] = []
    global_panel = CellPanel(
        cv_fpr=0.3, macro_f1_mean=0.80, auroc_mean=0.90, cv_tpr=0.75
    )
    local_panel = CellPanel(
        cv_fpr=0.2, macro_f1_mean=0.85, auroc_mean=0.92, cv_tpr=0.80
    )
    check_local_threshold_utility_tradeoff(
        (_STAGE, 0), global_panel, local_panel, warnings_out
    )
    assert len(warnings_out) == 0
