"""Attack-protocol constants."""

from __future__ import annotations

from typing import TYPE_CHECKING

from datp.artifacts.poison_names import B4_K, B4_MAX_ITER, B4_N_INIT
from datp.attacks.enums import (
    AttackerObjective,
    PoisoningSourceStrategy,
    ThresholdPolicy,
)

if TYPE_CHECKING:
    from datp.config.attack_config import B4ClusterConfig

BOUNDED_SWEEP_FRACTIONS: tuple[float, ...] = (0.0, 0.10, 0.20, 0.40)
BOUNDED_SWEEP_FRACTION_SET: frozenset[float] = frozenset(BOUNDED_SWEEP_FRACTIONS)

FULL_SWEEP_FRACTIONS: tuple[float, ...] = (0.0, 0.05, 0.10, 0.20, 0.40)
FULL_SWEEP_FRACTION_SET: frozenset[float] = frozenset(FULL_SWEEP_FRACTIONS)

DEFAULT_POLICIES: tuple[ThresholdPolicy, ...] = (
    ThresholdPolicy.B1_GLOBAL,
    ThresholdPolicy.B2_PERSONALIZED,
    ThresholdPolicy.B4_CLUSTER,
)

BOUNDED_SWEEP_OBJECTIVES: tuple[AttackerObjective, ...] = (
    AttackerObjective.THRESHOLD_RAISE,
    AttackerObjective.THRESHOLD_LOWER,
)

BOUNDED_SWEEP_SOURCES: tuple[PoisoningSourceStrategy, ...] = (
    PoisoningSourceStrategy.RANDOM_BENIGN,
    PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
    PoisoningSourceStrategy.LOW_SCORE_BENIGN,
)

TRAINING_SEEDS: tuple[int, ...] = (0, 1, 2, 3, 4)
POISONING_SEEDS: tuple[int, ...] = (100, 101, 102, 103, 104)
ANALYSIS_SEEDS: tuple[int, ...] = (300, 301, 302, 303, 304)
COMPROMISE_PATTERN_SEED: int = 400
B4_RANDOM_STATE: int = 42  # for k-means only; coincidentally same as BOOTSTRAP_RANDOM_STATE


def default_b4_cluster_config() -> "B4ClusterConfig":
    from datp.config.attack_config import B4ClusterConfig

    return B4ClusterConfig(
        k=B4_K,
        n_init=B4_N_INIT,
        max_iter=B4_MAX_ITER,
        random_state=B4_RANDOM_STATE,
    )
