from __future__ import annotations

from datp.types import (
    BootstrapCount,
    ClusterCount,
    IntervalBound,
    IterationCount,
    PoisonFraction,
    Quantile,
    RandomSeed,
    SampleCount,
    ScoreValue,
    SignificanceLevel,
    SignedCount,
    Threshold,
    Tolerance,
)


from datp.attacks.enums import (
    AttackerObjective,
    PoisoningSourceStrategy,
)
from datp.core.enums import ThresholdPolicy

NBAIOT_MAIN_SWEEP_FRACTIONS: tuple[PoisonFraction, ...] = (0.0, 0.10, 0.20, 0.40)
NBAIOT_MAIN_SWEEP_FRACTION_SET: frozenset[PoisonFraction] = frozenset(
    NBAIOT_MAIN_SWEEP_FRACTIONS
)

NBAIOT_FULL_OPTIONAL_SWEEP_FRACTIONS: tuple[PoisonFraction, ...] = (
    0.0,
    0.05,
    0.10,
    0.20,
    0.40,
)
NBAIOT_FULL_OPTIONAL_SWEEP_FRACTION_SET: frozenset[PoisonFraction] = frozenset(
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

TRAINING_SEEDS: tuple[RandomSeed, ...] = tuple(RandomSeed(seed) for seed in range(10))
POISONING_SEEDS: tuple[RandomSeed, ...] = tuple(
    RandomSeed(seed) for seed in range(100, 110)
)
ANALYSIS_SEEDS: tuple[RandomSeed, ...] = tuple(
    RandomSeed(seed) for seed in range(300, 310)
)
CLUSTER_RANDOM_STATE: RandomSeed = RandomSeed(42)

N_MIN: SampleCount = 100
TAIL_MASS: PoisonFraction = 0.10
MATERIALITY_FACTOR: ScoreValue = 0.1
THRESHOLD_QUANTILE: Threshold = 95.0
TRIM_FRACTION_PRIMARY: PoisonFraction = 0.05
TRIM_FRACTION_APPENDIX: PoisonFraction = 0.10
CLUSTER_K_NBAIOT: ClusterCount = 3
CLUSTER_N_INIT: IterationCount = 10
CLUSTER_MAX_ITER: IterationCount = 300
EPS_NUM: Tolerance = 1e-12
SIGN_CONSISTENCY_THRESHOLD: SignedCount = (
    8  # At least 8/10 seed aggregates in expected direction
)
BOOTSTRAP_CI: IntervalBound = 0.95
BOOTSTRAP_N: BootstrapCount = 10_000
BOOTSTRAP_MIN_FINITE: BootstrapCount = 2
HOLM_ALPHA: SignificanceLevel = 0.05
MU_FLAG_DIVISOR: ScoreValue = 8.0
VICTIM_MAJORITY_THRESHOLD: SignedCount = 5
IQR_FLOOR_FACTOR: ScoreValue = 0.01

SENSITIVITY_SIGN_CONSISTENCY_GRID: tuple[SignedCount, ...] = (6, 7, 8, 9, 10)
SENSITIVITY_VICTIM_MAJORITY_GRID: tuple[SignedCount, ...] = (3, 4, 5, 6, 7)
SENSITIVITY_MATERIALITY_GRID: tuple[ScoreValue, ...] = (0.05, 0.1, 0.2)
SENSITIVITY_IQR_FLOOR_GRID: tuple[ScoreValue, ...] = (0.005, 0.01, 0.02)

CLUSTER_SENSITIVITY_K_GRID: tuple[SignedCount, ...] = (2, 3, 4)
CLUSTER_SENSITIVITY_N_INIT_GRID: tuple[IterationCount, ...] = (1, 10)
CLUSTER_SENSITIVITY_RANDOM_STATES: tuple[RandomSeed, ...] = tuple(
    RandomSeed(seed) for seed in (0, 1, 7, 42, 123)
)
CLUSTER_SENSITIVITY_FRACTIONS: tuple[PoisonFraction, ...] = (0.10, 0.20, 0.40)
DRAW_VARIANT_FRACTIONS: tuple[PoisonFraction, ...] = (0.10, 0.20, 0.40)

SCALE_NORMALIZATION_STATISTIC_QUANTILE: Quantile = 50.0
PERMUTATION_MAX_EXACT_SEEDS: RandomSeed = RandomSeed(16)
