"""Tests verifying grid sweeps matrix cells enumeration, target size calculations, and config subset checks."""

from __future__ import annotations

import math
from typing import Any

import pytest

from datp.attacks.enums import (
    AttackerObjective,
    PoisoningKnowledge,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
)
from datp.attacks.planning.bounded_sweep_matrix import (
    enumerate_bounded_sweep_matrix,
    enumerate_full_sweep_matrix,
)
from datp.config.attack_config import CalibrationPoisoningConfig, SeedPools
from datp.config.models import ExperimentStage
from datp.core.enums import ThresholdPolicy

_VICTIMS: tuple[str, ...] = ("c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8")
_VICTIMS_BY_SEED: dict[int, tuple[str, ...]] = dict.fromkeys(tuple(range(10)), _VICTIMS)


def _bounded_config() -> CalibrationPoisoningConfig:
    """Helper to build a default bounded sweep CalibrationPoisoningConfig."""
    return CalibrationPoisoningConfig.for_bounded_sweep()


def _full_config(**overrides: Any) -> CalibrationPoisoningConfig:
    """Helper to build a full sweep CalibrationPoisoningConfig."""
    from datp.attacks.constants import NBAIOT_FULL_OPTIONAL_SWEEP_FRACTIONS

    defaults: dict[str, Any] = {
        "policies": (
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        ),
        "sources": (
            PoisoningSourceStrategy.RANDOM_BENIGN,
            PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            PoisoningSourceStrategy.LOW_SCORE_BENIGN,
        ),
        "objectives": (
            AttackerObjective.THRESHOLD_RAISE,
            AttackerObjective.THRESHOLD_LOWER,
        ),
        "knowledge": PoisoningKnowledge.GRAY_BOX_SCORE_ACCESS,
        "target_scope": PoisoningTargetScope.SINGLE_CLIENT,
        "stage": ExperimentStage.NBAIOT_FULL_OPTIONAL,
        "fractions": NBAIOT_FULL_OPTIONAL_SWEEP_FRACTIONS,
    }
    defaults.update(overrides)
    return CalibrationPoisoningConfig(**defaults)


def test_bounded_enumerator_rejects_full_config() -> None:
    """Verify that the bounded sweep enumerator rejects configurations with full/optional stage."""
    with pytest.raises(ValueError, match="ExperimentStage.NBAIOT_MAIN"):
        enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED, _full_config())


def test_full_enumerator_rejects_bounded_config() -> None:
    """Verify that the full sweep enumerator rejects configurations with main sweep stage."""
    with pytest.raises(ValueError, match="ExperimentStage.NBAIOT_FULL_OPTIONAL"):
        enumerate_full_sweep_matrix(_VICTIMS_BY_SEED, _bounded_config())


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


def test_full_matrix_size_is_exactly_5400() -> None:
    """Verify that the full sweep matrix generates exactly 5,400 configuration cells."""
    cells = enumerate_full_sweep_matrix(_VICTIMS_BY_SEED, _full_config())
    assert len(cells) == 10 * 9 * 3 * 4 * 5


def test_full_matrix_fractions_add_005_to_bounded_grid() -> None:
    """Verify that the full sweep grid adds 0.05 step to fractions."""
    cells = enumerate_full_sweep_matrix(_VICTIMS_BY_SEED, _full_config())
    assert sorted({c.fraction for c in cells}) == pytest.approx(
        [0.0, 0.05, 0.10, 0.20, 0.40]
    )


def test_full_matrix_superset_of_bounded_matrix() -> None:
    """Verify that the full matrix configuration set is a strict superset of bounded matrix configurations."""
    bounded = set(enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED, _bounded_config()))
    full = set(enumerate_full_sweep_matrix(_VICTIMS_BY_SEED, _full_config()))
    assert bounded.issubset(full)
    assert sorted({c.fraction for c in (full - bounded)}) == pytest.approx([0.05])


def test_full_matrix_keeps_all_other_locks() -> None:
    """Verify that the full sweep preserves all enums configurations enforcements."""
    cells = enumerate_full_sweep_matrix(_VICTIMS_BY_SEED, _full_config())
    assert {c.policy for c in cells} == set(ThresholdPolicy)
    assert all(c.target_scope == PoisoningTargetScope.SINGLE_CLIENT for c in cells)
    assert {(c.training_seed, c.poisoning_seed) for c in cells} == {
        (seed, seed + 100) for seed in range(10)
    }


def test_full_matrix_missing_seed_raises_keyerror() -> None:
    """Verify that missing keys in training seeds map raise KeyError on full sweeps."""
    with pytest.raises(KeyError):
        enumerate_full_sweep_matrix({0: _VICTIMS}, _full_config())


def test_enumerator_uses_config_policies_not_constants() -> None:
    """Verify that enumerators honor policy bounds specified in configuration arguments."""
    config = _full_config(policies=(ThresholdPolicy.GLOBAL_THRESHOLD,))
    cells = enumerate_full_sweep_matrix(_VICTIMS_BY_SEED, config)
    assert all(c.policy == ThresholdPolicy.GLOBAL_THRESHOLD for c in cells)
    policies_seen = {c.policy for c in cells}
    assert ThresholdPolicy.LOCAL_THRESHOLD not in policies_seen
    assert ThresholdPolicy.CLUSTER_THRESHOLD not in policies_seen


def test_enumerator_uses_config_fractions_not_constants() -> None:
    """Verify that enumerators honor sweep fractions specified in configuration arguments."""
    config = _full_config(fractions=(0.10,))
    cells = enumerate_full_sweep_matrix(_VICTIMS_BY_SEED, config)
    assert all(math.isclose(c.fraction, 0.10) for c in cells)


def test_enumerator_uses_config_seeds_not_constants() -> None:
    """Verify that enumerators honor custom seed pools specified in configuration arguments."""
    single_seed_pool = SeedPools(training=(0,), poisoning=(100,), analysis=(300,))
    config = _full_config(seeds=single_seed_pool)
    cells = enumerate_full_sweep_matrix(_VICTIMS_BY_SEED, config)

    expected = 1 * len(_VICTIMS) * len(config.policies) * 4 * len(config.fractions)
    assert len(cells) == expected
    pairs = {(c.training_seed, c.poisoning_seed) for c in cells}
    assert pairs == {(0, 100)}
