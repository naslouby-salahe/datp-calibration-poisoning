
from __future__ import annotations

import types as _builtins
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from datp.core.enums import ThresholdPolicy
from datp.thresholding.eligibility import ClientThresholdsCollection
from datp.types import (
    ClassificationScore,
    ClientId,
    RecordKey,
    ScoreVector,
    Threshold,
)

if TYPE_CHECKING:
    from datp.attacks.score_containers import ScoreCollection


@dataclass(frozen=True, slots=True)
class PoisonedClientCal:

    client_id: ClientId
    cal: ScoreVector


@dataclass(frozen=True, slots=True)
class PoisonedCalibrationSet(Mapping[ClientId, PoisonedClientCal]):

    clients: Mapping[ClientId, PoisonedClientCal]

    def __post_init__(self) -> None:
        object.__setattr__(self, "clients", _builtins.MappingProxyType(self.clients))

    def __getitem__(self, client_id: ClientId) -> PoisonedClientCal:
        return self.clients[client_id]

    def __iter__(self):
        return iter(self.clients)

    def __len__(self) -> int:
        return len(self.clients)

    @classmethod
    def from_mapping(
        cls, poisoned_cal: Mapping[RecordKey, ScoreVector] | Mapping[ClientId, ScoreVector]
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
        object.__setattr__(self, "records", _builtins.MappingProxyType(self.records))

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
