"""Single-victim injection and threshold-recompute orchestration for one CP2 cell.

Pure orchestration over already-tested core modules (reservoir/source
selection, fixed-budget injection, B1/B2/B4 threshold recompute) — no science
of its own. Shared by the Phase D synthetic smoke harness
(``datp.testsupport.cp2_smoke_harness``) and the Phase E real-data MVP runner
(``datp.attacks.mvp_runner``) so both run the identical pipeline. All
randomness flows through ``SeedSequence`` (no integer seed addition); clean
arrays are never mutated in place.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import assert_never

import numpy as np

from datp.artifacts.poison_names import CP2_Q, CP2_TAIL_MASS
from datp.attacks.b4_recompute import Cp2B4ThresholdPair, compute_b4_pair
from datp.attacks.injector import InjectionResult, inject_fixed_budget
from datp.attacks.poison_enums import PoisoningSourceStrategy, ThresholdPolicy
from datp.attacks.reservoir import ReservoirResult
from datp.attacks.score_containers import Cp2ScoreCollection
from datp.attacks.source_strategies import select_reservoir
from datp.attacks.threshold_recompute import (
    Cp2ThresholdPair,
    compute_b1_pair,
    compute_b2_pair,
)
from datp.core.seed_sequence import make_cp2_rng

PolicyPair = Cp2ThresholdPair | Cp2B4ThresholdPair


def _client_idx(collection: Cp2ScoreCollection, client_id: str) -> int:
    """Deterministic per-client index for SeedSequence (position in sorted ids)."""
    return collection.all_ids.index(client_id)


@dataclass(frozen=True, slots=True)
class InjectionOutcome:
    """Result of injecting one victim; carries the full poisoned cal dict.

    poisoned_cal holds every eligible client's calibration array: the victim's
    is poisoned, every other eligible client's is an exact copy of its clean
    array.
    """

    victim_id: str
    poisoned_cal: dict[str, np.ndarray]
    reservoir: ReservoirResult
    injection: InjectionResult


def inject_single_victim(
    collection: Cp2ScoreCollection,
    *,
    victim_id: str,
    source: PoisoningSourceStrategy,
    fraction: float,
    training_seed: int,
    poisoning_seed: int,
    scope_idx: int = 0,
    tail_mass: float = CP2_TAIL_MASS,
) -> InjectionOutcome:
    """Build the poisoned calibration dict for a single-client attack.

    Non-victim eligible clients keep an exact copy of their clean cal. The
    victim's clean cal is never mutated in place (inject_fixed_budget copies
    internally).
    """
    victim_clean = collection.clients[victim_id].cal
    reservoir = select_reservoir(
        source=source, clean_cal=victim_clean, tail_mass=tail_mass
    )
    rng = make_cp2_rng(
        training_seed=training_seed,
        poisoning_seed=poisoning_seed,
        client_idx=_client_idx(collection, victim_id),
        scope_idx=scope_idx,
        child_index=0,
    )
    injection = inject_fixed_budget(
        clean_cal=victim_clean,
        reservoir=reservoir,
        fraction=fraction,
        rng=rng,
    )

    poisoned_cal: dict[str, np.ndarray] = {}
    for cid in collection.eligible_ids:
        if cid == victim_id:
            poisoned_cal[cid] = injection.poisoned_cal
        else:
            poisoned_cal[cid] = collection.clients[cid].cal.copy()

    return InjectionOutcome(
        victim_id=victim_id,
        poisoned_cal=poisoned_cal,
        reservoir=reservoir,
        injection=injection,
    )


def recompute_pair(
    collection: Cp2ScoreCollection,
    poisoned_cal: dict[str, np.ndarray],
    policy: ThresholdPolicy,
    *,
    q: float = CP2_Q,
    seed: int = 0,
) -> PolicyPair:
    """Recompute the clean/poisoned threshold pair for one policy."""
    if policy == ThresholdPolicy.B1_GLOBAL:
        return compute_b1_pair(collection, poisoned_cal, q)
    if policy == ThresholdPolicy.B2_PERSONALIZED:
        tau_global_clean = compute_b1_pair(
            collection, poisoned_cal, q
        ).tau_global_clean
        return compute_b2_pair(collection, poisoned_cal, q, tau_global_clean)
    if policy == ThresholdPolicy.B4_CLUSTER:
        return compute_b4_pair(collection, poisoned_cal, q, seed=seed)
    assert_never(policy)


def pending_threshold(pair: PolicyPair) -> float:
    """Threshold assigned to Calibration-Pending clients (the global fallback)."""
    return pair.tau_global_pois
