"""Canonical run-path builder for calibration-poisoning outputs.

Single owner of all output path construction. Do not scatter path-string
construction across modules — import and call from here.

Canonical path structure:
    outputs/conference_calibration_poisoning/
        <stage>/
            <dataset>/
                <policy>/
                    <objective>/
                        <source>/
                            f_<fraction>/
                                scope_<scope>/
                                    train_<training_seed>/
                                        poison_<poisoning_seed>/
"""

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
    ThresholdPolicy,
)
from datp.core.enums import PathToken
from datp.core.seeds import SeedPair
from datp.data.catalog import DatasetID
from datp.config.stages import ExperimentStage


@dataclass(frozen=True, slots=True)
class CellId:
    """Identity of one experiment cell.

    A cell = one (policy, objective, source, fraction, scope, training_seed,
    poisoning_seed) tuple under a fixed (stage, dataset).
    """

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
        return self.seed_pair.training_seed

    @property
    def poisoning_seed(self) -> int:
        return self.seed_pair.poisoning_seed

    def __post_init__(self) -> None:
        if not (0.0 <= self.fraction <= 1.0):
            raise ValueError(f"fraction {self.fraction} is outside [0.0, 1.0]")


@dataclass(frozen=True, slots=True)
class CellPaths:
    """Resolved canonical paths for one experiment cell."""

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
    """Canonical artifact layout for runs.

    All path construction goes through this class. ``base_dir`` is the
    repository-level ``outputs/`` directory.
    """

    base_dir: Path

    @property
    def poison_output_root(self) -> Path:
        """Root for all outputs: <base_dir>/conference_calibration_poisoning/"""
        return self.base_dir / CALIBRATION_POISONING_OUTPUT_ROOT

    def _fraction_segment(self, fraction: float) -> str:
        return f"{PathToken.FRACTION_PREFIX}{fraction:.2f}"

    def _scope_segment(self, scope: PoisoningTargetScope) -> str:
        return f"{PathToken.SCOPE_PREFIX}{scope.value}"

    def _training_seed_segment(self, seed: int) -> str:
        return f"{PathToken.TRAIN_PREFIX}{seed}"

    def _poisoning_seed_segment(self, seed: int) -> str:
        return f"{PathToken.POISON_PREFIX}{seed}"

    def run_dir(self, cell: CellId) -> Path:
        """Return the canonical run directory for one experiment cell."""
        return (
            self.poison_output_root
            / cell.stage.value
            / cell.dataset.value
            / cell.policy.value
            / cell.objective.value
            / cell.source.value
            / self._fraction_segment(cell.fraction)
            / self._scope_segment(cell.target_scope)
            / self._training_seed_segment(cell.training_seed)
            / self._poisoning_seed_segment(cell.poisoning_seed)
        )

    def cell_paths(self, cell: CellId) -> CellPaths:
        """Return all canonical file paths for one experiment cell."""
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
        return self.poison_output_root / ManifestFile.PROJECT_AUDIT_REPORT

    def clean_score_artifacts_manifest(self) -> Path:
        return self.poison_output_root / ManifestFile.CLEAN_SCORE_ARTIFACTS

    def nbaiot_main_manifest(self) -> Path:
        return self.poison_output_root / ManifestFile.NBAIOT_MAIN_MANIFEST

    def paper_figure_manifest(self) -> Path:
        return self.poison_output_root / ManifestFile.PAPER_FIGURE_MANIFEST
