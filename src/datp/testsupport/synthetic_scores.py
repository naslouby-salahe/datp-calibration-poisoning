"""Deterministic synthetic per-client score arrays for smoke testing.

CPU-only. No real data. Covers eligible, Calibration-Pending, and degenerate-tail
cases. All generators are deterministic via SeedSequence.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from datp.artifacts.poison_names import N_MIN
from datp.core.seed_sequence import make_seed_rng
from datp.scoring.schema import SCORE_COLUMN


@dataclass(frozen=True, slots=True)
class SyntheticClientScores:
    """Score arrays for one synthetic client.

    cal: benign calibration scores (reconstruction errors).
    test_benign: benign test scores.
    test_attack: attack test scores (higher than benign).
    """

    client_id: str
    cal: np.ndarray
    test_benign: np.ndarray
    test_attack: np.ndarray

    @property
    def n_cal(self) -> int:
        return int(self.cal.shape[0])

    @property
    def is_eligible(self) -> bool:
        return self.n_cal >= N_MIN

    @property
    def score_column(self) -> str:
        return SCORE_COLUMN


@dataclass(frozen=True, slots=True)
class SyntheticScoreSet:
    """A collection of synthetic clients forming one scenario."""

    clients: tuple[SyntheticClientScores, ...]

    @property
    def eligible(self) -> tuple[SyntheticClientScores, ...]:
        return tuple(c for c in self.clients if c.is_eligible)

    @property
    def pending(self) -> tuple[SyntheticClientScores, ...]:
        return tuple(c for c in self.clients if not c.is_eligible)

    @property
    def eligible_ids(self) -> tuple[str, ...]:
        return tuple(c.client_id for c in self.eligible)

    @property
    def pending_ids(self) -> tuple[str, ...]:
        return tuple(c.client_id for c in self.pending)

    @property
    def calibration_scores(self) -> "SyntheticCalibrationScoreSet":
        return SyntheticCalibrationScoreSet(
            tuple(
                SyntheticCalibrationScores(client_id=c.client_id, scores=c.cal)
                for c in self.clients
            )
        )

    def client_by_id(self, client_id: str) -> SyntheticClientScores:
        for c in self.clients:
            if c.client_id == client_id:
                return c
        raise KeyError(f"No client with id {client_id!r}")


@dataclass(frozen=True, slots=True)
class SyntheticCalibrationScores:
    client_id: str
    scores: np.ndarray


@dataclass(frozen=True, slots=True)
class SyntheticCalibrationScoreSet:
    clients: tuple[SyntheticCalibrationScores, ...]

    def __len__(self) -> int:
        return len(self.clients)

    def for_client(self, client_id: str) -> np.ndarray:
        for client in self.clients:
            if client.client_id == client_id:
                return client.scores
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
    """Generate one synthetic client's scores.

    Calibration and benign test scores are drawn from the same distribution
    (loc=cal_loc, scale=cal_scale). Attack test scores are drawn from a
    higher distribution (loc=attack_loc). All values are clipped to [0, inf).
    """
    rng = make_seed_rng(
        training_seed=spec.training_seed,
        poisoning_seed=spec.poisoning_seed,
        client_idx=spec.client_idx,
        scope_idx=spec.scope_idx,
        child_index=0,
    )
    cal = np.maximum(
        rng.normal(loc=spec.cal_loc, scale=spec.cal_scale, size=spec.n_cal), 0.0
    )
    test_benign = np.maximum(
        rng.normal(loc=spec.cal_loc, scale=spec.cal_scale, size=spec.n_test_benign), 0.0
    )
    test_attack = np.maximum(
        rng.normal(
            loc=spec.attack_loc, scale=spec.attack_scale, size=spec.n_test_attack
        ),
        0.0,
    )
    return SyntheticClientScores(
        client_id=spec.client_id,
        cal=cal,
        test_benign=test_benign,
        test_attack=test_attack,
    )


def make_eligible_client(
    *,
    client_id: str = "eligible_0",
    client_idx: int = 0,
    training_seed: int = 0,
    poisoning_seed: int = 100,
) -> SyntheticClientScores:
    """Shorthand: eligible client with n_cal >= N_MIN."""
    return make_synthetic_client(
        SyntheticClientSpec(
            client_id=client_id,
            n_cal=N_MIN + 100,
            client_idx=client_idx,
            training_seed=training_seed,
            poisoning_seed=poisoning_seed,
        )
    )


def make_pending_client(
    *,
    client_id: str = "pending_0",
    client_idx: int = 99,
    training_seed: int = 0,
    poisoning_seed: int = 100,
) -> SyntheticClientScores:
    """Shorthand: Calibration-Pending client with n_cal < N_MIN."""
    return make_synthetic_client(
        SyntheticClientSpec(
            client_id=client_id,
            n_cal=N_MIN - 1,
            client_idx=client_idx,
            training_seed=training_seed,
            poisoning_seed=poisoning_seed,
        )
    )


def make_degenerate_tail_client(
    *,
    client_id: str = "degenerate_0",
    client_idx: int = 50,
    training_seed: int = 0,
    poisoning_seed: int = 100,
) -> SyntheticClientScores:
    """Client with eligible n_cal but degenerate tail (< 2 distinct values in 10% tail).

    All calibration scores are identical (constant), so any percentile-based tail
    will have fewer than 2 distinct values.
    """
    n_cal = N_MIN + 50
    cal = np.full(n_cal, 0.05)
    rng = make_seed_rng(
        training_seed=training_seed,
        poisoning_seed=poisoning_seed,
        client_idx=client_idx,
        scope_idx=0,
        child_index=0,
    )
    test_benign = np.maximum(rng.normal(loc=0.05, scale=0.02, size=50), 0.0)
    test_attack = np.maximum(rng.normal(loc=0.30, scale=0.05, size=50), 0.0)
    return SyntheticClientScores(
        client_id=client_id,
        cal=cal,
        test_benign=test_benign,
        test_attack=test_attack,
    )


def make_standard_score_set(
    *,
    n_eligible: int = 9,
    n_pending: int = 1,
    include_degenerate: bool = False,
    training_seed: int = 0,
    poisoning_seed: int = 100,
) -> SyntheticScoreSet:
    """Build a standard Synthetic score set.

    Default: 9 eligible + 1 pending client (matches N-BaIoT 9-device setup).
    """
    clients: list[SyntheticClientScores] = []
    for i in range(n_eligible):
        clients.append(
            make_eligible_client(
                client_id=f"eligible_{i}",
                client_idx=i,
                training_seed=training_seed,
                poisoning_seed=poisoning_seed,
            )
        )
    for i in range(n_pending):
        clients.append(
            make_pending_client(
                client_id=f"pending_{i}",
                client_idx=n_eligible + i,
                training_seed=training_seed,
                poisoning_seed=poisoning_seed,
            )
        )
    if include_degenerate:
        clients.append(
            make_degenerate_tail_client(
                client_id="degenerate_0",
                client_idx=n_eligible + n_pending,
                training_seed=training_seed,
                poisoning_seed=poisoning_seed,
            )
        )
    return SyntheticScoreSet(clients=tuple(clients))
