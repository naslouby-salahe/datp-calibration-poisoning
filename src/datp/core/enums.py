"""Central enum registry for DATP domain vocabulary."""

from __future__ import annotations

import enum


class DatasetID(enum.StrEnum):
    """Supported dataset identifiers."""

    NBAIOT = "nbaiot"


class ThresholdPolicy(enum.StrEnum):
    """Threshold computation strategy: global, local, or cluster-based."""

    GLOBAL_THRESHOLD = "global_threshold"
    LOCAL_THRESHOLD = "local_threshold"
    CLUSTER_THRESHOLD = "cluster_threshold"


class ClientIdentity(enum.StrEnum):
    """How a client is identified in the dataset."""

    DEVICE_DIRECTORY = "device_directory"
    MERGED_FILE = "merged_file"
    VICTIM_MAC = "victim_mac"
    VIRTUAL_CLIENT = "virtual_client"


class DeviceType(enum.StrEnum):
    """Compute device type for PyTorch."""

    CUDA = "cuda"
    CPU = "cpu"


class ArtifactFile(enum.StrEnum):
    """Canonical artifact file names used across the pipeline."""

    MODEL_CHECKPOINT = "model.pt"
    DECODER_CHECKPOINT = "decoder.pt"
    SCORING_SENTINEL = "SCORING_DONE.txt"
    SCORING_MANIFEST = "scoring_manifest.json"
    METRICS = "metrics.json"
    METRICS_TMP = "metrics.json.tmp"
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
    JS_DIVERGENCE = "js_divergence.json"
    RUN_IN_PROGRESS = "IN_PROGRESS"
    RUN_DONE = "DONE.txt"
    RUN_ABORTED = "ABORTED.txt"
    RESOLVED_CONFIG = "resolved_config.yaml"


class PathToken(enum.StrEnum):
    """Reusable path string tokens for artifact layout."""

    PARQUET_EXT = ".parquet"
    PARQUET_GLOB = "*.parquet"
    CSV_GLOB = "*.csv"
    SEED_PREFIX = "seed_"
    ROUND_PREFIX = "round_"
    ALPHA_PREFIX = "alpha_"
    FRACTION_PREFIX = "f_"
    SCOPE_PREFIX = "scope_"
    TRAIN_PREFIX = "train_"
    POISON_PREFIX = "poison_"
    ALPHA_IID = "alpha_iid"


class ClientStatus(enum.StrEnum):
    """Whether a client meets the calibration eligibility threshold."""

    ELIGIBLE = "eligible"
    CALIBRATION_PENDING = "calibration_pending"


class ThresholdAggregationMethod(enum.StrEnum):
    """How per-client thresholds are aggregated into a global operating point."""

    ELIGIBLE_CLIENT_ARITHMETIC_MEAN = "eligible_client_arithmetic_mean"
    PER_CLIENT_PERCENTILE = "per_client_percentile"
    ELIGIBLE_CLUSTER_ARITHMETIC_MEAN = "eligible_cluster_arithmetic_mean"


class ThresholdSource(enum.StrEnum):
    """Origin of a threshold value."""

    GLOBAL = "global"
    LOCAL = "local"
    CLUSTER = "cluster"
    TAU_GLOBAL_FALLBACK = "tau_global_fallback"


class NormalizationScope(enum.StrEnum):
    """Scope of normalization applied to reconstruction errors."""

    GLOBAL = "global"
    PER_CLIENT = "per_client"
    PER_CLIENT_ZSCORE = "per_client_zscore"
    POOLED_ZSCORE = "pooled_zscore"


class PipelineStage(enum.StrEnum):
    """Pipeline stages from data preparation through reporting."""

    PREPARE = "prepare"
    TRAIN = "train"
    SCORE = "score"
    THRESHOLD = "threshold"
    EVALUATE = "evaluate"
    REPORT = "report"


class Activation(enum.StrEnum):
    """Supported activation functions for neural network layers."""

    RELU = "relu"
    LEAKY_RELU = "leaky_relu"
    ELU = "elu"
    TANH = "tanh"
    SIGMOID = "sigmoid"


class ScoringStage(enum.StrEnum):
    """Scoring data splits: calibration, test-benign, and test-attack."""

    CAL = "cal"
    TEST_BENIGN = "test_benign"
    TEST_ATTACK = "test_attack"

    @property
    def client_data_attr(self) -> str:
        """Return the attribute name used to access this stage's data on a client object."""
        return "val" if self == ScoringStage.CAL else self.value

    @classmethod
    def all(cls) -> tuple["ScoringStage", ...]:
        """Return all ScoringStage members as a tuple."""
        return tuple(cls)


class MetricName(enum.StrEnum):
    """Canonical metric names used across the pipeline."""

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
    """Keys used in JSON metric payloads."""

    CLIENT_ID = "client_id"
    PER_CLIENT = "per_client"
    CONFUSION_MATRIX = "confusion_matrix"
    POLICY = "policy"
    STAGE = "stage"
    SEED = "seed"
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
    CONFIG_IDENTITY = "config_identity"
    SPLIT_MANIFEST_IDENTITY = "split_manifest_identity"
    MODEL_CHECKPOINT_IDENTITY = "model_checkpoint_identity"
    SCORE_ARTIFACT_IDENTITY = "score_artifact_identity"
    METRIC_CODE_VERSION = "metric_code_version"
    THRESHOLD_CODE_VERSION = "threshold_code_version"
    PACKAGE_VERSION = "package_version"
    GENERATED_AT_UTC = "generated_at_utc"


class ConfusionKey(enum.StrEnum):
    """Keys for confusion matrix entries in JSON payloads."""

    TP = "tp"
    FP = "fp"
    TN = "tn"
    FN = "fn"


class AuditField(enum.StrEnum):
    """Fields in the audit summary JSON payload."""

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
    """Fields in validation result JSON payloads."""

    STATUS = "status"
    SOURCE = "source"
    VALIDATED_STAGES = "validated_stages"
    SEEDS = "seeds"


class RunKind(enum.StrEnum):
    """Kind of experiment run."""

    CORE_LADDER = "core_ladder"


class SeedScope(enum.StrEnum):
    """Whether a result covers a single representative seed or all seeds."""

    REPRESENTATIVE_SEED = "representative_seed"
    ALL_SEEDS = "all_seeds"


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

CLUSTER_FINGERPRINT_FEATURES: tuple[str, ...] = ("mean", "std", "skew", "p95")
