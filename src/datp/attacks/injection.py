from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from functools import cached_property
from itertools import product
from math import floor
from types import MappingProxyType
from typing import assert_never

import numpy as np

from datp.config import (
    N_MIN,
    NBAIOT_MAIN_SWEEP_FRACTION_SET,
    CalibrationPoisoningConfig,
    ExperimentStage,
)
from datp.core import SeedPair
from datp.enums import (
    AttackerObjective,
    PoisoningDefense,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ReservoirDraw,
    ReservoirStatus,
    ScoringStage,
    ThresholdPolicy,
    objective_for_source,
)
from datp.thresholding import (
    CalibrationErrorSet,
    ClientCalibrationErrors,
    ClientThresholdsCollection,
    EligibilityResult,
    identify_eligible,
)
from datp.types import (
    ClassificationScore,
    ClientId,
    Index,
    NarrativeText,
    PoisonFraction,
    RandomSeed,
    Ratio,
    RecordKey,
    SampleCount,
    ScoreVector,
    SignedCount,
    Threshold,
)


@dataclass(frozen=True, slots=True)
class PoisonedClientCal:
    client_id: ClientId
    cal: ScoreVector


@dataclass(frozen=True, slots=True)
class PoisonedCalibrationSet(Mapping[ClientId, PoisonedClientCal]):
    clients: Mapping[ClientId, PoisonedClientCal]

    def __post_init__(self) -> None:
        object.__setattr__(self, "clients", MappingProxyType(self.clients))

    def __getitem__(self, client_id: ClientId) -> PoisonedClientCal:
        return self.clients[client_id]

    def __iter__(self):
        return iter(self.clients)

    def __len__(self) -> int:
        return len(self.clients)

    @classmethod
    def from_mapping(
        cls,
        poisoned_cal: Mapping[RecordKey, ScoreVector] | Mapping[ClientId, ScoreVector],
    ) -> PoisonedCalibrationSet:
        return cls(
            {
                ClientId(cid): PoisonedClientCal(ClientId(cid), np.asarray(cal))
                for cid, cal in poisoned_cal.items()
            }
        )


@dataclass(frozen=True, slots=True)
class ThresholdPairBase:
    policy: ThresholdPolicy
    tau_global_clean: Threshold
    tau_global_pois: Threshold
    thresholds_clean: ClientThresholdsCollection
    thresholds_pois: ClientThresholdsCollection


@dataclass(frozen=True, slots=True)
class AurocRecord:
    client_id: ClientId
    auroc: ClassificationScore | None


@dataclass(frozen=True, slots=True)
class AurocSet(Mapping[ClientId, AurocRecord]):
    records: Mapping[ClientId, AurocRecord]

    def __post_init__(self) -> None:
        object.__setattr__(self, "records", MappingProxyType(self.records))

    @classmethod
    def from_records(cls, records: Sequence[AurocRecord]) -> AurocSet:
        return cls({r.client_id: r for r in records})

    def __getitem__(self, client_id: ClientId) -> AurocRecord:
        return self.records[client_id]

    def __iter__(self):
        return iter(self.records)

    def __len__(self) -> int:
        return len(self.records)


@dataclass(frozen=True, slots=True)
class MetricEngineInput:
    collection: ScoreCollection
    pair: ThresholdPairBase
    mu_flag_threshold: Threshold | None = None
    auroc_set: AurocSet | None = None


@dataclass(frozen=True, slots=True)
class ClientScores:
    client_id: ClientId
    cal: ScoreVector
    test_benign: ScoreVector
    test_attack: ScoreVector


class ClientScoresById(Mapping[ClientId, ClientScores]):
    def __init__(self, clients: Iterable[ClientScores]):
        ordered = tuple(clients)
        self._clients = ordered
        self._map = MappingProxyType({c.client_id: c for c in ordered})

    def __reduce__(
        self,
    ) -> tuple[type[ClientScoresById], tuple[tuple[ClientScores, ...]]]:
        return ClientScoresById, (self._clients,)

    def __iter__(self) -> Iterator[ClientId]:
        return iter(self._map)

    def __len__(self) -> int:
        return len(self._clients)

    def __bool__(self) -> bool:
        return len(self._clients) > 0

    def __getitem__(self, client_id: ClientId) -> ClientScores:
        return self._map[client_id]


