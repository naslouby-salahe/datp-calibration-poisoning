from __future__ import annotations

from typing import Literal

AUDIT_DIR = "audit"
AUDIT_SCHEMA_VERSION = "1.0"
DATA_AUDIT_DIR = "data_audit"

BASELINE_INVARIANTS_JSON = "baseline_invariants.json"
RUN_MANIFEST_CSV = "run_manifest.csv"
SEED_DELTAS_CSV = "seed_deltas.csv"
PER_CLIENT_METRICS_CSV = "per_client_metrics.csv"
PER_ATTACK_METRICS_CSV = "per_attack_metrics.csv"
THRESHOLD_VALUES_CSV = "threshold_values.csv"
RECONSTRUCTION_ERROR_SUMMARY_CSV = "reconstruction_error_summary.csv"
CLUSTER_ASSIGNMENTS_CSV = "cluster_assignments.csv"
DATASET_PARTITION_AUDIT_JSON = "dataset_partition_audit.json"
CONVERGENCE_AUDIT_CSV = "convergence_audit.csv"
METRIC_DENOMINATOR_AUDIT_CSV = "metric_denominator_audit.csv"
FPR_COMPANION_METRICS_CSV = "fpr_companion_metrics.csv"
WORST_CLIENT_TRACKING_CSV = "worst_client_tracking.csv"
CICIOT_HOMOGENEITY_AUDIT_CSV = "ciciot_homogeneity_audit.csv"
REGIME_C_ALPHA_AUDIT_CSV = "regime_c_alpha_audit.csv"
REGIME_C_SEVERITY_TREND_CSV = "regime_c_severity_trend.csv"
B4_CLUSTER_STABILITY_CSV = "b4_cluster_stability.csv"
METRIC_RECOMPUTATION_AUDIT_CSV = "metric_recomputation_audit.csv"
SCORE_CELL_VERIFICATION_JSON = "score_cell_verification.json"
SCORE_CELL_VERIFICATION_INDEX_JSON = "score_cell_verification_index.json"
RECOMPUTED_METRICS_JSON = "recomputed_metrics.json"
RECOMPUTED_METRICS_INDEX_JSON = "recomputed_metrics_index.json"
CELL_VERDICT_JSON = "cell_verdict.json"
CELL_VERDICTS_JSON = "cell_verdicts.json"

SCALAR_METRIC_TOLERANCE = 0.01
COVERAGE_RATIO_TOLERANCE = 0.001
WARNINGS_MD = "warnings.md"
AUDIT_SUMMARY_MD = "audit_summary.md"

BINARY_ATTACK_LABEL = "binary_attack"
BLOCKED_RESUME_COMMAND = "datp sweep --resume"
BLOCKED_RESUME_REGIME_A_COMMAND = "datp sweep --regime=a --resume"
DIAGNOSTIC_REGIME_A_COMMAND = "datp diagnostic --regime a --seed 0"
_AUDIT_RESULTS_COMMAND = "make audit-results"
FLAT_CV_TPR_EPSILON = 1e-6
WORST_CLIENT_STABLE_MIN_SEEDS = 3
DEFAULT_COVERAGE_RATIO = "0/0"
FINGERPRINT_METHOD_BENIGN_RECON_ERROR_HISTOGRAM: Literal[
    "benign_recon_error_histogram"
] = "benign_recon_error_histogram"

NBAIOT_CONFOUND_SUMMARY = (
    "N-BaIoT natural per-device partition mixes device-specific benign "
    "feature heterogeneity with attack-variant skew (different devices were "
    "exposed to different gafgyt/mirai subtypes during capture). Threshold "
    "dispersion across this partition is therefore not pure feature-skew "
    "isolation; Regime C is the controlled-mixture comparator for that purpose."
)

REGIME_C_SCOPE_NOTE = (
    "Regime C reports severity/context behaviour (how threshold dispersion "
    "scales with feature-distribution mixing intensity). It does not provide "
    "confirmatory evidence for the primary Regime A B1-vs-B2 claim."
)
