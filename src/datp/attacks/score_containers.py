"""Typed CP2 score containers and victim-set model.

Reuses inherited eligibility logic from thresholding.eligibility. Calibration-Pending
clients receive tau_global, are excluded from CV(FPR), victim sets, and B4 clustering.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from datp.artifacts.poison_names import CP2_N_MIN
from datp.thresholding.eligibility import identify_eligible


@dataclass(frozen=True, slots=True)
class Cp2ClientScores:
    """Per-client score arrays for one CP2 experiment.

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


@dataclass(frozen=True, slots=True)
class Cp2ScoreCollection:
    """Holds all client scores and partitions them into eligible/pending sets.

    Delegates to the inherited eligibility logic (identify_eligible).
    Eligible/pending IDs are eagerly computed and stored as tuple fields.
    """

    clients: dict[str, Cp2ClientScores]
    n_min: int = CP2_N_MIN
    _eligible_ids: tuple[str, ...] = ()
    _pending_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        cal_dict = {cid: c.cal for cid, c in self.clients.items()}
        eligible_ids, pending_ids = identify_eligible(cal_dict, self.n_min)
        object.__setattr__(self, "_eligible_ids", tuple(sorted(eligible_ids)))
        object.__setattr__(self, "_pending_ids", tuple(sorted(pending_ids)))

    @property
    def eligible_ids(self) -> tuple[str, ...]:
        return self._eligible_ids

    @property
    def pending_ids(self) -> tuple[str, ...]:
        return self._pending_ids

    @property
    def all_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.clients.keys()))

    def cal_dict(self) -> dict[str, np.ndarray]:
        """Return {client_id: cal_scores} for all clients."""
        return {cid: c.cal for cid, c in self.clients.items()}

    def eligible_cal_dict(self) -> dict[str, np.ndarray]:
        """Return {client_id: cal_scores} for eligible clients only."""
        return {cid: self.clients[cid].cal for cid in self.eligible_ids}

    @property
    def coverage_ratio(self) -> float:
        total = len(self.clients)
        if total == 0:
            return 0.0
        return len(self.eligible_ids) / total


@dataclass(frozen=True, slots=True)
class Cp2VictimSet:
    """The set of eligible clients that can be poisoned.

    Only eligible clients (n_cal >= n_min) are valid victims. Calibration-Pending
    clients cannot be victims. The replacement preserves cardinality n_i, so
    eligibility is invariant under attack.
    """

    eligible_ids: tuple[str, ...]
    collection: Cp2ScoreCollection

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
        return self.collection.clients[victim_id].cal


def build_victim_set(collection: Cp2ScoreCollection) -> Cp2VictimSet:
    """Build the victim set from a score collection (eligible clients only)."""
    return Cp2VictimSet(
        eligible_ids=collection.eligible_ids,
        collection=collection,
    )


def build_score_collection(
    client_scores: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]],
    n_min: int = CP2_N_MIN,
) -> Cp2ScoreCollection:
    """Build a Cp2ScoreCollection from raw arrays.

    Each value is (cal, test_benign, test_attack).
    """
    clients = {
        cid: Cp2ClientScores(
            client_id=cid,
            cal=cal,
            test_benign=test_benign,
            test_attack=test_attack,
        )
        for cid, (cal, test_benign, test_attack) in client_scores.items()
    }
    return Cp2ScoreCollection(clients=clients, n_min=n_min)
