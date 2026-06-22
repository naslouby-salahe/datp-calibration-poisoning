from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConfusionCounts:
    """Raw confusion matrix counts for a single client evaluation."""

    tp: int
    fp: int
    tn: int
    fn: int


@dataclass(frozen=True, slots=True)
class BinaryMetrics:
    fpr: float
    tpr: float
    tnr: float
    fnr: float
    balanced_accuracy: float
    precision: float
    recall: float
    macro_f1: float


def recompute_binary_metrics(tp: int, fp: int, tn: int, fn: int) -> BinaryMetrics:
    n_benign = fp + tn
    n_attack = tp + fn
    fpr = fp / n_benign if n_benign > 0 else math.nan
    tpr = tp / n_attack if n_attack > 0 else math.nan
    tnr = tn / n_benign if n_benign > 0 else math.nan
    fnr = fn / n_attack if n_attack > 0 else math.nan
    if n_benign > 0 and n_attack > 0:
        balanced_accuracy = (tpr + tnr) / 2.0
        prec0 = tn / (tn + fn) if (tn + fn) > 0 else 0.0
        rec0 = tnr
        f1_0 = 2 * prec0 * rec0 / (prec0 + rec0) if (prec0 + rec0) > 0 else 0.0
        prec1 = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec1 = tpr
        f1_1 = 2 * prec1 * rec1 / (prec1 + rec1) if (prec1 + rec1) > 0 else 0.0
        macro_f1 = (f1_0 + f1_1) / 2.0
    else:
        balanced_accuracy = math.nan
        prec1 = math.nan
        rec1 = tpr
        macro_f1 = math.nan
    return BinaryMetrics(
        fpr=fpr,
        tpr=tpr,
        tnr=tnr,
        fnr=fnr,
        balanced_accuracy=balanced_accuracy,
        precision=prec1,
        recall=rec1,
        macro_f1=macro_f1,
    )
