"""Typed Score containers and victim-set model.

Reuses inherited eligibility logic from thresholding.eligibility. Calibration-Pending
clients receive tau_global, are excluded from CV(FPR), victim sets, and CLUSTER_THRESHOLD clustering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, SupportsIndex, overload

import numpy as np

from datp.artifacts.poison_names import N_MIN
from datp.thresholding.eligibility import (
    CalibrationErrorSet,
    ClientCalibrationErrors,
    EligibilityResult,
    identify_eligible,
)


@dataclass(frozen=True, slots=True)
class ClientScores:
    """Per-client score arrays for one experiment.

    cal: benign calibration scores (reconstruction errors).
    test_benign: benign test scores.
    test_attack: attack test scores.
    """

    client_id: str
    cal: np.ndarray
    test_benign: np.ndarray
    test_attack: np.ndarray

    @property
    def n_cal(self) -> int:
        return int(self.cal.shape[0])


class ClientScoresTuple(tuple[ClientScores, ...]):
    def __new__(cls, clients: Any) -> "ClientScoresTuple":
        return super().__new__(cls, clients)

    @overload
    def __getitem__(self, key: str) -> ClientScores: ...

    @overload
    def __getitem__(self, key: SupportsIndex) -> ClientScores: ...

    @overload
    def __getitem__(self, key: slice) -> tuple[ClientScores, ...]: ...

    def __getitem__(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, key: str | SupportsIndex | slice
    ) -> ClientScores | tuple[ClientScores, ...]:
        if isinstance(key, str):
            for client in self:
                if client.client_id == key:
                    return client
            raise KeyError(key)
        return super().__getitem__(key)

    def items(self):
        for client in self:
            yield client.client_id, client

    def keys(self):
        return (client.client_id for client in self)

    def values(self):
        return iter(self)


@dataclass(frozen=True, slots=True)
class ScoreCollection:
    """Holds all client scores and partitions them into eligible/pending sets.

    Delegates to the inherited eligibility logic (identify_eligible).
    Eligible/pending IDs are eagerly computed and stored as tuple fields.
    """

    clients: ClientScoresTuple
    n_min: int = N_MIN
    _eligible_result: EligibilityResult = field(init=False)

    def __post_init__(self) -> None:
        clients: Any = self.clients
        if hasattr(clients, "values"):
            clients = tuple(clients.values())
        object.__setattr__(self, "clients", ClientScoresTuple(clients))
        error_set = CalibrationErrorSet(
            clients=tuple(
                ClientCalibrationErrors(client_id=c.client_id, errors=c.cal)
                for c in self.clients
            )
        )
        result = identify_eligible(error_set, self.n_min)
        object.__setattr__(
            self,
            "_eligible_result",
            EligibilityResult(
                eligible_ids=tuple(sorted(result.eligible_ids)),
                pending_ids=tuple(sorted(result.pending_ids)),
            ),
        )

    @property
    def eligible_ids(self) -> tuple[str, ...]:
        return self._eligible_result.eligible_ids

    @property
    def pending_ids(self) -> tuple[str, ...]:
        return self._eligible_result.pending_ids

    @property
    def all_ids(self) -> tuple[str, ...]:
        return tuple(sorted(c.client_id for c in self.clients))

    def for_client(self, client_id: str) -> ClientScores:
        for client in self.clients:
            if client.client_id == client_id:
                return client
        raise KeyError(client_id)

    def iter_clients(self):
        for client in self.clients:
            yield client.client_id, client

    def client_index(self, client_id: str) -> int:
        """Deterministic index of *client_id* in the sorted client list, used for SeedSequence."""
        return self.all_ids.index(client_id)

    def cal_dict(self) -> dict[str, np.ndarray]:
        """Return {client_id: cal_scores} for all clients."""
        return {cid: c.cal for cid, c in self.iter_clients()}

    def eligible_cal_dict(self) -> dict[str, np.ndarray]:
        """Return {client_id: cal_scores} for eligible clients only."""
        return {cid: self.for_client(cid).cal for cid in self.eligible_ids}

    @property
    def coverage_ratio(self) -> float:
        total = len(self.clients)
        if total == 0:
            return 0.0
        return len(self.eligible_ids) / total


@dataclass(frozen=True, slots=True)
class VictimSet:
    """The set of eligible clients that can be poisoned.

    Only eligible clients (n_cal >= n_min) are valid victims. Calibration-Pending
    clients cannot be victims. The replacement preserves cardinality n_i, so
    eligibility is invariant under attack.
    """

    eligible_ids: tuple[str, ...]
    collection: ScoreCollection

    @property
    def n_victims(self) -> int:
        return len(self.eligible_ids)

    def victim_cal(self, victim_id: str) -> np.ndarray:
        """Return the clean calibration scores for a victim."""
        if victim_id not in self.eligible_ids:
            raise ValueError(
                f"Client {victim_id!r} is not an eligible victim. "
                f"Eligible: {self.eligible_ids}"
            )
        return self.collection.for_client(victim_id).cal


def build_victim_set(collection: ScoreCollection) -> VictimSet:
    """Build the victim set from a score collection (eligible clients only)."""
    return VictimSet(
        eligible_ids=collection.eligible_ids,
        collection=collection,
    )


def build_score_collection(
    client_scores: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]],
    n_min: int = N_MIN,
) -> ScoreCollection:
    """Build a ScoreCollection from raw arrays.

    Each value is (cal, test_benign, test_attack).
    """
    clients = tuple(
        ClientScores(
            client_id=cid,
            cal=cal,
            test_benign=test_benign,
            test_attack=test_attack,
        )
        for cid, (cal, test_benign, test_attack) in client_scores.items()
    )
    return ScoreCollection(clients=ClientScoresTuple(clients), n_min=n_min)
