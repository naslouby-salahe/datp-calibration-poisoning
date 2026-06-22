from __future__ import annotations

from collections.abc import Callable

from datp.core.enums import ThresholdPolicy
from datp.config.stages import ExperimentStage
from datp.core.metric_enums import MetricName
from datp.validation._audit_types import _CellPanel
from datp.validation.enums import HomogeneityVerdict, WarningCode, WorstDirection
from datp.validation.schemas import (
    CICIoTHomogeneityRecord,
    WarningRecord,
    WorstClientRecord,
)

_STAGE = ExperimentStage.NBAIOT_MAIN


def _homogeneity_record(
    verdict: HomogeneityVerdict,
    *,
    js_mean: float | None = 0.02,
    n_clients: int = 10,
) -> CICIoTHomogeneityRecord:
    return CICIoTHomogeneityRecord(
        stage=_STAGE,
        seed=0,
        policy=ThresholdPolicy.GLOBAL_THRESHOLD,
        n_clients_compared=n_clients,
        n_pairs=max(0, n_clients * (n_clients - 1) // 2),
        n_bins=20,
        pairwise_js_mean=js_mean,
        pairwise_js_std=0.01 if js_mean is not None else None,
        pairwise_js_p50=js_mean,
        pairwise_js_p95=None,
        pairwise_js_max=None,
        fingerprint_method="benign_recon_error_histogram",
        homogeneity_verdict=verdict,
    )


# ── Flat CV-TPR warnings ──────────────────────────────────────────────────────


def test_flat_cv_tpr_warning_emitted() -> None:
    from datp.validation._warnings import emit_flat_cv_tpr_warnings

    warnings_out: list[WarningRecord] = []
    cell_panel: dict[tuple[ExperimentStage, int, ThresholdPolicy], _CellPanel] = {
        (_STAGE, 0, ThresholdPolicy.GLOBAL_THRESHOLD): _CellPanel(cv_tpr=0.5),
        (_STAGE, 0, ThresholdPolicy.LOCAL_THRESHOLD): _CellPanel(cv_tpr=0.5),
        (_STAGE, 0, ThresholdPolicy.CLUSTER_THRESHOLD): _CellPanel(cv_tpr=0.5),
    }
    emit_flat_cv_tpr_warnings(cell_panel, warnings_out)
    assert any(w.code == "FLAT_CV_TPR_SUSPICIOUS" for w in warnings_out)


def test_no_flat_cv_tpr_warning_when_different() -> None:
    from datp.validation._warnings import emit_flat_cv_tpr_warnings

    warnings_out: list[WarningRecord] = []
    cell_panel: dict[tuple[ExperimentStage, int, ThresholdPolicy], _CellPanel] = {
        (_STAGE, 0, ThresholdPolicy.GLOBAL_THRESHOLD): _CellPanel(cv_tpr=0.3),
        (_STAGE, 0, ThresholdPolicy.LOCAL_THRESHOLD): _CellPanel(cv_tpr=0.6),
        (_STAGE, 0, ThresholdPolicy.CLUSTER_THRESHOLD): _CellPanel(cv_tpr=0.4),
    }
    emit_flat_cv_tpr_warnings(cell_panel, warnings_out)
    assert not any(w.code == "FLAT_CV_TPR_SUSPICIOUS" for w in warnings_out)


# ── Worst-client stability warnings ──────────────────────────────────────────


def _worst_client_records(
    client_id_fn: "Callable[[int], str]",
) -> list[WorstClientRecord]:
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
    from datp.validation._warnings import emit_worst_client_stability_warnings

    warnings_out: list[WarningRecord] = []
    emit_worst_client_stability_warnings(
        _worst_client_records(lambda _: "Danmini_Doorbell"), warnings_out
    )
    assert "WORST_CLIENT_STABLE" in [w.code for w in warnings_out]


def test_worst_client_varies_info_when_different() -> None:
    from datp.validation._warnings import emit_worst_client_stability_warnings

    warnings_out: list[WarningRecord] = []
    emit_worst_client_stability_warnings(
        _worst_client_records(lambda s: f"Client_{s}"), warnings_out
    )
    codes = [w.code for w in warnings_out]
    assert "WORST_CLIENT_VARIES" in codes
    assert "WORST_CLIENT_STABLE" not in codes


# ── LOCAL_THRESHOLD utility tradeoff warnings ─────────────────────────────────


def test_check_local_threshold_utility_tradeoff_warns_when_local_improves_cv_fpr_but_worsens_utility() -> (
    None
):
    from datp.validation._warnings import check_local_threshold_utility_tradeoff

    warnings_out: list[WarningRecord] = []
    global_panel = _CellPanel(
        cv_fpr=0.3, macro_f1_mean=0.85, pr_auc_mean=0.90, auroc_mean=0.92, cv_tpr=0.80
    )
    local_panel = _CellPanel(
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
    from datp.validation._warnings import check_local_threshold_utility_tradeoff

    warnings_out: list[WarningRecord] = []
    global_panel = _CellPanel(cv_fpr=0.2, macro_f1_mean=0.80)
    local_panel = _CellPanel(cv_fpr=0.3, macro_f1_mean=0.85)
    check_local_threshold_utility_tradeoff(
        (_STAGE, 0), global_panel, local_panel, warnings_out
    )
    assert len(warnings_out) == 0


def test_check_local_threshold_utility_tradeoff_no_warning_when_no_utility_worsened() -> (
    None
):
    from datp.validation._warnings import check_local_threshold_utility_tradeoff

    warnings_out: list[WarningRecord] = []
    global_panel = _CellPanel(
        cv_fpr=0.3, macro_f1_mean=0.80, auroc_mean=0.90, cv_tpr=0.75
    )
    local_panel = _CellPanel(
        cv_fpr=0.2, macro_f1_mean=0.85, auroc_mean=0.92, cv_tpr=0.80
    )
    check_local_threshold_utility_tradeoff(
        (_STAGE, 0), global_panel, local_panel, warnings_out
    )
    assert len(warnings_out) == 0


# ── CICIoT homogeneity warnings ───────────────────────────────────────────────


def test_emit_ciciot_homogeneity_warning_homogeneous() -> None:
    from datp.validation._warnings import emit_ciciot_homogeneity_warnings

    warnings_out: list[WarningRecord] = []
    emit_ciciot_homogeneity_warnings(
        [_homogeneity_record(HomogeneityVerdict.HOMOGENEOUS, js_mean=0.02)],
        warnings_out,
        homogeneity_threshold=0.05,
    )
    assert any(w.code == WarningCode.CICIOT_HOMOGENEITY_VERIFIED for w in warnings_out)


def test_emit_ciciot_homogeneity_warning_heterogeneous() -> None:
    from datp.validation._warnings import emit_ciciot_homogeneity_warnings

    warnings_out: list[WarningRecord] = []
    emit_ciciot_homogeneity_warnings(
        [_homogeneity_record(HomogeneityVerdict.HETEROGENEOUS, js_mean=0.12)],
        warnings_out,
        homogeneity_threshold=0.05,
    )
    assert any(w.code == WarningCode.CICIOT_NOT_HOMOGENEOUS for w in warnings_out)


def test_emit_ciciot_homogeneity_warning_incomplete() -> None:
    from datp.validation._warnings import emit_ciciot_homogeneity_warnings

    warnings_out: list[WarningRecord] = []
    emit_ciciot_homogeneity_warnings(
        [
            _homogeneity_record(
                HomogeneityVerdict.BLOCKED_PENDING_RUN, js_mean=None, n_clients=1
            )
        ],
        warnings_out,
        homogeneity_threshold=0.05,
    )
    assert WarningCode.CICIOT_HOMOGENEITY_INCOMPLETE in [w.code for w in warnings_out]
