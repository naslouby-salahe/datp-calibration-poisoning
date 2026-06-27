"""Single-victim and multi-victim injection plus threshold recomputation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from functools import cached_property
from typing import cast

import numpy as np
from joblib import Parallel, delayed

from datp.attacks.constants import TAIL_MASS, THRESHOLD_QUANTILE
from datp.attacks.enums import (
    AttackerObjective,
    PoisoningSourceStrategy,
    is_diagnostic_source,
)
from datp.attacks.injection.injector import InjectionResult, inject_fixed_budget
from datp.attacks.planning.guardrails import (
    assert_no_inplace_mutation,
    assert_reservoir_not_test_or_training,
)
from datp.attacks.reservoirs.reservoir import ReservoirResult, build_reservoir
from datp.attacks.score_containers import ScoreCollection
from datp.attacks.threshold_recomputation.cluster_threshold_recompute import (
    compute_cluster_pair,
)
from datp.attacks.threshold_recomputation.threshold_recompute import (
    compute_global_pair,
    compute_local_pair,
)
from datp.attacks.types import PoisonedCalibrationSet, ThresholdPairBase
from datp.core.enums import ScoringStage, ThresholdPolicy
from datp.core.seeds import SeedPair, SeedRecord, make_seed_rng

PolicyPair = ThresholdPairBase

_SOURCES_SORTED = tuple(sorted(PoisoningSourceStrategy, key=lambda s: s.value))
_OBJECTIVES_SORTED = tuple(sorted(AttackerObjective, key=lambda o: o.value))


def cell_child_index(
    source: PoisoningSourceStrategy,
    objective: AttackerObjective | None,
    fraction: float,
) -> int:
    """Derive a deterministic child index for RNG seeding from source, objective, and fraction."""
    if objective is None:
        return 0
    return (
        (_SOURCES_SORTED.index(source) * len(_OBJECTIVES_SORTED) * 1000)
        + (_OBJECTIVES_SORTED.index(objective) * 1000)
        + round(fraction * 1000)
    )


@dataclass(frozen=True, slots=True)
class InjectionSpec:
    """Immutable specification for a single poisoning injection."""

    source: PoisoningSourceStrategy
    fraction: float
    seed_pair: SeedPair
    objective: AttackerObjective | None
    scope_idx: int = 0
    tail_mass: float = TAIL_MASS


@dataclass(frozen=True)
class InjectionOutcome:
    """Result of injecting one victim: poisoned calibration set, reservoir, and injection details."""

    victim_id: str
    poisoned_cal_set: PoisonedCalibrationSet
    reservoir: ReservoirResult
    injection: InjectionResult


def _build_poisoned_clients(
    collection: ScoreCollection, victim_cal_map: dict[str, np.ndarray]
) -> dict[str, np.ndarray]:
    """Merge victim poisoned calibrations with clean copies for non-victim clients."""
    return {
        cid: victim_cal_map[cid]
        if cid in victim_cal_map
        else collection.for_client(cid).cal.copy()
        for cid in collection.eligible_ids
    }


def inject_single_victim(
    collection: ScoreCollection, *, victim_id: str, spec: InjectionSpec
) -> InjectionOutcome:
    """Build a reservoir, inject poisoned values, and return the outcome for one victim."""
    v_clean = collection.for_client(victim_id).cal
    _clean_snapshot = v_clean.copy()

    assert_reservoir_not_test_or_training(ScoringStage.CAL)
    if is_diagnostic_source(spec.source):
        raise ValueError(
            f"Source {spec.source!r} is diagnostic-only and must not enter "
            "the bounded/full experiment matrix."
        )
    res = build_reservoir(
        clean_cal=v_clean, source=spec.source, tail_mass=spec.tail_mass
    )
    rng = make_seed_rng(
        SeedRecord(
            pair=spec.seed_pair,
            client_idx=collection.client_index(victim_id),
            scope_idx=spec.scope_idx,
        ),
        child_index=cell_child_index(spec.source, spec.objective, spec.fraction),
    )

    inj = inject_fixed_budget(
        clean_cal=v_clean, reservoir=res, fraction=spec.fraction, rng=rng
    )
    assert_no_inplace_mutation(_clean_snapshot, v_clean, "victim_cal")

    return InjectionOutcome(
        victim_id=victim_id,
        poisoned_cal_set=PoisonedCalibrationSet.from_mapping(
            _build_poisoned_clients(collection, {victim_id: inj.poisoned_cal})
        ),
        reservoir=res,
        injection=inj,
    )


@dataclass(frozen=True)
class MultiInjectionOutcome:
    """Aggregated result of injecting multiple victims."""

    outcomes: tuple[InjectionOutcome, ...]
    poisoned_cal_set: PoisonedCalibrationSet

    @cached_property
    def _victim_map(self) -> dict[str, InjectionOutcome]:
        """Victim ID to InjectionOutcome lookup."""
        return {o.victim_id: o for o in self.outcomes}

    @cached_property
    def victim_ids(self) -> tuple[str, ...]:
        """Sorted victim IDs."""
        return tuple(self._victim_map.keys())

    def for_victim(self, victim_id: str) -> InjectionOutcome:
        """Return the InjectionOutcome for a given victim ID."""
        return self._victim_map[victim_id]


def _validate_and_order_victim_ids(victim_ids: Sequence[str]) -> tuple[str, ...]:
    """Validate victim IDs are unique and contain at least 2 elements."""
    ordered = tuple(sorted(set(victim_ids)))
    if len(ordered) != len(victim_ids) or len(ordered) < 2:
        raise ValueError("victim_ids must be unique and contain at least 2 elements")
    return ordered


def inject_multi_victim(
    collection: ScoreCollection, *, victim_ids: Sequence[str], spec: InjectionSpec
) -> MultiInjectionOutcome:
    """Inject multiple victims in parallel and merge their poisoned calibrations."""
    ordered = _validate_and_order_victim_ids(victim_ids)

    outcomes = cast(
        tuple[InjectionOutcome, ...],
        tuple(
            Parallel(n_jobs=-1, prefer="threads")(
                delayed(inject_single_victim)(collection, victim_id=vid, spec=spec)
                for vid in ordered
            )
        ),
    )

    return MultiInjectionOutcome(
        outcomes=outcomes,
        poisoned_cal_set=PoisonedCalibrationSet.from_mapping(
            _build_poisoned_clients(
                collection, {o.victim_id: o.injection.poisoned_cal for o in outcomes}
            )
        ),
    )


def recompute_pair(
    collection: ScoreCollection,
    poisoned_cal_set: PoisonedCalibrationSet,
    policy: ThresholdPolicy,
) -> PolicyPair:
    """Recompute clean/poisoned threshold pair for the given policy."""
    match policy:
        case ThresholdPolicy.GLOBAL_THRESHOLD:
            return compute_global_pair(collection, poisoned_cal_set, THRESHOLD_QUANTILE)
        case ThresholdPolicy.LOCAL_THRESHOLD:
            t = compute_global_pair(
                collection, poisoned_cal_set, THRESHOLD_QUANTILE
            ).tau_global_clean
            return compute_local_pair(
                collection, poisoned_cal_set, THRESHOLD_QUANTILE, t
            )
        case ThresholdPolicy.CLUSTER_THRESHOLD:
            return compute_cluster_pair(
                collection, poisoned_cal_set, THRESHOLD_QUANTILE
            )
