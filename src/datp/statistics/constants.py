"""Statistics constants: bootstrap settings, Cliff's delta boundaries, and field enums."""

import enum

DEFAULT_CI_LEVEL: float = 0.95
BOOTSTRAP_RANDOM_STATE: int = 42
BCA_MIN_PAIRED_SEEDS: int = 3

# Cliff's delta magnitude boundaries (Romano et al., 2006).
CLIFFS_DELTA_NEGLIGIBLE = 0.147
CLIFFS_DELTA_SMALL = 0.33
CLIFFS_DELTA_MEDIUM = 0.474

EXTREME_PERCENTILE = 95
JS_LAPLACE_SMOOTHING = 1e-12
JS_BIN_EPSILON = 1e-9


class BootstrapMethod(enum.StrEnum):
    """Bootstrap confidence interval methods: percentile or bias-corrected accelerated."""

    PERCENTILE = "percentile"
    BCA = "bca"


class EffectMagnitude(enum.StrEnum):
    """Cliff's delta magnitude categories: negligible, small, medium, or large."""

    NEGLIGIBLE = "negligible"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class BootstrapField(enum.StrEnum):
    """Bootstrap CI payload keys."""

    PER_SEED_DELTAS = "per_seed_deltas"
    MEAN_DELTA = "mean_delta"
    CI_LOWER = "ci_lower"
    CI_UPPER = "ci_upper"
    CI = "ci"
    EXCLUDES_ZERO = "excludes_zero"
    N_BOOTSTRAP = "n_bootstrap"
    N_SEEDS = "n_seeds"


class StatsField(enum.StrEnum):
    """Statistics output payload keys."""

    PRIMARY_ENDPOINT = "primary_endpoint"
    HETEROGENEITY_CONTEXT_CHECK = "heterogeneity_context_check"
    CONDITION = "condition"
    GLOBAL_CV_FPR_MEAN = "global_cv_fpr_mean"
    PRACTICAL_SIGNIFICANCE_THRESHOLD = "practical_significance_threshold"
    PRACTICAL_SIGNIFICANCE_MET = "practical_significance_met"
    PRIMARY_ENDPOINT_CI_EXCLUDES_ZERO = "primary_endpoint_ci_excludes_zero"
    CONTEXT_RESULT = "context_result"
    NOTE = "note"
    PAIRED_CLIENT_FPR_POLICY = "paired_client_fpr_policy"
    WILCOXON_GLOBAL_VS_LOCAL = "wilcoxon_global_vs_local"
    CLIFFS_DELTA_GLOBAL_VS_LOCAL = "cliffs_delta_global_vs_local"
