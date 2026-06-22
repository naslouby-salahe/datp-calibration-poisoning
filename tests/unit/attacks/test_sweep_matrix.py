"""Unit tests for the locked bounded sweep cell-matrix enumerator ."""

from __future__ import annotations

import math

import pytest

from datp.attacks.sweep_matrix import (
    enumerate_sweep_cells,
    enumerate_full_sweep_matrix,
)
from datp.attacks.enums import (
    PoisoningKnowledge,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ThresholdPolicy,
)
from datp.config.attack_config import CalibrationPoisoningConfig, SeedPools
from datp.config.stages import ExperimentStage

_VICTIMS: tuple[str, ...] = ("c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8")
_VICTIMS_BY_SEED: dict[int, tuple[str, ...]] = dict.fromkeys((0, 1, 2, 3, 4), _VICTIMS)


def _bounded_config() -> CalibrationPoisoningConfig:
    return CalibrationPoisoningConfig.for_bounded_sweep()


def _full_config(**overrides: object) -> CalibrationPoisoningConfig:
    from datp.attacks.constants import NBAIOT_FULL_OPTIONAL_SWEEP_FRACTIONS

    defaults: dict[str, object] = {
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
        "knowledge": PoisoningKnowledge.GRAY_BOX_SCORE_ACCESS,
        "target_scope": PoisoningTargetScope.SINGLE_CLIENT,
        "stage": ExperimentStage.NBAIOT_FULL_OPTIONAL,
        "fractions": NBAIOT_FULL_OPTIONAL_SWEEP_FRACTIONS,
    }
    defaults.update(overrides)
    return CalibrationPoisoningConfig(**defaults)  # type: ignore[arg-type]


def test_bounded_enumerator_rejects_full_config():
    with pytest.raises(ValueError, match="ExperimentStage.NBAIOT_MAIN"):
        enumerate_sweep_cells(_VICTIMS_BY_SEED, _full_config())


def test_full_enumerator_rejects_bounded_config():
    with pytest.raises(ValueError, match="ExperimentStage.NBAIOT_FULL_OPTIONAL"):
        enumerate_full_sweep_matrix(_VICTIMS_BY_SEED, _bounded_config())


def test_matrix_size_is_exactly_1620():
    cells = enumerate_sweep_cells(_VICTIMS_BY_SEED, _bounded_config())
    assert len(cells) == 5 * 9 * 3 * 3 * 4


def test_matrix_policies_are_exactly_default_three():
    cells = enumerate_sweep_cells(_VICTIMS_BY_SEED, _bounded_config())
    assert {c.policy for c in cells} == {
        ThresholdPolicy.GLOBAL_THRESHOLD,
        ThresholdPolicy.LOCAL_THRESHOLD,
        ThresholdPolicy.CLUSTER_THRESHOLD,
    }


def test_matrix_excludes_fraction_005():
    cells = enumerate_sweep_cells(_VICTIMS_BY_SEED, _bounded_config())
    assert all(not math.isclose(c.fraction, 0.05, abs_tol=0.0) for c in cells)


def test_matrix_fractions_are_exactly_locked_grid():
    cells = enumerate_sweep_cells(_VICTIMS_BY_SEED, _bounded_config())
    assert sorted({c.fraction for c in cells}) == pytest.approx([0.0, 0.10, 0.20, 0.40])


def test_matrix_sources_are_exactly_bounded_three():
    cells = enumerate_sweep_cells(_VICTIMS_BY_SEED, _bounded_config())
    assert {c.source for c in cells} == {
        PoisoningSourceStrategy.RANDOM_BENIGN,
        PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        PoisoningSourceStrategy.LOW_SCORE_BENIGN,
    }


def test_matrix_seed_pairs_are_exactly_the_locked_five():
    cells = enumerate_sweep_cells(_VICTIMS_BY_SEED, _bounded_config())
    pairs = {(c.training_seed, c.poisoning_seed) for c in cells}
    assert pairs == {(0, 100), (1, 101), (2, 102), (3, 103), (4, 104)}


