from __future__ import annotations

import enum
from collections.abc import Mapping, Sequence


class DatasetID(enum.StrEnum):

    NBAIOT = "nbaiot"


class NBaIoTDevice(enum.StrEnum):

    DANMINI_DOORBELL = "Danmini_Doorbell"
    ECOBEE_THERMOSTAT = "Ecobee_Thermostat"
    ENNIO_DOORBELL = "Ennio_Doorbell"
    PHILIPS_B120N10_BABY_MONITOR = "Philips_B120N10_Baby_Monitor"
    PROVISION_PT_737E_SECURITY_CAMERA = "Provision_PT_737E_Security_Camera"
    PROVISION_PT_838_SECURITY_CAMERA = "Provision_PT_838_Security_Camera"
    SAMSUNG_SNH_1011_N_WEBCAM = "Samsung_SNH_1011_N_Webcam"
    SIMPLEHOME_XCS7_1002_WHT_SECURITY_CAMERA = "SimpleHome_XCS7_1002_WHT_Security_Camera"
    SIMPLEHOME_XCS7_1003_WHT_SECURITY_CAMERA = "SimpleHome_XCS7_1003_WHT_Security_Camera"


class NBaIoTDeviceFamily(enum.StrEnum):

    DOORBELL = "doorbell"
    CAMERA = "camera"
    OTHER = "other"


class NBaIoTAttackFamily(enum.StrEnum):

    GAFGYT = "gafgyt_attacks"
    MIRAI = "mirai_attacks"


class NBaIoTBalancePolicy(enum.StrEnum):

    NATURAL_DISTRIBUTION = "natural_distribution"
    BALANCED = "balanced"


class ThresholdPolicy(enum.StrEnum):

    GLOBAL_THRESHOLD = "global_threshold"
    LOCAL_THRESHOLD = "local_threshold"
    CLUSTER_THRESHOLD = "cluster_threshold"


class DeviceType(enum.StrEnum):

    CUDA = "cuda"
    CPU = "cpu"


class LogLevel(enum.StrEnum):

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ArtifactFile(enum.StrEnum):

    BENIGN_TRAFFIC = "benign_traffic.csv"
    SCORING_SENTINEL = "SCORING_DONE.txt"
    SCORING_MANIFEST = "scoring_manifest.json"
    METRICS = "metrics.json"
    NBAIOT_MAIN_MANIFEST = "nbaiot_main_manifest.json"
    SENSITIVITY_MANIFEST = "sensitivity_manifest.json"
    REPORTING_AUDIT = "reporting_audit.json"
    BOOTSTRAP_CIS_JSON = "bootstrap_cis.json"
    BOOTSTRAP_CIS_CSV = "bootstrap_cis.csv"
    METRICS_SCHEMA_VALIDATION = "metrics_schema_validation.json"
    SCALER = "scaler.pkl"
    MANIFEST = "manifest.json"
    LOG = "datp.log"
    CONVERGENCE_CURVE = "convergence_curve.csv"
    CONVERGENCE_SUMMARY = "convergence_summary.json"
    RUN_IN_PROGRESS = "IN_PROGRESS"
    RUN_DONE = "DONE.txt"
    RUN_ABORTED = "ABORTED.txt"
    RESOLVED_CONFIG = "resolved_config.yaml"


class PathToken(enum.StrEnum):

    PARQUET_EXT = ".parquet"
    PARQUET_GLOB = "*.parquet"
    CSV_EXT = ".csv"
    PDF_EXT = ".pdf"
    PNG_EXT = ".png"
    TEX_EXT = ".tex"
    JSON_EXT = ".json"
    CSV_GLOB = "*.csv"
    SEED_PREFIX = "seed_"


class ClientStatus(enum.StrEnum):

    ELIGIBLE = "eligible"
    CALIBRATION_PENDING = "calibration_pending"


class ThresholdAggregationMethod(enum.StrEnum):

    ELIGIBLE_CLIENT_ARITHMETIC_MEAN = "eligible_client_arithmetic_mean"
    PER_CLIENT_PERCENTILE = "per_client_percentile"
    ELIGIBLE_CLUSTER_ARITHMETIC_MEAN = "eligible_cluster_arithmetic_mean"


