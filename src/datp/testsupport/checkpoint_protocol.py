from __future__ import annotations

from datp.types import (
    BootstrapCount,
    ClassificationScore,
    ClientId,
    FalsePositiveRate,
    RandomSeed,
    RoundIndex,
    RunId,
    SchemaVersion,
    ScoreValue,
    TruePositiveRate,
)


import itertools
from dataclasses import dataclass
from pathlib import Path

from datp.artifacts.io import write_json_atomic
from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactFile
from datp.config.models import ExperimentStage
from datp.core.enums import (
    POLICY_THRESHOLD_SOURCE,
    THRESHOLD_AGGREGATION_BY_POLICY,
    MetricName,
    RunKind,
    ScoringStage,
    ThresholdPolicy,
)
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.core.provenance import hash_file
from datp.core.types import MetricsProvenance
from datp.data.catalog import DatasetID
from datp.scoring.manifest import ScoringManifestStatus
from datp.thresholding.metrics_serialization import (
    ConfusionMatrix,
    METRIC_SCHEMA_VERSION,
    METRICS_SCHEMA_VERSION,
    THRESHOLD_SCHEMA_VERSION,
    MetricsClientDetail,
    SweepMetrics,
)

_SMOKE_CLIENT_IDS: tuple[ClientId, ...] = (ClientId("c1"), ClientId("c2"))
_SMOKE_SCORE_SPLITS: tuple[ScoringStage, ...] = (
    ScoringStage.CAL,
    ScoringStage.TEST_BENIGN,
    ScoringStage.TEST_ATTACK,
)
_SMOKE_MANIFEST_SCHEMA_VERSION: SchemaVersion = "1"
_SMOKE_FAKE_CHECKPOINT_TEMPLATE = "fake checkpoint {seed} {round}\n"


@dataclass(frozen=True, slots=True)
class _FakeMetricSpec:
    policy: ThresholdPolicy
    seed: RandomSeed
    checkpoint_round: RoundIndex
    cv_fpr: FalsePositiveRate
    worst_fpr: FalsePositiveRate
    p10_macro_f1: ClassificationScore
    worst_ba: ScoreValue


@dataclass(frozen=True, slots=True)
class _FakePolicyBaseline:
    policy: ThresholdPolicy
    cv_fpr: FalsePositiveRate
    worst_fpr: FalsePositiveRate
    p10_macro_f1: ClassificationScore
    worst_ba: ScoreValue


_FAKE_POLICY_BASELINES: tuple[_FakePolicyBaseline, ...] = (
    _FakePolicyBaseline(ThresholdPolicy.GLOBAL_THRESHOLD, 0.30, 0.22, 0.70, 0.91),
    _FakePolicyBaseline(ThresholdPolicy.LOCAL_THRESHOLD, 0.20, 0.12, 0.73, 0.92),
    _FakePolicyBaseline(ThresholdPolicy.CLUSTER_THRESHOLD, 0.25, 0.17, 0.72, 0.915),
)


def build_fake_checkpoint_metrics(
    *,
    rounds: tuple[RoundIndex, ...],
    seeds: tuple[RandomSeed, ...],
) -> tuple[SweepMetrics, ...]:
    metrics: list[SweepMetrics] = []
    for checkpoint_round, seed in itertools.product(rounds, seeds):
        for baseline in _FAKE_POLICY_BASELINES:
            metrics.append(
                _fake_metric(
                    _FakeMetricSpec(
                        policy=baseline.policy,
                        seed=RandomSeed(seed),
                        checkpoint_round=checkpoint_round,
                        cv_fpr=baseline.cv_fpr + 0.01 * seed,
                        worst_fpr=baseline.worst_fpr + 0.01 * seed,
                        p10_macro_f1=baseline.p10_macro_f1 + checkpoint_round / 1000.0,
                        worst_ba=baseline.worst_ba + checkpoint_round / 2000.0,
                    )
                )
            )
    return tuple(metrics)


def _fake_metric(spec: _FakeMetricSpec) -> SweepMetrics:
    return SweepMetrics(
        schema_version=METRICS_SCHEMA_VERSION,
        metric_schema_version=METRIC_SCHEMA_VERSION,
        threshold_schema_version=THRESHOLD_SCHEMA_VERSION,
        run_id=RunId(
            f"nbaiot_main_{spec.policy}_seed{spec.seed}_round{spec.checkpoint_round}"
        ),
        run_kind=RunKind.CORE_LADDER,
        policy=spec.policy,
        stage=ExperimentStage.NBAIOT_MAIN,
        seed=spec.seed,
        checkpoint_round=spec.checkpoint_round,
        dataset=DatasetID.NBAIOT,
        threshold_scope=THRESHOLD_AGGREGATION_BY_POLICY[spec.policy],
        threshold_strategy_name=spec.policy,
        tau_global=0.5,
        eligible_ids=_SMOKE_CLIENT_IDS,
        pending_ids=(),
        eval_incomplete_ids=(),
        eligible_count=len(_SMOKE_CLIENT_IDS),
        pending_count=0,
        eval_incomplete_count=0,
        client_count=len(_SMOKE_CLIENT_IDS),
        coverage_ratio=1.0,
        cv_fpr=spec.cv_fpr,
        mean_fpr=spec.worst_fpr - 0.025,
        std_fpr=0.01,
        cv_tpr=0.02,
        iqr_fpr=0.01,
        iqr_tpr=0.01,
        worst_client_fpr=spec.worst_fpr,
        worst_client_id=_SMOKE_CLIENT_IDS[0],
        worst_ba=spec.worst_ba,
        p10_macro_f1=spec.p10_macro_f1,
        aggregate_metrics=_build_aggregate(spec),
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
        per_client=_build_per_client(spec),
    )


