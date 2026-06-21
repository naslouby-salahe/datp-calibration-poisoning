from __future__ import annotations

import enum


class BootstrapMethod(enum.StrEnum):
    PERCENTILE = "percentile"
    BCA = "bca"


class EffectMagnitude(enum.StrEnum):
    NEGLIGIBLE = "negligible"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class BootstrapField(enum.StrEnum):
    """Dict keys for bootstrap CI payloads."""

    PER_SEED_DELTAS = "per_seed_deltas"
    MEAN_DELTA = "mean_delta"
    CI_LOWER = "ci_lower"
    CI_UPPER = "ci_upper"
    CI = "ci"
    EXCLUDES_ZERO = "excludes_zero"
    N_BOOTSTRAP = "n_bootstrap"
    N_SEEDS = "n_seeds"


class StatsField(enum.StrEnum):
    """Dict keys for statistics (bootstrap CI) output payload."""

    PRIMARY_ENDPOINT = "primary_endpoint"
    HETEROGENEITY_CONTEXT_CHECK = "heterogeneity_context_check"
    CONDITION = "condition"
    GLOBAL_CV_FPR_MEAN = "global_cv_fpr_mean"
    NATURAL_MINUS_IID = "natural_minus_iid"
    PRACTICAL_SIGNIFICANCE_THRESHOLD = "practical_significance_threshold"
    PRACTICAL_SIGNIFICANCE_MET = "practical_significance_met"
    IID_DATA_AVAILABLE = "iid_data_available"
    PRIMARY_ENDPOINT_CI_EXCLUDES_ZERO = "primary_endpoint_ci_excludes_zero"
    CONTEXT_RESULT = "context_result"
    NOTE = "note"
    PAIRED_CLIENT_FPR_POLICY = "paired_client_fpr_policy"
    WILCOXON_GLOBAL_VS_LOCAL = "wilcoxon_global_vs_local"
    CLIFFS_DELTA_GLOBAL_VS_LOCAL = "cliffs_delta_global_vs_local"
