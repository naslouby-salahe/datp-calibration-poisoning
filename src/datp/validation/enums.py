
from __future__ import annotations

import enum
from collections.abc import Mapping

from datp.core.enums import MetricName


class AuditStatus(enum.StrEnum):

    PASS = "PASS"
    FAIL = "FAIL"
    MISSING = "MISSING"
    PARTIAL = "PARTIAL"
    BLOCKED_PENDING_RUN = "BLOCKED_PENDING_RUN"
    WARNING = "WARNING"


class ValidationCodePrefix(enum.StrEnum):

    MANIFEST = "manifest"
    REPRODUCTION = "reproduction"


class InvariantField(enum.StrEnum):

    SPLIT_HASH = "split_hash"
    SCORING_CODE_HASH = "scoring_code_hash"
    METRICS_CODE_HASH = "metrics_code_hash"
    MODEL_OR_ENCODER_HASH = "model_hash_or_encoder_hash"
    RECONSTRUCTION_ERROR_ARRAYS = "reconstruction_error_arrays"


class ReuseVerdict(enum.StrEnum):

    VERIFIED_REUSE_SAFE = "VERIFIED_REUSE_SAFE"
    REUSE_BLOCKED_RERUN_REQUIRED = "REUSE_BLOCKED_RERUN_REQUIRED"


class CellVerdictReason(enum.StrEnum):

    ALL_CHECKS_PASSED = "all checks passed"


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
    SCORE_CELL_VERIFICATION = "score_cell_verification.json"
    SCORE_CELL_VERIFICATION_INDEX = "score_cell_verification_index.json"
    CELL_VERDICT = "cell_verdict.json"
    CELL_VERDICTS = "cell_verdicts.json"
    WARNINGS = "warnings.md"
    AUDIT_SUMMARY = "audit_summary.md"


class AuditSchemaVersion(enum.StrEnum):

    V1_0 = "1.0"


class AttackLabel(enum.StrEnum):

    BINARY_ATTACK = "binary_attack"


class RemediationCommand(enum.StrEnum):

    SWEEP_RESUME = "datp sweep --resume"
    AUDIT_RESULTS = "datp audit results"


class CoverageFallback(enum.StrEnum):

    DEFAULT = "0/0"


class ValidationThreshold(float, enum.Enum):

    SCALAR_METRIC_TOLERANCE = 0.01
    COVERAGE_RATIO_TOLERANCE = 0.001
    FLAT_CV_TPR_EPSILON = 1e-6


class ValidationCountThreshold(int, enum.Enum):

    WORST_CLIENT_STABLE_MIN_SEEDS = 3


class MetricCheckCode(enum.StrEnum):

    SCALAR_WITHIN_TOLERANCE = "scalar_within_tolerance"
    COVERAGE_RATIO_WITHIN_TOLERANCE = "coverage_ratio_within_tolerance"
    ELIGIBLE_COUNT_EXACT = "eligible_count_exact"
    PENDING_COUNT_EXACT = "pending_count_exact"
    ELIGIBLE_IDS_EXACT = "eligible_ids_exact"
    PENDING_IDS_EXACT = "pending_ids_exact"
    CLIENT_COUNT_EXACT = "client_count_exact"
    PER_CLIENT_CONFUSION_EXACT = "per_client_confusion_exact"
    PER_CLIENT_THRESHOLDS_WITHIN_TOLERANCE = "per_client_thresholds_within_tolerance"


class ScoreCheckCode(enum.StrEnum):

    MANIFEST_PRESENT = "manifest_present"
    MANIFEST_PARSEABLE = "manifest_parseable"
    MANIFEST_FIELDS_PRESENT = "manifest_fields_present"
    MANIFEST_COMPLETION_STATUS = "manifest_completion_status"
    SCORING_SENTINEL_PRESENT = "scoring_sentinel_present"
    STAGE_MATCH = "stage_match"
    SEED_MATCH = "seed_match"
    DATASET_MATCH = "dataset_match"
    CLIENT_IDS_MATCH_PARTITION = "client_ids_match_partition"
    EXPECTED_VS_ACTUAL_CLIENTS = "expected_vs_actual_clients"
    EXPECTED_VS_ACTUAL_SPLITS = "expected_vs_actual_splits"
    SPLIT_DIRECTORIES_PRESENT = "split_directories_present"
    PER_CLIENT_SPLIT_FILES_PRESENT = "per_client_split_files_present"
    PARQUET_SCHEMA_VALID = "parquet_schema_valid"
    PARQUET_NON_EMPTY = "parquet_non_empty"
    CHECKPOINT_HASH_FIELD_PRESENT = "checkpoint_hash_field_present"
    CHECKPOINT_FILE_PRESENT = "checkpoint_file_present"
    CHECKPOINT_HASH_MATCHES = "checkpoint_hash_matches"


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