class ThresholdSource(enum.StrEnum):

    GLOBAL = "global"
    LOCAL = "local"
    CLUSTER = "cluster"
    TAU_GLOBAL_FALLBACK = "tau_global_fallback"


class ProvenanceSentinel(enum.StrEnum):

    UNKNOWN = "UNKNOWN"
    UNKNOWN_LOWERCASE = "unknown"
    MISSING_MANIFEST_HASH = "MISSING_MANIFEST_HASH"


class PayloadValidationErrorType(enum.StrEnum):

    MISSING = "missing"


class Activation(enum.StrEnum):

    RELU = "relu"
    LEAKY_RELU = "leaky_relu"
    ELU = "elu"
    TANH = "tanh"
    SIGMOID = "sigmoid"


class ClientDataAttribute(enum.StrEnum):

    VAL = "val"
    TEST_BENIGN = "test_benign"
    TEST_ATTACK = "test_attack"


class ScoringStage(enum.StrEnum):

    CAL = "cal"
    TEST_BENIGN = "test_benign"
    TEST_ATTACK = "test_attack"

    @property
    def client_data_attr(self) -> ClientDataAttribute:
        if self is ScoringStage.CAL:
            return ClientDataAttribute.VAL
        if self is ScoringStage.TEST_BENIGN:
            return ClientDataAttribute.TEST_BENIGN
        return ClientDataAttribute.TEST_ATTACK

    @classmethod
    def all(cls) -> tuple["ScoringStage", ...]:
        return tuple(cls)


class MetricName(enum.StrEnum):

    FPR = "fpr"
    TPR = "tpr"
    MACRO_F1 = "macro_f1"
    BALANCED_ACCURACY = "balanced_accuracy"
    AUROC = "auroc"
    PR_AUC = "pr_auc"
    CV_FPR = "cv_fpr"
    CV_TPR = "cv_tpr"
    CV_FPR_DELTA_GLOBAL_MINUS_LOCAL = "cv_fpr_delta_global_minus_local"
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
    MACRO_F1_MEAN = "macro_f1_mean"
    MACRO_F1_P10 = "macro_f1_p10"
    AUROC_MEAN = "auroc_mean"
    PR_AUC_MEAN = "pr_auc_mean"
    CONVERGENCE_ROUND = "convergence_round"
    MAX_MIN_FPR_GAP = "max_min_fpr_gap"
    TAU_GLOBAL = "tau_global"
    WORST_CLIENT_ID = "worst_client_id"
    VICTIM_DELTA_TAU = "delta_tau"
    VICTIM_DELTA_TPR = "victim_delta_tpr"
    VICTIM_DELTA_FPR = "victim_delta_fpr"
    VICTIM_DELTA_FN = "victim_delta_fn"
    VICTIM_DELTA_FP = "victim_delta_fp"
    VICTIM_DELTA_BA = "victim_delta_ba"
    VICTIM_DELTA_MACRO_F1 = "victim_delta_macro_f1"
    NONVICTIM_MEAN_DELTA_TPR = "nonvictim_mean_delta_tpr"
    NONVICTIM_WORST_DELTA_TPR = "nonvictim_worst_delta_tpr"
    NONVICTIM_MEAN_DELTA_FPR = "nonvictim_mean_delta_fpr"
    NONVICTIM_WORST_DELTA_FPR = "nonvictim_worst_delta_fpr"
    NONVICTIM_MEAN_DELTA_BA = "nonvictim_mean_delta_ba"
    NONVICTIM_MEAN_DELTA_MACRO_F1 = "nonvictim_mean_delta_macro_f1"
    NONVICTIM_DELTA_FN_TOTAL = "nonvictim_delta_fn_total"
    NONVICTIM_DELTA_FP_TOTAL = "nonvictim_delta_fp_total"
    DELTA_MEAN_FPR = "delta_mean_fpr"
    DELTA_CV_FPR = "delta_cv_fpr"
    DELTA_IQR_FPR = "delta_iqr_fpr"
    DELTA_MAX_MIN_FPR = "delta_max_min_fpr"
    DELTA_WORST_CLIENT_FPR = "delta_worst_client_fpr"
    FIXED_CLUSTER_VICTIM_DELTA_TAU = "fixed_cluster_victim_delta_tau"
    FIXED_CLUSTER_VICTIM_DELTA_TPR = "fixed_cluster_victim_delta_tpr"
    FIXED_CLUSTER_VICTIM_DELTA_FPR = "fixed_cluster_victim_delta_fpr"
    FIXED_CLUSTER_DELTA_CV_FPR = "fixed_cluster_delta_cv_fpr"
    FIXED_CLUSTER_DELTA_MEAN_FPR = "fixed_cluster_delta_mean_fpr"
    FIXED_CLUSTER_NONVICTIM_MEAN_DELTA_TPR = "fixed_cluster_nonvictim_mean_delta_tpr"
    FIXED_CLUSTER_NONVICTIM_MEAN_DELTA_FPR = "fixed_cluster_nonvictim_mean_delta_fpr"
    WORST_VICTIM_DROP = "worst_victim_drop"
    DELTA_TAU_BOUND_UTILIZATION = "delta_tau_bound_utilization"
    CAL_DUPLICATE_RATE = "cal_duplicate_rate"
    TNR = "tnr"
    FNR = "fnr"
    PRECISION = "precision"
    RECALL = "recall"


