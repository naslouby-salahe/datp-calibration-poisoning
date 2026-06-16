from __future__ import annotations

import enum


class DeviceType(enum.StrEnum):
    """Torch device types — canonical enum for all device resolution."""

    CUDA = "cuda"
    CPU = "cpu"


class BootstrapMethod(enum.StrEnum):
    PERCENTILE = "percentile"
    BCA = "bca"


class EffectMagnitude(enum.StrEnum):
    NEGLIGIBLE = "negligible"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class Baseline(enum.StrEnum):
    B0 = "b0"
    B1 = "b1"
    B2 = "b2"
    B3 = "b3"
    B4 = "b4"


class Regime(enum.StrEnum):
    A = "a"
    B = "b"
    C = "c"


class ClientStatus(enum.StrEnum):
    ELIGIBLE = "eligible"
    CALIBRATION_PENDING = "calibration_pending"


class BaselineRunStatus(enum.StrEnum):
    """Outcome of a single baseline run within a sweep cell."""

    DONE = "done"
    SKIPPED = "skipped"
    FAILED = "failed"


class ThresholdAggregationMethod(enum.StrEnum):
    ELIGIBLE_CLIENT_ARITHMETIC_MEAN = "eligible_client_arithmetic_mean"
    PER_CLIENT_PERCENTILE = "per_client_percentile"
    ELIGIBLE_FAMILY_ARITHMETIC_MEAN = "eligible_family_arithmetic_mean"
    ELIGIBLE_CLUSTER_ARITHMETIC_MEAN = "eligible_cluster_arithmetic_mean"
    POOLED_PERCENTILE = "pooled_percentile"


class ThresholdSource(enum.StrEnum):
    """Identifies the calibration scope for a threshold.

    Values intentionally mirror Baseline names — each baseline has a canonical
    ThresholdSource. See BASELINE_THRESHOLD_SOURCE mapping for the relationship.
    """

    B0_POOLED = "pooled_percentile"
    B1_SHARED = "b1"
    B2_PER_CLIENT = "b2"
    B3_FAMILY = "b3"
    B4_CLUSTER = "b4"
    TAU_GLOBAL_FALLBACK = "tau_global_fallback"


class NormalizationScope(enum.StrEnum):
    GLOBAL = "global"
    PER_CLIENT = "per_client"
    PER_CLIENT_ZSCORE = "per_client_zscore"
    POOLED_ZSCORE = "pooled_zscore"


class PipelineStage(enum.StrEnum):
    PREPARE = "prepare"
    TRAIN = "train"
    SCORE = "score"
    THRESHOLD = "threshold"
    EVALUATE = "evaluate"
    REPORT = "report"


class Activation(enum.StrEnum):
    """Autoencoder activation functions — canonical enum for all model configs."""

    RELU = "relu"
    LEAKY_RELU = "leaky_relu"
    ELU = "elu"
    TANH = "tanh"
    SIGMOID = "sigmoid"


class B0NormalizationMode(enum.StrEnum):
    PER_CLIENT_PREPARED = "per_client_prepared"
    POOLED_ZSCORE = "pooled_zscore"


class B4RegimeAMode(enum.StrEnum):
    """B4 cluster-count selection mode for Regime A.

    FIXED uses the configured ``b4_k_regime_a``; SILHOUETTE selects K via
    silhouette score over the candidate Ks.
    """

    FIXED = "fixed"
    SILHOUETTE = "silhouette"


class BaselineRole(enum.StrEnum):
    CONTROLLED_THRESHOLD = "controlled_threshold"
    CENTRALIZED_REFERENCE = "centralized_reference"


class ScoringStage(enum.StrEnum):
    CAL = "cal"
    TEST_BENIGN = "test_benign"
    TEST_ATTACK = "test_attack"

    @property
    def client_data_attr(self) -> str:
        """Attribute name on ``ClientData`` that holds this stage's tensor."""
        if self == ScoringStage.CAL:
            return "val"
        return self.value

    @classmethod
    def all(cls) -> tuple["ScoringStage", ...]:
        return tuple(cls)


SCORING_STAGES: tuple[ScoringStage, ...] = ScoringStage.all()


class AbsorptionClass(enum.StrEnum):
    """Absorption ratio classification per scientific protocol.

    Ratio = Δ_personalized / Δ_FedAvg where each Δ = CV(FPR)[B1] − CV(FPR)[B2].
    """

    STRONG_RETENTION = "strong_retention"
    PARTIAL = "partial"
    NEAR_FULL = "near_full"


