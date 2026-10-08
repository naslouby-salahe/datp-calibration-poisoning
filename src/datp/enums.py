from __future__ import annotations

import enum
from collections.abc import Sequence

from datp.types import NarrativeText


class DatasetID(enum.StrEnum):
    NBAIOT = "nbaiot"


class DatasetDisplayName(enum.StrEnum):
    NBAIOT = "N-BaIoT"


class AnalysisColumn(enum.StrEnum):
    ANALYSIS_SEEDS = "analysis_seeds"
    ARTIFACT_PROVENANCE = "artifact_provenance"
    BOOTSTRAP_CI_LOWER = "bootstrap_ci_lower"
    BOOTSTRAP_CI_UPPER = "bootstrap_ci_upper"
    BOOTSTRAP_MEAN = "bootstrap_mean"
    BOOTSTRAP_N_SEED_AGGREGATES = "bootstrap_n_seed_aggregates"
    CELLS = "cells"
    CLAIM_BEARING = "claim_bearing"
    CLAIM_CLASS = "claim_class"
    CLAIM_CLASS_ABSOLUTE = "claim_class_absolute"
    CLUSTER_CHURN = "cluster_churn"
    CLUSTER_FIXED_GATE1_PASS = "cluster_fixed_gate1_pass"
    CODE_COMMIT = "code_commit"
    CONFIG_HASH = "config_hash"
    CONTROL_OBJECTIVE = "control_objective"
    CONTROL_SOURCE = "control_source"
    DATASET = "dataset"
    DIRECTIONAL_EXCESS_SEED_SUPPORT = "directional_excess_seed_support"
    DRAW = "draw"
    EXACT_BINOMIAL_P = "exact_binomial_p"
    EXACT_SUPPORT_COUNT = "exact_support_count"
    EXACT_SUPPORT_N = "exact_support_n"
    EXPECTED_SIGN_SEED_SUPPORT = "expected_sign_seed_support"
    FIXED_DELTA_CV_FPR = "fixed_delta_cv_fpr"
    FIXED_NONVICTIM_DELTA_FPR = "fixed_nonvictim_delta_fpr"
    FIXED_NONVICTIM_DELTA_TPR = "fixed_nonvictim_delta_tpr"
    FIXED_VICTIM_DELTA_FPR = "fixed_victim_delta_fpr"
    FIXED_VICTIM_DELTA_TAU = "fixed_victim_delta_tau"
    FIXED_VICTIM_DELTA_TPR = "fixed_victim_delta_tpr"
    FRACTION = "fraction"
    FRACTIONS = "fractions"
    FROZEN_SCALER_EFFECT = "frozen_scaler_effect"
    FULL_BUDGET_FEASIBLE_RATE = "full_budget_feasible_rate"
    GATE1_PASS = "gate1_pass"
    GATE2_PASS = "gate2_pass"
    GATE3_METRIC_PASS = "gate3_metric_pass"
    GATE3_PASS = "gate3_pass"
    IQR_DELTA_TAU = "iqr_delta_tau"
    IQR_FLOOR_FACTOR = "iqr_floor_factor"
    K = "k"
    LEAVE_ONE_VICTIM_OUT_MAX = "leave_one_victim_out_max"
    LEAVE_ONE_VICTIM_OUT_MEDIAN = "leave_one_victim_out_median"
    LEAVE_ONE_VICTIM_OUT_MIN = "leave_one_victim_out_min"
    MATERIAL_SIGNED_RATE = "material_signed_rate"
    MATERIALITY_FACTOR = "materiality_factor"
    MAX_BOUND_UTILIZATION = "max_bound_utilization"
    MAX_N_REASSIGNED = "max_n_reassigned"
    MEAN_BOUND_UTILIZATION = "mean_bound_utilization"
    MEAN_BUFFER_TO_OVERWRITE_RATIO = "mean_buffer_to_overwrite_ratio"
    MEAN_DELTA_TAU = "mean_delta_tau"
    MEAN_DELTA_TAU_TRIM_APPENDIX = "mean_delta_tau_trim_appendix"
    MEAN_DELTA_TAU_TRIM_PRIMARY = "mean_delta_tau_trim_primary"
    MEAN_DELTA_TAU_UNDEFENDED = "mean_delta_tau_undefended"
    MEAN_DELTA_TAU_VARIANT = "mean_delta_tau_variant"
    MEAN_DELTA_TAU_WITH_REPLACEMENT = "mean_delta_tau_with_replacement"
    MEAN_DIRECTIONAL_EXCESS = "mean_directional_excess"
    MEAN_DUPLICATE_RATE_CLEAN = "mean_duplicate_rate_clean"
    MEAN_DUPLICATE_RATE_POISONED = "mean_duplicate_rate_poisoned"
    MEAN_DUPLICATE_RATE_VARIANT = "mean_duplicate_rate_variant"
    MEAN_DUPLICATE_RATE_WITH_REPLACEMENT = "mean_duplicate_rate_with_replacement"
    MEAN_EFFECT = "mean_effect"
    MEAN_EFFECTIVE_N_REPLACED = "mean_effective_n_replaced"
    MEAN_FIXED_VICTIM_DELTA_TAU = "mean_fixed_victim_delta_tau"
    MEAN_INIT_SD_VICTIM_DELTA_TAU = "mean_init_sd_victim_delta_tau"
    MEAN_N_REASSIGNED = "mean_n_reassigned"
    MEAN_N_REPLACED = "mean_n_replaced"
    MEAN_OVERWRITE_REFERENCE_SHIFT = "mean_overwrite_reference_shift"
    MEAN_POOL_SIZE = "mean_pool_size"
    MEAN_REQUESTED_N_REPLACED = "mean_requested_n_replaced"
    MEAN_RESIDUAL_VS_CLEAN_TRIM_APPENDIX = "mean_residual_vs_clean_trim_appendix"
    MEAN_RESIDUAL_VS_CLEAN_TRIM_PRIMARY = "mean_residual_vs_clean_trim_primary"
    MEAN_SCORE_SCALE_CV_CLEAN = "mean_score_scale_cv_clean"
    MEAN_SILHOUETTE_CLEAN = "mean_silhouette_clean"
    MEAN_SILHOUETTE_POISONED = "mean_silhouette_poisoned"
    MEAN_TAU_LOCAL_CV_CLEAN = "mean_tau_local_cv_clean"
    MEAN_TAU_LOCAL_MAX_MIN_RATIO_CLEAN = "mean_tau_local_max_min_ratio_clean"
    MEAN_VICTIM_DELTA_TAU = "mean_victim_delta_tau"
    MEAN_VICTIM_SIZE_CLEAN = "mean_victim_size_clean"
    MEAN_VICTIM_SIZE_POISONED = "mean_victim_size_poisoned"
    MEDIAN_DELTA_TAU = "median_delta_tau"
    MEDIAN_DIRECTIONAL_EXCESS = "median_directional_excess"
    MEDIAN_HARM = "median_harm"
    METRIC = "metric"
    MODAL_SIZES_CLEAN = "modal_sizes_clean"
    MODAL_SIZES_POISONED = "modal_sizes_poisoned"
    N_CALIBRATION_INSTABILITY = "n_calibration_instability"
    N_CHANGED_VS_DEFAULT = "n_changed_vs_default"
    N_EXCLUSIONS = "n_exclusions"
    N_FULL_VULNERABILITY = "n_full_vulnerability"
    N_GROUPS = "n_groups"
    N_INIT = "n_init"
    N_MECHANISM_ONLY = "n_mechanism_only"
    N_NULL_OR_CONDITIONAL = "n_null_or_conditional"
    N_REPORTING_ROWS = "n_reporting_rows"
    N_ROWS = "n_rows"
    N_SEEDS = "n_seeds"
    N_SEEDS_NEGATIVE = "n_seeds_negative"
    NON_VICTIM_EFFECT = "non_victim_effect"
    NORMALIZED_GLOBAL_CV_FPR_CLEAN = "normalized_global_cv_fpr_clean"
    NORMALIZED_GLOBAL_CV_FPR_POISONED = "normalized_global_cv_fpr_poisoned"
    NORMALIZED_GLOBAL_VICTIM_DELTA_FPR = "normalized_global_victim_delta_fpr"
    NORMALIZED_GLOBAL_VICTIM_DELTA_TAU = "normalized_global_victim_delta_tau"
    OBJECTIVE = "objective"
    PER_SEED_DIRECTIONAL_EXCESS = "per_seed_directional_excess"
    PER_SEED_VALUES = "per_seed_values"
    PERMUTATION_P = "permutation_p"
    POISONING_SEEDS = "poisoning_seeds"
    POLICIES = "policies"
    POLICY = "policy"
    RANDOM_CONTROL_DIRECTIONAL_COUNT = "random_control_directional_count"
    RANDOM_CONTROL_INSTABILITY_COUNT = "random_control_instability_count"
    RANDOM_CONTROL_UNSTABLE = "random_control_unstable"
    RANDOM_CONTROL_UNSTABLE_DIRECTIONAL = "random_control_unstable_directional"
    RAW_GLOBAL_CV_FPR_CLEAN = "raw_global_cv_fpr_clean"
    RAW_GLOBAL_CV_FPR_POISONED = "raw_global_cv_fpr_poisoned"
    RAW_GLOBAL_VICTIM_DELTA_FPR = "raw_global_victim_delta_fpr"
    RAW_GLOBAL_VICTIM_DELTA_TAU = "raw_global_victim_delta_tau"
    REASSIGNMENT_RATE = "reassignment_rate"
    RECOMPUTED_DELTA_CV_FPR = "recomputed_delta_cv_fpr"
    RECOMPUTED_NONVICTIM_DELTA_FPR = "recomputed_nonvictim_delta_fpr"
    RECOMPUTED_NONVICTIM_DELTA_TPR = "recomputed_nonvictim_delta_tpr"
    RECOMPUTED_VICTIM_DELTA_FPR = "recomputed_victim_delta_fpr"
    RECOMPUTED_VICTIM_DELTA_TAU = "recomputed_victim_delta_tau"
    RECOMPUTED_VICTIM_DELTA_TPR = "recomputed_victim_delta_tpr"
    REFIT_MINUS_FROZEN_SCALER = "refit_minus_frozen_scaler"
    REPORTING_ROW_COUNT_SEMANTICS = "reporting_row_count_semantics"
    SCHEMA_VERSION = "schema_version"
    SEED_SIGN_COUNT = "seed_sign_count"
    SHARE_FULL_VULNERABILITY = "share_full_vulnerability"
    SHARE_FULL_VULNERABILITY_ABSOLUTE_CONTROL_GATE = (
        "share_full_vulnerability_absolute_control_gate"
    )
    SIGN_CONSISTENCY = "sign_consistency"
    SIGN_STABLE_EXCLUSIONS = "sign_stable_exclusions"
    SOURCE = "source"
    SOURCE_OBJECTIVE_PAIRS = "source_objective_pairs"
    SOURCES = "sources"
    SPILLOVER_COUNT = "spillover_count"
    STAGE = "stage"
    SUMMARY_METRIC = "summary_metric"
    SYNTHESIZED_VALUES = "synthesized_values"
    TRAINING_SEEDS = "training_seeds"
    TRIM_PRIMARY_REDUCTION = "trim_primary_reduction"
    VARIANT_TO_BASELINE_RATIO = "variant_to_baseline_ratio"
    VICTIM_EFFECT = "victim_effect"
    VICTIM_ID = "victim_id"
    VICTIM_MAJORITY = "victim_majority"
    VICTIM_MAJORITY_COUNT = "victim_majority_count"
    VICTIM_SINGLETON_CLEAN_RATE = "victim_singleton_clean_rate"
    VICTIM_SINGLETON_POISONED_RATE = "victim_singleton_poisoned_rate"