class NormalizationScope(enum.StrEnum):

    GLOBAL = "global"
    PER_CLIENT = "per_client"
    PER_CLIENT_ZSCORE = "per_client_zscore"


class PayloadKey(enum.StrEnum):

    CLIENT_ID = "client_id"
    PER_CLIENT = "per_client"
    CONFUSION_MATRIX = "confusion_matrix"
    POLICY = "policy"
    STAGE = "stage"
    SEED = "seed"
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
    CONFIG_IDENTITY = "config_identity"
    SPLIT_MANIFEST_IDENTITY = "split_manifest_identity"
    MODEL_IDENTITY = "model_identity"
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


class AuditField(enum.StrEnum):

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

    STATUS = "status"
    SOURCE = "source"
    VALIDATED_STAGES = "validated_stages"
    SEEDS = "seeds"


class RunKind(enum.StrEnum):

    CORE_LADDER = "core_ladder"


class SeedScope(enum.StrEnum):

    REPRESENTATIVE_SEED = "representative_seed"
    ALL_SEEDS = "all_seeds"
    ALL_TRAINING_SEEDS = "all_training_seeds"


SCORING_STAGES: tuple[ScoringStage, ...] = ScoringStage.all()


MAIN_BODY_POLICIES: frozenset[ThresholdPolicy] = frozenset(
    {
        ThresholdPolicy.GLOBAL_THRESHOLD,
        ThresholdPolicy.LOCAL_THRESHOLD,
        ThresholdPolicy.CLUSTER_THRESHOLD,
    }
)


THRESHOLD_AGGREGATION_BY_POLICY: dict[ThresholdPolicy, ThresholdAggregationMethod] = {
    ThresholdPolicy.GLOBAL_THRESHOLD: ThresholdAggregationMethod.ELIGIBLE_CLIENT_ARITHMETIC_MEAN,
    ThresholdPolicy.LOCAL_THRESHOLD: ThresholdAggregationMethod.PER_CLIENT_PERCENTILE,
    ThresholdPolicy.CLUSTER_THRESHOLD: ThresholdAggregationMethod.ELIGIBLE_CLUSTER_ARITHMETIC_MEAN,
}


POLICY_THRESHOLD_SOURCE: dict[ThresholdPolicy, ThresholdSource] = {
    ThresholdPolicy.GLOBAL_THRESHOLD: ThresholdSource.GLOBAL,
    ThresholdPolicy.LOCAL_THRESHOLD: ThresholdSource.LOCAL,
    ThresholdPolicy.CLUSTER_THRESHOLD: ThresholdSource.CLUSTER,
}


CONTROLLED_POLICIES: tuple[ThresholdPolicy, ...] = (
    ThresholdPolicy.GLOBAL_THRESHOLD,
    ThresholdPolicy.LOCAL_THRESHOLD,
    ThresholdPolicy.CLUSTER_THRESHOLD,
)


class AttackerObjective(enum.StrEnum):

    THRESHOLD_RAISE = "threshold_raise"
    THRESHOLD_LOWER = "threshold_lower"


class ClaimClassification(enum.StrEnum):

    CALIBRATION_INSTABILITY = "calibration_instability"
    FULL_VULNERABILITY = "full_vulnerability"
    MECHANISM_ONLY = "mechanism_only"
    NULL_OR_CONDITIONAL = "null_or_conditional"


