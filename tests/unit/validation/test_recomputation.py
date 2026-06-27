"""Tests verifying metric recomputation, saved-vs-recalculated checks, and evaluation incompleteness exclusions."""

from __future__ import annotations

import pytest

from datp.config.models import ExperimentStage
from datp.core.enums import MetricName, ThresholdPolicy
from datp.validation.enums import DenominatorStatus
from datp.validation.metric_reproducer import (
    RecomputationParams,
    append_recomputation_records,
)


def _base_params(**overrides: object) -> RecomputationParams:
    """Helper to build standard RecomputationParams input structures."""
    defaults: dict = {
        "run_id": "nbaiot_main_global_threshold_seed0",
        "seed": 0,
        "stage": ExperimentStage.NBAIOT_MAIN,
        "policy": ThresholdPolicy.GLOBAL_THRESHOLD,
        "client_id": "c1",
        "tp": 10,
        "fp": 0,
        "tn": 10,
        "fn": 0,
        "n_benign": 10,
        "n_attack": 10,
        "saved_fpr": 0.0,
        "saved_tpr": 1.0,
        "saved_balanced_accuracy": 1.0,
        "saved_macro_f1": 1.0,
    }
    defaults.update(overrides)
    return RecomputationParams(**defaults)


def test_recomputation_fails_on_wrong_fpr() -> None:
    """Verify that a mismatch between saved and recomputed FPR is flagged as FAIL."""
    records: list = []
    append_recomputation_records(records, _base_params(saved_fpr=0.99))
    fpr_rows = [r for r in records if r.metric == MetricName.FPR]
    assert len(fpr_rows) == 1
    assert fpr_rows[0].status == DenominatorStatus.FAIL
    assert fpr_rows[0].recomputed_value == pytest.approx(0.0)


def test_recomputation_excludes_attack_metrics_when_n_attack_zero() -> None:
    """Verify attack metrics are marked EXCLUDED_EVALUATION_INCOMPLETE if n_attack is zero."""
    records: list = []
    append_recomputation_records(
        records,
        _base_params(
            tp=0,
            fp=1,
            tn=9,
            fn=0,
            n_benign=10,
            n_attack=0,
            saved_fpr=0.1,
            saved_tpr=None,
            saved_balanced_accuracy=None,
            saved_macro_f1=None,
        ),
    )
    for m in (MetricName.TPR, MetricName.BALANCED_ACCURACY, MetricName.MACRO_F1):
        rows = [r for r in records if r.metric == m]
        assert rows[0].status == DenominatorStatus.EXCLUDED_EVALUATION_INCOMPLETE

    fpr_rows = [r for r in records if r.metric == MetricName.FPR]
    assert fpr_rows[0].status == DenominatorStatus.PASS


def test_recomputation_fails_on_denominator_mismatch() -> None:
    """Verify validation fails if denominator totals disagree with raw confusion matrix counts."""
    records: list = []

    append_recomputation_records(
        records,
        _base_params(
            tp=5,
            fp=1,
            tn=8,
            fn=1,
            n_benign=10,
            n_attack=6,
            saved_fpr=0.1,
            saved_tpr=0.9,
            saved_balanced_accuracy=0.9,
            saved_macro_f1=0.9,
        ),
    )
    fpr_rows = [r for r in records if r.metric == MetricName.FPR]
    assert len(fpr_rows) == 1
    assert fpr_rows[0].status == DenominatorStatus.FAIL
    assert fpr_rows[0].recomputed_value == pytest.approx(1 / 9)
