"""Score collections, client-score tuples, and victim-set construction."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, KeysView, ValuesView
from dataclasses import dataclass
from functools import cached_property
from types import MappingProxyType
from typing import SupportsIndex, overload

import numpy as np

from datp.attacks.constants import N_MIN
from datp.thresholding.eligibility import (
    CalibrationErrorSet,
    ClientCalibrationErrors,
    EligibilityResult,
    identify_eligible,
)


@dataclass(frozen=True, slots=True)
class ClientScores:
    """Per-client score arrays for one experiment."""

    client_id: str
    cal: np.ndarray
    test_benign: np.ndarray
    test_attack: np.ndarray

    @property
    def n_cal(self) -> int:
        """Number of calibration scores for this client."""
        return self.cal.shape[0]


class ClientScoresTuple:
    """Immutable client-score collection with O(1) client-id lookups."""

    def __init__(self, clients: Iterable[ClientScores]):
        """Initialize from an iterable of ClientScores, preserving insertion order."""
        ordered = tuple(clients)
        self._clients = ordered
        self._map = MappingProxyType({c.client_id: c for c in ordered})

    def __iter__(self) -> Iterator[ClientScores]:
        """Iterate over clients in insertion order."""
        return iter(self._clients)

    def __len__(self) -> int:
        """Return the number of clients."""
        return len(self._clients)

    def __bool__(self) -> bool:
        """Return True if there is at least one client."""
        return bool(self._clients)

    @overload
    def __getitem__(self, key: str) -> ClientScores: ...  # noqa: D102
    @overload
    def __getitem__(self, key: SupportsIndex) -> ClientScores: ...  # noqa: D102
    @overload
    def __getitem__(self, key: slice) -> tuple[ClientScores, ...]: ...  # noqa: D102

    def __getitem__(
        self, key: str | SupportsIndex | slice
    ) -> ClientScores | tuple[ClientScores, ...]:
        """Access a client by string ID, integer index, or slice."""
        if isinstance(key, str):
            return self._map[key]
        return self._clients[key]

    def items(self) -> tuple[tuple[str, ClientScores], ...]:
        """Return (client_id, ClientScores) pairs as a tuple."""
        return tuple(self._map.items())

    def keys(self) -> KeysView[str]:
        """Return a view of all client IDs."""
        return self._map.keys()

    def values(self) -> ValuesView[ClientScores]:
        """Return a view of all ClientScores objects."""
        return self._map.values()


@dataclass(frozen=True)
class ScoreCollection:
    """Holds all client scores and partitions them into eligible/pending sets."""

    clients: ClientScoresTuple
    n_min: int = N_MIN

    @cached_property
    def _eligibility(self) -> EligibilityResult:
        res = identify_eligible(
            CalibrationErrorSet(
                tuple(ClientCalibrationErrors(c.client_id, c.cal) for c in self.clients)
            ),
            self.n_min,
        )
        return EligibilityResult(
            eligible_ids=tuple(sorted(res.eligible_ids)),
            pending_ids=tuple(sorted(res.pending_ids)),
        )

    @property
    def eligible_ids(self) -> tuple[str, ...]:
        """Client IDs that meet the minimum calibration sample threshold."""
        return self._eligibility.eligible_ids

    @property
    def pending_ids(self) -> tuple[str, ...]:
        """Client IDs that fall below the minimum calibration sample threshold."""
        return self._eligibility.pending_ids

    @cached_property
    def all_ids(self) -> tuple[str, ...]:
        """All client IDs, sorted."""
        return tuple(sorted(self.clients.keys()))

    @cached_property
    def _id_index(self) -> dict[str, int]:
        return {cid: i for i, cid in enumerate(self.all_ids)}

    def for_client(self, client_id: str) -> ClientScores:
        """Look up a client by ID."""
        return self.clients[client_id]

    def iter_clients(self):
        """Iterate over (client_id, ClientScores) pairs."""
        return self.clients.items()

    def client_index(self, client_id: str) -> int:
        """Deterministic index of *client_id* in the sorted client list."""
        return self._id_index[client_id]

    def cal_dict(self) -> dict[str, np.ndarray]:
        """Return {client_id: cal_scores} for all clients."""
        return {cid: c.cal for cid, c in self.clients.items()}

    def eligible_cal_dict(self) -> dict[str, np.ndarray]:
        """Return {client_id: cal_scores} for eligible clients only."""
        return {cid: self.clients[cid].cal for cid in self.eligible_ids}

    @property
    def coverage_ratio(self) -> float:
        """Fraction of clients that are eligible for threshold computation."""
        return len(self.eligible_ids) / len(self.clients) if self.clients else 0.0


@dataclass(frozen=True, slots=True)
class VictimSet:
    """The set of eligible clients that can be poisoned."""

    eligible_ids: tuple[str, ...]
    collection: ScoreCollection

    @property
    def n_victims(self) -> int:
        """Number of eligible victim clients."""
        return len(self.eligible_ids)

    def victim_cal(self, victim_id: str) -> np.ndarray:
        """Return the clean calibration scores for a victim."""
        if victim_id not in self.eligible_ids:
            raise ValueError(
                f"Client {victim_id!r} is not eligible. Eligible: {self.eligible_ids}"
            )
        return self.collection.for_client(victim_id).cal


def build_victim_set(collection: ScoreCollection) -> VictimSet:
    """Build the victim set from a score collection (eligible clients only)."""
    return VictimSet(eligible_ids=collection.eligible_ids, collection=collection)


def build_score_collection(
    client_scores: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]],
    n_min: int = N_MIN,
) -> ScoreCollection:
    """Build a ScoreCollection from {client_id: (cal, test_benign, test_attack)}."""
    clients = tuple(
        ClientScores(client_id=cid, cal=cal, test_benign=tb, test_attack=ta)
        for cid, (cal, tb, ta) in client_scores.items()
    )
    return ScoreCollection(clients=ClientScoresTuple(clients), n_min=n_min)