class ThresholdScaleScenario(enum.StrEnum):

    RAW_CLEAN = "raw_clean"
    RAW_POISONED = "raw_pois"
    NORMALIZED_CLEAN = "norm_clean"
    NORMALIZED_POISONED = "norm_pois"


class PoisoningSourceStrategy(enum.StrEnum):

    RANDOM_BENIGN = "random_benign"
    HIGH_SCORE_BENIGN = "high_score_benign"
    LOW_SCORE_BENIGN = "low_score_benign"
    LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY = (
        "low_score_targeted_removal_diagnostic_only"
    )


class CalibrationInjectionRule(enum.StrEnum):

    REPLACE_FIXED_BUDGET = "replace_fixed_budget"


class SplitSemantics(enum.StrEnum):

    CHRONOLOGICAL_BENIGN_ONLY_60_1_20_1_18 = (
        "chronological_benign_only_60_1_20_1_18"
    )


class ReservoirMode(enum.StrEnum):

    VICTIM_LOCAL_BENIGN_CAL_SOURCE_PRECEDENCE_RULE_2 = (
        "victim_local_benign_cal_source_precedence_rule_2"
    )


class ManifestProvenanceSource(enum.StrEnum):
    NBAIOT_MAIN_SWEEP = "nbaiot_main_manifest"


class ReservoirDraw(enum.StrEnum):

    WITH_REPLACEMENT = "with_replacement"
    WITHOUT_REPLACEMENT = "without_replacement"
    DISJOINT_RESERVOIR = "disjoint_reservoir"
    INTERPOLATED_TAIL = "interpolated_tail"


class SeedAggregationMethod(enum.StrEnum):

    MEAN = "mean"
    MAXIMUM = "max"


SYNTHESIZED_DRAWS: frozenset[ReservoirDraw] = frozenset(
    {ReservoirDraw.INTERPOLATED_TAIL}
)


class PoisoningKnowledge(enum.StrEnum):

    GRAY_BOX_SCORE_ACCESS = "gray_box_score_access"


class PoisoningTargetScope(enum.StrEnum):

    SINGLE_CLIENT = "single_client"
    MULTI_CLIENT = "multi_client"


class PoisoningDefense(enum.StrEnum):

    NONE = "none"
    TRIMMED_CALIBRATION = "trimmed_calibration"


class ReservoirStatus(enum.StrEnum):

    FEASIBLE = "feasible"
    INFEASIBLE_DEGENERATE_TAIL = "infeasible_degenerate_tail"


DIAGNOSTIC_ONLY_SOURCES: frozenset[PoisoningSourceStrategy] = frozenset(
    {
        PoisoningSourceStrategy.LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY,
    }
)


def objective_for_source(
    source: PoisoningSourceStrategy,
) -> AttackerObjective | None:
    match source:
        case PoisoningSourceStrategy.HIGH_SCORE_BENIGN:
            return AttackerObjective.THRESHOLD_RAISE
        case (
            PoisoningSourceStrategy.LOW_SCORE_BENIGN
            | PoisoningSourceStrategy.LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY
        ):
            return AttackerObjective.THRESHOLD_LOWER
        case _:
            return None


def is_diagnostic_source(source: PoisoningSourceStrategy) -> bool:
    return source in DIAGNOSTIC_ONLY_SOURCES


class FederatedRoundStage(enum.StrEnum):
    FIT = "fit"
    EVALUATE = "evaluate"


class ConvergenceStatus(enum.StrEnum):

    CONVERGED = "converged"
    NOT_CONVERGED = "not_converged"
    UNKNOWN = "unknown"
    MISSING_SUMMARY = "MISSING_SUMMARY"


class ConvergenceSummaryKey(enum.StrEnum):

    ROUNDS_INITIAL = "rounds_initial"
    ROUNDS_MAX = "rounds_max"
    RELATIVE_THRESHOLD = "relative_threshold"
    WINDOW = "window"
    ACTUAL_ROUNDS = "actual_rounds_run"
    CONVERGENCE_ROUND = "convergence_round"
    CONVERGENCE_CRITERION = "convergence_criterion_value"
    CONVERGENCE_STATUS = "convergence_status"
    WEIGHTED_LOSS = "weighted_validation_loss_per_round"