@dataclass(frozen=True)
class ScoreCollection:
    clients: ClientScoresById
    n_min: SampleCount = N_MIN

    @cached_property
    def eligibility(self) -> EligibilityResult:
        res = identify_eligible(self.calibration_errors, self.n_min)
        return EligibilityResult(
            eligible_ids=tuple(sorted(res.eligible_ids)),
            pending_ids=tuple(sorted(res.pending_ids)),
        )

    @property
    def eligible_ids(self) -> tuple[ClientId, ...]:
        return self.eligibility.eligible_ids

    @property
    def calibration_errors(self) -> CalibrationErrorSet:
        return CalibrationErrorSet(
            tuple(
                ClientCalibrationErrors(client.client_id, client.cal)
                for client in self.clients.values()
            )
        )

    @property
    def eligible_calibration_errors(self) -> CalibrationErrorSet:
        eligible_ids = frozenset(self.eligible_ids)
        return CalibrationErrorSet(
            tuple(
                ClientCalibrationErrors(client.client_id, client.cal)
                for client in self.clients.values()
                if client.client_id in eligible_ids
            )
        )

    @cached_property
    def all_ids(self) -> tuple[ClientId, ...]:
        return tuple(sorted(self.clients))

    @cached_property
    def _id_index(self) -> dict[ClientId, Index]:
        return {cid: i for i, cid in enumerate(self.all_ids)}

    def client_index(self, client_id: ClientId) -> Index:
        return self._id_index[client_id]

    @property
    def coverage_ratio(self) -> Ratio:
        return len(self.eligible_ids) / len(self.clients) if self.clients else 0.0


def build_score_collection(
    client_scores: Mapping[ClientId, tuple[ScoreVector, ScoreVector, ScoreVector]],
    n_min: SampleCount = N_MIN,
) -> ScoreCollection:
    clients = tuple(
        ClientScores(client_id=ClientId(cid), cal=cal, test_benign=tb, test_attack=ta)
        for cid, (cal, tb, ta) in client_scores.items()
    )
    return ScoreCollection(clients=ClientScoresById(clients), n_min=n_min)


@dataclass(frozen=True, slots=True)
class ReservoirResult:
    pool: ScoreVector
    status: ReservoirStatus
    source: PoisoningSourceStrategy
    n_pool: SampleCount
    n_distinct: SampleCount


def build_reservoir(
    *,
    clean_cal: ScoreVector,
    source: PoisoningSourceStrategy,
    tail_mass: PoisonFraction,
) -> ReservoirResult:
    if source == PoisoningSourceStrategy.RANDOM_BENIGN:
        pool = clean_cal.copy()
    else:
        n_tail = max(1, floor(tail_mass * clean_cal.size))
        sorted_cal = np.sort(clean_cal)

        if source == PoisoningSourceStrategy.HIGH_SCORE_BENIGN:
            pool = sorted_cal[-n_tail:].copy()
        elif source == PoisoningSourceStrategy.LOW_SCORE_BENIGN:
            pool = sorted_cal[:n_tail].copy()
        else:
            raise ValueError(f"Unsupported source strategy: {source}")

    n_distinct = len(np.unique(pool))
    status = (
        ReservoirStatus.FEASIBLE
        if source == PoisoningSourceStrategy.RANDOM_BENIGN or n_distinct >= 2
        else ReservoirStatus.INFEASIBLE_DEGENERATE_TAIL
    )

    return ReservoirResult(
        pool=pool,
        status=status,
        source=source,
        n_pool=pool.size,
        n_distinct=n_distinct,
    )


def trimmed_calibration(cal: ScoreVector, trim_fraction: PoisonFraction) -> ScoreVector:
    if not 0.0 <= trim_fraction < 0.5:
        raise ValueError(f"trim_fraction must be in [0, 0.5); got {trim_fraction}")
    if cal.ndim != 1:
        raise ValueError(f"cal must be 1-D; got shape {cal.shape}")

    k = floor(trim_fraction * cal.size)
    if k == 0:
        return cal.copy()

    return np.sort(cal)[k:-k].copy()


def build_defended_collection(
    collection: ScoreCollection, trim_fraction: PoisonFraction
) -> ScoreCollection:
    defended_clients = ClientScoresById(
        ClientScores(
            client_id=cid,
            cal=trimmed_calibration(c.cal, trim_fraction),
            test_benign=c.test_benign,
            test_attack=c.test_attack,
        )
        for cid, c in collection.clients.items()
    )
    return ScoreCollection(clients=defended_clients, n_min=collection.n_min)


def defend_poisoned_cal(
    poisoned_cal: dict[RecordKey, ScoreVector], trim_fraction: PoisonFraction
) -> dict[RecordKey, ScoreVector]:
    return {
        cid: trimmed_calibration(cal, trim_fraction)
        for cid, cal in poisoned_cal.items()
    }