def classify_absorption(
    ratio: float,
    *,
    strong_retention_threshold: float,
    partial_threshold: float,
) -> AbsorptionClass:
    """Classify absorption ratio into the locked categories.

    Thresholds are config-driven — read from
    ``ExperimentConfig.absorption_strong_retention`` and
    ``ExperimentConfig.absorption_partial``. Do not hardcode.
    """
    if ratio >= strong_retention_threshold:
        return AbsorptionClass.STRONG_RETENTION
    if ratio >= partial_threshold:
        return AbsorptionClass.PARTIAL
    return AbsorptionClass.NEAR_FULL





# Derived maps — do not duplicate in other modules; import from here.

REGIME_BASELINES: dict[Regime, frozenset[Baseline]] = {
    Regime.A: frozenset(
        {Baseline.B0, Baseline.B1, Baseline.B2, Baseline.B3, Baseline.B4}
    ),
    Regime.B: frozenset({Baseline.B0, Baseline.B1, Baseline.B2, Baseline.B4}),
    Regime.C: frozenset({Baseline.B1, Baseline.B2, Baseline.B4}),
}

MAIN_BODY_BASELINES: frozenset[Baseline] = frozenset(
    {
        Baseline.B0,
        Baseline.B1,
        Baseline.B2,
        Baseline.B3,
        Baseline.B4,
    }
)

ISOLATED_BASELINES: frozenset[Baseline] = frozenset({Baseline.B0})

THRESHOLD_AGGREGATION_BY_BASELINE: dict[Baseline, ThresholdAggregationMethod] = {
    Baseline.B0: ThresholdAggregationMethod.POOLED_PERCENTILE,
    Baseline.B1: ThresholdAggregationMethod.ELIGIBLE_CLIENT_ARITHMETIC_MEAN,
    Baseline.B2: ThresholdAggregationMethod.PER_CLIENT_PERCENTILE,
    Baseline.B3: ThresholdAggregationMethod.ELIGIBLE_FAMILY_ARITHMETIC_MEAN,
    Baseline.B4: ThresholdAggregationMethod.ELIGIBLE_CLUSTER_ARITHMETIC_MEAN,
}

BASELINE_THRESHOLD_SOURCE: dict[Baseline, ThresholdSource] = {
    Baseline.B0: ThresholdSource.B0_POOLED,
    Baseline.B1: ThresholdSource.B1_SHARED,
    Baseline.B2: ThresholdSource.B2_PER_CLIENT,
    Baseline.B3: ThresholdSource.B3_FAMILY,
    Baseline.B4: ThresholdSource.B4_CLUSTER,
}

BASELINE_ROLE: dict[Baseline, BaselineRole] = {
    Baseline.B0: BaselineRole.CENTRALIZED_REFERENCE,
    Baseline.B1: BaselineRole.CONTROLLED_THRESHOLD,
    Baseline.B2: BaselineRole.CONTROLLED_THRESHOLD,
    Baseline.B3: BaselineRole.CONTROLLED_THRESHOLD,
    Baseline.B4: BaselineRole.CONTROLLED_THRESHOLD,
}

# Threshold ladder — the four controlled baselines being compared.
# B0 is a centralized reference, not part of the ladder.
# B5 is a local-only ablation, not part of the ladder.
CONTROLLED_BASELINES: tuple[Baseline, ...] = (
    Baseline.B1,
    Baseline.B2,
    Baseline.B3,
    Baseline.B4,
)

# B4 fingerprint feature order: locked per scientific contract.
# Locked per scientific protocol — do not reorder.
B4_FINGERPRINT_FEATURES: tuple[str, ...] = ("mean", "std", "skew", "p95")


class MetricName(enum.StrEnum):
    FPR = "fpr"
    TPR = "tpr"
    TNR = "tnr"
    FNR = "fnr"
    PRECISION = "precision"
    RECALL = "recall"
    MACRO_F1 = "macro_f1"
    BALANCED_ACCURACY = "balanced_accuracy"
    AUROC = "auroc"
    PR_AUC = "pr_auc"
    CV_FPR = "cv_fpr"
    CV_TPR = "cv_tpr"
    MEAN_FPR = "mean_fpr"
    STD_FPR = "std_fpr"
    IQR_FPR = "iqr_fpr"
    IQR_TPR = "iqr_tpr"
    WORST_CLIENT_FPR = "worst_client_fpr"
    WORST_BA = "worst_ba"
    P10_MACRO_F1 = "p10_macro_f1"
    WORST_CLIENT_TPR = "worst_client_tpr"
    WORST_CLIENT_MACRO_F1 = "worst_client_macro_f1"
    WORST_CLIENT_BALANCED_ACCURACY = "worst_client_balanced_accuracy"
    MAX_MIN_FPR_GAP = "max_min_fpr_gap"
    TAU_GLOBAL = "tau_global"
    WORST_CLIENT_ID = "worst_client_id"


