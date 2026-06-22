from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from datp.core.types import ClientThreshold
from datp.evaluation.binary import BinaryMetrics, ConfusionCounts, recompute_binary_metrics


@dataclass(frozen=True, slots=True)
class ClientEvaluationRecord:
    """Per-client evaluation record with metrics, confusion counts, and threshold."""

    client_id: str
    metrics: BinaryMetrics
    confusion: ConfusionCounts
    n_benign: int
    n_attack: int
    threshold: ClientThreshold
    evaluation_incomplete: bool


def compute_client_record(
    client_id: str,
    scores_benign: np.ndarray,
    scores_attack: np.ndarray,
    client_threshold: ClientThreshold,
) -> ClientEvaluationRecord:
    benign = np.asarray(scores_benign, dtype=np.float64)
    attack = np.asarray(scores_attack, dtype=np.float64)
    n_benign = int(benign.size)
    n_attack = int(attack.size)

    fp = int(np.sum(benign > client_threshold.threshold))
    tn = n_benign - fp
    tp = int(np.sum(attack > client_threshold.threshold))
    fn = n_attack - tp

    return ClientEvaluationRecord(
        client_id=client_id,
        metrics=recompute_binary_metrics(tp, fp, tn, fn),
        confusion=ConfusionCounts(tp=tp, fp=fp, tn=tn, fn=fn),
        n_benign=n_benign,
        n_attack=n_attack,
        threshold=client_threshold,
        evaluation_incomplete=n_attack == 0,
    )