class AuditStatus(enum.StrEnum):

    PASS = "PASS"
    FAIL = "FAIL"
    MISSING = "MISSING"
    PARTIAL = "PARTIAL"
    BLOCKED_PENDING_RUN = "BLOCKED_PENDING_RUN"
    WARNING = "WARNING"


class InvariantField(enum.StrEnum):

    SPLIT_HASH = "split_hash"
    SCORING_CODE_HASH = "scoring_code_hash"
    METRICS_CODE_HASH = "metrics_code_hash"
    MODEL_OR_ENCODER_HASH = "model_hash_or_encoder_hash"
    RECONSTRUCTION_ERROR_ARRAYS = "reconstruction_error_arrays"


class WarningCode(enum.StrEnum):

    GLOBAL_NOT_POOLED_PERCENTILE = "GLOBAL_NOT_POOLED_PERCENTILE"
    LOCAL_UTILITY_TRADEOFF = "LOCAL_UTILITY_TRADEOFF"
    CLUSTER_DIAGNOSTICS_INCOMPLETE = "CLUSTER_DIAGNOSTICS_INCOMPLETE"
    FIXED_OPERATING_POINT_METRICS_PENDING = "FIXED_OPERATING_POINT_METRICS_PENDING"
    FLAT_CV_TPR_SUSPICIOUS = "FLAT_CV_TPR_SUSPICIOUS"
    MISSING_CONVERGENCE_CURVES = "MISSING_CONVERGENCE_CURVES"
    MISSING_CONFUSION_MATRIX = "MISSING_CONFUSION_MATRIX"
    MISSING_PARTITION_MANIFEST = "MISSING_PARTITION_MANIFEST"
    NAKED_CV_FPR = "NAKED_CV_FPR"
    PRIMARY_DELTA_INCOMPLETE = "PRIMARY_DELTA_INCOMPLETE"
    NO_COMPLETED_RESULTS = "NO_COMPLETED_RESULTS"
    SCHEMA_VERSION_MISMATCH = "SCHEMA_VERSION_MISMATCH"
    THRESHOLD_RECONSTRUCTION_FAILED = "THRESHOLD_RECONSTRUCTION_FAILED"
    WORST_CLIENT_STABLE = "WORST_CLIENT_STABLE"
    WORST_CLIENT_VARIES = "WORST_CLIENT_VARIES"


class AuditSeverity(enum.StrEnum):

    INFO = "INFO"
    WARNING = "WARNING"
    FAIL = "FAIL"
    BLOCKED_PENDING_RUN = "BLOCKED_PENDING_RUN"


class DenominatorStatus(enum.StrEnum):

    PASS = "PASS"
    FAIL = "FAIL"
    EXCLUDED_EVALUATION_INCOMPLETE = "EXCLUDED_EVALUATION_INCOMPLETE"
    BLOCKED_PENDING_RUN = "BLOCKED_PENDING_RUN"


class WorstDirection(enum.StrEnum):

    MAX_IS_WORST = "max_is_worst"
    MIN_IS_WORST = "min_is_worst"


WORST_CLIENT_DIRECTIONS: Mapping[MetricName, WorstDirection] = {
    MetricName.FPR: WorstDirection.MAX_IS_WORST,
    MetricName.TPR: WorstDirection.MIN_IS_WORST,
    MetricName.MACRO_F1: WorstDirection.MIN_IS_WORST,
    MetricName.BALANCED_ACCURACY: WorstDirection.MIN_IS_WORST,
}


class AuditDir(enum.StrEnum):

    AUDIT = "audit"
    DATA_AUDIT = "data_audit"


class AuditArtifact(enum.StrEnum):

    POLICY_INVARIANTS = "policy_invariants.json"
    RUN_MANIFEST = "run_manifest.csv"
    SEED_DELTAS = "seed_deltas.csv"
    PER_CLIENT_METRICS = "per_client_metrics.csv"
    PER_ATTACK_METRICS = "per_attack_metrics.csv"
    THRESHOLD_VALUES = "threshold_values.csv"
    RECONSTRUCTION_ERROR_SUMMARY = "reconstruction_error_summary.csv"
    CLUSTER_ASSIGNMENTS = "cluster_assignments.csv"
    DATASET_PARTITION_AUDIT = "dataset_partition_audit.json"
    CONVERGENCE_AUDIT = "convergence_audit.csv"
    METRIC_DENOMINATOR_AUDIT = "metric_denominator_audit.csv"
    FPR_COMPANION_METRICS = "fpr_companion_metrics.csv"
    WORST_CLIENT_TRACKING = "worst_client_tracking.csv"
    CLUSTER_STABILITY = "cluster_stability.csv"
    METRIC_RECOMPUTATION_AUDIT = "metric_recomputation_audit.csv"
    WARNINGS = "warnings.md"
    AUDIT_SUMMARY = "audit_summary.md"


