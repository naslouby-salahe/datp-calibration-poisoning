from __future__ import annotations

from datp.types import (
    ClientId,
    Quantile,
    SampleCount,
    ScoreValue,
    ScoreVector,
    Threshold,
)


from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from datp.core.enums import ClientStatus, ThresholdPolicy
from datp.core.identity import PolicyRunId
from datp.core.types import (
    ClientThreshold,
    ClusterMetadata,
    ThresholdResult,
)
from datp.thresholding.thresholds import (
    arithmetic_mean_threshold,
    percentile_threshold,
)


@dataclass(frozen=True, slots=True)
class EligibilityResult:

    eligible_ids: tuple[ClientId, ...]
    pending_ids: tuple[ClientId, ...]


@dataclass(frozen=True, slots=True)
class ClientCalibrationErrors:

    client_id: ClientId
    errors: ScoreVector

    def __post_init__(self) -> None:
        object.__setattr__(self, "errors", np.array(self.errors, copy=False))


@dataclass(frozen=True, slots=True)
class CalibrationErrorSet:

    clients: tuple[ClientCalibrationErrors, ...]

    @classmethod
    def from_mapping(
        cls,
        client_errors: Mapping[ClientId, ScoreVector],
    ) -> "CalibrationErrorSet":
        return cls(
            clients=tuple(
                ClientCalibrationErrors(client_id=ClientId(cid), errors=errors)
                for cid, errors in client_errors.items()
            )
        )

    def for_client(self, client_id: ClientId) -> ClientCalibrationErrors:
        for client in self.clients:
            if client.client_id == client_id:
                return client
        raise KeyError(client_id)

@dataclass(frozen=True, slots=True)
class ClientThresholdsCollection(Mapping[ClientId, float]):

    entries: tuple[ClientThreshold, ...]

    @classmethod
    def from_mapping(
        cls,
        thresholds: Mapping[ClientId, Threshold],
        strategy: ThresholdPolicy,
    ) -> "ClientThresholdsCollection":
        return cls(
            entries=tuple(
                ClientThreshold(
                    client_id=ClientId(cid),
                    threshold=tau,
                    status=ClientStatus.ELIGIBLE,
                    strategy=strategy,
                )
                for cid, tau in thresholds.items()
            )
        )

    @property
    def tau_values(self) -> tuple[Threshold, ...]:
        return tuple(entry.threshold for entry in self.entries)

    @property
    def client_ids(self) -> tuple[ClientId, ...]:
        return tuple(entry.client_id for entry in self.entries)

    def __len__(self) -> int:
        return len(self.entries)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Mapping):
            return dict(self.items()) == other
        return super().__eq__(other)

    def __getitem__(self, client_id: ClientId) -> ScoreValue:
        for entry in self.entries:
            if entry.client_id == client_id:
                return entry.threshold
        raise KeyError(client_id)

    def __iter__(self):
        return iter(self.client_ids)


def identify_eligible(
    error_set: CalibrationErrorSet | Mapping[ClientId, ScoreVector],
    n_min: SampleCount,
) -> EligibilityResult:
    if not isinstance(error_set, CalibrationErrorSet):
        error_set = CalibrationErrorSet.from_mapping(error_set)
    eligible: list[ClientId] = []
    pending: list[ClientId] = []
    for client in error_set.clients:
        if client.errors.size >= n_min:
            eligible.append(client.client_id)
        else:
            pending.append(client.client_id)
    return EligibilityResult(eligible_ids=tuple(eligible), pending_ids=tuple(pending))


def compute_client_thresholds(
    error_set: CalibrationErrorSet | Mapping[ClientId, ScoreVector],
    eligibility: EligibilityResult,
    q: Quantile,
) -> ClientThresholdsCollection:
    if not isinstance(error_set, CalibrationErrorSet):
        error_set = CalibrationErrorSet.from_mapping(error_set)
    return ClientThresholdsCollection(
        entries=tuple(
                ClientThreshold(
                client_id=cid,
                threshold=percentile_threshold(error_set.for_client(cid).errors, q=q),
                status=ClientStatus.ELIGIBLE,
                strategy=ThresholdPolicy.LOCAL_THRESHOLD,
            )
            for cid in eligibility.eligible_ids
        )
    )


def compute_tau_global(
    thresholds: ClientThresholdsCollection | Mapping[ClientId, Threshold],
) -> ScoreValue:
    if not isinstance(thresholds, ClientThresholdsCollection):
        thresholds = ClientThresholdsCollection.from_mapping(
            thresholds,
            ThresholdPolicy.LOCAL_THRESHOLD,
        )
    if not thresholds.entries:
        raise ValueError(
            "[eligibility] Cannot compute tau_global: no eligible clients. Expected: at least 1 eligible client. Got: 0."
        )
    return arithmetic_mean_threshold(np.array(thresholds.tau_values))


def build_threshold_result(
    run: PolicyRunId,
    tau_global: Threshold,
    eligible_thresholds: ClientThresholdsCollection | Mapping[ClientId, Threshold],
    pending_clients: Sequence[ClientId],
    cluster_metadata: ClusterMetadata | None,
) -> ThresholdResult:
    thresholds: list[ClientThreshold] = []

    if not isinstance(eligible_thresholds, ClientThresholdsCollection):
        eligible_thresholds = ClientThresholdsCollection(
            entries=tuple(
                ClientThreshold(
                    client_id=ClientId(cid),
                    threshold=tau,
                    status=ClientStatus.ELIGIBLE,
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
                status=ClientStatus.ELIGIBLE,
                strategy=run.policy,
            )
        )

    for cid in pending_clients:
        thresholds.append(
            ClientThreshold(
                client_id=ClientId(cid),
                threshold=tau_global,
                status=ClientStatus.CALIBRATION_PENDING,
                strategy=run.policy,
            )
        )

    return ThresholdResult(
        run=run,
        tau_global=tau_global,
        client_thresholds=tuple(thresholds),
        cluster=cluster_metadata,
    )
