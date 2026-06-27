"""Binary classification metrics, dispersion stats, and client-level evaluation records."""

from __future__ import annotations

import json
import math
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

from datp.artifacts.names import ArtifactDir
from datp.config.models import ExperimentStage
from datp.core.enums import ConfusionKey, PayloadKey, ThresholdPolicy
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.core.types import ClientThreshold
from datp.data.catalog import DatasetID, dataset_for_stage
from datp.scoring.loading import ScoreProvider
from datp.statistics.aggregates import compute_fpr_fleet_stats, cv, iqr


@dataclass(frozen=True, slots=True)
class ConfusionCounts:
    """Confusion matrix counts (tp, fp, tn, fn) for binary classifier evaluation."""

    tp: int
    fp: int
    tn: int
    fn: int


@dataclass(frozen=True, slots=True)
class BinaryMetrics:
    """Aggregated binary classification metrics derived from a confusion matrix."""

    fpr: float
    tpr: float
    tnr: float
    fnr: float
    balanced_accuracy: float
    precision: float
    recall: float
    macro_f1: float


@dataclass(frozen=True, slots=True)
class BinaryRankingMetrics:
    """Ranking-based metrics (AUROC, PR-AUC) for binary classification scores."""

    auroc: float | None
    pr_auc: float | None


@dataclass(frozen=True, slots=True)
class ClientEvaluationRecord:
    """Per-client evaluation record: binary metrics, confusion counts, and threshold info."""

    client_id: str
    metrics: BinaryMetrics
    confusion: ConfusionCounts
    n_benign: int
    n_attack: int
    threshold: ClientThreshold
    evaluation_incomplete: bool


@dataclass(frozen=True, slots=True)
class DispersionMetrics:
    """Fleet-level dispersion statistics (CV, IQR, min/max gaps) across eligible clients."""

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
class PerAttackFamilyTPR:
    """Per-attack-family true positive rate for a single client."""

    client_id: str
    attack_label: str
    family: str | None
    detected_count: int
    denominator: int
    tpr: float


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Top-level evaluation result for a policy run: per-client records and fleet dispersion."""

    run: PolicyRunId
    dataset: DatasetID
    clients: tuple[ClientEvaluationRecord, ...]
    eligible_ids: tuple[str, ...]
    pending_ids: tuple[str, ...]
    incomplete_ids: tuple[str, ...]
    coverage_ratio: float
    dispersion: DispersionMetrics

    @property
    def policy(self) -> ThresholdPolicy:
        """The threshold policy for this evaluation run."""
        return self.run.policy

    @property
    def stage(self) -> ExperimentStage:
        """The experiment stage for this evaluation run."""
        return self.run.stage

    @property
    def seed(self) -> int:
        """The random seed for this evaluation run."""
        return self.run.seed

    @property
    def cv_fpr(self) -> float:
        """Coefficient of variation of FPR across eligible clients."""
        return self.dispersion.cv_fpr

    @property
    def mean_fpr(self) -> float:
        """Mean FPR across eligible clients."""
        return self.dispersion.mean_fpr

    @property
    def std_fpr(self) -> float:
        """Standard deviation of FPR across eligible clients."""
        return self.dispersion.std_fpr

    @property
    def cv_tpr(self) -> float:
        """Coefficient of variation of TPR across eligible clients."""
        return self.dispersion.cv_tpr

    @property
    def iqr_fpr(self) -> float:
        """Interquartile range of FPR across eligible clients."""
        return self.dispersion.iqr_fpr

    @property
    def iqr_tpr(self) -> float:
        """Interquartile range of TPR across eligible clients."""
        return self.dispersion.iqr_tpr

    @property
    def max_min_fpr_gap(self) -> float:
        """Maximum minus minimum FPR gap across eligible clients."""
        return self.dispersion.max_min_fpr_gap

    @property
    def worst_client_fpr(self) -> float:
        """FPR of the worst-performing eligible client."""
        return self.dispersion.worst_client_fpr

    @property
    def worst_client_id(self) -> str | None:
        """ID of the worst-performing eligible client, or None if none exist."""
        return self.dispersion.worst_client_id

    @property
    def eligible_count(self) -> int:
        """Number of eligible clients included in dispersion statistics."""
        return self.dispersion.eligible_count

    @property
    def client_count(self) -> int:
        """Total number of clients in the evaluation run."""
        return self.dispersion.client_count

    @property
    def worst_ba(self) -> float:
        """Minimum balanced accuracy across complete eligible clients."""
        return self.dispersion.worst_ba

    @property
    def p10_macro_f1(self) -> float:
        """10th percentile of macro F1 across complete eligible clients."""
        return self.dispersion.p10_macro_f1

    @property
    def eval_incomplete_ids(self) -> tuple[str, ...]:
        """IDs of clients with incomplete evaluation (zero attack samples)."""
        return self.incomplete_ids


def recompute_binary_metrics(tp: int, fp: int, tn: int, fn: int) -> BinaryMetrics:
    """Compute binary classification metrics directly from confusion matrix counts."""
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
    benign_scores: np.ndarray, attack_scores: np.ndarray
) -> BinaryRankingMetrics:
    """Compute AUROC and PR-AUC from benign and attack score arrays."""
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
    client_id: str,
    scores_benign: np.ndarray,
    scores_attack: np.ndarray,
    client_threshold: ClientThreshold,
) -> ClientEvaluationRecord:
    """Build a single client's evaluation record from scores and threshold."""
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
    eligible_ids: tuple[str, ...],
    incomplete_ids: tuple[str, ...],
) -> DispersionMetrics:
    """Aggregate fleet-level dispersion metrics across eligible and complete clients."""
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
    seed: int,
    clients: tuple[ClientEvaluationRecord, ...],
    eligible_ids: tuple[str, ...],
    pending_ids: tuple[str, ...],
    incomplete_ids: tuple[str, ...] | None,
) -> EvaluationResult:
    """Construct and validate an EvaluationResult from per-client records and eligibility sets."""
    if not clients:
        raise ValueError(
            "[evaluation.metrics] clients are empty. Expected: at least one client. Got: empty tuple."
        )

    client_ids = [cr.client_id for cr in clients]
    if len(client_ids) != len(set(client_ids)):
        raise ValueError(
            f"[evaluation.metrics] Duplicate client metrics. Expected: unique client_id. Got: {str(client_ids)}."
        )

    if unknown := (set(eligible_ids) | set(pending_ids)) - set(client_ids):
        raise ValueError(
            f"[evaluation.metrics] Eligibility references unknown clients. Expected: IDs present in clients. Got: {str(sorted(unknown))}."
        )

    if overlap := set(eligible_ids) & set(pending_ids):
        raise ValueError(
            f"[evaluation.metrics] Client has mixed eligibility status. Expected: disjoint IDs. Got: {str(sorted(overlap))}."
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
    seed: int,
    *,
    score_provider: ScoreProvider | None,
) -> EvaluationResult:
    """Evaluate a full policy run by computing per-client records and aggregating results."""
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
    clients, eligible, pending, incomplete = [], [], [], []

    for ct in client_thresholds:
        sb, sa = provider.load_test_scores(ct.client_id)
        clients.append(compute_client_record(ct.client_id, sb, sa, ct))
        (pending if ct.calibration_pending else eligible).append(ct.client_id)
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


