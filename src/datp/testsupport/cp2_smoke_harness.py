"""CP2 synthetic smoke harness (CPU-only, deterministic, no real data).

Wires the full CP2 calibration-poisoning pipeline end to end on synthetic score
arrays so the Phase D smoke invariants can be asserted before any real N-BaIoT
artifact is touched:

    synthetic scores
      -> Cp2ScoreCollection / Cp2VictimSet
      -> victim-local reservoir (source strategy)
      -> REPLACE_FIXED_BUDGET injection (no in-place mutation)
      -> B1 / B2 / B4 threshold recomputation (+ B4 Δτ decomposition)
      -> CP2 metric engine (Δτ family, CV(FPR)+coverage, AUROC invariance)
      -> two-layer inference (bootstrap on 5 seed-level aggregates)
      -> run manifest emission / round-trip

The harness contains no science of its own — it only orchestrates already-tested
core modules. All randomness flows through ``SeedSequence`` (no integer seed
addition). Every generator is CPU-only.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from datp.artifacts.poison_names import (
    CP2_B4_K,
    CP2_B4_N_INIT,
    CP2_B4_RANDOM_STATE,
    CP2_N_MIN,
    CP2_Q,
)
from datp.attacks.cell_runner import (
    InjectionOutcome,
    PolicyPair,
    inject_single_victim,
    pending_threshold,
    recompute_pair,
)
from datp.attacks.metric_engine import (
    Cp2MetricResult,
    compute_metrics,
    compute_mu_flag_threshold,
)
from datp.attacks.poison_enums import (
    PoisoningSourceStrategy,
    ThresholdPolicy,
)
from datp.attacks.score_containers import (
    Cp2ScoreCollection,
    Cp2VictimSet,
    build_score_collection,
    build_victim_set,
)
from datp.core.enums import Baseline, Regime
from datp.core.identity import BaselineRunId, TrainingCellId
from datp.testsupport.synthetic_scores import SyntheticScoreSet
from datp.thresholding.eligibility import compute_client_thresholds, compute_tau_global
from datp.thresholding.strategies.b4_cluster import compute as b4_compute

__all__ = [
    "InjectionOutcome",
    "PolicyPair",
    "inject_single_victim",
    "pending_threshold",
    "recompute_pair",
]


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------

def collection_from_score_set(score_set: SyntheticScoreSet) -> Cp2ScoreCollection:
    """Build a Cp2ScoreCollection from a synthetic score set."""
    raw = {
        c.client_id: (c.cal, c.test_benign, c.test_attack)
        for c in score_set.clients
    }
    return build_score_collection(raw, n_min=CP2_N_MIN)


# ---------------------------------------------------------------------------
# One full cell: clean baseline + poisoned outcome
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SmokeCellResult:
    """Full clean-vs-poisoned result for one (policy, source, fraction) cell."""

    policy: ThresholdPolicy
    victim_id: str
    fraction: float
    source: PoisoningSourceStrategy
    outcome: InjectionOutcome
    clean_pair: PolicyPair
    poisoned_pair: PolicyPair
    clean_metrics: Cp2MetricResult
    poisoned_metrics: Cp2MetricResult
    mu_flag_threshold: float


def run_smoke_cell(
    collection: Cp2ScoreCollection,
    *,
    victim_id: str,
    policy: ThresholdPolicy,
    source: PoisoningSourceStrategy,
    fraction: float,
    training_seed: int = 0,
    poisoning_seed: int = 100,
    scope_idx: int = 0,
    q: float = CP2_Q,
    b4_seed: int = 0,
) -> SmokeCellResult:
    """Run one full smoke cell.

    Order matters: the clean baseline is computed first so ``mu_flag_threshold`` is
    locked from clean artifacts BEFORE the poisoned metrics are evaluated.
    """
    # Clean baseline (fraction 0 => poisoned cal == clean cal, exact copies).
    clean_outcome = inject_single_victim(
        collection,
        victim_id=victim_id,
        source=source,
        fraction=0.0,
        training_seed=training_seed,
        poisoning_seed=poisoning_seed,
        scope_idx=scope_idx,
    )
    clean_pair = recompute_pair(
        collection, clean_outcome.poisoned_cal, policy, q=q, seed=b4_seed
    )
    clean_metrics = compute_metrics(collection, clean_pair, None)

    # Lock mu_flag_threshold from the clean fleet FPR.
    mu_flag = compute_mu_flag_threshold(clean_metrics.fleet_fpr.mean_fpr)

    # Poisoned outcome.
    outcome = inject_single_victim(
        collection,
        victim_id=victim_id,
        source=source,
        fraction=fraction,
        training_seed=training_seed,
        poisoning_seed=poisoning_seed,
        scope_idx=scope_idx,
    )
    poisoned_pair = recompute_pair(
        collection, outcome.poisoned_cal, policy, q=q, seed=b4_seed
    )
    poisoned_metrics = compute_metrics(collection, poisoned_pair, mu_flag)

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


# ---------------------------------------------------------------------------
# Two-layer seed sweep (for the statistics invariant)
# ---------------------------------------------------------------------------

def victim_seed_deltas(
    collection: Cp2ScoreCollection,
    *,
    victim_id: str,
    policy: ThresholdPolicy,
    source: PoisoningSourceStrategy,
    fraction: float,
    poisoning_seeds: tuple[int, ...],
    training_seed: int = 0,
    scope_idx: int = 0,
    q: float = CP2_Q,
) -> dict[int, float]:
    """Per-seed victim Δτ for one victim across the poisoning-seed pool.

    Returns {poisoning_seed: Δτ_victim}. Used to build the two-layer paired-delta
    structure for inference (Layer 1).
    """
    deltas: dict[int, float] = {}
    for ps in poisoning_seeds:
        outcome = inject_single_victim(
            collection,
            victim_id=victim_id,
            source=source,
            fraction=fraction,
            training_seed=training_seed,
            poisoning_seed=ps,
            scope_idx=scope_idx,
        )
        pair = recompute_pair(collection, outcome.poisoned_cal, policy, q=q)
        entry = compute_metrics(collection, pair, None).delta_tau[victim_id]
        deltas[ps] = entry.delta_tau
    return deltas


# ---------------------------------------------------------------------------
# B4 cluster-count probe (K must stay fixed at 3)
# ---------------------------------------------------------------------------

def b4_cluster_count(
    cal_dict: dict[str, np.ndarray],
    *,
    q: float = CP2_Q,
    n_min: int = CP2_N_MIN,
    seed: int = 0,
    k: int = CP2_B4_K,
    n_init: int = CP2_B4_N_INIT,
    random_state: int = CP2_B4_RANDOM_STATE,
) -> int:
    """Run B4 on a calibration dict and return the realized cluster count K.

    Asserts (via the result) that B4 is never silently overridden to a
    data-adaptive K — the procedure is pinned to k_candidates=[k].
    """
    eligible_ids = [cid for cid, arr in cal_dict.items() if arr.size >= n_min]
    taus = compute_client_thresholds(
        {cid: cal_dict[cid] for cid in eligible_ids}, eligible_ids, q=q
    )
    tau_global = compute_tau_global(taus)
    cell = TrainingCellId(regime=Regime.A, seed=seed, alpha=None)
    run = BaselineRunId(cell=cell, baseline=Baseline.B4)
    result = b4_compute(
        cal_dict,
        n_min=n_min,
        tau_global=tau_global,
        q=q,
        random_state=random_state,
        k_regime_a=k,
        k_candidates=[k],
        n_init=n_init,
        run=run,
        regime=Regime.A,
    )
    assert result.metadata.b4 is not None, "B4 metadata must be set after B4 run"
    return result.metadata.b4.k


def build_smoke_victim_set(score_set: SyntheticScoreSet) -> Cp2VictimSet:
    """Convenience: synthetic score set -> victim set (eligible clients only)."""
    return build_victim_set(collection_from_score_set(score_set))
