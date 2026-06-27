"""Unit tests for fleet-level FPR bundle computation."""

from __future__ import annotations

import math

import numpy as np
import pytest

from datp.statistics.aggregates import cv
from tests.unit.evaluation._builders import _make_client_record, _make_eval_result


def test_cv_fpr_eligible_only() -> None:
    c1 = _make_client_record("c1", fpr=0.10, tpr=0.90)
    c2 = _make_client_record("c2", fpr=0.15, tpr=0.85)
    c3 = _make_client_record("c3", fpr=0.20, tpr=0.80)
    c4_pending = _make_client_record("c4", fpr=0.50, tpr=0.60)

    ev = _make_eval_result(
        per_client=[c1, c2, c3, c4_pending],
        eligible_ids=["c1", "c2", "c3"],
        pending_ids=["c4"],
    )

    expected_cv = cv(np.array([0.10, 0.15, 0.20]), ddof=0)
    assert abs(ev.cv_fpr - expected_cv) < 1e-12
    assert abs(ev.cv_fpr - cv(np.array([0.10, 0.15, 0.20, 0.50]), ddof=0)) > 0.01


def test_coverage_ratio() -> None:
    clients = [_make_client_record(f"c{i}", fpr=0.1, tpr=0.9) for i in range(4)]
    ev = _make_eval_result(
        per_client=clients,
        eligible_ids=["c0", "c1", "c2"],
        pending_ids=["c3"],
    )
    assert ev.coverage_ratio == pytest.approx(0.75)


def test_fpr_bundle_includes_mean_std_worst() -> None:
    c1 = _make_client_record("c1", fpr=0.10, tpr=0.90)
    c2 = _make_client_record("c2", fpr=0.20, tpr=0.80)
    c3 = _make_client_record("c3", fpr=0.30, tpr=0.70)
    ev = _make_eval_result([c1, c2, c3], ["c1", "c2", "c3"], [])

    assert ev.mean_fpr == pytest.approx(0.20, abs=1e-10)
    assert ev.std_fpr == pytest.approx(np.std([0.10, 0.20, 0.30], ddof=1), abs=1e-10)
    assert ev.worst_client_fpr == pytest.approx(0.30, abs=1e-10)
    assert ev.worst_client_id == "c3"
    assert ev.eligible_count == 3
    assert ev.client_count == 3


def test_bundle_excludes_pending_from_fpr_stats() -> None:
    c1 = _make_client_record("c1", fpr=0.10, tpr=0.90)
    c2 = _make_client_record("c2", fpr=0.20, tpr=0.80)
    c_pending = _make_client_record("cp", fpr=0.99, tpr=0.50)
    ev = _make_eval_result([c1, c2, c_pending], ["c1", "c2"], ["cp"])

    assert ev.mean_fpr == pytest.approx(0.15, abs=1e-10)
    assert ev.worst_client_fpr == pytest.approx(0.20, abs=1e-10)
    assert ev.worst_client_id == "c2"
    assert ev.eligible_count == 2
    assert ev.client_count == 3


def test_bundle_single_eligible_std_is_nan() -> None:
    c1 = _make_client_record("c1", fpr=0.10, tpr=0.90)
    ev = _make_eval_result([c1], ["c1"], [])
    assert math.isnan(ev.std_fpr)
    assert ev.mean_fpr == pytest.approx(0.10, abs=1e-10)


def test_bundle_no_eligible_all_nan() -> None:
    c_pending = _make_client_record("cp", fpr=0.5, tpr=0.5)
    ev = _make_eval_result([c_pending], [], ["cp"])
    assert math.isnan(ev.cv_fpr)
    assert math.isnan(ev.mean_fpr)
    assert math.isnan(ev.std_fpr)
    assert math.isnan(ev.worst_client_fpr)
    assert ev.worst_client_id is None
    assert ev.eligible_count == 0
    assert ev.client_count == 1