class PayloadKey(enum.StrEnum):
    CLIENT_ID = "client_id"
    PER_CLIENT = "per_client"
    CONFUSION_MATRIX = "confusion_matrix"
    BASELINE = "baseline"
    REGIME = "regime"
    SEED = "seed"
    ALPHA = "alpha"
    JS_DIVERGENCE = "js_divergence"
    COVERAGE_RATIO = "coverage_ratio"
    DATASET = "dataset"
    ELIGIBLE_COUNT = "eligible_count"
    PENDING_COUNT = "pending_count"
    CLIENT_COUNT = "client_count"
    ELIGIBLE_IDS = "eligible_ids"
    PENDING_IDS = "pending_ids"
    EVAL_INCOMPLETE_COUNT = "eval_incomplete_count"
    EVAL_INCOMPLETE_IDS = "eval_incomplete_ids"
    THRESHOLD_VALUE = "threshold_value"
    THRESHOLD_SOURCE = "threshold_source"
    N_BENIGN = "n_benign"
    N_ATTACK = "n_attack"
    CALIBRATION_PENDING = "calibration_pending"
    EVALUATION_INCOMPLETE = "evaluation_incomplete"
    RUN_KIND = "run_kind"
    RUN_ID = "run_id"
    SCHEMA_VERSION = "schema_version"
    METRIC_SCHEMA_VERSION = "metric_schema_version"
    THRESHOLD_SCHEMA_VERSION = "threshold_schema_version"
    THRESHOLD_SCOPE = "threshold_scope"
    THRESHOLD_STRATEGY_NAME = "threshold_strategy_name"
    AGGREGATE_METRICS = "aggregate_metrics"
    PROVENANCE = "provenance"
    NORMALIZATION_SCOPE = "normalization_scope"
    NORMALIZATION_MODE = "normalization_mode"
    TAU_B0 = "tau_b0"
    # Provenance sub-keys
    CONFIG_IDENTITY = "config_identity"
    SPLIT_MANIFEST_IDENTITY = "split_manifest_identity"
    MODEL_CHECKPOINT_IDENTITY = "model_checkpoint_identity"
    SCORE_ARTIFACT_IDENTITY = "score_artifact_identity"
    METRIC_CODE_VERSION = "metric_code_version"
    THRESHOLD_CODE_VERSION = "threshold_code_version"
    PACKAGE_VERSION = "package_version"
    GENERATED_AT_UTC = "generated_at_utc"


class ConfusionKey(enum.StrEnum):
    TP = "tp"
    FP = "fp"
    TN = "tn"
    FN = "fn"


class RunKind(enum.StrEnum):
    CORE_LADDER = "core_ladder"
    STRESS_TEST = "stress_test"
    CENTRALIZED_REFERENCE = "centralized_reference"
    COMPARATOR = "comparator"


def controlled_baselines_for_regime(regime: Regime) -> tuple[Baseline, ...]:
    """Return controlled threshold-ladder baselines for a regime.

    B3 (family threshold) applies only in Regime A (N-BaIoT device families).
    """
    if regime == Regime.A:
        return CONTROLLED_BASELINES
    return tuple(b for b in CONTROLLED_BASELINES if b != Baseline.B3)


class ConvergenceStatus(enum.StrEnum):
    CONVERGED = "converged"
    NOT_CONVERGED = "not_converged"
    UNKNOWN = "unknown"
    BLOCKED_PENDING_RUN = "BLOCKED_PENDING_RUN"
    MISSING_CHECKPOINT = "MISSING_CHECKPOINT"


