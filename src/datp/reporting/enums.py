
from __future__ import annotations

import enum


class FigureName(enum.StrEnum):

    FIGURE_1 = "figure_1"
    FIGURE_2 = "figure_2"
    FIGURE_3 = "figure_3"
    FIGURE_5 = "figure_5"
    FIGURE_6 = "figure_6"


class FigureFileStem(enum.StrEnum):

    FIGURE_1 = "figure1_seed"
    FIGURE_2 = "figure2_ecdf"
    FIGURE_3 = "figure3_boxplots"
    FIGURE_5 = "figure5_client_effects"
    FIGURE_6 = "figure6_seed_distributions"


class ReportTerm(enum.StrEnum):

    FIXED_CLUSTER = "fixed_cluster"
    CELL = "cell"
    SEED_AGGREGATE = "seed_aggregate"


class AnalysisReportStem(enum.StrEnum):

    THRESHOLD_SHIFT_SUMMARY = "threshold_shift_summary"
    DIRECTIONAL_EXCESS_OVER_RANDOM = "directional_excess_over_random"
    RANDOM_CONTROL_INSTABILITY = "random_control_instability"
    LEAVE_ONE_VICTIM_OUT_SENSITIVITY = "leave_one_victim_out_sensitivity"
    DOWNSTREAM_HARM_RAISING = "downstream_harm_raising"
    DOWNSTREAM_HARM_LOWERING = "downstream_harm_lowering"
    CLUSTER_DIAGNOSTICS_SUMMARY = "cluster_diagnostics_summary"
    CLAIM_GATE_DECISIONS = "claim_gate_decisions"
    DOWNSTREAM_EXTENDED = "downstream_extended"
    CLIENT_LEVEL_EFFECTS = "client_level_effects"
    CLUSTER_STABILITY_SUMMARY = "cluster_stability_summary"
    DUPLICATE_AND_BOUND_SUMMARY = "duplicate_and_bound_summary"
    GATE_SENSITIVITY = "gate_sensitivity"
    CLUSTER_STABILITY_SENSITIVITY = "cluster_stability_sensitivity"
    SCALE_NORMALIZATION_SUMMARY = "scale_normalization_summary"
    DRAW_VARIANT_SUMMARY = "draw_variant_summary"
    TRUST_BOUNDARY_SUMMARY = "trust_boundary_summary"


class MechanismWording(enum.StrEnum):

    EMPIRICAL = "EMPIRICAL"
    HYPOTHESIS = "HYPOTHESIS"


class HeterogeneityContextResult(enum.StrEnum):

    PARTIAL_CONTEXT = "PARTIAL_CONTEXT"
    CONTEXT_NOT_AVAILABLE = "CONTEXT_NOT_AVAILABLE_OR_WEAK"


class ComparisonLabel(enum.StrEnum):

    GLOBAL_VS_LOCAL = "global_vs_local"
    GLOBAL_VS_CLUSTER = "global_vs_cluster"
    CLUSTER_VS_LOCAL = "cluster_vs_local"


class SidecarField(enum.StrEnum):

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
    FRACTION = "fraction"
    SEED_SELECTION_RULE = "seed_selection_rule"
    CLIENT_SELECTION_RULE = "client_selection_rule"
