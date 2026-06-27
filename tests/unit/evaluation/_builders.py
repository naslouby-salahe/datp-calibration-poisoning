"""Shared test builders for evaluation metric fixtures."""

from __future__ import annotations
from datp.core.enums import ThresholdPolicy

import math
from dataclasses import dataclass

from datp.config.models import ExperimentStage
from datp.core.types import ClientThreshold
from datp.evaluation.metrics import (
    BinaryMetrics,
    ClientEvaluationRecord,
    ConfusionCounts,
    EvaluationResult,
    build_evaluation_result,
)


@dataclass(frozen=True, slots=True)
class _EvalSpec:
    policy: ThresholdPolicy = ThresholdPolicy.GLOBAL_THRESHOLD
    stage: ExperimentStage = ExperimentStage.NBAIOT_MAIN
    seed: int = 42
    eval_incomplete_ids: tuple[str, ...] = ()


def _make_eval_result(
    per_client: list[ClientEvaluationRecord],
    eligible_ids: list[str],
    pending_ids: list[str],
    spec: _EvalSpec = _EvalSpec(),
) -> EvaluationResult:
    return build_evaluation_result(
        policy=spec.policy,
        stage=spec.stage,
        seed=spec.seed,
        clients=tuple(per_client),
        eligible_ids=tuple(eligible_ids),
        pending_ids=tuple(pending_ids),
        incomplete_ids=spec.eval_incomplete_ids,
    )


def _make_client_record(
    client_id: str,
    fpr: float,
    tpr: float,
    *,
    n_benign: int = 100,
    n_attack: int = 100,
) -> ClientEvaluationRecord:
    tnr = 1.0 - fpr
    fnr = 1.0 - tpr
    ba = (tpr + tnr) / 2.0
    tp = int(tpr * n_attack)
    fp = int(fpr * n_benign)
    tn = int(tnr * n_benign)
    fn = int(fnr * n_attack)
    prec = tp / (tp + fp) if (tp + fp) > 0 else math.nan
    rec = tp / (tp + fn) if (tp + fn) > 0 else math.nan
    if n_benign > 0 and n_attack > 0:
        prec0 = tn / (tn + fn) if (tn + fn) > 0 else 0.0
        rec0 = tnr
        f1_0 = 2 * prec0 * rec0 / (prec0 + rec0) if (prec0 + rec0) > 0 else 0.0
        prec1 = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec1 = tpr
        f1_1 = 2 * prec1 * rec1 / (prec1 + rec1) if (prec1 + rec1) > 0 else 0.0
        macro_f1 = (f1_0 + f1_1) / 2.0
    else:
        macro_f1 = math.nan
    return ClientEvaluationRecord(
        client_id=client_id,
        metrics=BinaryMetrics(
            fpr=fpr,
            tpr=tpr,
            tnr=tnr,
            fnr=fnr,
            balanced_accuracy=ba,
            precision=prec,
            recall=rec,
            macro_f1=macro_f1,
        ),
        confusion=ConfusionCounts(tp=tp, fp=fp, tn=tn, fn=fn),
        n_benign=n_benign,
        n_attack=n_attack,
        threshold=ClientThreshold(
            client_id=client_id,
            threshold=0.5,
            calibration_pending=False,
            strategy=ThresholdPolicy.GLOBAL_THRESHOLD,
        ),
        evaluation_incomplete=(n_attack == 0),
    )
