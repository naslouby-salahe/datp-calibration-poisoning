from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

from datp.config import ExperimentStage
from datp.core import ClientThreshold, PolicyRunId, TrainingCellId
from datp.data import dataset_for_stage
from datp.enums import (
    ClientStatus,
    DatasetID,
    ThresholdPolicy,
)
from datp.scoring import ScoreProvider
from datp.statistics import compute_fpr_fleet_stats, cv, iqr
from datp.types import (
    ClassificationScore,
    ClientCount,
    ClientId,
    FalseNegativeRate,
    FalsePositiveRate,
    RandomSeed,
    Ratio,
    SampleCount,
    ScoreValue,
    ScoreVector,
    TrueNegativeRate,
    TruePositiveRate,
)


@dataclass(frozen=True, slots=True)
class ConfusionCounts:
    tp: SampleCount
    fp: SampleCount
    tn: SampleCount
    fn: SampleCount


@dataclass(frozen=True, slots=True)
class BinaryMetrics:
    fpr: FalsePositiveRate
    tpr: TruePositiveRate
    tnr: TrueNegativeRate
    fnr: FalseNegativeRate
    balanced_accuracy: ClassificationScore
    precision: ClassificationScore
    recall: ClassificationScore
    macro_f1: ClassificationScore


@dataclass(frozen=True, slots=True)
class BinaryRankingMetrics:
    auroc: ClassificationScore | None
    pr_auc: ClassificationScore | None


@dataclass(frozen=True, slots=True)
class ClientEvaluationRecord:
    client_id: ClientId
    metrics: BinaryMetrics
    confusion: ConfusionCounts
    n_benign: SampleCount
    n_attack: SampleCount
    threshold: ClientThreshold
    evaluation_incomplete: bool


@dataclass(frozen=True, slots=True)
class DispersionMetrics:
    cv_fpr: FalsePositiveRate
    mean_fpr: FalsePositiveRate
    std_fpr: FalsePositiveRate
    iqr_fpr: FalsePositiveRate
    cv_tpr: TruePositiveRate
    iqr_tpr: TruePositiveRate
    max_min_fpr_gap: FalsePositiveRate
    worst_client_fpr: FalsePositiveRate
    worst_client_id: ClientId | None
    eligible_count: ClientCount
    client_count: ClientCount
    worst_ba: ScoreValue
    p10_macro_f1: ClassificationScore


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    run: PolicyRunId
    dataset: DatasetID
    clients: tuple[ClientEvaluationRecord, ...]
    eligible_ids: tuple[ClientId, ...]
    pending_ids: tuple[ClientId, ...]
    incomplete_ids: tuple[ClientId, ...]
    coverage_ratio: Ratio
    dispersion: DispersionMetrics


def recompute_binary_metrics(
    tp: SampleCount, fp: SampleCount, tn: SampleCount, fn: SampleCount
) -> BinaryMetrics:
    n_benign, n_attack = fp + tn, tp + fn
    fpr = fp / n_benign if n_benign else math.nan
    tpr = tp / n_attack if n_attack else math.nan
    tnr = tn / n_benign if n_benign else math.nan
    fnr = fn / n_attack if n_attack else math.nan

    if n_benign and n_attack:
        ba = (tpr + tnr) / 2.0
        prec0 = tn / (tn + fn) if (tn + fn) else 0.0
        f1_0 = 2 * prec0 * tnr / (prec0 + tnr) if (prec0 + tnr) else 0.0
        prec1 = tp / (tp + fp) if (tp + fp) else 0.0
        f1_1 = 2 * prec1 * tpr / (prec1 + tpr) if (prec1 + tpr) else 0.0
        macro_f1 = (f1_0 + f1_1) / 2.0
    else:
        ba = prec1 = macro_f1 = math.nan

    return BinaryMetrics(fpr, tpr, tnr, fnr, ba, prec1, tpr, macro_f1)


def compute_binary_ranking_metrics(
    benign_scores: ScoreVector | None, attack_scores: ScoreVector | None
) -> BinaryRankingMetrics:
    if (
        benign_scores is None
        or attack_scores is None
        or not benign_scores.size
        or not attack_scores.size
    ):
        return BinaryRankingMetrics(None, None)
    labels = np.concatenate([np.zeros(benign_scores.size), np.ones(attack_scores.size)])
    scores = np.concatenate([benign_scores, attack_scores])
    return BinaryRankingMetrics(
        float(roc_auc_score(labels, scores)),
        float(average_precision_score(labels, scores)),
    )


def compute_client_record(
    client_id: ClientId,
    scores_benign: ScoreVector,
    scores_attack: ScoreVector,
    client_threshold: ClientThreshold,
) -> ClientEvaluationRecord:
    benign, attack = (
        np.asarray(scores_benign, dtype=np.float64),
        np.asarray(scores_attack, dtype=np.float64),
    )
    n_benign, n_attack = benign.size, attack.size
    fp = int(np.sum(benign > client_threshold.threshold))
    tp = int(np.sum(attack > client_threshold.threshold))
    tn, fn = n_benign - fp, n_attack - tp
    return ClientEvaluationRecord(
        client_id,
        recompute_binary_metrics(tp, fp, tn, fn),
        ConfusionCounts(tp, fp, tn, fn),
        n_benign,
        n_attack,
        client_threshold,
        n_attack == 0,
    )