def apply_defense(
    collection: ScoreCollection,
    poisoned_cal: dict[RecordKey, ScoreVector],
    *,
    defense: PoisoningDefense,
    trim_fraction: PoisonFraction,
) -> tuple[ScoreCollection, dict[RecordKey, ScoreVector]]:
    if defense == PoisoningDefense.NONE:
        return collection, poisoned_cal
    elif defense == PoisoningDefense.TRIMMED_CALIBRATION:
        return (
            build_defended_collection(collection, trim_fraction),
            defend_poisoned_cal(poisoned_cal, trim_fraction),
        )
    else:
        assert_never(defense)


@dataclass(frozen=True, slots=True)
class InjectionResult:
    poisoned_cal: ScoreVector
    n_replaced: SampleCount
    n_total: SampleCount
    fraction: PoisonFraction
    positions_replaced: ScoreVector


def inject_fixed_budget(
    *,
    clean_cal: ScoreVector,
    reservoir: ReservoirResult,
    fraction: PoisonFraction,
    rng: np.random.Generator,
    draw: ReservoirDraw = ReservoirDraw.WITH_REPLACEMENT,
) -> InjectionResult:
    if not 0.0 <= fraction <= 1.0:
        raise ValueError(f"fraction must be in [0, 1]; got {fraction}")

    n = len(clean_cal)

    if fraction <= 0.0:
        return InjectionResult(clean_cal.copy(), 0, n, 0.0, np.empty(0, dtype=np.intp))

    if reservoir.status == ReservoirStatus.INFEASIBLE_DEGENERATE_TAIL:
        raise ValueError(
            f"Cannot inject: reservoir is INFEASIBLE "
            f"(degenerate tail, {reservoir.n_distinct} distinct values). "
            f"Mark cell INFEASIBLE."
        )

    m = max(1, round(fraction * n))
    if draw == ReservoirDraw.DISJOINT_RESERVOIR:
        raise ValueError("DISJOINT_RESERVOIR is handled by inject_disjoint_reservoir.")
    positions = rng.choice(n, size=m, replace=False)
    poisoned = clean_cal.copy()
    poisoned[positions] = _draw_values(reservoir.pool, m, rng, draw)

    return InjectionResult(poisoned, m, n, fraction, positions)


def _draw_values(
    pool: ScoreVector, m: SignedCount, rng: np.random.Generator, draw: ReservoirDraw
) -> ScoreVector:
    match draw:
        case ReservoirDraw.WITH_REPLACEMENT:
            return rng.choice(pool, size=m, replace=True)
        case ReservoirDraw.WITHOUT_REPLACEMENT:
            if m > pool.size:
                raise ValueError(
                    f"Cannot draw {m} values without replacement from a pool of {pool.size}."
                )
            return rng.choice(pool, size=m, replace=False)
        case ReservoirDraw.INTERPOLATED_TAIL:
            ordered = np.sort(pool)
            if ordered.size < 2:
                raise ValueError("Interpolation needs a pool of at least 2 values.")
            lower = rng.integers(0, ordered.size - 1, size=m)
            weight = rng.random(m)
            return ordered[lower] + weight * (ordered[lower + 1] - ordered[lower])
        case _:
            raise ValueError(f"Unsupported draw mode: {draw}")


def disjoint_budget(
    n: SampleCount,
    requested: SignedCount,
    tail_mass: PoisonFraction,
    source: PoisoningSourceStrategy,
) -> SignedCount:
    for m in range(requested, 0, -1):
        source_size = n - m
        pool = (
            source_size
            if source == PoisoningSourceStrategy.RANDOM_BENIGN
            else max(1, floor(tail_mass * source_size))
        )
        if pool >= m:
            return m
    return 0


def inject_disjoint_reservoir(
    *,
    clean_cal: ScoreVector,
    source: PoisoningSourceStrategy,
    tail_mass: PoisonFraction,
    fraction: PoisonFraction,
    rng: np.random.Generator,
) -> tuple[InjectionResult, ReservoirResult]:
    n = len(clean_cal)
    if fraction <= 0.0:
        return InjectionResult(
            clean_cal.copy(), 0, n, 0.0, np.empty(0, dtype=np.intp)
        ), build_reservoir(clean_cal=clean_cal, source=source, tail_mass=tail_mass)
    m = disjoint_budget(n, max(1, round(fraction * n)), tail_mass, source)
    if m == 0:
        raise ValueError("No feasible disjoint-reservoir budget.")
    positions = rng.choice(n, size=m, replace=False)
    keep = np.ones(n, dtype=bool)
    keep[positions] = False
    reservoir = build_reservoir(
        clean_cal=clean_cal[keep], source=source, tail_mass=tail_mass
    )
    if reservoir.status == ReservoirStatus.INFEASIBLE_DEGENERATE_TAIL:
        raise ValueError(
            f"Cannot inject: disjoint reservoir is INFEASIBLE ({reservoir.n_distinct} distinct values)."
        )
    poisoned = clean_cal.copy()
    poisoned[positions] = rng.choice(reservoir.pool, size=m, replace=False)
    return InjectionResult(poisoned, m, n, m / n, positions), reservoir


