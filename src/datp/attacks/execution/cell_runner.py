
from __future__ import annotations

from dataclasses import dataclass


from datp.attacks.constants import TAIL_MASS, THRESHOLD_QUANTILE
from datp.attacks.enums import (
    AttackerObjective,
    PoisoningSourceStrategy,
    ReservoirDraw,
    is_diagnostic_source,
)
from datp.attacks.injection.injector import (
    InjectionResult,
    inject_disjoint_reservoir,
    inject_fixed_budget,
)
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
from datp.types import (
    ClientId,
    Index,
    PoisonFraction,
    ScoreVector,
)

_SOURCES_SORTED = tuple(sorted(PoisoningSourceStrategy, key=lambda s: s))
_OBJECTIVES_SORTED = tuple(sorted(AttackerObjective, key=lambda o: o))


def cell_child_index(
    source: PoisoningSourceStrategy,
    objective: AttackerObjective | None,
    fraction: PoisonFraction,
) -> Index:
    if objective is None:
        return 0
    return (
        (_SOURCES_SORTED.index(source) * len(_OBJECTIVES_SORTED) * 1000)
        + (_OBJECTIVES_SORTED.index(objective) * 1000)
        + round(fraction * 1000)
    )


@dataclass(frozen=True, slots=True)
class InjectionSpec:

    source: PoisoningSourceStrategy
    fraction: PoisonFraction
    seed_pair: SeedPair
    objective: AttackerObjective | None
    scope_idx: Index = 0
    tail_mass: PoisonFraction = TAIL_MASS
    draw: ReservoirDraw = ReservoirDraw.WITH_REPLACEMENT


@dataclass(frozen=True)
class InjectionOutcome:

    victim_id: ClientId
    poisoned_cal_set: PoisonedCalibrationSet
    reservoir: ReservoirResult
    injection: InjectionResult


def _build_poisoned_clients(
    collection: ScoreCollection, victim_cal_map: dict[ClientId, ScoreVector]
) -> dict[ClientId, ScoreVector]:
    return {
        cid: victim_cal_map[cid]
        if cid in victim_cal_map
        else collection.clients[cid].cal.copy()
        for cid in collection.eligible_ids
    }


def inject_single_victim(
    collection: ScoreCollection, *, victim_id: ClientId, spec: InjectionSpec
) -> InjectionOutcome:
    v_clean = collection.clients[victim_id].cal
    _clean_snapshot = v_clean.copy()

    assert_reservoir_not_test_or_training(ScoringStage.CAL)
    if is_diagnostic_source(spec.source):
        raise ValueError(
            f"Source {spec.source!r} is diagnostic-only and must not enter "
            "the bounded/full experiment matrix."
        )
    rng = make_seed_rng(
        SeedRecord(
            pair=spec.seed_pair,
            client_idx=collection.client_index(victim_id),
            scope_idx=spec.scope_idx,
        ),
        child_index=cell_child_index(spec.source, spec.objective, spec.fraction),
    )
    if spec.draw == ReservoirDraw.DISJOINT_RESERVOIR:
        inj, res = inject_disjoint_reservoir(
            clean_cal=v_clean,
            source=spec.source,
            tail_mass=spec.tail_mass,
            fraction=spec.fraction,
            rng=rng,
        )
    else:
        res = build_reservoir(
            clean_cal=v_clean, source=spec.source, tail_mass=spec.tail_mass
        )
        inj = inject_fixed_budget(
            clean_cal=v_clean,
            reservoir=res,
            fraction=spec.fraction,
            rng=rng,
            draw=spec.draw,
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


def recompute_pair(
    collection: ScoreCollection,
    poisoned_cal_set: PoisonedCalibrationSet,
    policy: ThresholdPolicy,
) -> ThresholdPairBase:
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
