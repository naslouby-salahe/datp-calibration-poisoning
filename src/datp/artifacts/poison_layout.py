"""Filesystem layout for calibration-poisoning experiment outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from datp.artifacts.poison_names import (
    CALIBRATION_POISONING_OUTPUT_ROOT,
    ManifestFile,
    RunFile,
)
from datp.attacks.enums import (
    AttackerObjective,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
)
from datp.config.models import ExperimentStage
from datp.core.enums import PathToken, ThresholdPolicy
from datp.core.seeds import SeedPair
from datp.data.catalog import DatasetID


@dataclass(frozen=True, slots=True)
class CellId:
    """Identifies a poisoning experiment cell."""

    stage: ExperimentStage
    dataset: DatasetID
    policy: ThresholdPolicy
    objective: AttackerObjective
    source: PoisoningSourceStrategy
    fraction: float
    target_scope: PoisoningTargetScope
    seed_pair: SeedPair

    @property
    def training_seed(self) -> int:
        """The training seed from the seed pair."""
        return self.seed_pair.training_seed

    @property
    def poisoning_seed(self) -> int:
        """The poisoning seed from the seed pair."""
        return self.seed_pair.poisoning_seed

    def __post_init__(self) -> None:
        """Validate that fraction is within [0.0, 1.0]."""
        if not (0.0 <= self.fraction <= 1.0):
            raise ValueError(f"fraction {self.fraction} is outside [0.0, 1.0]")


@dataclass(frozen=True, slots=True)
class CellPaths:
    """Resolved filesystem paths for a poisoning cell."""

    cell: CellId
    run_dir: Path
    poisoned_scores: Path
    threshold_deltas: Path
    cell_metrics: Path
    seed_record: Path
    provenance: Path
    run_done: Path
    run_in_progress: Path


@dataclass(frozen=True, slots=True)
class PoisonLayout:
    """Directory layout for calibration-poisoning outputs under the conference output root."""

    base_dir: Path

    @property
    def poison_output_root(self) -> Path:
        """The root directory for all calibration-poisoning outputs."""
        return self.base_dir / CALIBRATION_POISONING_OUTPUT_ROOT

    def run_dir(self, cell: CellId) -> Path:
        """Return the run directory for a poisoning cell."""
        return (
            self.poison_output_root
            / cell.stage.value
            / cell.dataset.value
            / cell.policy.value
            / cell.objective.value
            / cell.source.value
            / f"{PathToken.FRACTION_PREFIX}{cell.fraction:.2f}"
            / f"{PathToken.SCOPE_PREFIX}{cell.target_scope.value}"
            / f"{PathToken.TRAIN_PREFIX}{cell.training_seed}"
            / f"{PathToken.POISON_PREFIX}{cell.poisoning_seed}"
        )

    def cell_paths(self, cell: CellId) -> CellPaths:
        """Return CellPaths for a poisoning cell."""
        rd = self.run_dir(cell)
        return CellPaths(
            cell=cell,
            run_dir=rd,
            poisoned_scores=rd / RunFile.POISONED_SCORES,
            threshold_deltas=rd / RunFile.THRESHOLD_DELTAS,
            cell_metrics=rd / RunFile.CELL_METRICS,
            seed_record=rd / RunFile.SEED_RECORD,
            provenance=rd / RunFile.PROVENANCE,
            run_done=rd / RunFile.RUN_DONE,
            run_in_progress=rd / RunFile.RUN_IN_PROGRESS,
        )

    def project_audit_report(self) -> Path:
        """Return path to the project audit report manifest."""
        return self.poison_output_root / ManifestFile.PROJECT_AUDIT_REPORT

    def clean_score_artifacts_manifest(self) -> Path:
        """Return path to the clean score artifacts manifest."""
        return self.poison_output_root / ManifestFile.CLEAN_SCORE_ARTIFACTS

    def nbaiot_main_manifest(self) -> Path:
        """Return path to the N-BaIoT main experiment manifest."""
        return self.poison_output_root / ManifestFile.NBAIOT_MAIN_MANIFEST

    def paper_figure_manifest(self) -> Path:
        """Return path to the paper figure manifest."""
        return self.poison_output_root / ManifestFile.PAPER_FIGURE_MANIFEST
