from __future__ import annotations

# Lazy attribute access breaks an import cycle: evaluation modules import
# from baselines and core, while downstream consumers (reporting, audit, CLI)
# import from evaluation. Deferring actual imports to first attribute access
# prevents circular-import failures at module-load time.

__all__ = [  # pylint: disable=undefined-all-variable
    "BinaryMetrics",
    "BinaryRankingMetrics",
    "ClientEvaluationRecord",
    "ConfusionCounts",
    "DispersionMetrics",
    "EvaluationResult",
    "compute_binary_ranking_metrics",
    "compute_client_record",
    "build_evaluation_result",
    "evaluate_baseline",
    "recompute_binary_metrics",
    "save_confusion_matrices",
]


def __getattr__(name: str) -> object:
    _from_metrics = {
        "BinaryMetrics",
        "ClientEvaluationRecord",
        "ConfusionCounts",
        "DispersionMetrics",
        "EvaluationResult",
        "build_evaluation_result",
        "compute_client_record",
        "evaluate_baseline",
        "recompute_binary_metrics",
    }
    _from_ranking = {"BinaryRankingMetrics", "compute_binary_ranking_metrics"}
    _from_confusion = {"save_confusion_matrices"}

    if name in _from_metrics:
        from datp.evaluation import metrics as _m  # noqa: PLC0415

        return getattr(_m, name)
    if name in _from_ranking:
        from datp.evaluation import ranking as _r  # noqa: PLC0415

        return getattr(_r, name)
    if name in _from_confusion:
        from datp.evaluation.confusion import save_confusion_matrices  # noqa: PLC0415

        return save_confusion_matrices
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