class CheckpointKey(enum.StrEnum):
    STATE_DICT = "state_dict"
    MODEL_CONFIG = "model_config"


class ConvergenceColumn(enum.StrEnum):
    ROUND = "round"
    FEDAVG_WEIGHTED_BENIGN_VAL_LOSS = "fedavg_weighted_benign_val_loss"


class ServerMetricKey(enum.StrEnum):
    WEIGHTED_VAL_LOSS = "weighted_val_loss"


class EnvironmentVariable(enum.StrEnum):
    CUBLAS_WORKSPACE_CONFIG = "CUBLAS_WORKSPACE_CONFIG"
    RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO = "RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO"
    RAY_MEMORY_USAGE_THRESHOLD = "RAY_memory_usage_threshold"


class AxisLabel(enum.StrEnum):
    DEVICE = "Device"
    FPR = "FPR"
    ECDF = "ECDF"
    RECONSTRUCTION_ERROR = "Reconstruction Error"
    THRESHOLD_POLICY = "ThresholdPolicy"


class TableColumn(enum.StrEnum):
    CV_FPR_MEAN = "CV(FPR) mean"
    CV_FPR_STD = "CV(FPR) std"
    CV_TPR_MEAN = "CV(TPR) mean"
    CV_TPR_STD = "CV(TPR) std"
    WORST_BA_MEAN = "Worst BA mean"
    WORST_BA_STD = "Worst BA std"
    P10_MACRO_F1_MEAN = "P10 client Macro-F1 mean"
    P10_MACRO_F1_STD = "P10 client Macro-F1 std"
    ELIGIBLE = "Eligible"
    PENDING = "Pending"
    COVERAGE = "Coverage"


