from __future__ import annotations

import enum


class FigureName(enum.StrEnum):
    """Canonical identifiers for the four main paper figures."""

    FIGURE_1 = "figure_1"
    FIGURE_2 = "figure_2"
    FIGURE_3 = "figure_3"
    FIGURE_4 = "figure_4"


class MechanismWording(enum.StrEnum):
    """Spearman-based gating of mechanism language in figures and tables.

    EMPIRICAL: ρ > 0 and p < significance_alpha — observed positive association.
    HYPOTHESIS: ρ ≤ 0 or p ≥ significance_alpha — insufficient evidence; treat as hypothesis only.
    """

    EMPIRICAL = "EMPIRICAL"
    HYPOTHESIS = "HYPOTHESIS"


class HeterogeneityContextResult(enum.StrEnum):
    """Result of the heterogeneity context check."""

    CONTEXT_SUPPORTS = "CONTEXT_SUPPORTS_HETEROGENEITY"
    PARTIAL_CONTEXT = "PARTIAL_CONTEXT"
    CONTEXT_NOT_AVAILABLE = "CONTEXT_NOT_AVAILABLE_OR_WEAK"


class ComparisonLabel(enum.StrEnum):
    """Canonical baseline-comparison labels used in statistics payloads and CSV."""

    GLOBAL_VS_LOCAL = "global_vs_local"
    GLOBAL_VS_CLUSTER = "global_vs_cluster"
    CLUSTER_VS_LOCAL = "cluster_vs_local"


class SidecarField(enum.StrEnum):
    """Dict keys for figure/table sidecar JSON payloads."""

    FIGURE = "figure"
    TITLE = "title"
    DATASET = "dataset"
    STAGE = "stage"
    SEED = "seed"
    SEEDS = "seeds"
    SOURCE_METRICS_FILES = "source_metrics_files"
    SOURCE_SCORE_MANIFESTS = "source_score_manifests"
    RUN_IDS = "run_ids"
    ALPHAS = "alphas"
    ELIGIBLE_COUNTS = "eligible_counts"
    CLIENT_COUNTS = "client_counts"
    COVERAGE_RATIOS = "coverage_ratios"
    METRIC_NAMES = "metric_names"
    EVIDENCE_ROLE = "evidence_role"
    SEED_SCOPE = "seed_scope"
    NOT_CONFIRMATORY_WARNING = "not_confirmatory_warning"
    VALIDATION_STATUS = "validation_status"
    POLICIES = "policies"
    POLICY_ORDER = "policy_order"
    ELIGIBILITY_POLICY = "eligibility_policy"
    AXIS_LABELS = "axis_labels"
    CLIENTS = "clients"
    CLIENT_ID = "client_id"
    CLIENT_IDS = "client_ids"
    VALUES = "values"
    SEED_AGGREGATION_POLICY = "seed_aggregation_policy"
    PAIRED_SEED_CV_FPR_DELTA = "paired_seed_cv_fpr_delta_global_minus_local"
    TAU_GLOBAL = "tau_global"
    MAX_POINTS_PER_CLIENT = "max_points_per_client"
