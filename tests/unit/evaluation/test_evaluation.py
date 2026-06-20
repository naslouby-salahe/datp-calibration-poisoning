from __future__ import annotations

import dataclasses
import subprocess
from pathlib import Path

import numpy as np
import pytest

from datp.core.enums import Baseline, Regime
from datp.core.identity import BaselineRunId, TrainingCellId
from datp.core.types import ClientThreshold, ThresholdMetadata, ThresholdResult
from datp.evaluation.metric_filtering import _filter_eligible_metrics
from datp.evaluation.metrics import (
    BinaryMetrics,
    ClientEvaluationRecord,
    ConfusionCounts,
    build_evaluation_result,
)
from datp.thresholding.metrics_serialization import build_metrics_dict
from tests.unit.evaluation._builders import _make_client_record, _make_eval_result


# ── Eligibility / filtering ───────────────────────────────────────────────────


def test_eval_incomplete_excluded_from_attack_metrics() -> None:
    c1 = _make_client_record("c1", fpr=0.1, tpr=0.9, n_attack=100)
    c2 = _make_client_record("c2", fpr=0.2, tpr=0.8, n_attack=100)
    c3_noattack = ClientEvaluationRecord(
        client_id="c3",
        metrics=BinaryMetrics(
            fpr=0.05,
            tpr=float("nan"),
            tnr=0.95,
            fnr=float("nan"),
            balanced_accuracy=float("nan"),
            precision=float("nan"),
            recall=float("nan"),
            macro_f1=float("nan"),
        ),
        confusion=ConfusionCounts(tp=0, fp=5, tn=95, fn=0),
        n_benign=100,
        n_attack=0,
        threshold=ClientThreshold(
            client_id="c3",
            threshold=0.5,
            calibration_pending=False,
            strategy=Baseline.B1,
        ),
        evaluation_incomplete=True,
    )

    fm = _filter_eligible_metrics(
        clients=[c1, c2, c3_noattack],
        eligible_ids=["c1", "c2", "c3"],
        incomplete_ids=["c3"],
    )

    assert fm.fpr_eligible.shape[0] == 3
    assert fm.tpr_eligible.shape[0] == 2
    assert fm.ba_eligible.shape[0] == 2
    assert fm.f1_eligible.shape[0] == 2


def test_filter_eligible_metrics_excludes_pending() -> None:
    c_elig = _make_client_record("e1", fpr=0.1, tpr=0.9)
    c_pend = _make_client_record("p1", fpr=0.5, tpr=0.6)

    fm = _filter_eligible_metrics(
        clients=[c_elig, c_pend],
        eligible_ids=["e1"],
        incomplete_ids=None,
    )

    assert fm.fpr_eligible.shape[0] == 1
    assert float(fm.fpr_eligible[0]) == pytest.approx(0.1)


# ── EvaluationResult structure ────────────────────────────────────────────────


def test_evaluation_result_asdict() -> None:
    c1 = _make_client_record("c1", fpr=0.1, tpr=0.9)
    ev = _make_eval_result([c1], ["c1"], [])
    d = dataclasses.asdict(ev)
    assert "run" in d
    assert "clients" in d
    assert "coverage_ratio" in d
    assert "dispersion" in d
    assert "cv_fpr" in d["dispersion"]
    assert "iqr_fpr" in d["dispersion"]
    assert "worst_ba" in d["dispersion"]
    assert "p10_macro_f1" in d["dispersion"]
    assert isinstance(d["clients"], tuple)


def test_client_record_asdict() -> None:
    cr = _make_client_record("c1", fpr=0.05, tpr=0.95)
    d = dataclasses.asdict(cr)
    assert d["client_id"] == "c1"
    assert "confusion" in d
    assert set(d["confusion"].keys()) == {"tp", "fp", "tn", "fn"}


