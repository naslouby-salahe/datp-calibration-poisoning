from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from datp.core.errors import fmt
from datp.core.identity import PolicyRunId
from datp.core.types import (
    ClusterMetadata,
    ClientThreshold,
    ThresholdMetadata,
    ThresholdResult,
)
from datp.thresholding.thresholds import (
    arithmetic_mean_threshold,
    percentile_threshold,
)


@dataclass(frozen=True, slots=True)
class EligibilityResult:
    eligible_ids: tuple[str, ...]
    pending_ids: tuple[str, ...]

    def __iter__(self):
        yield list(self.eligible_ids)
        yield list(self.pending_ids)


@dataclass(frozen=True, slots=True)
class ClientCalibrationErrors:
    client_id: str
    errors: np.ndarray

    def __post_init__(self) -> None:
        object.__setattr__(self, "errors", np.array(self.errors, copy=False))


@dataclass(frozen=True, slots=True)
class CalibrationErrorSet:
    clients: tuple[ClientCalibrationErrors, ...]

    @classmethod
    def from_mapping(
        cls, client_errors: Mapping[str, np.ndarray]
    ) -> "CalibrationErrorSet":
        return cls(
            clients=tuple(
                ClientCalibrationErrors(client_id=cid, errors=errors)
                for cid, errors in client_errors.items()
            )
        )

    def for_client(self, client_id: str) -> ClientCalibrationErrors:
        for client in self.clients:
            if client.client_id == client_id:
                return client
        raise KeyError(client_id)

    @property
    def client_ids(self) -> tuple[str, ...]:
        return tuple(client.client_id for client in self.clients)


@dataclass(frozen=True, slots=True)
class ClientThresholdsCollection:
    entries: tuple[ClientThreshold, ...]

    @classmethod
    def from_mapping(
        cls, thresholds: Mapping[str, float], strategy: ThresholdPolicy
    ) -> "ClientThresholdsCollection":
        return cls(
            entries=tuple(
                ClientThreshold(
                    client_id=cid,
                    threshold=tau,
                    calibration_pending=False,
                    strategy=strategy,
                )
                for cid, tau in thresholds.items()
            )
        )

    def for_client(self, client_id: str) -> ClientThreshold:
        for entry in self.entries:
            if entry.client_id == client_id:
                return entry
        raise KeyError(client_id)

    @property
    def tau_values(self) -> tuple[float, ...]:
        return tuple(entry.threshold for entry in self.entries)

    @property
    def client_ids(self) -> tuple[str, ...]:
        return tuple(entry.client_id for entry in self.entries)

    def __bool__(self) -> bool:
        return bool(self.entries)

    def __len__(self) -> int:
        return len(self.entries)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Mapping):
            return dict(self.items()) == dict(other.items())
        return super().__eq__(other)

    def __getitem__(self, client_id: str) -> float:
        return self.for_client(client_id).threshold

    def __iter__(self):
        return iter(self.client_ids)

    def items(self):
        for entry in self.entries:
            yield entry.client_id, entry.threshold

    def keys(self):
        return iter(self.client_ids)

    def values(self):
        return iter(self.tau_values)


def identify_eligible(
    error_set: CalibrationErrorSet | Mapping[str, np.ndarray],
    n_min: int,
) -> EligibilityResult:
    if not isinstance(error_set, CalibrationErrorSet):
        error_set = CalibrationErrorSet.from_mapping(error_set)
    eligible: list[str] = []
    pending: list[str] = []
    for client in error_set.clients:
        cid = client.client_id
        errors = client.errors
        if errors.size >= n_min:
            eligible.append(cid)
        else:
            pending.append(cid)
    return EligibilityResult(eligible_ids=tuple(eligible), pending_ids=tuple(pending))


def compute_client_thresholds(
    error_set: CalibrationErrorSet | Mapping[str, np.ndarray],
    eligibility: EligibilityResult | Sequence[str],
    q: float,
) -> ClientThresholdsCollection:
    if not isinstance(error_set, CalibrationErrorSet):
        error_set = CalibrationErrorSet.from_mapping(error_set)
    if not isinstance(eligibility, EligibilityResult):
        eligibility = EligibilityResult(eligible_ids=tuple(eligibility), pending_ids=())
    return ClientThresholdsCollection(
        entries=tuple(
            ClientThreshold(
                client_id=cid,
                threshold=percentile_threshold(error_set.for_client(cid).errors, q=q),
                calibration_pending=False,
                strategy=ThresholdPolicy.LOCAL_THRESHOLD,
            )
            for cid in eligibility.eligible_ids
        )
    )


def compute_tau_global(
    thresholds: ClientThresholdsCollection | Mapping[str, float],
) -> float:
    """tau_global = (1/K_elig)×Στᵢ (GLOBAL_THRESHOLD formula); never sample-weighted; raises ValueError if client_taus is empty."""
    if not isinstance(thresholds, ClientThresholdsCollection):
        thresholds = ClientThresholdsCollection.from_mapping(thresholds, ThresholdPolicy.LOCAL_THRESHOLD)
    if not thresholds.entries:
        raise ValueError(
            fmt(
                "eligibility",
                "Cannot compute tau_global: no eligible clients",
                "at least 1 eligible client",
                "0",
            )
        )
    return arithmetic_mean_threshold(np.array(thresholds.tau_values))


def build_threshold_result(
    run: PolicyRunId,
    tau_global: float,
    eligible_thresholds: ClientThresholdsCollection | Mapping[str, float],
    pending_clients: tuple[str, ...] | Sequence[str],
    cluster_metadata: ClusterMetadata | None,
) -> ThresholdResult:
    thresholds: list[ClientThreshold] = []

    if not isinstance(eligible_thresholds, ClientThresholdsCollection):
        eligible_thresholds = ClientThresholdsCollection(
            entries=tuple(
                ClientThreshold(
                    client_id=cid,
                    threshold=tau,
                    calibration_pending=False,
                    strategy=run.policy,
                )
                for cid, tau in eligible_thresholds.items()
            )
        )

    for entry in eligible_thresholds.entries:
        thresholds.append(
            ClientThreshold(
                client_id=entry.client_id,
                threshold=entry.threshold,
                calibration_pending=False,
                strategy=run.policy,
            )
        )

    for cid in pending_clients:
        thresholds.append(
            ClientThreshold(
                client_id=cid,
                threshold=tau_global,
                calibration_pending=True,
                strategy=run.policy,
            )
        )

    return ThresholdResult(
        run=run,
        tau_global=tau_global,
        client_thresholds=tuple(thresholds),
        metadata=ThresholdMetadata(cluster=cluster_metadata),
    )