class GuardrailError(ValueError):
    pass


def assert_no_inplace_mutation(
    original: ScoreVector,
    after: ScoreVector,
    label: NarrativeText = "calibration array",
) -> None:
    if not np.array_equal(original, after):
        raise GuardrailError(f"Clean {label} was mutated in place. Operate on a copy.")


def assert_reservoir_not_test_or_training(reservoir_source: ScoringStage) -> None:
    if reservoir_source in {ScoringStage.TEST_BENIGN, ScoringStage.TEST_ATTACK}:
        raise GuardrailError(f"Reservoir source {reservoir_source!r} is forbidden.")


def assert_fractions_in_locked_grid(fractions: Iterable[PoisonFraction]) -> None:
    if invalid := set(fractions) - NBAIOT_MAIN_SWEEP_FRACTION_SET:
        raise GuardrailError(f"Fractions {invalid} are not in the locked grid.")


def assert_bounded_scale_requires_single_client(
    target_scope: PoisoningTargetScope,
) -> None:
    if target_scope != PoisoningTargetScope.SINGLE_CLIENT:
        raise GuardrailError(
            f"NBAIOT_MAIN requires SINGLE_CLIENT target scope; got {target_scope!r}."
        )


def is_valid_source_objective_pair(
    source: PoisoningSourceStrategy,
    objective: AttackerObjective,
) -> bool:
    expected = objective_for_source(source)
    return expected is None or objective == expected


def assert_valid_source_objective_pair(
    source: PoisoningSourceStrategy,
    objective: AttackerObjective,
) -> None:
    if not is_valid_source_objective_pair(source, objective):
        raise GuardrailError(
            f"Source {source!r} requires objective "
            f"{objective_for_source(source)!r}; got {objective!r}."
        )


@dataclass(frozen=True, slots=True)
class SweepCellSpec:
    seed_pair: SeedPair
    victim_id: ClientId
    policy: ThresholdPolicy
    objective: AttackerObjective
    source: PoisoningSourceStrategy
    fraction: PoisonFraction
    target_scope: PoisoningTargetScope = PoisoningTargetScope.SINGLE_CLIENT

    @property
    def training_seed(self) -> RandomSeed:
        return self.seed_pair.training_seed

    @property
    def poisoning_seed(self) -> RandomSeed:
        return self.seed_pair.poisoning_seed


def _enumerate_single_victim_matrix(
    victims_by_training_seed: Mapping[RandomSeed, Sequence[ClientId]],
    config: CalibrationPoisoningConfig,
) -> tuple[SweepCellSpec, ...]:
    valid_pairs = tuple(
        (source, objective)
        for source in config.sources
        for objective in config.objectives
        if is_valid_source_objective_pair(source, objective)
    )
    cells: list[SweepCellSpec] = []
    for t_seed, p_seed in zip(
        config.seeds.training, config.seeds.poisoning, strict=True
    ):
        if (victims := victims_by_training_seed.get(t_seed)) is None:
            raise KeyError(f"no victim list provided for training_seed={t_seed}")

        seed_pair = SeedPair(training_seed=t_seed, poisoning_seed=p_seed)
        cells.extend(_cells_for_seed(victims, seed_pair, config, valid_pairs))

    return tuple(cells)


def _cells_for_seed(
    victims: Sequence[ClientId],
    seed_pair: SeedPair,
    config: CalibrationPoisoningConfig,
    valid_pairs: tuple[tuple[PoisoningSourceStrategy, AttackerObjective], ...],
) -> tuple[SweepCellSpec, ...]:
    return tuple(
        SweepCellSpec(
            seed_pair=seed_pair,
            victim_id=victim,
            policy=policy,
            objective=objective,
            source=source,
            fraction=fraction,
        )
        for victim, policy, (source, objective), fraction in product(
            victims, config.policies, valid_pairs, config.fractions
        )
    )


def enumerate_bounded_sweep_matrix(
    victims_by_training_seed: Mapping[RandomSeed, Sequence[ClientId]],
    config: CalibrationPoisoningConfig,
) -> tuple[SweepCellSpec, ...]:
    if config.stage != ExperimentStage.NBAIOT_MAIN:
        raise ValueError(f"Requires ExperimentStage.NBAIOT_MAIN; got {config.stage}")
    return _enumerate_single_victim_matrix(victims_by_training_seed, config)