def compute_fpr(benign_errors: np.ndarray, threshold: float) -> float:
    """Return the false positive rate for benign errors at the given threshold."""
    return float(np.mean(benign_errors > threshold)) if benign_errors.size else 0.0


def compute_empirical_coverage(test_benign: np.ndarray, threshold: float) -> float:
    """Return the empirical coverage of benign scores at or below the threshold."""
    return float(np.mean(test_benign <= threshold)) if test_benign.size else 0.0


def compute_per_attack_tpr(
    client_id: str,
    attack_scores: np.ndarray,
    attack_labels: np.ndarray,
    threshold: float,
    family_fn: Callable[[str], str | None],
) -> list[PerAttackFamilyTPR]:
    """Compute per-attack-family true positive rates for a single client."""
    scores, labels = (
        np.asarray(attack_scores, dtype=np.float64),
        np.asarray(attack_labels, dtype=object),
    )
    if scores.shape[0] != labels.shape[0]:
        raise ValueError(
            f"[evaluation.metrics] mismatch. Expected: {str(scores.shape[0])}. Got: {str(labels.shape[0])}."
        )

    res = []
    for lbl in np.unique(labels):
        mask = labels == lbl
        detected = int(np.sum(scores[mask] > threshold))
        denom = int(mask.sum())
        res.append(
            PerAttackFamilyTPR(
                client_id,
                str(lbl),
                family_fn(str(lbl)),
                detected,
                denom,
                detected / denom if denom else math.nan,
            )
        )
    return res


def save_confusion_matrices(eval_result: EvaluationResult, base_dir: Path) -> Path:
    """Save confusion matrices from an evaluation result as a JSON artifact."""
    out_path = (
        Path(base_dir)
        / ArtifactDir.CONFUSION_MATRICES
        / str(eval_result.stage)
        / f"{eval_result.policy}_seed{eval_result.seed}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        PayloadKey.POLICY: eval_result.policy.value,
        PayloadKey.STAGE: eval_result.stage.value,
        PayloadKey.SEED: eval_result.seed,
        PayloadKey.COVERAGE_RATIO: eval_result.coverage_ratio,
        PayloadKey.PER_CLIENT: [
            {
                PayloadKey.CLIENT_ID: cr.client_id,
                PayloadKey.CONFUSION_MATRIX: {
                    ConfusionKey.TP.value: cr.confusion.tp,
                    ConfusionKey.FP.value: cr.confusion.fp,
                    ConfusionKey.TN.value: cr.confusion.tn,
                    ConfusionKey.FN.value: cr.confusion.fn,
                },
                PayloadKey.N_BENIGN: cr.n_benign,
                PayloadKey.N_ATTACK: cr.n_attack,
            }
            for cr in eval_result.clients
        ],
    }

    fd, tmp = tempfile.mkstemp(dir=out_path.parent, suffix=".tmp.json")
    try:
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
            f.write("\n")
        Path(tmp).replace(out_path)
    except OSError:
        Path(tmp).unlink(missing_ok=True)
        raise
    return out_path
