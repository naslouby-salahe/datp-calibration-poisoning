"""Unit tests for per-client evaluation record construction."""

from __future__ import annotations
from datp.core.enums import ThresholdPolicy

import math

import numpy as np
import pytest

from datp.core.types import ClientThreshold
from datp.evaluation.metrics import compute_client_record


def _ct(threshold: float = 0.5) -> ClientThreshold:
    return ClientThreshold(
        client_id="test",
        threshold=threshold,
        calibration_pending=False,
        strategy=ThresholdPolicy.GLOBAL_THRESHOLD,
    )


def test_compute_client_metrics_perfect_separation() -> None:
    benign = np.array([0.1, 0.2, 0.3, 0.5, 0.9])
    attack = np.array([2.1, 2.5, 3.0, 4.0])
    result = compute_client_record("test", benign, attack, _ct(1.5))

    assert result.metrics.fpr == pytest.approx(0.0)
    assert result.metrics.tpr == pytest.approx(1.0)
    assert result.metrics.balanced_accuracy == pytest.approx(1.0)
    assert result.confusion.fp == 0
    assert result.confusion.tp == 4
    assert result.confusion.tn == 5
    assert result.confusion.fn == 0
    assert result.n_benign == 5
    assert result.n_attack == 4


def test_threshold_rule_strictly_greater_than() -> None:
    benign = np.array([1.5, 0.5])
    attack = np.array([1.5, 2.0])
    result = compute_client_record("test", benign, attack, _ct(1.5))
    assert result.confusion.tn == 2
    assert result.confusion.fn == 1
    assert result.confusion.tp == 1


def test_compute_client_metrics_all_false_positives() -> None:
    benign = np.array([0.1, 0.5, 1.0, 2.0])
    attack = np.array([3.0, 4.0])
    result = compute_client_record("test", benign, attack, _ct(0.0))

    assert result.metrics.fpr == pytest.approx(1.0)
    assert result.metrics.tpr == pytest.approx(1.0)
    assert result.confusion.fp == 4
    assert result.confusion.tn == 0


def test_benign_only_client_produces_fpr_and_nan_attack_metrics() -> None:
    benign = np.array([0.1, 0.5, 0.9])
    attack = np.array([], dtype=np.float64)
    result = compute_client_record("test", benign, attack, _ct(0.7))

    assert not math.isnan(result.metrics.fpr)
    assert math.isnan(result.metrics.tpr)
    assert math.isnan(result.metrics.balanced_accuracy)
    assert math.isnan(result.metrics.macro_f1)
    assert result.n_benign == 3
    assert result.n_attack == 0


def test_macro_f1_matches_sklearn_zero_division_behavior() -> None:
    benign = np.array([2.0, 3.0, 4.0, 5.0])
    attack = np.array([0.1, 0.2, 0.3])
    result = compute_client_record("test", benign, attack, _ct(1.5))
    assert result.confusion.fp == 4
    assert result.confusion.tn == 0
    assert result.confusion.tp == 0
    assert result.confusion.fn == 3
    assert result.metrics.macro_f1 == pytest.approx(0.0)
