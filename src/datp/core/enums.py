from __future__ import annotations

import enum


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


class ClusterFingerprintFeature(enum.StrEnum):

    MEAN = "mean"
    STANDARD_DEVIATION = "std"
    SKEWNESS = "skew"
    NINETY_FIFTH_PERCENTILE = "p95"


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
    MODEL_CHECKPOINT = "model.pt"
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
    PARAMS_SNAPSHOT = "params.npz"
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
    ROUND_PREFIX = "round_"
    CHECKPOINT_PROTOCOL_SMOKE_TEMP_PREFIX = "datp_checkpoint_protocol_smoke_"


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

CLUSTER_FINGERPRINT_FEATURES: tuple[ClusterFingerprintFeature, ...] = (
    ClusterFingerprintFeature.MEAN,
    ClusterFingerprintFeature.STANDARD_DEVIATION,
    ClusterFingerprintFeature.SKEWNESS,
    ClusterFingerprintFeature.NINETY_FIFTH_PERCENTILE,
)
