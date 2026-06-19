"""Unit tests for the locked bounded sweep cell-matrix enumerator ."""

from __future__ import annotations

import pytest

from datp.attacks.bounded_sweep_matrix import (
    enumerate_bounded_sweep_matrix,
    enumerate_full_sweep_matrix,
)
from datp.attacks.enums import (
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ThresholdPolicy,
)

_VICTIMS = ("c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8")
_VICTIMS_BY_SEED = {ts: _VICTIMS for ts in (0, 1, 2, 3, 4)}


def test_matrix_size_is_exactly_1620():
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED)
    assert len(cells) == 5 * 9 * 3 * 3 * 4


def test_matrix_policies_are_exactly_default_three():
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED)
    assert {c.policy for c in cells} == {
        ThresholdPolicy.B1_GLOBAL,
        ThresholdPolicy.B2_PERSONALIZED,
        ThresholdPolicy.B4_CLUSTER,
    }


def test_matrix_excludes_fraction_005():
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED)
    assert all(c.fraction != 0.05 for c in cells)


def test_matrix_fractions_are_exactly_locked_grid():
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED)
    assert {c.fraction for c in cells} == {0.0, 0.10, 0.20, 0.40}


def test_matrix_sources_are_exactly_bounded_three():
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED)
    assert {c.source for c in cells} == {
        PoisoningSourceStrategy.RANDOM_BENIGN,
        PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        PoisoningSourceStrategy.LOW_SCORE_BENIGN,
    }


def test_matrix_seed_pairs_are_exactly_the_locked_five():
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED)
    pairs = {(c.training_seed, c.poisoning_seed) for c in cells}
    assert pairs == {(0, 100), (1, 101), (2, 102), (3, 103), (4, 104)}


def test_matrix_target_scope_is_always_single_client():
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED)
    assert all(c.target_scope == PoisoningTargetScope.SINGLE_CLIENT for c in cells)


def test_matrix_missing_seed_raises_keyerror():
    incomplete = {0: _VICTIMS}
    with pytest.raises(KeyError):
        enumerate_bounded_sweep_matrix(incomplete)


# ---------------------------------------------------------------------------
# Full-scope matrix (fraction 0.05 added) — execution gated; enumeration only.
# ---------------------------------------------------------------------------


def test_full_matrix_size_is_exactly_2025():
    cells = enumerate_full_sweep_matrix(_VICTIMS_BY_SEED)
    assert len(cells) == 5 * 9 * 3 * 3 * 5


def test_full_matrix_fractions_add_005_to_bounded_grid():
    cells = enumerate_full_sweep_matrix(_VICTIMS_BY_SEED)
    assert {c.fraction for c in cells} == {0.0, 0.05, 0.10, 0.20, 0.40}


def test_full_matrix_superset_of_bounded_matrix():
    bounded = set(enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED))
    full = set(enumerate_full_sweep_matrix(_VICTIMS_BY_SEED))
    assert bounded.issubset(full)
    # The only difference is the 0.05 cells.
    assert {c.fraction for c in (full - bounded)} == {0.05}


def test_full_matrix_keeps_all_other_locks():
    cells = enumerate_full_sweep_matrix(_VICTIMS_BY_SEED)
    assert {c.policy for c in cells} == set(ThresholdPolicy)
    assert all(c.target_scope == PoisoningTargetScope.SINGLE_CLIENT for c in cells)
    assert {(c.training_seed, c.poisoning_seed) for c in cells} == {
        (0, 100),
        (1, 101),
        (2, 102),
        (3, 103),
        (4, 104),
    }


def test_full_matrix_missing_seed_raises_keyerror():
    with pytest.raises(KeyError):
        enumerate_full_sweep_matrix({0: _VICTIMS})
