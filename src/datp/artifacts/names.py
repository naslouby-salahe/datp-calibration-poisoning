from __future__ import annotations

import enum
from enum import StrEnum

__all__ = [
    "ArtifactDir",
    "ArtifactFile",
    "PathToken",
    "RunState",
]


class ArtifactDir(StrEnum):
    OUTPUTS = "outputs"
    RESULTS = "results"
    CHECKPOINTS = "checkpoints"
    SCORES = "scores"
    LOGS = "logs"
    CONSOLE_LOGS = "console_logs"
    ANALYSIS = "analysis"
    FIGURES = "figures"
    TABLES = "tables"
    CONFUSION_MATRICES = "confusion_matrices"


class ArtifactFile(enum.StrEnum):
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


class RunState(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    ABORTED = "ABORTED"
    CORRUPT = "CORRUPT"
