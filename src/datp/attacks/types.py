"""Frozen dataclass types for poisoned calibrations, thresholds, Auroc, and metrics."""

from __future__ import annotations

import types as _builtins
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from datp.core.enums import ThresholdPolicy
from datp.thresholding.eligibility import ClientThresholdsCollection

if TYPE_CHECKING:
    from datp.attacks.injection.injector import InjectionResult
    from datp.attacks.score_containers import ScoreCollection


@dataclass(frozen=True, slots=True)
class PoisonedClientCal:
    """Poisoned calibration scores for one client."""

    client_id: str
    cal: np.ndarray


@dataclass(frozen=True, slots=True)
class PoisonedCalibrationSet:
    """Immutable mapping of client IDs to poisoned calibration arrays."""

    clients: Mapping[str, PoisonedClientCal]

    def __post_init__(self) -> None:
        """Freeze the clients mapping as an immutable proxy after dataclass init."""
        object.__setattr__(self, "clients", _builtins.MappingProxyType(self.clients))

    @classmethod
    def from_mapping(
        cls, poisoned_cal: Mapping[str, np.ndarray]
    ) -> PoisonedCalibrationSet:
        """Construct from a raw mapping of client IDs to poisoned calibration arrays."""
        return cls(
            {
                cid: PoisonedClientCal(cid, np.asarray(cal))
                for cid, cal in poisoned_cal.items()
            }
        )

    @classmethod
    def from_injection_results(
        cls,
        base_collection: ScoreCollection,
        injection_map: Mapping[str, InjectionResult],
    ) -> PoisonedCalibrationSet:
        """Build a poisoned set by merging injection results into a base score collection."""
        return cls(
            {
                cid: PoisonedClientCal(
                    cid,
                    injection_map[cid].poisoned_cal if cid in injection_map else c.cal,
                )
                for cid, c in base_collection.iter_clients()
            }
        )

    def for_client(self, client_id: str) -> PoisonedClientCal:
        """Return the poisoned calibration entry for a single client."""
        return self.clients[client_id]

    @property
    def client_ids(self) -> tuple[str, ...]:
        """All client IDs present in this poisoned calibration set."""
        return tuple(self.clients.keys())


@dataclass(frozen=True, slots=True)
class ThresholdPairBase:
    """Clean and poisoned global thresholds plus per-client threshold collections."""

    policy: ThresholdPolicy
    tau_global_clean: float
    tau_global_pois: float
    thresholds_clean: ClientThresholdsCollection
    thresholds_pois: ClientThresholdsCollection


@dataclass(frozen=True, slots=True)
class AurocRecord:
    """AUROC score for one client (None if not computable)."""

    client_id: str
    auroc: float | None


@dataclass(frozen=True, slots=True)
class AurocSet:
    """Collection of per-client AUROC records."""

    records: Mapping[str, AurocRecord]

    def __post_init__(self) -> None:
        """Freeze the records mapping as an immutable proxy after dataclass init."""
        object.__setattr__(self, "records", _builtins.MappingProxyType(self.records))

    @classmethod
    def from_records(cls, records: Sequence[AurocRecord]) -> AurocSet:
        """Construct an AurocSet keyed by client ID from a sequence of AurocRecords."""
        return cls({r.client_id: r for r in records})

    def __getitem__(self, client_id: str) -> AurocRecord:
        """Bracket-access alias for for_client."""
        return self.for_client(client_id)

    def __iter__(self) -> Iterator[str]:
        """Iterate over client IDs in this AUROC set."""
        return iter(self.keys())

    def for_client(self, client_id: str) -> AurocRecord:
        """Return the AUROC record for a single client."""
        return self.records[client_id]

    def keys(self) -> tuple[str, ...]:
        """All client IDs in this AUROC set."""
        return tuple(self.records.keys())

    def values(self) -> tuple[AurocRecord, ...]:
        """All AUROC records in this set."""
        return tuple(self.records.values())

    def items(self) -> tuple[tuple[str, AurocRecord], ...]:
        """Client-ID-to-AurocRecord pairs in this set."""
        return tuple(self.records.items())


@dataclass(frozen=True, slots=True)
class MetricEngineInput:
    """Aggregated inputs for computing attack-evaluation metrics."""

    collection: ScoreCollection
    pair: ThresholdPairBase
    mu_flag_threshold: float | None = None
    auroc_set: AurocSet | None = None


@dataclass(frozen=True, slots=True)
class SingleVictimOutcome:
    """Result of poisoning and evaluating a single victim client."""

    victim_id: str
    injection_result: InjectionResult
    poisoned_cal_set: PoisonedCalibrationSet
    rng_state_after: np.ndarray
