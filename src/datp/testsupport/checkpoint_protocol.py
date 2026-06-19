from __future__ import annotations

from datp.core.enums import (
    Baseline,
    Regime,
    RunKind,
    ThresholdAggregationMethod,
    ThresholdSource,
)
from datp.core.types import MetricsProvenance
from datp.data.catalog import DatasetID
from datp.thresholding.metrics_serialization import (
    METRIC_SCHEMA_VERSION,
    METRICS_SCHEMA_VERSION,
    THRESHOLD_SCHEMA_VERSION,
    MetricsClientDetail,
    SweepMetrics,
)


def build_fake_checkpoint_metrics(
    *, rounds: tuple[int, ...], seeds: tuple[int, ...]
) -> tuple[SweepMetrics, ...]:
    metrics: list[SweepMetrics] = []
    for checkpoint_round in rounds:
        for seed in seeds:
            metrics.append(
                _fake_metric(
                    baseline=Baseline.B1,
                    seed=seed,
                    checkpoint_round=checkpoint_round,
                    cv_fpr=0.30 + 0.01 * seed,
                    worst_fpr=0.22 + 0.01 * seed,
                    p10_macro_f1=0.70 + checkpoint_round / 1000.0,
                    worst_ba=0.91 + checkpoint_round / 2000.0,
                )
            )
            metrics.append(
                _fake_metric(
                    baseline=Baseline.B2,
                    seed=seed,
                    checkpoint_round=checkpoint_round,
                    cv_fpr=0.20 + 0.01 * seed,
                    worst_fpr=0.12 + 0.01 * seed,
                    p10_macro_f1=0.73 + checkpoint_round / 1000.0,
                    worst_ba=0.92 + checkpoint_round / 2000.0,
                )
            )
    return tuple(metrics)


def _fake_metric(
    *,
    baseline: Baseline,
    seed: int,
    checkpoint_round: int,
    cv_fpr: float,
    worst_fpr: float,
    p10_macro_f1: float,
    worst_ba: float,
) -> SweepMetrics:
    per_client = (
        _client_detail(
            "c1", fpr=worst_fpr, tpr=0.95, macro_f1=p10_macro_f1, ba=worst_ba
        ),
        _client_detail(
            "c2",
            fpr=max(worst_fpr - 0.05, 0.0),
            tpr=0.96,
            macro_f1=p10_macro_f1 + 0.02,
            ba=worst_ba + 0.01,
        ),
    )
    aggregate = {
        "cv_fpr": cv_fpr,
        "mean_fpr": worst_fpr - 0.025,
        "std_fpr": 0.01,
        "cv_tpr": 0.02,
        "iqr_fpr": 0.01,
        "iqr_tpr": 0.01,
        "max_min_fpr_gap": 0.05,
        "worst_client_fpr": worst_fpr,
        "worst_client_id": "c1",
        "worst_ba": worst_ba,
        "p10_macro_f1": p10_macro_f1,
    }
    return SweepMetrics(
        schema_version=METRICS_SCHEMA_VERSION,
        metric_schema_version=METRIC_SCHEMA_VERSION,
        threshold_schema_version=THRESHOLD_SCHEMA_VERSION,
        run_id=f"a_{baseline.value}_seed{seed}_round{checkpoint_round}",
        run_kind=RunKind.CORE_LADDER,
        baseline=baseline,
        regime=Regime.A,
        seed=seed,
        alpha=None,
        checkpoint_round=checkpoint_round,
        dataset=DatasetID.NBAIOT,
        threshold_scope=ThresholdAggregationMethod.PER_CLIENT_PERCENTILE
        if baseline == Baseline.B2
        else ThresholdAggregationMethod.ELIGIBLE_CLIENT_ARITHMETIC_MEAN,
        threshold_strategy_name=baseline.value,
        tau_global=0.5,
        eligible_ids=("c1", "c2"),
        pending_ids=(),
        eval_incomplete_ids=(),
        eligible_count=2,
        pending_count=0,
        eval_incomplete_count=0,
        client_count=2,
        coverage_ratio=1.0,
        cv_fpr=cv_fpr,
        mean_fpr=worst_fpr - 0.025,
        std_fpr=0.01,
        cv_tpr=0.02,
        iqr_fpr=0.01,
        iqr_tpr=0.01,
        worst_client_fpr=worst_fpr,
        worst_client_id="c1",
        worst_ba=worst_ba,
        p10_macro_f1=p10_macro_f1,
        aggregate_metrics=aggregate,  # type: ignore[arg-type]
        provenance=MetricsProvenance(
            config_identity="config",
            split_manifest_identity="split",
            model_checkpoint_identity="checkpoint",
            score_artifact_identity="score",
            metric_code_version="metric",
            threshold_code_version="threshold",
            package_version="package",
            generated_at_utc="2026-06-04T00:00:00Z",
        ),
        per_client=per_client,
    )


def _client_detail(
    client_id: str,
    *,
    fpr: float,
    tpr: float,
    macro_f1: float,
    ba: float,
) -> MetricsClientDetail:
    return MetricsClientDetail(
        client_id=client_id,
        fpr=fpr,
        tpr=tpr,
        tnr=1.0 - fpr,
        fnr=1.0 - tpr,
        precision=0.9,
        recall=tpr,
        balanced_accuracy=ba,
        macro_f1=macro_f1,
        confusion_matrix={"tp": 10, "fp": 1, "tn": 9, "fn": 0},
        n_benign=10,
        n_attack=10,
        calibration_pending=False,
        evaluation_incomplete=False,
        threshold_value=0.5,
        threshold_source=ThresholdSource.B2_PER_CLIENT,
    )
