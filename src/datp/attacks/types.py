"""Shared attack-domain value objects."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from datp.attacks.enums import ThresholdPolicy
from datp.thresholding.eligibility import ClientThresholdsCollection

if TYPE_CHECKING:
    from datp.attacks.injector import InjectionResult
    from datp.attacks.score_containers import ScoreCollection


@dataclass(frozen=True, slots=True)
class PoisonedClientCal:
    client_id: str
    cal: np.ndarray

    def __post_init__(self) -> None:
        object.__setattr__(self, "cal", np.array(self.cal, copy=False))


@dataclass(frozen=True, slots=True)
class PoisonedCalibrationSet:
    clients: tuple[PoisonedClientCal, ...]

    @classmethod
    def from_mapping(
        cls, poisoned_cal: Mapping[str, np.ndarray]
    ) -> "PoisonedCalibrationSet":
        return cls(
            clients=tuple(
                PoisonedClientCal(client_id=cid, cal=cal)
                for cid, cal in poisoned_cal.items()
            )
        )

    @classmethod
    def from_injection_results(
        cls,
        base_collection: "ScoreCollection",
        injection_map: Mapping[str, "InjectionResult"],
    ) -> "PoisonedCalibrationSet":
        clients: list[PoisonedClientCal] = []
        for client_id, client_scores in base_collection.iter_clients():
            if client_id in injection_map:
                cal = injection_map[client_id].poisoned_cal
            else:
                cal = client_scores.cal
            clients.append(PoisonedClientCal(client_id=client_id, cal=cal))
        return cls(clients=tuple(clients))

    def for_client(self, client_id: str) -> PoisonedClientCal:
        for client in self.clients:
            if client.client_id == client_id:
                return client
        raise KeyError(client_id)

    @property
    def client_ids(self) -> tuple[str, ...]:
        return tuple(client.client_id for client in self.clients)


@dataclass(frozen=True, slots=True)
class ThresholdPairBase:
    policy: ThresholdPolicy
    tau_global_clean: float
    tau_global_pois: float
    thresholds_clean: ClientThresholdsCollection
    thresholds_pois: ClientThresholdsCollection


@dataclass(frozen=True, slots=True)
class AurocRecord:
    """AUROC per eligible client; invariant under calibration-channel attack."""

    client_id: str
    auroc: float | None


@dataclass(frozen=True, slots=True)
class AurocSet:
    records: tuple[AurocRecord, ...]

    def __getitem__(self, client_id: str) -> AurocRecord:
        return self.for_client(client_id)

    def __iter__(self) -> Iterator[str]:
        return iter(self.keys())

    def for_client(self, client_id: str) -> AurocRecord:
        for record in self.records:
            if record.client_id == client_id:
                return record
        raise KeyError(client_id)

    def keys(self) -> tuple[str, ...]:
        return tuple(record.client_id for record in self.records)

    def values(self) -> tuple[AurocRecord, ...]:
        return self.records

    def items(self) -> tuple[tuple[str, AurocRecord], ...]:
        return tuple((record.client_id, record) for record in self.records)


@dataclass(frozen=True, slots=True)
class MetricEngineInput:
    collection: "ScoreCollection"
    pair: ThresholdPairBase
    mu_flag_threshold: float | None
    auroc_set: AurocSet


@dataclass(frozen=True, slots=True)
class SingleVictimOutcome:
    victim_id: str
    injection_result: "InjectionResult"
    poisoned_cal_set: PoisonedCalibrationSet
    rng_state_after: np.ndarray