class Workflow(enum.StrEnum):
    REPORT_STATS = "report.stats"
    REPORT_FIGURES = "report.figures"
    REPORT_POISONING_FIGURES = "report.poisoning_figures"
    REPORT_TABLES = "report.tables"
    REPORT_VALIDATION = "report.validation"
    REPORT_BASELINE = "report.baseline"
    POISONING_SUMMARIES = "report.poisoning_summaries"
    SENSITIVITY_SUMMARIES = "report.sensitivity_summaries"
    FEATURE_RESERVOIR_LOAD = "poisoning.feature_reservoir_load"
    FEDERATED_SIMULATION = "federated.simulation"
    FEDERATED_TRAINING = "federated.training"
    DATA_PREPARATION = "data.preparation"
    PARTITION_AUDIT = "data.partition_audit"
    BASELINE_SWEEP = "baseline.sweep"


class ControlGate(enum.StrEnum):
    DIRECTIONAL = "directional"
    ABSOLUTE = "absolute"


class WorkflowEvent(enum.StrEnum):
    STARTED = "workflow started"
    COMPLETED = "workflow completed"


class AxisName(enum.StrEnum):
    X = "x"
    Y = "y"


class ErrorScope(enum.StrEnum):
    CONFIG = "config"
    DATA_SCALING = "data.scaling"
    DATA_ARTIFACTS = "data.artifacts"
    DATA_STORAGE = "data.storage"
    MODELING_AUTOENCODER = "modeling.autoencoder"
    EVALUATION_METRICS = "evaluation.metrics"
    PREPARE_DATA = "experiments.stages.prepare_data"
    DATA_MANIFESTS = "data.manifests"
    DATA_AUDIT = "data.audit"
    DATA_NBAIOT = "data.nbaiot"
    SCORING_MANIFEST = "scoring.manifest"
    THRESHOLDS = "thresholding.thresholds"
    THRESHOLD_POLICIES = "thresholding.policies"
    THRESHOLD_DERIVATION = "thresholding.derivation"
    SCORING_GENERATION = "scoring.generation"
    SCORING_LOADING = "scoring.loading"


