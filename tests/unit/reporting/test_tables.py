from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

import csv
import math
from pathlib import Path

import numpy as np
import pytest

from datp.config.compose import BASE_CONFIG
from datp.config.stages import ExperimentStage
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.core.types import ClientThreshold
from datp.data.catalog import DatasetID
from datp.evaluation.metrics import (
    BinaryMetrics,
    ClientEvaluationRecord,
    ConfusionCounts,
    DispersionMetrics,
    EvaluationResult,
)
from datp.reporting.tables import (
    MANDATORY_FOOTNOTE,
    ResultTable,
    _build_table_row,
    generate_table3,
    generate_table4,
)

RNG = np.random.default_rng(99)

_DEVICE_IDS = [f"dev_{i}" for i in range(6)]
_ELIGIBLE_IDS = _DEVICE_IDS[:5]
_PENDING_IDS = _DEVICE_IDS[5:]


def _make_client_record(
    client_id: str, policy: ThresholdPolicy
) -> ClientEvaluationRecord:
    fpr = float(RNG.uniform(0.01, 0.15))
    tpr = float(RNG.uniform(0.85, 0.99))
    tnr = 1.0 - fpr
    fnr = 1.0 - tpr
    return ClientEvaluationRecord(
        client_id=client_id,
        metrics=BinaryMetrics(
            fpr=fpr,
            tpr=tpr,
            tnr=tnr,
            fnr=fnr,
            precision=90 / (90 + 5),
            recall=90 / (90 + 10),
            balanced_accuracy=float(RNG.uniform(0.80, 0.98)),
            macro_f1=float(RNG.uniform(0.75, 0.95)),
        ),
        confusion=ConfusionCounts(tp=90, fp=5, tn=95, fn=10),
        n_benign=100,
        n_attack=100,
        threshold=ClientThreshold(
            client_id=client_id,
            threshold=0.1,
            calibration_pending=client_id in _PENDING_IDS,
            strategy=policy,
        ),
        evaluation_incomplete=False,
    )


def _make_eval_result(policy: ThresholdPolicy, seed: int) -> EvaluationResult:
    clients = tuple(_make_client_record(d, policy) for d in _DEVICE_IDS)
    eligible_fprs = [c.metrics.fpr for c in clients if c.client_id in _ELIGIBLE_IDS]
    eligible_tprs = [c.metrics.tpr for c in clients if c.client_id in _ELIGIBLE_IDS]
    from datp.statistics.cv import cv

    _cv_fpr = cv(np.array(eligible_fprs), ddof=0)
    cv_fpr = float(_cv_fpr) if not math.isnan(_cv_fpr) else 0.0
    _cv_tpr = cv(np.array(eligible_tprs), ddof=0)
    cv_tpr = float(_cv_tpr) if not math.isnan(_cv_tpr) else 0.0
    mean_fpr = float(np.mean(eligible_fprs))
    std_fpr = float(np.std(eligible_fprs, ddof=1))
    fpr_arr = np.array(eligible_fprs)
    tpr_arr = np.array(eligible_tprs)
    iqr_fpr = (
        float(np.percentile(fpr_arr, 75) - np.percentile(fpr_arr, 25))
        if len(fpr_arr) >= 2
        else float("nan")
    )
    iqr_tpr = (
        float(np.percentile(tpr_arr, 75) - np.percentile(tpr_arr, 25))
        if len(tpr_arr) >= 2
        else float("nan")
    )
    ba_list = [
        c.metrics.balanced_accuracy for c in clients if c.client_id in _ELIGIBLE_IDS
    ]
    f1_list = [c.metrics.macro_f1 for c in clients if c.client_id in _ELIGIBLE_IDS]
    worst_fpr = float(max(eligible_fprs)) if eligible_fprs else float("nan")
    worst_id: str | None = next(
        (
            c.client_id
            for c in clients
            if c.client_id in _ELIGIBLE_IDS
            and math.isclose(c.metrics.fpr, worst_fpr, abs_tol=1e-12)
        ),
        None,
    )
    cell = TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=seed)
    run = PolicyRunId(cell=cell, policy=policy)
    return EvaluationResult(
        run=run,
        dataset=DatasetID.NBAIOT,
        clients=clients,
        eligible_ids=tuple(_ELIGIBLE_IDS),
        pending_ids=tuple(_PENDING_IDS),
        incomplete_ids=(),
        coverage_ratio=len(_ELIGIBLE_IDS) / len(_DEVICE_IDS),
        dispersion=DispersionMetrics(
            cv_fpr=cv_fpr,
            mean_fpr=mean_fpr,
            std_fpr=std_fpr,
            cv_tpr=cv_tpr,
            iqr_fpr=iqr_fpr,
            iqr_tpr=iqr_tpr,
            max_min_fpr_gap=worst_fpr - float(min(eligible_fprs))
            if len(eligible_fprs) >= 2
            else 0.0,
            worst_client_fpr=worst_fpr,
            worst_client_id=worst_id,
            eligible_count=len(eligible_fprs),
            client_count=len(clients),
            worst_ba=float(min(ba_list)) if ba_list else float("nan"),
            p10_macro_f1=float(np.percentile(f1_list, 10)) if f1_list else float("nan"),
        ),
    )


