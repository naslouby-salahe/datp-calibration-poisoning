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
    SECONDARY_REGIME_A = "secondary_regime_a"
    SECONDARY_REGIME_B = "secondary_regime_b"
    REGIME_C = "regime_c"
    REGIME_C_BONFERRONI = "regime_c_bonferroni_b1_vs_b2"
    HETEROGENEITY_CONTEXT_CHECK = "heterogeneity_context_check"
    CONDITION = "condition"
    B1_CV_FPR_REGIME_A_MEAN = "b1_cv_fpr_regime_a_mean"
    B1_CV_FPR_IID_MEAN = "b1_cv_fpr_iid_mean"
    NATURAL_MINUS_IID = "natural_minus_iid"
    PRACTICAL_SIGNIFICANCE_THRESHOLD = "practical_significance_threshold"
    PRACTICAL_SIGNIFICANCE_MET = "practical_significance_met"
    IID_DATA_AVAILABLE = "iid_data_available"
    PRIMARY_ENDPOINT_CI_EXCLUDES_ZERO = "primary_endpoint_ci_excludes_zero"
    CONTEXT_RESULT = "context_result"
    NOTE = "note"
    PAIRED_CLIENT_FPR_POLICY = "paired_client_fpr_policy"
    WILCOXON_B1_VS_B2 = "wilcoxon_b1_vs_b2"
    CLIFFS_DELTA_B1_VS_B2 = "cliffs_delta_b1_vs_b2"