class CheckpointProtocolMode(enum.StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class CheckpointConvergenceMode(enum.StrEnum):
    LOG_ONLY = "log_only"
    EARLY_STOP = "early_stop"


class PrimaryCheckpointSelectionRule(enum.StrEnum):
    GLOBAL_LOWER_TAIL_TRADEOFF_FROM_REGIME_A = "global_lower_tail_tradeoff_from_regime_a"


class CheckpointArtifactPathMode(enum.StrEnum):
    ROUND_AWARE = "round_aware"


class CheckpointArtifactStatus(enum.StrEnum):
    PRESENT = "present"
    MISSING = "missing"
    INVALID = "invalid"
    SUPPRESSED = "suppressed"


class CheckpointSelectionVerdict(enum.StrEnum):
    SELECTED = "selected"
    REJECTED = "rejected"


class ConvergenceSummaryKey(enum.StrEnum):
    """Canonical keys for the convergence summary JSON artifact.

    Shared by the producer (federated/checkpoints.py) and consumer
    (validation/convergence.py).
    """

    ROUNDS_INITIAL = "rounds_initial"
    ROUNDS_MAX = "rounds_max"
    RELATIVE_THRESHOLD = "relative_threshold"
    WINDOW = "window"
    ACTUAL_ROUNDS = "actual_rounds_run"
    CONVERGENCE_ROUND = "convergence_round"
    CONVERGENCE_CRITERION = "convergence_criterion_value"
    CONVERGENCE_STATUS = "convergence_status"
    WEIGHTED_LOSS = "weighted_validation_loss_per_round"


class EvidenceRole(enum.StrEnum):
    """Scientific evidence role for a figure or analysis result."""

    DESCRIPTIVE = "descriptive"
    DESCRIPTIVE_WITH_CONFIRMATORY_SIDECAR_DELTA = (
        "descriptive_with_confirmatory_sidecar_delta"
    )
    SECONDARY = "secondary"


class SeedScope(enum.StrEnum):
    """Which seeds a figure or result covers."""

    REPRESENTATIVE_SEED = "representative_seed"
    ALL_SEED = "all_seed"


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
    """Result of the heterogeneity context check for Regime A primary endpoint.

    Evaluates whether the Regime C IID comparison and the primary B1-minus-B2
    bootstrap CI together provide supporting context for the heterogeneity narrative.
    """

    CONTEXT_SUPPORTS = "CONTEXT_SUPPORTS_HETEROGENEITY"
    PARTIAL_CONTEXT = "PARTIAL_CONTEXT"
    CONTEXT_NOT_AVAILABLE = "CONTEXT_NOT_AVAILABLE_OR_WEAK"


class ComparisonLabel(enum.StrEnum):
    """Canonical baseline-comparison labels used in statistics payloads and CSV."""

    B1_VS_B2 = "b1_vs_b2"
    B1_VS_B4 = "b1_vs_b4"
    B4_VS_B2 = "b4_vs_b2"


class SidecarField(enum.StrEnum):
    """Dict keys for figure/table sidecar JSON payloads."""

    FIGURE = "figure"
    TITLE = "title"
    DATASET = "dataset"
    REGIME = "regime"
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
    BASELINES = "baselines"
    BASELINE_ORDER = "baseline_order"
    ELIGIBILITY_POLICY = "eligibility_policy"
    AXIS_LABELS = "axis_labels"
    CLIENTS = "clients"
    CLIENT_ID = "client_id"
    CLIENT_IDS = "client_ids"
    VALUES = "values"
    SEED_AGGREGATION_POLICY = "seed_aggregation_policy"
    PAIRED_SEED_CV_FPR_DELTA = "paired_seed_cv_fpr_delta_b1_minus_b2"
    TAU_GLOBAL = "tau_global"
    MAX_POINTS_PER_CLIENT = "max_points_per_client"


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


class AuditField(enum.StrEnum):
    """Dict keys for reporting audit output payload."""

    SCHEMA_VERSION = "schema_version"
    GENERATED_TABLES = "generated_tables"
    GENERATED_FIGURES = "generated_figures"
    SOURCE_METRICS_FILES = "source_metrics_files"
    SOURCE_SCORE_MANIFESTS = "source_score_manifests"
    SOURCE_RUN_IDS = "source_run_ids_or_artifact_paths"
    VALIDATION_RESULTS = "validation_results"
    RECOMPUTATION_CHECKS = "recomputation_checks"
    COVERAGE_CHECKS = "coverage_checks"
    MISSING_FIELD_CHECKS = "missing_field_checks"
    STALE_ARTIFACT_CHECKS = "stale_artifact_checks"
    DESCRIPTIVE_FIGURE_CHECKS = "descriptive_figure_checks"
    CONVERGENCE_METADATA_CHECKS = "convergence_metadata_checks"
    FIGURE_TABLE_OUTPUT_PATHS = "figure_table_output_paths"
    WARNINGS = "warnings"
    FAILURES = "failures"


class ValidationField(enum.StrEnum):
    """Dict keys for metrics schema validation payload."""

    STATUS = "status"
    SOURCE = "source"
    VALIDATED_REGIMES = "validated_regimes"
    SEEDS = "seeds"
    REGIME_C_ALPHAS = "regime_c_alphas"


# Baselines used for statistical comparisons per regime.
# Excludes isolated B0; excludes B3 in Regime A (family threshold, not part of the
# causal B1/B2/B4 ladder comparisons).
STATS_REPORTING_BASELINES: dict[Regime, frozenset[Baseline]] = {
    Regime.A: REGIME_BASELINES[Regime.A] - ISOLATED_BASELINES - {Baseline.B3},
    Regime.B: REGIME_BASELINES[Regime.B] - ISOLATED_BASELINES,
    Regime.C: REGIME_BASELINES[Regime.C] - ISOLATED_BASELINES,
}
