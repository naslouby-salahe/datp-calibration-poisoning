"""Tests verifying grid sweeps matrix cells enumeration, target size calculations, and config subset checks."""

from __future__ import annotations

import math

import pytest

from datp.attacks.enums import (
    AttackerObjective,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
)
from datp.attacks.planning.bounded_sweep_matrix import (
    enumerate_bounded_sweep_matrix,
)
from datp.config.attack_config import CalibrationPoisoningConfig
from datp.core.enums import ThresholdPolicy

_VICTIMS: tuple[str, ...] = ("c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8")
_VICTIMS_BY_SEED: dict[int, tuple[str, ...]] = dict.fromkeys(tuple(range(10)), _VICTIMS)


def _bounded_config() -> CalibrationPoisoningConfig:
    """Helper to build a default bounded sweep CalibrationPoisoningConfig."""
    return CalibrationPoisoningConfig.for_bounded_sweep()


def test_matrix_size_is_exactly_4320() -> None:
    """Verify that the default bounded sweep matrix contains exactly 4,320 evaluation cells."""
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED, _bounded_config())
    assert len(cells) == 10 * 9 * 3 * 4 * 4


def test_matrix_policies_are_exactly_default_three() -> None:
    """Verify that the sweep matrix includes all three threshold policies exactly."""
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED, _bounded_config())
    assert {c.policy for c in cells} == {
        ThresholdPolicy.GLOBAL_THRESHOLD,
        ThresholdPolicy.LOCAL_THRESHOLD,
        ThresholdPolicy.CLUSTER_THRESHOLD,
    }


def test_matrix_excludes_fraction_005() -> None:
    """Verify that the bounded sweep matrix excludes the 0.05 fraction grid points."""
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED, _bounded_config())
    assert all(not math.isclose(c.fraction, 0.05, abs_tol=0.0) for c in cells)


def test_matrix_fractions_are_exactly_locked_grid() -> None:
    """Verify that fractions used in the sweep map exactly to main grid fractions."""
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED, _bounded_config())
    assert sorted({c.fraction for c in cells}) == pytest.approx([0.0, 0.10, 0.20, 0.40])


def test_matrix_sources_are_exactly_bounded_three() -> None:
    """Verify that sources sweep covers the three core client strategies."""
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED, _bounded_config())
    assert {c.source for c in cells} == {
        PoisoningSourceStrategy.RANDOM_BENIGN,
        PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        PoisoningSourceStrategy.LOW_SCORE_BENIGN,
    }


def test_matrix_source_objective_pairs_are_exactly_main_four() -> None:
    """Verify that the sweep combines sources and objectives according to design rules."""
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED, _bounded_config())
    assert {(c.source, c.objective) for c in cells} == {
        (
            PoisoningSourceStrategy.RANDOM_BENIGN,
            AttackerObjective.THRESHOLD_RAISE,
        ),
        (
            PoisoningSourceStrategy.RANDOM_BENIGN,
            AttackerObjective.THRESHOLD_LOWER,
        ),
        (
            PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            AttackerObjective.THRESHOLD_RAISE,
        ),
        (
            PoisoningSourceStrategy.LOW_SCORE_BENIGN,
            AttackerObjective.THRESHOLD_LOWER,
        ),
    }


def test_matrix_seed_pairs_are_exactly_the_locked_ten() -> None:
    """Verify that training and poisoning seed combinations map exactly to range indices."""
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED, _bounded_config())
    pairs = {(c.training_seed, c.poisoning_seed) for c in cells}
    assert pairs == {(seed, seed + 100) for seed in range(10)}


def test_matrix_target_scope_is_always_single_client() -> None:
    """Verify that target_scope is SINGLE_CLIENT for all sweep configurations."""
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED, _bounded_config())
    assert all(c.target_scope == PoisoningTargetScope.SINGLE_CLIENT for c in cells)


def test_matrix_missing_seed_raises_keyerror() -> None:
    """Verify that passing an incomplete training seeds mapping raises KeyError."""
    incomplete = {0: _VICTIMS}
    with pytest.raises(KeyError):
        enumerate_bounded_sweep_matrix(incomplete, _bounded_config())