class NBaIoTDevice(enum.StrEnum):
    DANMINI_DOORBELL = "Danmini_Doorbell"
    ECOBEE_THERMOSTAT = "Ecobee_Thermostat"
    ENNIO_DOORBELL = "Ennio_Doorbell"
    PHILIPS_B120N10_BABY_MONITOR = "Philips_B120N10_Baby_Monitor"
    PROVISION_PT_737E_SECURITY_CAMERA = "Provision_PT_737E_Security_Camera"
    PROVISION_PT_838_SECURITY_CAMERA = "Provision_PT_838_Security_Camera"
    SAMSUNG_SNH_1011_N_WEBCAM = "Samsung_SNH_1011_N_Webcam"
    SIMPLEHOME_XCS7_1002_WHT_SECURITY_CAMERA = (
        "SimpleHome_XCS7_1002_WHT_Security_Camera"
    )
    SIMPLEHOME_XCS7_1003_WHT_SECURITY_CAMERA = (
        "SimpleHome_XCS7_1003_WHT_Security_Camera"
    )


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
    CONFIG_IDENTITY = "config_identity"
    SPLIT_MANIFEST_IDENTITY = "split_manifest_identity"
    MODEL_IDENTITY = "model_identity"
    SCORE_ARTIFACT_IDENTITY = "score_artifact_identity"
    METRIC_CODE_VERSION = "metric_code_version"
    THRESHOLD_CODE_VERSION = "threshold_code_version"
    PACKAGE_VERSION = "package_version"
    GENERATED_AT_UTC = "generated_at_utc"


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
    RANDOM_TRAIN_FEATURE_BENIGN = "random_train_feature_benign"
    HIGH_SCORE_TRAIN_FEATURE_BENIGN = "high_score_train_feature_benign"
    LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY = (
        "low_score_targeted_removal_diagnostic_only"
    )


