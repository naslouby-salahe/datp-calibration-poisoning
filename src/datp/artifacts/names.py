"""Canonical artifact directory names and run-state sentinel values."""

from __future__ import annotations

from enum import StrEnum

from datp.core.enums import ArtifactFile, PathToken

__all__ = [
    "ArtifactDir",
    "ArtifactFile",
    "PathToken",
    "RunState",
]


class ArtifactDir(StrEnum):
    """Canonical artifact directory names."""

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


class RunState(StrEnum):
    """Sentinel-based run state values."""

    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    ABORTED = "ABORTED"
    CORRUPT = "CORRUPT"