_STYLE = BASE_CONFIG.reporting.style


def _synthetic_results() -> dict[ThresholdPolicy, list[EvaluationResult]]:
    data: dict[ThresholdPolicy, list[EvaluationResult]] = {}
    for bl in (
        ThresholdPolicy.GLOBAL_THRESHOLD,
        ThresholdPolicy.LOCAL_THRESHOLD,
        ThresholdPolicy.CLUSTER_THRESHOLD,
    ):
        data[bl] = [_make_eval_result(bl, seed) for seed in range(2)]
    return data


def _synthetic_results_single_seed() -> dict[ThresholdPolicy, list[EvaluationResult]]:
    return {
        ThresholdPolicy.GLOBAL_THRESHOLD: [
            _make_eval_result(ThresholdPolicy.GLOBAL_THRESHOLD, 0)
        ]
    }


# ── generate_table3 ──────────────────────────────────────────────


def test_generate_table3_creates_files(tmp_path: Path) -> None:
    tex_path = generate_table3(_synthetic_results(), tmp_path, style=_STYLE)
    assert tex_path.exists()
    assert tex_path.suffix == ".tex"
    csv_path = tmp_path / "table3_nbaiot.csv"
    assert csv_path.exists()


def test_table3_contains_footnote(tmp_path: Path) -> None:
    tex_path = generate_table3(_synthetic_results(), tmp_path, style=_STYLE)
    content = tex_path.read_text(encoding="utf-8")
    assert MANDATORY_FOOTNOTE in content


def test_table3_contains_coverage_ratio(tmp_path: Path) -> None:
    tex_path = generate_table3(_synthetic_results(), tmp_path, style=_STYLE)
    content = tex_path.read_text(encoding="utf-8")
    assert "0.83" in content


def test_table_labels_p10_macro_f1_precisely(tmp_path: Path) -> None:
    tex_path = generate_table3(_synthetic_results(), tmp_path, style=_STYLE)
    content = tex_path.read_text(encoding="utf-8")
    assert "P10 client Macro-F1" in content
    assert "& Worst BA & Macro-F1 &" not in content


# ── generate_table4 ──────────────────────────────────────────────


def test_generate_table4_creates_files(tmp_path: Path) -> None:
    tex_path = generate_table4(_synthetic_results(), tmp_path, style=_STYLE)
    assert tex_path.exists()
    assert tex_path.suffix == ".tex"
    csv_path = tmp_path / "table4_ciciot.csv"
    assert csv_path.exists()


# ── _build_table_row ─────────────────────────────────────────────


def test_build_table_row_multi_seed() -> None:
    results = [_make_eval_result(ThresholdPolicy.GLOBAL_THRESHOLD, s) for s in range(3)]
    row = _build_table_row(ThresholdPolicy.GLOBAL_THRESHOLD, results)
    assert row.policy == ThresholdPolicy.GLOBAL_THRESHOLD
    assert row.eligible_count == 5
    assert row.pending_count == 1
    assert row.coverage_ratio == pytest.approx(5 / 6)
    assert row.cv_fpr_std > 0  # multi-seed std nonzero


def test_build_table_row_single_seed() -> None:
    results = [_make_eval_result(ThresholdPolicy.LOCAL_THRESHOLD, 0)]
    row = _build_table_row(ThresholdPolicy.LOCAL_THRESHOLD, results)
    assert row.policy == ThresholdPolicy.LOCAL_THRESHOLD
    assert row.cv_fpr_std == pytest.approx(0.0)
    assert row.cv_tpr_std == pytest.approx(0.0)


def test_build_table_row_eligible_count_mismatch_raises() -> None:
    r1 = _make_eval_result(ThresholdPolicy.GLOBAL_THRESHOLD, 0)
    r2 = _make_eval_result(ThresholdPolicy.GLOBAL_THRESHOLD, 1)
    object.__setattr__(r2, "eligible_ids", ("dev_0", "dev_1"))
    with pytest.raises(ValueError, match="Coverage count mismatch"):
        _build_table_row(ThresholdPolicy.GLOBAL_THRESHOLD, [r1, r2])


# ── ResultTable.to_csv ───────────────────────────────────────────


def test_result_table_to_csv(tmp_path: Path) -> None:
    results = [_make_eval_result(ThresholdPolicy.GLOBAL_THRESHOLD, 0)]
    row = _build_table_row(ThresholdPolicy.GLOBAL_THRESHOLD, results)
    table = ResultTable(title="Test", style=_STYLE, rows=[row])
    csv_path = table.to_csv(tmp_path / "test.csv")
    assert csv_path.exists()

    with csv_path.open("r") as f:
        reader = list(csv.reader(f))
    assert reader[0][0] == "ThresholdPolicy"
    assert MANDATORY_FOOTNOTE in reader[-1][0]


# ── Non-finite coverage rejection ────────────────────────────────


def test_build_table_row_nonfinite_coverage_raises() -> None:
    r1 = _make_eval_result(ThresholdPolicy.GLOBAL_THRESHOLD, 0)
    object.__setattr__(r1, "coverage_ratio", float("nan"))
    with pytest.raises(ValueError, match="Coverage ratio missing"):
        _build_table_row(ThresholdPolicy.GLOBAL_THRESHOLD, [r1])
