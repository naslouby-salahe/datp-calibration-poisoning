"""Unit tests for report build validation and completeness checks."""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from datp.core.enums import ConfusionKey, MetricName, RunKind, ThresholdPolicy
from datp.reporting.build import _eligible_intersection_fprs, _evaluation_from_payload
from datp.thresholding.metrics_serialization import SweepMetrics


def _payload(*, cv_fpr: float = math.nan, pending: list[str] | None = None) -> SweepMetrics:
    pending_ids = pending or []
    per_client = [
        {
            "client_id": "c1",
            MetricName.FPR.value: 0.0,
            MetricName.TPR.value: 1.0,
            MetricName.TNR.value: 1.0,
            MetricName.FNR.value: 0.0,
            MetricName.PRECISION.value: 1.0,
            MetricName.RECALL.value: 1.0,
            MetricName.BALANCED_ACCURACY.value: 1.0,
            MetricName.MACRO_F1.value: 1.0,
            "confusion_matrix": {
                ConfusionKey.TP.value: 10,
                ConfusionKey.FP.value: 0,
                ConfusionKey.TN.value: 10,
                ConfusionKey.FN.value: 0,
            },
            "n_benign": 10,
            "n_attack": 10,
            "calibration_pending": False,
            "evaluation_incomplete": False,
            "threshold_value": 0.5,
            "threshold_source": "global",
        },
        {
            "client_id": "c2",
            MetricName.FPR.value: 0.0,
            MetricName.TPR.value: 1.0,
            MetricName.TNR.value: 1.0,
            MetricName.FNR.value: 0.0,
            MetricName.PRECISION.value: 1.0,
            MetricName.RECALL.value: 1.0,
            MetricName.BALANCED_ACCURACY.value: 1.0,
            MetricName.MACRO_F1.value: 1.0,
            "confusion_matrix": {
                ConfusionKey.TP.value: 10,
                ConfusionKey.FP.value: 0,
                ConfusionKey.TN.value: 10,
                ConfusionKey.FN.value: 0,
            },
            "n_benign": 10,
            "n_attack": 10,
            "calibration_pending": "c2" in pending_ids,
            "evaluation_incomplete": False,
            "threshold_value": 0.5,
            "threshold_source": "tau_global_fallback"
            if "c2" in pending_ids
            else "global",
        },
    ]
    eligible = 2 - len(pending_ids)
    return SweepMetrics.model_validate({
        "schema_version": "2",
        "metric_schema_version": "2",
        "threshold_schema_version": "1",
        "run_id": "a_global_threshold_seed0",
        "run_kind": RunKind.CORE_LADDER,
        "dataset": "nbaiot",
        "policy": "global_threshold",
        "stage": "nbaiot_main",
        "seed": 0,
        "checkpoint_round": None,
        "threshold_scope": "eligible_client_arithmetic_mean",
        "threshold_strategy_name": "global_threshold",
        "tau_global": 0.5,
        "per_client": per_client,
        "eligible_ids": [
            row["client_id"]
            for row in per_client
            if row["client_id"] not in pending_ids
        ],
        "pending_ids": pending_ids,
        "eval_incomplete_ids": [],
        "eligible_count": eligible,
        "pending_count": len(pending_ids),
        "eval_incomplete_count": 0,
        "client_count": 2,
        "coverage_ratio": eligible / 2,
        "cv_fpr": cv_fpr,
        "mean_fpr": 0.0,
        "std_fpr": 0.0,
        "cv_tpr": 0.0,
        "iqr_fpr": 0.0,
        "iqr_tpr": 0.0,
        "worst_client_fpr": 0.0,
        "worst_client_id": "c1",
        "worst_ba": 1.0,
        "p10_macro_f1": 1.0,
        "aggregate_metrics": {
            MetricName.CV_FPR: cv_fpr,
            MetricName.P10_MACRO_F1: 1.0,
        },
        "provenance": {
            "config_identity": "test",
            "split_manifest_identity": "test",
            "model_checkpoint_identity": "test",
            "score_artifact_identity": "test",
            "metric_code_version": "test",
            "threshold_code_version": "test",
            "package_version": "test",
            "generated_at_utc": "2026-01-01T00:00:00+00:00",
        },
    })


def test_reporting_loader_recomputes_and_rejects_bad_saved_cv_fpr() -> None:
    with pytest.raises(ValueError, match="Metric schema mismatch"):
        _evaluation_from_payload(_payload(cv_fpr=0.25), metric_tol=1e-9)


def test_reporting_loader_rejects_denominator_mismatch() -> None:
    payload = _payload()
    first = payload.per_client[0].model_copy(update={"n_benign": 11})
    payload = payload.model_copy(update={"per_client": (first, *payload.per_client[1:])})
    with pytest.raises(ValueError, match="Benign denominator mismatch"):
        _evaluation_from_payload(payload, metric_tol=1e-9)


def test_reporting_loader_rejects_missing_eligible_ids() -> None:
    payload = _payload()
    raw = payload.model_dump(mode="json")
    raw.pop("eligible_ids")
    with pytest.raises(ValidationError):
        SweepMetrics.model_validate(raw)


def test_eligible_intersection_rejects_mismatched_sets() -> None:
    left = _evaluation_from_payload(_payload(pending=[]), metric_tol=1e-9)
    right_payload = _payload(pending=["c2"]).model_copy(
        update={
            "policy": ThresholdPolicy.LOCAL_THRESHOLD,
            "std_fpr": math.nan,
            "iqr_fpr": math.nan,
            "cv_tpr": math.nan,
            "iqr_tpr": math.nan,
        }
    )
    right = _evaluation_from_payload(right_payload, metric_tol=1e-9)

    with pytest.raises(ValueError, match="Eligible-client set mismatch"):
        _eligible_intersection_fprs(left, right)
