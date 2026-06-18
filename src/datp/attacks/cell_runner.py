"""Single-victim injection and threshold-recompute orchestration for one cell.

Pure orchestration over already-tested core modules (reservoir/source
selection, fixed-budget injection, B1/B2/B4 threshold recompute) — no science
of its own. Shared by the synthetic smoke harness
(``datp.testsupport.smoke_harness``) and the real-data bounded runner
(``datp.attacks.bounded_sweep_cell``) so both run the identical pipeline. All
randomness flows through ``SeedSequence`` (no integer seed addition); clean
arrays are never mutated in place.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import assert_never

import numpy as np

from datp.artifacts.poison_names import TAIL_MASS, THRESHOLD_QUANTILE
from datp.attacks.b4_recompute import B4ThresholdPair, compute_b4_pair
from datp.attacks.injector import InjectionResult, inject_fixed_budget
from datp.attacks.reservoir import ReservoirResult
from datp.attacks.score_containers import ScoreCollection
from datp.attacks.source_strategies import select_reservoir
from datp.attacks.threshold_recompute import (
    ThresholdPair,
    compute_b1_pair,
    compute_b2_pair,
)
from datp.core.poison_enums import PoisoningSourceStrategy, ThresholdPolicy
from datp.core.seed_sequence import make_seed_rng

PolicyPair = ThresholdPair | B4ThresholdPair


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
    collection: ScoreCollection,
    *,
    victim_id: str,
    source: PoisoningSourceStrategy,
    fraction: float,
    training_seed: int,
    poisoning_seed: int,
    scope_idx: int = 0,
    tail_mass: float = TAIL_MASS,
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
    rng = make_seed_rng(
        training_seed=training_seed,
        poisoning_seed=poisoning_seed,
        client_idx=collection.client_index(victim_id),
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


@dataclass(frozen=True, slots=True)
class MultiInjectionOutcome:
    """Result of injecting several co-victims in one MULTI_CLIENT pass.

    poisoned_cal holds every eligible client's calibration array: each named
    co-victim's is poisoned via its own independent stream (keyed by the
    victim's client index in the seed scheme); every other eligible client's
    is an exact copy of its clean array.
    """

    victim_ids: tuple[str, ...]
    poisoned_cal: dict[str, np.ndarray]
    per_victim: dict[str, InjectionOutcome]


def inject_multi_victim(
    collection: ScoreCollection,
    *,
    victim_ids: Sequence[str],
    source: PoisoningSourceStrategy,
    fraction: float,
    training_seed: int,
    poisoning_seed: int,
    scope_idx: int = 0,
    tail_mass: float = TAIL_MASS,
) -> MultiInjectionOutcome:
    """Build the poisoned calibration dict for a multi-client (co-victim) attack.

    Each co-victim is poisoned independently with a stream keyed by its own
    client index (no shared or integer-added seeds), so a co-victim's poisoned
    array is identical to what it would receive when attacked alone under the
    same (training_seed, poisoning_seed, scope_idx). Non-victim eligible clients
    keep an exact copy of their clean cal. Clean arrays are never mutated.
    """
    ordered = sorted(set(victim_ids))
    if len(ordered) != len(victim_ids):
        raise ValueError(f"victim_ids must be unique; got {list(victim_ids)!r}")
    if len(ordered) < 2:
        raise ValueError(
            f"multi-client attack requires at least 2 co-victims; got {ordered!r}"
        )

    per_victim: dict[str, InjectionOutcome] = {
        vid: inject_single_victim(
            collection,
            victim_id=vid,
            source=source,
            fraction=fraction,
            training_seed=training_seed,
            poisoning_seed=poisoning_seed,
            scope_idx=scope_idx,
            tail_mass=tail_mass,
        )
        for vid in ordered
    }

    victim_set = set(ordered)
    poisoned_cal: dict[str, np.ndarray] = {}
    for cid in collection.eligible_ids:
        if cid in victim_set:
            poisoned_cal[cid] = per_victim[cid].poisoned_cal[cid]
        else:
            poisoned_cal[cid] = collection.clients[cid].cal.copy()

    return MultiInjectionOutcome(
        victim_ids=tuple(ordered),
        poisoned_cal=poisoned_cal,
        per_victim=per_victim,
    )


def recompute_pair(
    collection: ScoreCollection,
    poisoned_cal: dict[str, np.ndarray],
    policy: ThresholdPolicy,
    *,
    q: float = THRESHOLD_QUANTILE,
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
