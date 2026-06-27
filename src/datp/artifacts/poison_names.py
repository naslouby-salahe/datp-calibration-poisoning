"""Canonical artifact file names and the canonical output root."""

from __future__ import annotations

from enum import StrEnum


class ManifestFile(StrEnum):
    """Manifest file names for poisoning experiments."""

    PROJECT_AUDIT_REPORT = "project_audit_report.json"
    CLEAN_SCORE_ARTIFACTS = "clean_score_artifacts.json"
    SYNTHETIC_SMOKE_MANIFEST = "synthetic_smoke_manifest.json"
    NBAIOT_MAIN_MANIFEST = "nbaiot_main_manifest.json"
    CLUSTER_THRESHOLD_MANIFEST = "cluster_threshold_manifest.json"
    RESERVOIR_MANIFEST = "reservoir_manifest.json"
    INFEASIBLE_CELLS = "infeasible_cells.json"
    MULTI_CLIENT_PLAN = "multi_client_plan.json"
    PAPER_FIGURE_MANIFEST = "paper_figure_manifest.json"
    RUN_MANIFEST = "run_manifest.json"


class RunFile(StrEnum):
    """Per-run artifact file names."""

    POISONED_SCORES = "poisoned_scores.parquet"
    THRESHOLD_DELTAS = "threshold_deltas.json"
    CELL_METRICS = "cell_metrics.json"
    SEED_RECORD = "seed_record.json"
    PROVENANCE = "provenance.json"
    RUN_DONE = "DONE.txt"
    RUN_IN_PROGRESS = "IN_PROGRESS"


CALIBRATION_POISONING_OUTPUT_ROOT: str = "conference_calibration_poisoning"
"""Root directory under the base output directory for poisoning-experiment artifacts."""

NBAIOT_MAIN_MANIFEST_SOURCE: str = "nbaiot_main_manifest"
"""Key identifying the N-BaIoT main manifest in provenance records."""
