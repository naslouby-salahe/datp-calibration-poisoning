"""Stable evaluation metric import surface."""

from __future__ import annotations

from datp.evaluation.binary import (
    BinaryMetrics,
    ConfusionCounts,
    recompute_binary_metrics,
)
from datp.evaluation.client_records import (
    ClientEvaluationRecord,
    compute_client_record,
)
from datp.evaluation.dispersion import DispersionMetrics, aggregate_dispersion
from datp.evaluation.per_attack import (
    PerAttackFamilyTPR,
    compute_empirical_coverage,
    compute_fpr,
    compute_per_attack_tpr,
)
from datp.evaluation.results import EvaluationResult, build_evaluation_result, evaluate_policy_run

__all__ = [
    "BinaryMetrics",
    "ClientEvaluationRecord",
    "ConfusionCounts",
    "DispersionMetrics",
    "EvaluationResult",
    "PerAttackFamilyTPR",
    "aggregate_dispersion",
    "build_evaluation_result",
    "compute_client_record",
    "compute_empirical_coverage",
    "compute_fpr",
    "compute_per_attack_tpr",
    "evaluate_policy_run",
    "recompute_binary_metrics",
]
