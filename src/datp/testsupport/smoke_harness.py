"""Synthetic smoke harness for calibration-poisoning protocol invariants."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from datp.attacks.constants import (
    CLUSTER_K_NBAIOT,
    CLUSTER_MAX_ITER,
    CLUSTER_N_INIT,
    CLUSTER_RANDOM_STATE,
    N_MIN,
    THRESHOLD_QUANTILE,
)
from datp.attacks.enums import PoisoningSourceStrategy
from datp.attacks.execution.cell_runner import (
    InjectionOutcome,
    InjectionSpec,
    PolicyPair,
    inject_single_victim,
    recompute_pair,
)
from datp.attacks.metrics.metric_engine import (
    MetricEngineInput,
    MetricResult,
    compute_metrics,
    compute_mu_flag_threshold,
)
from datp.attacks.score_containers import (
    ScoreCollection,
    VictimSet,
    build_score_collection,
    build_victim_set,
)
from datp.config.models import ExperimentStage
from datp.core.enums import ThresholdPolicy
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.core.seeds import SeedPair
from datp.testsupport.synthetic_scores import SyntheticScoreSet
from datp.thresholding.eligibility import (
    compute_client_thresholds,
    compute_tau_global,
)
from datp.thresholding.policies import compute_cluster

__all__ = ["InjectionOutcome", "PolicyPair", "inject_single_victim", "recompute_pair"]


def collection_from_score_set(score_set: SyntheticScoreSet) -> ScoreCollection:
    """Build a ScoreCollection from deterministic synthetic score arrays."""
    raw = {
        client.client_id: (client.cal, client.test_benign, client.test_attack)
        for client in score_set.clients
    }
    return build_score_collection(raw, n_min=N_MIN)


@dataclass(frozen=True, slots=True)
class SmokeCellResult:
    """Full clean-vs-poisoned result for one smoke matrix cell."""

    policy: ThresholdPolicy
    victim_id: str
    fraction: float
    source: PoisoningSourceStrategy
    outcome: InjectionOutcome
    clean_pair: PolicyPair
    poisoned_pair: PolicyPair
    clean_metrics: MetricResult
    poisoned_metrics: MetricResult
    mu_flag_threshold: float


def _evaluate_state(
    collection: ScoreCollection,
    victim_id: str,
    spec: InjectionSpec,
    policy: ThresholdPolicy,
    mu_flag_threshold: float | None,
) -> tuple[InjectionOutcome, PolicyPair, MetricResult]:
    outcome = inject_single_victim(collection, victim_id=victim_id, spec=spec)
    pair = recompute_pair(collection, outcome.poisoned_cal_set, policy)
    metrics = compute_metrics(
        MetricEngineInput(
            collection=collection,
            pair=pair,
            mu_flag_threshold=mu_flag_threshold,
        )
    )
    return outcome, pair, metrics


def run_smoke_cell(
    collection: ScoreCollection,
    *,
    victim_id: str,
    policy: ThresholdPolicy,
    source: PoisoningSourceStrategy,
    fraction: float,
    training_seed: int = 0,
    poisoning_seed: int = 100,
    scope_idx: int = 0,
) -> SmokeCellResult:
    """Run one clean baseline plus one poisoned outcome.

    The clean baseline is computed first so ``mu_flag_threshold`` is locked from
    clean artifacts before poisoned metrics are evaluated.
    """
    base_spec = InjectionSpec(
        source=source,
        fraction=0.0,
        seed_pair=SeedPair(
            training_seed=training_seed,
            poisoning_seed=poisoning_seed,
        ),
        objective=None,
        scope_idx=scope_idx,
    )

    _, clean_pair, clean_metrics = _evaluate_state(
        collection,
        victim_id,
        base_spec,
        policy,
        None,
    )
    mu_flag = compute_mu_flag_threshold(clean_metrics.fleet_fpr.mean_fpr)

    poisoned_spec = InjectionSpec(
        source=source,
        fraction=fraction,
        seed_pair=base_spec.seed_pair,
        objective=base_spec.objective,
        scope_idx=base_spec.scope_idx,
    )
    outcome, poisoned_pair, poisoned_metrics = _evaluate_state(
        collection,
        victim_id,
        poisoned_spec,
        policy,
        mu_flag,
    )

    return SmokeCellResult(
        policy=policy,
        victim_id=victim_id,
        fraction=fraction,
        source=source,
        outcome=outcome,
        clean_pair=clean_pair,
        poisoned_pair=poisoned_pair,
        clean_metrics=clean_metrics,
        poisoned_metrics=poisoned_metrics,
        mu_flag_threshold=mu_flag,
    )


def victim_seed_deltas(
    collection: ScoreCollection,
    *,
    victim_id: str,
    policy: ThresholdPolicy,
    source: PoisoningSourceStrategy,
    fraction: float,
    poisoning_seeds: tuple[int, ...],
    training_seed: int = 0,
    scope_idx: int = 0,
) -> dict[int, float]:
    """Return per-poisoning-seed victim Δτ for one victim."""

    def get_delta(ps: int) -> float:
        spec = InjectionSpec(
            source=source,
            fraction=fraction,
            seed_pair=SeedPair(training_seed=training_seed, poisoning_seed=ps),
            objective=None,
            scope_idx=scope_idx,
        )
        _, _, metrics = _evaluate_state(collection, victim_id, spec, policy, None)
        return metrics.delta_tau[victim_id].delta_tau

    return {ps: get_delta(ps) for ps in poisoning_seeds}


def cluster_count(
    cal_dict: dict[str, np.ndarray],
    *,
    q: float = THRESHOLD_QUANTILE,
    n_min: int = N_MIN,
    seed: int = 0,
    k: int = CLUSTER_K_NBAIOT,
    n_init: int = CLUSTER_N_INIT,
    max_iter: int = CLUSTER_MAX_ITER,
    random_state: int = CLUSTER_RANDOM_STATE,
) -> int:
    """Run CLUSTER_THRESHOLD and return the realized fixed cluster count."""
    eligible_ids = [cid for cid, arr in cal_dict.items() if arr.size >= n_min]
    taus = compute_client_thresholds(
        {cid: cal_dict[cid] for cid in eligible_ids},
        eligible_ids,
        q=q,
    )
    run = PolicyRunId(
        cell=TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=seed),
        policy=ThresholdPolicy.CLUSTER_THRESHOLD,
    )
    result = compute_cluster(
        cal_dict,
        n_min=n_min,
        tau_global=compute_tau_global(taus),
        q=q,
        random_state=random_state,
        cluster_k=k,
        n_init=n_init,
        max_iter=max_iter,
        run=run,
    )
    if result.metadata.cluster is None:
        raise RuntimeError("cluster metadata must be set after CLUSTER_THRESHOLD run")
    return result.metadata.cluster.k


def build_smoke_victim_set(score_set: SyntheticScoreSet) -> VictimSet:
    """Build eligible-victim metadata from a synthetic score set."""
    return build_victim_set(collection_from_score_set(score_set))
