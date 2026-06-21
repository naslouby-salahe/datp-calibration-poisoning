"""Attack-protocol constants."""

from __future__ import annotations

from typing import TYPE_CHECKING

from datp.artifacts.poison_names import (
    CLUSTER_K_NBAIOT,
    CLUSTER_MAX_ITER,
    CLUSTER_N_INIT,
)
from datp.attacks.enums import (
    AttackerObjective,
    PoisoningSourceStrategy,
    ThresholdPolicy,
)

if TYPE_CHECKING:
    from datp.config.attack_config import ClusterConfig

NBAIOT_MAIN_SWEEP_FRACTIONS: tuple[float, ...] = (0.0, 0.10, 0.20, 0.40)
NBAIOT_MAIN_SWEEP_FRACTION_SET: frozenset[float] = frozenset(
    NBAIOT_MAIN_SWEEP_FRACTIONS
)

NBAIOT_FULL_OPTIONAL_SWEEP_FRACTIONS: tuple[float, ...] = (
    0.0,
    0.05,
    0.10,
    0.20,
    0.40,
)
NBAIOT_FULL_OPTIONAL_SWEEP_FRACTION_SET: frozenset[float] = frozenset(
    NBAIOT_FULL_OPTIONAL_SWEEP_FRACTIONS
)

DEFAULT_POLICIES: tuple[ThresholdPolicy, ...] = (
    ThresholdPolicy.GLOBAL_THRESHOLD,
    ThresholdPolicy.LOCAL_THRESHOLD,
    ThresholdPolicy.CLUSTER_THRESHOLD,
)

NBAIOT_MAIN_SWEEP_OBJECTIVES: tuple[AttackerObjective, ...] = (
    AttackerObjective.THRESHOLD_RAISE,
    AttackerObjective.THRESHOLD_LOWER,
)

NBAIOT_MAIN_SWEEP_SOURCES: tuple[PoisoningSourceStrategy, ...] = (
    PoisoningSourceStrategy.RANDOM_BENIGN,
    PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
    PoisoningSourceStrategy.LOW_SCORE_BENIGN,
)

TRAINING_SEEDS: tuple[int, ...] = (0, 1, 2, 3, 4)
POISONING_SEEDS: tuple[int, ...] = (100, 101, 102, 103, 104)
ANALYSIS_SEEDS: tuple[int, ...] = (300, 301, 302, 303, 304)
COMPROMISE_PATTERN_SEED: int = 400
CLUSTER_RANDOM_STATE: int = (
    42  # for k-means only; coincidentally same as BOOTSTRAP_RANDOM_STATE
)


def default_cluster_config() -> "ClusterConfig":
    from datp.config.attack_config import ClusterConfig

    return ClusterConfig(
        k=CLUSTER_K_NBAIOT,
        n_init=CLUSTER_N_INIT,
        max_iter=CLUSTER_MAX_ITER,
        random_state=CLUSTER_RANDOM_STATE,
    )
