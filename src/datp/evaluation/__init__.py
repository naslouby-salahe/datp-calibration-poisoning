"""Lazy-loading exports for evaluation metrics and artifact validation."""

from __future__ import annotations

__all__ = [
    "BinaryMetrics",
    "BinaryRankingMetrics",
    "ClientEvaluationRecord",
    "ConfusionCounts",
    "DispersionMetrics",
    "EvaluationResult",
    "PerAttackFamilyTPR",
    "aggregate_dispersion",
    "build_evaluation_result",
    "compute_binary_ranking_metrics",
    "compute_client_record",
    "compute_empirical_coverage",
    "compute_fpr",
    "compute_per_attack_tpr",
    "evaluate_policy_run",
    "recompute_binary_metrics",
    "save_confusion_matrices",
    "validate_metrics_payload",
]


def __getattr__(name: str) -> object:
    if name == "validate_metrics_payload":
        from datp.evaluation.artifact_validation import validate_metrics_payload

        return validate_metrics_payload

    if name in __all__:
        from datp.evaluation import metrics as _m

        return getattr(_m, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