def test_matrix_target_scope_is_always_single_client():
    cells = enumerate_sweep_cells(_VICTIMS_BY_SEED, _bounded_config())
    assert all(c.target_scope == PoisoningTargetScope.SINGLE_CLIENT for c in cells)


def test_matrix_missing_seed_raises_keyerror():
    incomplete = {0: _VICTIMS}
    with pytest.raises(KeyError):
        enumerate_sweep_cells(incomplete, _bounded_config())


# ---------------------------------------------------------------------------
# Full-scope matrix (fraction 0.05 added) — execution gated; enumeration only.
# ---------------------------------------------------------------------------


def test_full_matrix_size_is_exactly_2025():
    cells = enumerate_full_sweep_matrix(_VICTIMS_BY_SEED, _full_config())
    assert len(cells) == 5 * 9 * 3 * 3 * 5


def test_full_matrix_fractions_add_005_to_bounded_grid():
    cells = enumerate_full_sweep_matrix(_VICTIMS_BY_SEED, _full_config())
    assert sorted({c.fraction for c in cells}) == pytest.approx(
        [0.0, 0.05, 0.10, 0.20, 0.40]
    )


def test_full_matrix_superset_of_bounded_matrix():
    bounded = set(enumerate_sweep_cells(_VICTIMS_BY_SEED, _bounded_config()))
    full = set(enumerate_full_sweep_matrix(_VICTIMS_BY_SEED, _full_config()))
    assert bounded.issubset(full)
    # The only difference is the 0.05 cells.
    assert sorted({c.fraction for c in (full - bounded)}) == pytest.approx([0.05])


def test_full_matrix_keeps_all_other_locks():
    cells = enumerate_full_sweep_matrix(_VICTIMS_BY_SEED, _full_config())
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
        enumerate_full_sweep_matrix({0: _VICTIMS}, _full_config())


# ---------------------------------------------------------------------------
# Wiring tests: config fields drive enumeration, not module-level constants.
# ---------------------------------------------------------------------------


def test_enumerator_uses_config_policies_not_constants():
    """Only the policies in config appear in cells — no other policies leak in."""
    config = _full_config(policies=(ThresholdPolicy.GLOBAL_THRESHOLD,))
    cells = enumerate_full_sweep_matrix(_VICTIMS_BY_SEED, config)
    assert all(c.policy == ThresholdPolicy.GLOBAL_THRESHOLD for c in cells)
    policies_seen = {c.policy for c in cells}
    assert ThresholdPolicy.LOCAL_THRESHOLD not in policies_seen
    assert ThresholdPolicy.CLUSTER_THRESHOLD not in policies_seen


def test_enumerator_uses_config_fractions_not_constants():
    """Only the fractions in config appear in cells — no other fractions leak in."""
    config = _full_config(fractions=(0.10,))
    cells = enumerate_full_sweep_matrix(_VICTIMS_BY_SEED, config)
    assert all(math.isclose(c.fraction, 0.10) for c in cells)


def test_enumerator_uses_config_seeds_not_constants():
    """Only the seed triplet in config is iterated — length reflects pool size."""
    single_seed_pool = SeedPools(training=(0,), poisoning=(100,), analysis=(300,))
    config = _full_config(seeds=single_seed_pool)
    cells = enumerate_full_sweep_matrix(_VICTIMS_BY_SEED, config)
    # 1 seed × 9 victims × 3 policies × 3 sources × 5 fractions
    expected = (
        1
        * len(_VICTIMS)
        * len(config.policies)
        * len(config.sources)
        * len(config.fractions)
    )
    assert len(cells) == expected
    pairs = {(c.training_seed, c.poisoning_seed) for c in cells}
    assert pairs == {(0, 100)}
