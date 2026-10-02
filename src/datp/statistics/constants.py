from datp.types import SeedCount

import enum

BCA_MIN_PAIRED_SEEDS: SeedCount = 3

# Cliff's delta magnitude boundaries (Romano et al., 2006).
CLIFFS_DELTA_NEGLIGIBLE = 0.147
CLIFFS_DELTA_SMALL = 0.33
CLIFFS_DELTA_MEDIUM = 0.474

EXTREME_PERCENTILE = 95
JS_LAPLACE_SMOOTHING = 1e-12
JS_BIN_EPSILON = 1e-9


class BootstrapMethod(enum.StrEnum):

    PERCENTILE = "percentile"
    BCA = "bca"


class EffectMagnitude(enum.StrEnum):

    NEGLIGIBLE = "negligible"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class BootstrapField(enum.StrEnum):

    SCOPE = "scope"
    COMPARISON = "comparison"
    PER_SEED_DELTAS = "per_seed_deltas"
    MEAN_DELTA = "mean_delta"
    CI_LOWER = "ci_lower"
    CI_UPPER = "ci_upper"
    CI = "ci"
    EXCLUDES_ZERO = "excludes_zero"
    N_BOOTSTRAP = "n_bootstrap"
    N_SEEDS = "n_seeds"


class StatsField(enum.StrEnum):

    PRIMARY_ENDPOINT = "primary_endpoint"
    SECONDARY_NBAIOT = "secondary_nbaiot"
    SECONDARY_NBAIOT_ADDITIONAL = "secondary_nbaiot_additional"
    HETEROGENEITY_CONTEXT_CHECK = "heterogeneity_context_check"
    CONDITION = "condition"
    GLOBAL_CV_FPR_MEAN = "global_cv_fpr_mean"
    PRACTICAL_SIGNIFICANCE_THRESHOLD = "practical_significance_threshold"
    PRACTICAL_SIGNIFICANCE_MET = "practical_significance_met"
    PRIMARY_ENDPOINT_CI_EXCLUDES_ZERO = "primary_endpoint_ci_excludes_zero"
    CONTEXT_RESULT = "context_result"
    NOTE = "note"
