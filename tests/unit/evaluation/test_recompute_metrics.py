from __future__ import annotations
from datp.core.enums import ThresholdPolicy

import math

import numpy as np
import pytest

from datp.core.types import ClientThreshold
from datp.evaluation.metrics import compute_client_record, recompute_binary_metrics


class TestRecomputeBinaryMetrics:
    def test_matches_compute_client_record(self) -> None:
        benign = np.array([0.1, 0.2, 0.7], dtype=float)
        attack = np.array([0.8, 0.9, 0.95], dtype=float)
        ct = ClientThreshold(
            client_id="c",
            threshold=0.5,
            calibration_pending=False,
            strategy=ThresholdPolicy.GLOBAL_THRESHOLD,
        )
        cr = compute_client_record("c", benign, attack, ct)
        bm = recompute_binary_metrics(
            cr.confusion.tp, cr.confusion.fp, cr.confusion.tn, cr.confusion.fn
        )
        assert bm.fpr == pytest.approx(cr.metrics.fpr)
        assert bm.tpr == pytest.approx(cr.metrics.tpr)
        assert bm.balanced_accuracy == pytest.approx(cr.metrics.balanced_accuracy)
        assert bm.macro_f1 == pytest.approx(cr.metrics.macro_f1)

    def test_zero_attack_returns_nan_for_attack_metrics(self) -> None:
        bm = recompute_binary_metrics(tp=0, fp=2, tn=8, fn=0)
        assert not math.isnan(bm.fpr)
        assert math.isnan(bm.tpr)
        assert math.isnan(bm.balanced_accuracy)
        assert math.isnan(bm.macro_f1)

    def test_zero_benign_returns_nan_fpr(self) -> None:
        bm = recompute_binary_metrics(tp=3, fp=0, tn=0, fn=1)
        assert math.isnan(bm.fpr)
        assert not math.isnan(bm.tpr)

    def test_perfect_classifier(self) -> None:
        bm = recompute_binary_metrics(tp=10, fp=0, tn=10, fn=0)
        assert bm.fpr == pytest.approx(0.0)
        assert bm.tpr == pytest.approx(1.0)
        assert bm.balanced_accuracy == pytest.approx(1.0)
        assert bm.macro_f1 == pytest.approx(1.0)

    def test_worst_classifier(self) -> None:
        bm = recompute_binary_metrics(tp=0, fp=10, tn=0, fn=10)
        assert bm.fpr == pytest.approx(1.0)
        assert bm.tpr == pytest.approx(0.0)
        assert bm.balanced_accuracy == pytest.approx(0.0)
        assert bm.macro_f1 == pytest.approx(0.0)

    def test_denominator_check_fp_plus_tn_equals_n_benign(self) -> None:
        bm = recompute_binary_metrics(tp=5, fp=3, tn=7, fn=2)
        assert bm.fpr == pytest.approx(3 / 10)

    def test_denominator_check_tp_plus_fn_equals_n_attack(self) -> None:
        bm = recompute_binary_metrics(tp=5, fp=3, tn=7, fn=2)
        assert bm.tpr == pytest.approx(5 / 7)
