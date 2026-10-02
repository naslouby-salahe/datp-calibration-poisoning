
from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from functools import cached_property
from types import MappingProxyType


from datp.attacks.constants import N_MIN
from datp.types import (
    ClientId,
    Index,
    Ratio,
    SampleCount,
    ScoreVector,
)
from datp.thresholding.eligibility import (
    CalibrationErrorSet,
    ClientCalibrationErrors,
    EligibilityResult,
    identify_eligible,
)


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

    def __reduce__(self) -> tuple[type[ClientScoresById], tuple[tuple[ClientScores, ...]]]:
        return ClientScoresById, (self._clients,)

    def __iter__(self) -> Iterator[ClientId]:
        return iter(self._map)

    def __len__(self) -> int:
        return len(self._clients)

    def __bool__(self) -> bool:
        return bool(self._clients)

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
        return (
            len(self.eligible_ids) / len(self.clients)
            if self.clients
            else 0.0
        )


def build_score_collection(
    client_scores: dict[ClientId, tuple[ScoreVector, ScoreVector, ScoreVector]] | dict[ClientId, tuple[ScoreVector, ScoreVector, ScoreVector]],
    n_min: SampleCount = N_MIN,
) -> ScoreCollection:
    clients = tuple(
            ClientScores(client_id=ClientId(cid), cal=cal, test_benign=tb, test_attack=ta)
        for cid, (cal, tb, ta) in client_scores.items()
    )
    return ScoreCollection(clients=ClientScoresById(clients), n_min=n_min)
