"""Attack-protocol constants."""

from __future__ import annotations

from datp.attacks.enums import (
    AttackerObjective,
    PoisoningSourceStrategy,
)
from datp.core.enums import ThresholdPolicy

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

NBAIOT_MAIN_SOURCE_OBJECTIVE_PAIRS: tuple[
    tuple[PoisoningSourceStrategy, AttackerObjective], ...
] = (
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
)

TRAINING_SEEDS: tuple[int, ...] = tuple(range(10))
POISONING_SEEDS: tuple[int, ...] = tuple(range(100, 110))
ANALYSIS_SEEDS: tuple[int, ...] = tuple(range(300, 310))
COMPROMISE_PATTERN_SEED: int = 400
CLUSTER_RANDOM_STATE: int = 42

# Calibration-poisoning protocol constants.
N_MIN: int = 100
TAIL_MASS: float = 0.10
MATERIALITY_FACTOR: float = 0.1
THRESHOLD_QUANTILE: float = 95.0
TRIM_FRACTION_PRIMARY: float = 0.05
TRIM_FRACTION_APPENDIX: float = 0.10
CLUSTER_K_NBAIOT: int = 3
CLUSTER_N_INIT: int = 10
CLUSTER_MAX_ITER: int = 300
EPS_NUM: float = 1e-12
DDOF_CV: int = 0  # Delta degrees of freedom for coefficient-of-variation computation

# Two-layer statistical inference protocol constants.
SIGN_CONSISTENCY_THRESHOLD: int = (
    8  # At least 8/10 seed aggregates in expected direction
)
BOOTSTRAP_CI: float = 0.95
BOOTSTRAP_N: int = 10_000
BOOTSTRAP_MIN_FINITE: int = 2
HOLM_ALPHA: float = 0.05
MU_FLAG_DIVISOR: float = 8.0  # Divisor for mu-flag threshold: CV(FPR) / MU_FLAG_DIVISOR