def test_metrics_serialization_contains_eligibility_threshold_and_provenance_fields() -> (
    None
):
    from datp.evaluation.metrics import compute_client_record as _ccr

    ct_eligible = ClientThreshold(
        client_id="c1", threshold=0.5, calibration_pending=False, strategy=Baseline.B1
    )
    c1_rec = _ccr(
        "c1", np.array([0.01, 0.02, 0.07]), np.array([0.08, 0.09, 0.10]), ct_eligible
    )
    ct_pending = ClientThreshold(
        client_id="c2", threshold=0.5, calibration_pending=True, strategy=Baseline.B1
    )
    c2_rec = ClientEvaluationRecord(
        client_id="c2",
        metrics=c1_rec.metrics,
        confusion=c1_rec.confusion,
        n_benign=c1_rec.n_benign,
        n_attack=c1_rec.n_attack,
        threshold=ct_pending,
        evaluation_incomplete=c1_rec.evaluation_incomplete,
    )
    ev = build_evaluation_result(
        baseline=Baseline.B1,
        regime=Regime.A,
        seed=0,
        alpha=None,
        clients=(c1_rec, c2_rec),
        eligible_ids=("c1",),
        pending_ids=("c2",),
        incomplete_ids=(),
    )
    metrics = build_metrics_dict(
        ev,
        ThresholdResult(
            run=BaselineRunId(
                cell=TrainingCellId(regime=Regime.A, seed=0, alpha=None),
                baseline=Baseline.B1,
            ),
            tau_global=0.5,
            client_thresholds=(
                ClientThreshold(
                    client_id="c1",
                    threshold=0.5,
                    calibration_pending=False,
                    strategy=Baseline.B1,
                ),
                ClientThreshold(
                    client_id="c2",
                    threshold=0.5,
                    calibration_pending=True,
                    strategy=Baseline.B1,
                ),
            ),
            metadata=ThresholdMetadata(b3=None, b4=None),
        ),
        config_identity="test",
        split_manifest_identity="test",
        model_checkpoint_identity="test",
        score_artifact_identity="test",
        checkpoint_round=None,
    ).model_dump(mode="json")
    for key in (
        "schema_version",
        "metric_schema_version",
        "threshold_schema_version",
        "eligible_ids",
        "pending_ids",
        "eval_incomplete_ids",
        "coverage_ratio",
        "aggregate_metrics",
        "provenance",
    ):
        assert key in metrics
    assert metrics["per_client"][1]["calibration_pending"] is True
    assert metrics["per_client"][1]["threshold_source"] == "tau_global_fallback"


# ── Build evaluation result validation ───────────────────────────────────────


def test_build_evaluation_result_rejects_undefined_eligible_fpr() -> None:
    client = ClientEvaluationRecord(
        client_id="attack_only",
        metrics=BinaryMetrics(
            fpr=float("nan"),
            tpr=1.0,
            tnr=float("nan"),
            fnr=0.0,
            balanced_accuracy=float("nan"),
            precision=float("nan"),
            recall=1.0,
            macro_f1=float("nan"),
        ),
        confusion=ConfusionCounts(tp=3, fp=0, tn=0, fn=0),
        n_benign=0,
        n_attack=3,
        threshold=ClientThreshold(
            client_id="attack_only",
            threshold=0.5,
            calibration_pending=False,
            strategy=Baseline.B1,
        ),
        evaluation_incomplete=False,
    )

    with pytest.raises(ValueError, match="Undefined eligible-client FPR"):
        build_evaluation_result(
            baseline=Baseline.B1,
            regime=Regime.A,
            seed=0,
            alpha=None,
            clients=(client,),
            eligible_ids=("attack_only",),
            pending_ids=(),
            incomplete_ids=(),
        )


def test_build_evaluation_result_rejects_mixed_eligibility_status() -> None:
    client = _make_client_record("c1", fpr=0.1, tpr=0.9)

    with pytest.raises(ValueError, match="mixed eligibility"):
        build_evaluation_result(
            baseline=Baseline.B1,
            regime=Regime.A,
            seed=0,
            alpha=None,
            clients=(client,),
            eligible_ids=("c1",),
            pending_ids=("c1",),
            incomplete_ids=(),
        )


# ── Single CV implementation guard ───────────────────────────────────────────


def test_single_cv_implementation() -> None:
    result = subprocess.run(
        ["grep", "-rn", r"def cv(", "src/datp/"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[3],
    )
    lines = [line for line in result.stdout.strip().splitlines() if line.strip()]
    assert len(lines) == 1, f"Expected 1 'def cv(' match, got {len(lines)}: {lines}"
    assert "statistics/cv.py" in lines[0]