class FeatureDonorScope(enum.StrEnum):
    OWN_DEVICE = "own_device"
    CROSS_DEVICE = "cross_device"


class CalibrationInjectionRule(enum.StrEnum):
    REPLACE_FIXED_BUDGET = "replace_fixed_budget"


class SplitSemantics(enum.StrEnum):
    CHRONOLOGICAL_BENIGN_ONLY_60_1_20_1_18 = "chronological_benign_only_60_1_20_1_18"


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
        case PoisoningSourceStrategy.HIGH_SCORE_TRAIN_FEATURE_BENIGN:
            return AttackerObjective.THRESHOLD_RAISE
        case PoisoningSourceStrategy.RANDOM_TRAIN_FEATURE_BENIGN:
            return AttackerObjective.THRESHOLD_RAISE
        case (
            PoisoningSourceStrategy.LOW_SCORE_BENIGN
            | PoisoningSourceStrategy.LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY
        ):
            return AttackerObjective.THRESHOLD_LOWER
        case _:
            return None


def control_source_for(
    source: PoisoningSourceStrategy,
) -> PoisoningSourceStrategy | None:
    match source:
        case (
            PoisoningSourceStrategy.HIGH_SCORE_BENIGN
            | PoisoningSourceStrategy.LOW_SCORE_BENIGN
        ):
            return PoisoningSourceStrategy.RANDOM_BENIGN
        case PoisoningSourceStrategy.HIGH_SCORE_TRAIN_FEATURE_BENIGN:
            return PoisoningSourceStrategy.RANDOM_TRAIN_FEATURE_BENIGN
        case _:
            return None


def is_random_control(source: PoisoningSourceStrategy) -> bool:
    return source in {
        PoisoningSourceStrategy.RANDOM_BENIGN,
        PoisoningSourceStrategy.RANDOM_TRAIN_FEATURE_BENIGN,
    }


def is_train_feature_source(source: PoisoningSourceStrategy) -> bool:
    return source in {
        PoisoningSourceStrategy.RANDOM_TRAIN_FEATURE_BENIGN,
        PoisoningSourceStrategy.HIGH_SCORE_TRAIN_FEATURE_BENIGN,
    }


def is_diagnostic_source(source: PoisoningSourceStrategy) -> bool:
    return source in DIAGNOSTIC_ONLY_SOURCES


class FederatedRoundStage(enum.StrEnum):
    FIT = "fit"
    EVALUATE = "evaluate"


class ConvergenceStatus(enum.StrEnum):
    CONVERGED = "converged"
    NOT_CONVERGED = "not_converged"


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


class AuditDir(enum.StrEnum):
    DATA_AUDIT = "data_audit"


class FigureName(enum.StrEnum):
    FIGURE_1 = "figure_1"
    FIGURE_2 = "figure_2"
    FIGURE_3 = "figure_3"
    FIGURE_5 = "figure_5"
    FIGURE_6 = "figure_6"
    FIGURE_7 = "figure_7"


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
    CLAIM_ROBUSTNESS = "claim_robustness"
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
    MANIFESTS = "manifests"


class ArtifactDir(enum.StrEnum):
    OUTPUTS = "outputs"
    RESULTS = "results"
    CALIBRATION_POISONING = "conference_calibration_poisoning"
    SCORES = "scores"
    MODELS = "models"
    LOGS = "logs"
    WORKER_LOGS = "workers"
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
    def resolve(cls, arguments: Sequence[NarrativeText]) -> "CliCommand | None":
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