class AuditSchemaVersion(enum.StrEnum):

    V1_0 = "1.0"


class AttackLabel(enum.StrEnum):

    BINARY_ATTACK = "binary_attack"


class RemediationCommand(enum.StrEnum):

    RUN_BASELINE = "datp baseline"
    REPORT = "datp report"


class CoverageFallback(enum.StrEnum):

    DEFAULT = "0/0"


class ValidationThreshold(float, enum.Enum):

    FLAT_CV_TPR_EPSILON = 1e-6


class ValidationCountThreshold(int, enum.Enum):

    WORST_CLIENT_STABLE_MIN_SEEDS = 3


class AuditOutputName(enum.StrEnum):

    POLICY_INVARIANTS = "policy_invariants"
    RUN_MANIFEST = "run_manifest"
    SEED_DELTAS = "seed_deltas"
    PER_CLIENT_METRICS = "per_client_metrics"
    PER_ATTACK_METRICS = "per_attack_metrics"
    THRESHOLD_VALUES = "threshold_values"
    RECONSTRUCTION_ERROR_SUMMARY = "reconstruction_error_summary"
    CLUSTER_ASSIGNMENTS = "cluster_assignments"
    DATASET_PARTITION_AUDIT = "dataset_partition_audit"
    CONVERGENCE_AUDIT = "convergence_audit"
    METRIC_DENOMINATOR_AUDIT = "metric_denominator_audit"
    METRIC_RECOMPUTATION_AUDIT = "metric_recomputation_audit"
    FPR_COMPANION_METRICS = "fpr_companion_metrics"
    WORST_CLIENT_TRACKING = "worst_client_tracking"
    CLUSTER_STABILITY = "cluster_stability"
    WARNINGS = "warnings"
    AUDIT_SUMMARY = "audit_summary"


class FigureName(enum.StrEnum):

    FIGURE_1 = "figure_1"
    FIGURE_2 = "figure_2"
    FIGURE_3 = "figure_3"
    FIGURE_5 = "figure_5"
    FIGURE_6 = "figure_6"


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


class EvidenceRole(enum.StrEnum):

    DESCRIPTIVE = "descriptive"
    DESCRIPTIVE_WITH_CONFIRMATORY_SIDECAR_DELTA = (
        "descriptive_with_confirmatory_sidecar_delta"
    )


class PackageDir(enum.StrEnum):

    CONFIG = "config"
    AUDIT = "audit"
    MANIFESTS = "manifests"


class ArtifactDir(enum.StrEnum):

    OUTPUTS = "outputs"
    RESULTS = "results"
    CALIBRATION_POISONING = "conference_calibration_poisoning"
    SCORES = "scores"
    LOGS = "logs"
    ANALYSIS = "analysis"
    FIGURES = "figures"
    TABLES = "tables"


class RunState(enum.StrEnum):

    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    ABORTED = "ABORTED"
    CORRUPT = "CORRUPT"


class CliExitCode(enum.IntEnum):

    SUCCESS = 0
    ERROR = 1


class CliCommand(enum.StrEnum):

    BASELINE = "baseline"
    PLAN = "plan"
    POISON = "poison"
    SENSITIVITY = "sensitivity"
    STATUS = "status"
    REPORT = "report"

    @classmethod
    def resolve(cls, arguments: Sequence[str]) -> "CliCommand | None":
        for command in cls:
            if arguments[:1] == [command]:
                return command
        return None


class StatusColumn(enum.StrEnum):

    SCOPE = "Scope"
    COMPLETE = "Complete"
    MISSING = "Missing"
    ABORTED = "Aborted"
    TOTAL = "Total"


class StatusScope(enum.StrEnum):

    OVERALL = "Overall"
