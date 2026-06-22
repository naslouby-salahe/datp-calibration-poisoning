from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from datp.config.stages import ExperimentStage
from datp.core.errors import fmt
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.core.types import ClientThreshold
from datp.data.catalog import DatasetID
from datp.data.catalog import dataset_for_stage
from datp.scoring.loading import ScoreProvider
from datp.statistics.cv import cv

_MODULE = "evaluation.metrics"


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


@dataclass(frozen=True, slots=True)
class DispersionMetrics:
    """Aggregate dispersion statistics across eligible clients."""

    cv_fpr: float
    mean_fpr: float
    std_fpr: float
    iqr_fpr: float
    cv_tpr: float
    iqr_tpr: float
    max_min_fpr_gap: float
    worst_client_fpr: float
    worst_client_id: str | None
    eligible_count: int
    client_count: int
    worst_ba: float
    p10_macro_f1: float


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Canonical evaluation result for one policy run."""

    run: PolicyRunId
    dataset: DatasetID
    clients: tuple[ClientEvaluationRecord, ...]
    eligible_ids: tuple[str, ...]
    pending_ids: tuple[str, ...]
    incomplete_ids: tuple[str, ...]
    coverage_ratio: float
    dispersion: DispersionMetrics

    # --- Property accessors for widely-used attribute access patterns ---

    @property
    def policy(self) -> ThresholdPolicy:
        return self.run.policy

    @property
    def stage(self) -> ExperimentStage:
        return self.run.stage

    @property
    def seed(self) -> int:
        return self.run.seed

    @property
    def cv_fpr(self) -> float:
        return self.dispersion.cv_fpr

    @property
    def mean_fpr(self) -> float:
        return self.dispersion.mean_fpr

    @property
    def std_fpr(self) -> float:
        return self.dispersion.std_fpr

    @property
    def cv_tpr(self) -> float:
        return self.dispersion.cv_tpr

    @property
    def iqr_fpr(self) -> float:
        return self.dispersion.iqr_fpr

    @property
    def iqr_tpr(self) -> float:
        return self.dispersion.iqr_tpr

    @property
    def max_min_fpr_gap(self) -> float:
        return self.dispersion.max_min_fpr_gap

    @property
    def worst_client_fpr(self) -> float:
        return self.dispersion.worst_client_fpr

    @property
    def worst_client_id(self) -> str | None:
        return self.dispersion.worst_client_id

    @property
    def eligible_count(self) -> int:
        return self.dispersion.eligible_count

    @property
    def client_count(self) -> int:
        return self.dispersion.client_count

    @property
    def worst_ba(self) -> float:
        return self.dispersion.worst_ba

    @property
    def p10_macro_f1(self) -> float:
        return self.dispersion.p10_macro_f1

    @property
    def eval_incomplete_ids(self) -> tuple[str, ...]:
        return self.incomplete_ids


def compute_client_record(
    client_id: str,
    scores_benign: np.ndarray,
    scores_attack: np.ndarray,
    client_threshold: ClientThreshold,
) -> ClientEvaluationRecord:
    """Compute per-client binary classification metrics (anomaly rule: score > threshold)."""
    benign = np.asarray(scores_benign, dtype=np.float64)
    attack = np.asarray(scores_attack, dtype=np.float64)
    n_benign = int(benign.size)
    n_attack = int(attack.size)

    fp = int(np.sum(benign > client_threshold.threshold))
    tn = n_benign - fp
    tp = int(np.sum(attack > client_threshold.threshold))
    fn = n_attack - tp

    bm = recompute_binary_metrics(tp, fp, tn, fn)

    return ClientEvaluationRecord(
        client_id=client_id,
        metrics=bm,
        confusion=ConfusionCounts(tp=tp, fp=fp, tn=tn, fn=fn),
        n_benign=n_benign,
        n_attack=n_attack,
        threshold=client_threshold,
        evaluation_incomplete=n_attack == 0,
    )


def _aggregate_dispersion(
    clients: tuple[ClientEvaluationRecord, ...],
    eligible_ids: tuple[str, ...],
    incomplete_ids: tuple[str, ...],
) -> DispersionMetrics:
    from datp.evaluation.metric_filtering import _filter_eligible_metrics

    fm = _filter_eligible_metrics(clients, eligible_ids, incomplete_ids)

    fpr_arr = fm.fpr_eligible
    if np.isnan(fpr_arr).any():
        eligible_set = set(eligible_ids)
        bad_ids = [
            cr.client_id
            for cr in clients
            if cr.client_id in eligible_set and math.isnan(cr.metrics.fpr)
        ]
        raise ValueError(
            fmt(
                _MODULE,
                "Undefined eligible-client FPR cannot enter dispersion metrics",
                "every eligible client has at least one benign test row",
                ", ".join(bad_ids) or "unknown",
            )
        )
    tpr_arr = fm.tpr_eligible
    ba_arr = fm.ba_eligible
    f1_arr = fm.f1_eligible

    cv_fpr = cv(fpr_arr, ddof=0)
    mean_fpr = float(fpr_arr.mean()) if fpr_arr.size > 0 else math.nan
    std_fpr = float(fpr_arr.std(ddof=1)) if fpr_arr.size >= 2 else math.nan
    iqr_fpr = (
        float(np.percentile(fpr_arr, 75) - np.percentile(fpr_arr, 25))
        if fpr_arr.size >= 2
        else math.nan
    )
    if fpr_arr.size > 0:
        worst_idx = int(np.argmax(fpr_arr))
        worst_client_fpr = float(fpr_arr[worst_idx])
        eligible_list = [c for c in clients if c.client_id in set(eligible_ids)]
        worst_client_id: str | None = (
            eligible_list[worst_idx].client_id
            if worst_idx < len(eligible_list)
            else None
        )
        max_min_fpr_gap = float(fpr_arr.max() - fpr_arr.min())
    else:
        worst_client_fpr = math.nan
        worst_client_id = None
        max_min_fpr_gap = math.nan
    cv_tpr = cv(tpr_arr, ddof=0)
    iqr_tpr = (
        float(np.percentile(tpr_arr, 75) - np.percentile(tpr_arr, 25))
        if tpr_arr.size >= 2
        else math.nan
    )
    worst_ba = float(ba_arr.min()) if ba_arr .size > 0 else math.nan
    p10_macro_f1 = float(np.percentile(f1_arr, 10)) if f1_arr.size > 0 else math.nan

    return DispersionMetrics(
        cv_fpr=cv_fpr,
        mean_fpr=mean_fpr,
        std_fpr=std_fpr,
        iqr_fpr=iqr_fpr,
        cv_tpr=cv_tpr,
        iqr_tpr=iqr_tpr,
        max_min_fpr_gap=max_min_fpr_gap,
        worst_client_fpr=worst_client_fpr,
        worst_client_id=worst_client_id,
        eligible_count=fpr_arr.size,
        client_count=len(clients),
        worst_ba=worst_ba,
        p10_macro_f1=p10_macro_f1,
    )


def _validate_client_records(
    clients: tuple[ClientEvaluationRecord, ...],
    eligible_ids: tuple[str, ...],
    pending_ids: tuple[str, ...],
) -> None:
    if not clients:
        raise ValueError(
            fmt(_MODULE, "clients are empty", "at least one client", "empty tuple")
        )
    client_ids = [cr.client_id for cr in clients]
    if len(client_ids) != len(set(client_ids)):
        raise ValueError(
            fmt(
                _MODULE,
                "Duplicate client metrics",
                "unique client_id values",
                str(client_ids),
            )
        )
    known = set(client_ids)
    unknown_eligible = sorted(set(eligible_ids) - known)
    unknown_pending = sorted(set(pending_ids) - known)
    if unknown_eligible or unknown_pending:
        raise ValueError(
            fmt(
                _MODULE,
                "Eligibility references unknown clients",
                "eligible/pending IDs are present in clients",
                f"eligible={unknown_eligible}, pending={unknown_pending}",
            )
        )
    overlap = sorted(set(eligible_ids) & set(pending_ids))
    if overlap:
        raise ValueError(
            fmt(
                _MODULE,
                "Client has mixed eligibility status",
                "disjoint eligible/pending IDs",
                str(overlap),
            )
        )


def build_evaluation_result(
    *,
    policy: ThresholdPolicy,
    stage: ExperimentStage,
    seed: int,
    clients: tuple[ClientEvaluationRecord, ...],
    eligible_ids: tuple[str, ...],
    pending_ids: tuple[str, ...],
    incomplete_ids: tuple[str, ...] | None,
) -> EvaluationResult:
    _validate_client_records(clients, eligible_ids, pending_ids)
    incomplete = () if incomplete_ids is None else incomplete_ids
    dispersion = _aggregate_dispersion(clients, eligible_ids, incomplete)
    run = PolicyRunId(
        cell=TrainingCellId(stage=stage, seed=seed),
        policy=policy,
    )
    return EvaluationResult(
        run=run,
        dataset=dataset_for_stage(stage),
        clients=clients,
        eligible_ids=eligible_ids,
        pending_ids=pending_ids,
        incomplete_ids=incomplete,
        coverage_ratio=len(eligible_ids) / len(clients),
        dispersion=dispersion,
    )


def _find_duplicate_ids(ids: list[str]) -> list[str]:
    seen: set[str] = set()
    dupes: list[str] = []
    for cid in ids:
        if cid in seen:
            dupes.append(cid)
        else:
            seen.add(cid)
    return dupes


def _check_threshold_uniqueness(client_thresholds: Sequence[ClientThreshold]) -> None:
    client_ids = [ct.client_id for ct in client_thresholds]
    if len(client_ids) != len(set(client_ids)):
        dupes = _find_duplicate_ids(client_ids)
        raise ValueError(
            fmt(
                _MODULE,
                "Duplicate client_id values in client_thresholds",
                "unique ids",
                str(dupes),
            )
        )


def _check_threshold_strategy_uniformity(
    client_thresholds: Sequence[ClientThreshold],
) -> None:
    strategies = {ct.strategy for ct in client_thresholds}
    if len(strategies) > 1:
        raise ValueError(
            fmt(
                _MODULE,
                "Mixed threshold strategies in client_thresholds",
                "one strategy",
                str([s.value for s in strategies]),
            )
        )


def _validate_client_thresholds(client_thresholds: Sequence[ClientThreshold]) -> None:
    if not client_thresholds:
        raise ValueError(
            fmt(
                _MODULE,
                "client_thresholds is empty",
                "at least one entry",
                "empty list",
            )
        )
    _check_threshold_uniqueness(client_thresholds)
    _check_threshold_strategy_uniformity(client_thresholds)


def evaluate_policy_run(
    client_thresholds: Sequence[ClientThreshold],
    score_root: Path,
    stage: ExperimentStage,
    seed: int,
    *,
    score_provider: ScoreProvider | None,
) -> EvaluationResult:
    """Evaluate a baseline by loading per-client score artifacts and computing CV(FPR/TPR) over eligible clients only.

    Missing score artifacts always raise FileNotFoundError (no silent fallback).
    """
    _validate_client_thresholds(client_thresholds)

    provider = score_provider
    if provider is None:
        provider = ScoreProvider(score_root)

    client_records: list[ClientEvaluationRecord] = []
    eligible_ids: list[str] = []
    pending_ids: list[str] = []
    incomplete_ids: list[str] = []

    for ct in client_thresholds:
        cid = ct.client_id
        scores_benign, scores_attack = provider.load_test_scores(cid)

        client_records.append(
            compute_client_record(cid, scores_benign, scores_attack, ct)
        )
        (pending_ids if ct.calibration_pending else eligible_ids).append(cid)
        if len(scores_attack) == 0:
            incomplete_ids.append(cid)

    return build_evaluation_result(
        policy=client_thresholds[0].strategy,
        stage=stage,
        seed=seed,
        clients=tuple(client_records),
        eligible_ids=tuple(eligible_ids),
        pending_ids=tuple(pending_ids),
        incomplete_ids=tuple(incomplete_ids),
    )


def compute_fpr(benign_errors: np.ndarray, threshold: float) -> float:
    """Fraction of benign reconstruction errors exceeding the threshold."""
    if benign_errors.size == 0:
        return 0.0
    return float(np.mean(benign_errors > threshold))


def compute_empirical_coverage(test_benign: np.ndarray, threshold: float) -> float:
    """Fraction of test_benign scores <= threshold."""
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
    """Compute per-attack-label TPR; attack_scores and attack_labels must be aligned arrays."""
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
