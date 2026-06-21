"""Single-victim injection and threshold-recompute orchestration for one cell.

Pure orchestration over already-tested core modules (reservoir/source
selection, fixed-budget injection, GLOBAL_THRESHOLD/LOCAL_THRESHOLD/CLUSTER_THRESHOLD threshold recompute) — no science
of its own. Shared by the synthetic smoke harness
(``datp.testsupport.smoke_harness``) and the real-data bounded runner
(``datp.attacks.bounded_sweep_cell``) so both run the identical pipeline. All
randomness flows through ``SeedSequence`` (no integer seed addition); clean
arrays are never mutated in place.
"""

from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

from collections.abc import Sequence
from dataclasses import dataclass
from functools import cached_property
from typing import assert_never

import numpy as np

from datp.artifacts.poison_names import TAIL_MASS, THRESHOLD_QUANTILE
from datp.attacks.cluster_threshold_recompute import compute_cluster_pair
from datp.attacks.injector import InjectionResult, inject_fixed_budget
from datp.attacks.reservoir import ReservoirResult
from datp.attacks.score_containers import ScoreCollection
from datp.attacks.source_strategies import _select_reservoir
from datp.attacks.threshold_recompute import (
    compute_global_pair,
    compute_local_pair,
)
from datp.attacks.types import PoisonedCalibrationSet, ThresholdPairBase
from datp.attacks.enums import PoisoningSourceStrategy
from datp.core.seed_sequence import SeedRecord, make_seed_rng
from datp.core.seeds import SeedPair

PolicyPair = ThresholdPairBase


@dataclass(frozen=True, slots=True)
class InjectionSpec:
    """Bundled parameters for a single-victim or multi-victim injection.

    Collapses the nine individual keyword arguments that
    ``inject_single_victim`` and ``inject_multi_victim`` previously required
    into one typed object.  ``seed_pair`` carries the paired training and
    poisoning seeds; ``scope_idx`` and ``tail_mass`` use the repository
    defaults.
    """

    source: PoisoningSourceStrategy
    fraction: float
    seed_pair: SeedPair
    scope_idx: int = 0
    tail_mass: float = TAIL_MASS


@dataclass(frozen=True)
class InjectionOutcome:
    """Result of injecting one victim; carries the full poisoned cal dict.

    poisoned_cal holds every eligible client's calibration array: the victim's
    is poisoned, every other eligible client's is an exact copy of its clean
    array.
    """

    victim_id: str
    poisoned_cal_set: PoisonedCalibrationSet
    reservoir: ReservoirResult
    injection: InjectionResult

    @cached_property
    def poisoned_cal(self):
        return {
            client.client_id: client.cal for client in self.poisoned_cal_set.clients
        }


def _build_poisoned_clients(
    collection: ScoreCollection,
    *,
    victim_cal_map: dict[str, np.ndarray],
) -> list[tuple[str, np.ndarray]]:
    """Return (client_id, calibration_array) for every eligible client.

    Each victim's entry is taken from *victim_cal_map*; every other eligible
    client receives an exact copy of its clean calibration array.
    """
    result: list[tuple[str, np.ndarray]] = []
    for cid in collection.eligible_ids:
        if cid in victim_cal_map:
            result.append((cid, victim_cal_map[cid]))
        else:
            result.append((cid, collection.for_client(cid).cal.copy()))
    return result


def inject_single_victim(
    collection: ScoreCollection,
    *,
    victim_id: str,
    spec: InjectionSpec,
) -> InjectionOutcome:
    """Build the poisoned calibration dict for a single-client attack.

    Non-victim eligible clients keep an exact copy of their clean cal. The
    victim's clean cal is never mutated in place (inject_fixed_budget copies
    internally).
    """
    victim_clean = collection.for_client(victim_id).cal
    reservoir = _select_reservoir(
        source=spec.source, clean_cal=victim_clean, tail_mass=spec.tail_mass
    )
    rng = make_seed_rng(
        SeedRecord(
            pair=spec.seed_pair,
            client_idx=collection.client_index(victim_id),
            scope_idx=spec.scope_idx,
        ),
        child_index=0,
    )
    injection = inject_fixed_budget(
        clean_cal=victim_clean,
        reservoir=reservoir,
        fraction=spec.fraction,
        rng=rng,
    )
    poisoned_clients = _build_poisoned_clients(
        collection, victim_cal_map={victim_id: injection.poisoned_cal}
    )
    return InjectionOutcome(
        victim_id=victim_id,
        poisoned_cal_set=PoisonedCalibrationSet.from_mapping(dict(poisoned_clients)),
        reservoir=reservoir,
        injection=injection,
    )


