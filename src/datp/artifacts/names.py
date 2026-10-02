
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

    OUTPUTS = "outputs"
    RESULTS = "results"
    CALIBRATION_POISONING = "conference_calibration_poisoning"
    CHECKPOINTS = "checkpoints"
    SCORES = "scores"
    LOGS = "logs"
    ANALYSIS = "analysis"
    FIGURES = "figures"
    TABLES = "tables"
    CONFUSION_MATRICES = "confusion_matrices"


class RunState(StrEnum):

    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    ABORTED = "ABORTED"
    CORRUPT = "CORRUPT"
