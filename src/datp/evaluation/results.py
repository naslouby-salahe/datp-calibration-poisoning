from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from datp.config.stages import ExperimentStage
from datp.core.enums import ThresholdPolicy
from datp.core.errors import fmt
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.core.types import ClientThreshold
from datp.data.catalog import DatasetID, dataset_for_stage
from datp.evaluation.client_records import ClientEvaluationRecord, compute_client_record
from datp.evaluation.dispersion import DispersionMetrics, aggregate_dispersion
from datp.scoring.loading import ScoreProvider

_MODULE = "evaluation.results"


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
    dispersion = aggregate_dispersion(clients, eligible_ids, incomplete)
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
                "Mixed threshold policies in client_thresholds",
                "one policy",
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
