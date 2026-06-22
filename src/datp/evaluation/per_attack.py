from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from datp.core.errors import fmt

_MODULE = "evaluation.per_attack"


def compute_fpr(benign_errors: np.ndarray, threshold: float) -> float:
    if benign_errors.size == 0:
        return 0.0
    return float(np.mean(benign_errors > threshold))


def compute_empirical_coverage(test_benign: np.ndarray, threshold: float) -> float:
    if test_benign.size == 0:
        return 0.0
    return float(np.mean(test_benign <= threshold))


@dataclass(frozen=True, slots=True)
class PerAttackFamilyTPR:
    client_id: str
    attack_label: str
    family: str | None
    detected_count: int
    denominator: int
    tpr: float


def compute_per_attack_tpr(
    client_id: str,
    attack_scores: np.ndarray,
    attack_labels: np.ndarray,
    threshold: float,
    family_fn: Callable[[str], str | None],
) -> list[PerAttackFamilyTPR]:
    scores = np.asarray(attack_scores, dtype=np.float64)
    labels = np.asarray(attack_labels, dtype=object)

    if scores.shape[0] != labels.shape[0]:
        raise ValueError(
            fmt(
                _MODULE,
                "attack_scores and attack_labels length mismatch",
                str(scores.shape[0]),
                str(labels.shape[0]),
            )
        )

    results: list[PerAttackFamilyTPR] = []
    for lbl in np.unique(labels):
        mask = labels == lbl
        lbl_scores = scores[mask]
        detected = int(np.sum(lbl_scores > threshold))
        denom = int(mask.sum())
        tpr = detected / denom if denom > 0 else math.nan
        results.append(
            PerAttackFamilyTPR(
                client_id=client_id,
                attack_label=str(lbl),
                family=family_fn(str(lbl)),
                detected_count=detected,
                denominator=denom,
                tpr=tpr,
            )
        )
    return results