def aggregate_dispersion(
    clients: tuple[ClientEvaluationRecord, ...],
    eligible_ids: tuple[ClientId, ...],
    incomplete_ids: tuple[ClientId, ...],
) -> DispersionMetrics:
    eligible_set = set(eligible_ids)
    incomplete_set = set(incomplete_ids)

    eligible_clients = [c for c in clients if c.client_id in eligible_set]
    fpr_arr = np.array([c.metrics.fpr for c in eligible_clients], dtype=np.float64)

    if np.isnan(fpr_arr).any():
        bad_ids = [c.client_id for c in eligible_clients if math.isnan(c.metrics.fpr)]
        raise ValueError(
            f"[evaluation.metrics] Undefined eligible-client FPR. Expected: at least one benign test row. Got: {', '.join(bad_ids)}."
        )

    complete_clients = [
        c for c in eligible_clients if c.client_id not in incomplete_set
    ]
    tpr_arr = np.array(
        [c.metrics.tpr for c in complete_clients if not math.isnan(c.metrics.tpr)],
        dtype=np.float64,
    )
    ba_arr = np.array(
        [
            c.metrics.balanced_accuracy
            for c in complete_clients
            if not math.isnan(c.metrics.balanced_accuracy)
        ],
        dtype=np.float64,
    )
    f1_arr = np.array(
        [
            c.metrics.macro_f1
            for c in complete_clients
            if not math.isnan(c.metrics.macro_f1)
        ],
        dtype=np.float64,
    )

    fpr_stats = compute_fpr_fleet_stats(fpr_arr)
    worst_id = (
        eligible_clients[fpr_stats.worst_index].client_id
        if fpr_arr.size and fpr_stats.worst_index is not None
        else None
    )

    return DispersionMetrics(
        fpr_stats.cv,
        fpr_stats.mean,
        fpr_stats.std,
        fpr_stats.iqr,
        cv(tpr_arr, ddof=0),
        iqr(tpr_arr),
        fpr_stats.max_min_gap,
        fpr_stats.worst_value,
        worst_id,
        fpr_arr.size,
        len(clients),
        float(ba_arr.min()) if ba_arr.size else math.nan,
        float(np.percentile(f1_arr, 10)) if f1_arr.size else math.nan,
    )


def build_evaluation_result(
    *,
    policy: ThresholdPolicy,
    stage: ExperimentStage,
    seed: RandomSeed,
    clients: tuple[ClientEvaluationRecord, ...],
    eligible_ids: tuple[ClientId, ...],
    pending_ids: tuple[ClientId, ...],
    incomplete_ids: tuple[ClientId, ...] | None,
) -> EvaluationResult:
    if not clients:
        raise ValueError(
            "[evaluation.metrics] clients are empty. Expected: at least one client. Got: empty tuple."
        )

    client_ids = [cr.client_id for cr in clients]
    if len(client_ids) != len(set(client_ids)):
        raise ValueError(
            f"[evaluation.metrics] Duplicate client metrics. Expected: unique client_id. Got: {client_ids}."
        )

    if unknown := (set(eligible_ids) | set(pending_ids)) - set(client_ids):
        raise ValueError(
            f"[evaluation.metrics] Eligibility references unknown clients. Expected: IDs present in clients. Got: {sorted(unknown)}."
        )

    if overlap := set(eligible_ids) & set(pending_ids):
        raise ValueError(
            f"[evaluation.metrics] Client has mixed eligibility status. Expected: disjoint IDs. Got: {sorted(overlap)}."
        )

    incomplete = () if incomplete_ids is None else incomplete_ids
    return EvaluationResult(
        PolicyRunId(cell=TrainingCellId(stage=stage, seed=seed), policy=policy),
        dataset_for_stage(stage),
        clients,
        eligible_ids,
        pending_ids,
        incomplete,
        len(eligible_ids) / len(clients),
        aggregate_dispersion(clients, eligible_ids, incomplete),
    )


def evaluate_policy_run(
    client_thresholds: Sequence[ClientThreshold],
    score_root: Path,
    stage: ExperimentStage,
    seed: RandomSeed,
    *,
    score_provider: ScoreProvider | None,
) -> EvaluationResult:
    if not client_thresholds:
        raise ValueError(
            "[evaluation.metrics] client_thresholds is empty. Expected: at least one entry. Got: empty list."
        )

    client_ids = [ct.client_id for ct in client_thresholds]
    if len(client_ids) != len(set(client_ids)):
        raise ValueError(
            "[evaluation.metrics] Duplicate client_id values. Expected: unique ids. Got: duplicates found."
        )

    if len({ct.strategy for ct in client_thresholds}) > 1:
        raise ValueError(
            "[evaluation.metrics] Mixed threshold policies. Expected: one policy. Got: multiple found."
        )

    provider = score_provider or ScoreProvider(score_root)
    clients: list[ClientEvaluationRecord] = []
    eligible: list[ClientId] = []
    pending: list[ClientId] = []
    incomplete: list[ClientId] = []

    for ct in client_thresholds:
        sb, sa = provider.load_test_scores(ct.client_id)
        clients.append(compute_client_record(ct.client_id, sb, sa, ct))
        (pending if ct.status is ClientStatus.CALIBRATION_PENDING else eligible).append(
            ct.client_id
        )
        if sa.size == 0:
            incomplete.append(ct.client_id)

    return build_evaluation_result(
        policy=client_thresholds[0].strategy,
        stage=stage,
        seed=seed,
        clients=tuple(clients),
        eligible_ids=tuple(eligible),
        pending_ids=tuple(pending),
        incomplete_ids=tuple(incomplete),
    )