def _build_aggregate(
    spec: _FakeMetricSpec,
) -> dict[MetricName, ScoreValue | ClientId | None]:
    return {
        MetricName.CV_FPR: spec.cv_fpr,
        MetricName.MEAN_FPR: spec.worst_fpr - 0.025,
        MetricName.STD_FPR: 0.01,
        MetricName.CV_TPR: 0.02,
        MetricName.IQR_FPR: 0.01,
        MetricName.IQR_TPR: 0.01,
        MetricName.MAX_MIN_FPR_GAP: 0.05,
        MetricName.WORST_CLIENT_FPR: spec.worst_fpr,
        MetricName.WORST_CLIENT_ID: _SMOKE_CLIENT_IDS[0],
        MetricName.WORST_BA: spec.worst_ba,
        MetricName.P10_MACRO_F1: spec.p10_macro_f1,
    }


def _build_per_client(spec: _FakeMetricSpec) -> tuple[MetricsClientDetail, ...]:
    return (
        _client_detail(
            _SMOKE_CLIENT_IDS[0],
            spec.policy,
            fpr=spec.worst_fpr,
            tpr=0.95,
            macro_f1=spec.p10_macro_f1,
            ba=spec.worst_ba,
        ),
        _client_detail(
            _SMOKE_CLIENT_IDS[1],
            spec.policy,
            fpr=max(spec.worst_fpr - 0.05, 0.0),
            tpr=0.96,
            macro_f1=spec.p10_macro_f1 + 0.02,
            ba=spec.worst_ba + 0.01,
        ),
    )


def _client_detail(
    client_id: ClientId,
    policy: ThresholdPolicy,
    *,
    fpr: FalsePositiveRate,
    tpr: TruePositiveRate,
    macro_f1: ClassificationScore,
    ba: ScoreValue,
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
        confusion_matrix=ConfusionMatrix(tp=10, fp=1, tn=9, fn=0),
        n_benign=10,
        n_attack=10,
        calibration_pending=False,
        evaluation_incomplete=False,
        threshold_value=0.5,
        threshold_source=POLICY_THRESHOLD_SOURCE[policy],
    )


SMOKE_ROUNDS: tuple[RoundIndex, ...] = (25, 50)
SMOKE_SEEDS: tuple[RandomSeed, ...] = tuple(RandomSeed(seed) for seed in (0, 1, 2))
SMOKE_N_BOOTSTRAP: BootstrapCount = 200


def _require_checkpoint_round(metric: SweepMetrics) -> RoundIndex:
    if metric.checkpoint_round is None:
        raise RuntimeError("smoke metric lacks checkpoint_round")
    return metric.checkpoint_round


def build_smoke_fixture(artifact_root: Path) -> tuple[SweepMetrics, ...]:
    metrics = build_fake_checkpoint_metrics(rounds=SMOKE_ROUNDS, seeds=SMOKE_SEEDS)
    layout = ArtifactLayout(base_dir=artifact_root, stage=ExperimentStage.NBAIOT_MAIN)

    for checkpoint_round, seed in itertools.product(SMOKE_ROUNDS, SMOKE_SEEDS):
        cell = TrainingCellId(
            stage=ExperimentStage.NBAIOT_MAIN, seed=RandomSeed(seed)
        )
        ckpt_path = (
            layout.checkpoint_dir(cell, checkpoint_round)
            / ArtifactFile.MODEL_CHECKPOINT
        )
        ckpt_path.parent.mkdir(parents=True, exist_ok=True)
        ckpt_path.write_text(
            _SMOKE_FAKE_CHECKPOINT_TEMPLATE.format(
                seed=seed,
                round=checkpoint_round,
            )
        )
        _write_smoke_manifest(layout, cell, checkpoint_round, ckpt_path)

    for metric in metrics:
        checkpoint_round = _require_checkpoint_round(metric)
        cell = TrainingCellId(stage=metric.stage, seed=RandomSeed(metric.seed))
        manifest_path = layout.score_cell(
            cell,
            checkpoint_round,
        ).manifest_path
        ckpt_path = (
            layout.checkpoint_dir(cell, checkpoint_round)
            / ArtifactFile.MODEL_CHECKPOINT
        )

        updated_metric = metric.model_copy(
            update={
                "provenance": metric.provenance.model_copy(
                    update={
                        "model_checkpoint_identity": hash_file(ckpt_path),
                        "score_artifact_identity": hash_file(manifest_path),
                    }
                )
            }
        )
        metrics_path = layout.policy_run(
            PolicyRunId(cell=cell, policy=metric.policy),
            checkpoint_round,
        ).metrics_path
        write_json_atomic(metrics_path, updated_metric.model_dump(mode="json"))

    return metrics


def _write_smoke_manifest(
    layout: ArtifactLayout,
    cell: TrainingCellId,
    checkpoint_round: RoundIndex,
    checkpoint_path: Path,
) -> None:
    write_json_atomic(
        layout.score_cell(cell, checkpoint_round).manifest_path,
        {
            "schema_version": _SMOKE_MANIFEST_SCHEMA_VERSION,
            "checkpoint_round": checkpoint_round,
            "model_checkpoint_hash": hash_file(checkpoint_path),
            "expected_client_ids": list(_SMOKE_CLIENT_IDS),
            "expected_splits": list(_SMOKE_SCORE_SPLITS),
            "records": [],
            "completion_status": ScoringManifestStatus.COMPLETE,
        },
    )