@dataclass(frozen=True)
class MultiInjectionOutcome:
    """Result of injecting several co-victims in one MULTI_CLIENT pass.

    poisoned_cal holds every eligible client's calibration array: each named
    co-victim's is poisoned via its own independent stream (keyed by the
    victim's client index in the seed scheme); every other eligible client's
    is an exact copy of its clean array.
    """

    victim_ids: tuple[str, ...]
    poisoned_cal_set: PoisonedCalibrationSet
    per_victim: dict[str, InjectionOutcome]

    @cached_property
    def poisoned_cal(self):
        return {
            client.client_id: client.cal for client in self.poisoned_cal_set.clients
        }


def _validate_and_order_victim_ids(victim_ids: Sequence[str]) -> tuple[str, ...]:
    """Deduplicate, sort, and validate a co-victim id sequence."""
    ordered = tuple(sorted(set(victim_ids)))
    if len(ordered) != len(victim_ids):
        raise ValueError(f"victim_ids must be unique; got {list(victim_ids)!r}")
    if len(ordered) < 2:
        raise ValueError(
            f"multi-client attack requires at least 2 co-victims; got {ordered!r}"
        )
    return ordered


def inject_multi_victim(
    collection: ScoreCollection,
    *,
    victim_ids: Sequence[str],
    spec: InjectionSpec,
) -> MultiInjectionOutcome:
    """Build the poisoned calibration dict for a multi-client (co-victim) attack.

    Each co-victim is poisoned independently with a stream keyed by its own
    client index (no shared or integer-added seeds), so a co-victim's poisoned
    array is identical to what it would receive when attacked alone under the
    same (training_seed, poisoning_seed, scope_idx). Non-victim eligible clients
    keep an exact copy of their clean cal. Clean arrays are never mutated.
    """
    ordered = _validate_and_order_victim_ids(victim_ids)

    per_victim: dict[str, InjectionOutcome] = {
        vid: inject_single_victim(collection, victim_id=vid, spec=spec)
        for vid in ordered
    }

    victim_cal_map = {
        vid: per_victim[vid].poisoned_cal_set.for_client(vid).cal for vid in ordered
    }
    poisoned_clients = _build_poisoned_clients(
        collection, victim_cal_map=victim_cal_map
    )

    return MultiInjectionOutcome(
        victim_ids=ordered,
        poisoned_cal_set=PoisonedCalibrationSet.from_mapping(dict(poisoned_clients)),
        per_victim=per_victim,
    )


def recompute_pair(
    collection: ScoreCollection,
    poisoned_cal_set: PoisonedCalibrationSet,
    policy: ThresholdPolicy,
) -> PolicyPair:
    """Recompute the clean/poisoned threshold pair for one policy."""
    q = THRESHOLD_QUANTILE
    if policy == ThresholdPolicy.GLOBAL_THRESHOLD:
        return compute_global_pair(collection, poisoned_cal_set, q)
    if policy == ThresholdPolicy.LOCAL_THRESHOLD:
        tau_global_clean = compute_global_pair(
            collection, poisoned_cal_set, q
        ).tau_global_clean
        return compute_local_pair(collection, poisoned_cal_set, q, tau_global_clean)
    if policy == ThresholdPolicy.CLUSTER_THRESHOLD:
        return compute_cluster_pair(collection, poisoned_cal_set, q)
    assert_never(policy)


def pending_threshold(pair: PolicyPair) -> float:
    """Threshold assigned to Calibration-Pending clients (the global fallback)."""
    return pair.tau_global_pois
