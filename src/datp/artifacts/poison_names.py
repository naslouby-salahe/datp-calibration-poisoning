"""Canonical artifact file names and the canonical output root.

Import from here; do not hardcode artifact names elsewhere.
"""

from __future__ import annotations

from enum import StrEnum


class ManifestFile(StrEnum):
    """Canonical names for manifest and audit JSON files."""

    PROJECT_AUDIT_REPORT = "project_audit_report.json"
    CLEAN_SCORE_ARTIFACTS = "clean_score_artifacts.json"
    NBAIOT_BOUNDED_SWEEP_MANIFEST = "nbaiot_bounded_sweep_manifest.json"
    PAPER_FIGURE_MANIFEST = "paper_figure_manifest.json"
    RUN_MANIFEST = "run_manifest.json"


class RunFile(StrEnum):
    """Canonical names for per-cell run files."""

    POISONED_SCORES = "poisoned_scores.parquet"
    THRESHOLD_DELTAS = "threshold_deltas.json"
    CELL_METRICS = "cell_metrics.json"
    SEED_RECORD = "seed_record.json"
    PROVENANCE = "provenance.json"
    RUN_DONE = "DONE.txt"
    RUN_IN_PROGRESS = "IN_PROGRESS"


# Canonical output root for all runs.
# All outputs live under outputs/CALIBRATION_POISONING_OUTPUT_ROOT/.
CALIBRATION_POISONING_OUTPUT_ROOT: str = "conference_calibration_poisoning"

# Locked scalar constants — do not duplicate in other modules.
N_MIN: int = 100
TAIL_MASS: float = 0.10
MATERIALITY_FACTOR: float = 0.1
THRESHOLD_QUANTILE: float = 0.95  # Calibration quantile for threshold derivation.

# Trimmed-calibration defense: symmetric trim fraction removed from each tail
# before the threshold quantile and before B4 fingerprinting. Primary t=5%;
# t=10% is appendix-only.
TRIM_FRACTION_PRIMARY: float = 0.05
TRIM_FRACTION_APPENDIX: float = 0.10

# Locked B4 hyperparameters for N-BaIoT (Regime A).
B4_K: int = 3
B4_N_INIT: int = 10
B4_MAX_ITER: int = 300
