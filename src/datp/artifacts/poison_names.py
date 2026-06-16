"""CP2-specific artifact file names and the canonical output root.

Import from here; do not hardcode CP2 artifact names elsewhere.
"""

from __future__ import annotations

from enum import StrEnum


class Cp2ManifestFile(StrEnum):
    """Canonical names for CP2 manifest and audit JSON files."""

    PROJECT_AUDIT_REPORT = "project_audit_report.json"
    CLEAN_SCORE_ARTIFACTS = "clean_score_artifacts.json"
    NBAIOT_MVP_MANIFEST = "nbaiot_mvp_manifest.json"
    PAPER_FIGURE_MANIFEST = "paper_figure_manifest.json"
    CP2_RUN_MANIFEST = "cp2_run_manifest.json"


class Cp2RunFile(StrEnum):
    """Canonical names for per-cell run files."""

    POISONED_SCORES = "poisoned_scores.parquet"
    THRESHOLD_DELTAS = "threshold_deltas.json"
    CELL_METRICS = "cell_metrics.json"
    SEED_RECORD = "seed_record.json"
    PROVENANCE = "provenance.json"
    RUN_DONE = "CP2_DONE.txt"
    RUN_IN_PROGRESS = "CP2_IN_PROGRESS"


# Canonical output root for all CP2 runs.
# All CP2 outputs live under outputs/CP2_OUTPUT_ROOT/.
CP2_OUTPUT_ROOT: str = "conference_calibration_poisoning"

# Locked scalar constants — do not duplicate in other modules.
CP2_N_MIN: int = 100
CP2_TAIL_MASS: float = 0.10
CP2_MATERIALITY_FACTOR: float = 0.1
CP2_Q: float = 0.95  # Calibration quantile for threshold derivation.

# Locked B4 hyperparameters for N-BaIoT (Regime A).
CP2_B4_K: int = 3
CP2_B4_N_INIT: int = 10
CP2_B4_MAX_ITER: int = 300
CP2_B4_RANDOM_STATE: int = 42

# Locked seed pools.
CP2_TRAINING_SEEDS: tuple[int, ...] = (0, 1, 2, 3, 4)
CP2_POISONING_SEEDS: tuple[int, ...] = (100, 101, 102, 103, 104)
CP2_ANALYSIS_SEEDS: tuple[int, ...] = (300, 301, 302, 303, 304)
CP2_COMPROMISE_PATTERN_SEED: int = 400

