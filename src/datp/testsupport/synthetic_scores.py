"""Deterministic synthetic per-client score arrays for smoke testing."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from datp.attacks.constants import N_MIN
from datp.core.seeds import SeedPair, SeedRecord, make_seed_rng
from datp.scoring.manifest import SCORE_COLUMN


@dataclass(frozen=True, slots=True)
class SyntheticClientScores:
    """Score arrays for one synthetic client."""

    client_id: str
    cal: np.ndarray
    test_benign: np.ndarray
    test_attack: np.ndarray

    @property
    def n_cal(self) -> int:
        """Number of calibration samples for this synthetic client."""
        return int(self.cal.shape[0])

    @property
    def is_eligible(self) -> bool:
        """Whether this client meets the protocol minimum calibration size."""
        return self.n_cal >= N_MIN

    @property
    def score_column(self) -> str:
        """Canonical name of the score column in the scoring manifest."""
        return SCORE_COLUMN


@dataclass(frozen=True, slots=True)
class SyntheticCalibrationScores:
    """Calibration-only score array for one synthetic client."""

    client_id: str
    scores: np.ndarray


@dataclass(frozen=True, slots=True)
class SyntheticCalibrationScoreSet:
    """Collection of calibration-only synthetic score arrays keyed by client."""

    clients: tuple[SyntheticCalibrationScores, ...]

    def __len__(self) -> int:
        """Return the number of clients in this calibration score set."""
        return len(self.clients)

    def for_client(self, client_id: str) -> np.ndarray:
        """Return the calibration scores for a client by ID, raising KeyError if absent."""
        for client in self.clients:
            if client.client_id == client_id:
                return client.scores
        raise KeyError(f"No client with id {client_id!r}")


@dataclass(frozen=True, slots=True)
class SyntheticScoreSet:
    """A collection of synthetic clients forming one scenario."""

    clients: tuple[SyntheticClientScores, ...]

    @property
    def eligible(self) -> tuple[SyntheticClientScores, ...]:
        """Clients whose calibration size meets the protocol minimum."""
        return tuple(c for c in self.clients if c.is_eligible)

    @property
    def pending(self) -> tuple[SyntheticClientScores, ...]:
        """Clients whose calibration size falls below the protocol minimum."""
        return tuple(c for c in self.clients if not c.is_eligible)

    @property
    def eligible_ids(self) -> tuple[str, ...]:
        """Client IDs of all eligible clients in this score set."""
        return tuple(c.client_id for c in self.eligible)

    @property
    def pending_ids(self) -> tuple[str, ...]:
        """Client IDs of all calibration-pending clients in this score set."""
        return tuple(c.client_id for c in self.pending)

    @property
    def calibration_scores(self) -> SyntheticCalibrationScoreSet:
        """Extract calibration-only scores as a SyntheticCalibrationScoreSet."""
        return SyntheticCalibrationScoreSet(
            tuple(
                SyntheticCalibrationScores(client_id=c.client_id, scores=c.cal)
                for c in self.clients
            )
        )

    def client_by_id(self, client_id: str) -> SyntheticClientScores:
        """Return the full SyntheticClientScores for a client by ID, raising KeyError if absent."""
        for client in self.clients:
            if client.client_id == client_id:
                return client
        raise KeyError(f"No client with id {client_id!r}")


@dataclass(frozen=True, slots=True)
class SyntheticClientSpec:
    """Full parameter set for generating one synthetic client's scores."""

    client_id: str
    n_cal: int = 200
    n_test_benign: int = 50
    n_test_attack: int = 50
    cal_loc: float = 0.05
    cal_scale: float = 0.02
    attack_loc: float = 0.30
    attack_scale: float = 0.05
    training_seed: int = 0
    poisoning_seed: int = 100
    client_idx: int = 0
    scope_idx: int = 0


def make_synthetic_client(spec: SyntheticClientSpec) -> SyntheticClientScores:
    """Generate one synthetic client's non-negative reconstruction scores."""
    rng = make_seed_rng(
        SeedRecord(
            pair=SeedPair(
                training_seed=spec.training_seed,
                poisoning_seed=spec.poisoning_seed,
            ),
            client_idx=spec.client_idx,
            scope_idx=spec.scope_idx,
        ),
        child_index=0,
    )

    def draw(loc: float, scale: float, size: int) -> np.ndarray:
        return np.maximum(rng.normal(loc=loc, scale=scale, size=size), 0.0)

    return SyntheticClientScores(
        client_id=spec.client_id,
        cal=draw(spec.cal_loc, spec.cal_scale, spec.n_cal),
        test_benign=draw(spec.cal_loc, spec.cal_scale, spec.n_test_benign),
        test_attack=draw(spec.attack_loc, spec.attack_scale, spec.n_test_attack),
    )


def _make_from_spec(
    client_id: str,
    n_cal: int,
    client_idx: int,
    seeds: tuple[int, int],
) -> SyntheticClientScores:
    return make_synthetic_client(
        SyntheticClientSpec(
            client_id=client_id,
            n_cal=n_cal,
            client_idx=client_idx,
            training_seed=seeds[0],
            poisoning_seed=seeds[1],
        )
    )


def make_eligible_client(
    *,
    client_id: str = "eligible_0",
    client_idx: int = 0,
    training_seed: int = 0,
    poisoning_seed: int = 100,
) -> SyntheticClientScores:
    """Shorthand for an eligible client with n_cal above the protocol minimum."""
    return _make_from_spec(
        client_id,
        N_MIN + 100,
        client_idx,
        (training_seed, poisoning_seed),
    )


def make_pending_client(
    *,
    client_id: str = "pending_0",
    client_idx: int = 99,
    training_seed: int = 0,
    poisoning_seed: int = 100,
) -> SyntheticClientScores:
    """Shorthand for a Calibration-Pending client with n_cal below N_MIN."""
    return _make_from_spec(
        client_id,
        N_MIN - 1,
        client_idx,
        (training_seed, poisoning_seed),
    )


def make_degenerate_tail_client(
    *,
    client_id: str = "degenerate_0",
    client_idx: int = 50,
    training_seed: int = 0,
    poisoning_seed: int = 100,
) -> SyntheticClientScores:
    """Client with eligible n_cal but fewer than two distinct tail values."""
    rng = make_seed_rng(
        SeedRecord(
            pair=SeedPair(training_seed=training_seed, poisoning_seed=poisoning_seed),
            client_idx=client_idx,
            scope_idx=0,
        ),
        child_index=0,
    )
    return SyntheticClientScores(
        client_id=client_id,
        cal=np.full(N_MIN + 50, 0.05),
        test_benign=np.maximum(rng.normal(loc=0.05, scale=0.02, size=50), 0.0),
        test_attack=np.maximum(rng.normal(loc=0.30, scale=0.05, size=50), 0.0),
    )


@dataclass(frozen=True, slots=True)
class StandardScoreSetRequest:
    """Parameters for the standard N-BaIoT-shaped synthetic score fixture."""

    n_eligible: int = 9
    n_pending: int = 1
    include_degenerate: bool = False
    training_seed: int = 0
    poisoning_seed: int = 100


def make_standard_score_set(
    req: StandardScoreSetRequest = StandardScoreSetRequest(),
) -> SyntheticScoreSet:
    """Build the standard synthetic score set used by smoke tests."""
    clients = [
        make_eligible_client(
            client_id=f"eligible_{i}",
            client_idx=i,
            training_seed=req.training_seed,
            poisoning_seed=req.poisoning_seed,
        )
        for i in range(req.n_eligible)
    ]
    clients.extend(
        make_pending_client(
            client_id=f"pending_{i}",
            client_idx=req.n_eligible + i,
            training_seed=req.training_seed,
            poisoning_seed=req.poisoning_seed,
        )
        for i in range(req.n_pending)
    )
    if req.include_degenerate:
        clients.append(
            make_degenerate_tail_client(
                client_id="degenerate_0",
                client_idx=req.n_eligible + req.n_pending,
                training_seed=req.training_seed,
                poisoning_seed=req.poisoning_seed,
            )
        )
    return SyntheticScoreSet(clients=tuple(clients))
