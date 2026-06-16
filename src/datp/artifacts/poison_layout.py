"""CP2 canonical run-path builder.

Single owner of all CP2 output path construction. Do not scatter path-string
construction across modules — import and call from here.

Canonical path structure:
    outputs/conference_calibration_poisoning/
        <scale>/
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
    CP2_OUTPUT_ROOT,
    Cp2ManifestFile,
    Cp2RunFile,
)
from datp.attacks.poison_enums import (
    AttackerObjective,
    ExperimentScale,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ThresholdPolicy,
)


@dataclass(frozen=True, slots=True)
class Cp2CellId:
    """Identity of one CP2 experiment cell.

    A cell = one (policy, objective, source, fraction, scope, training_seed,
    poisoning_seed) tuple under a fixed (scale, dataset).
    """

    scale: ExperimentScale
    dataset: str
    policy: ThresholdPolicy
    objective: AttackerObjective
    source: PoisoningSourceStrategy
    fraction: float
    target_scope: PoisoningTargetScope
    training_seed: int
    poisoning_seed: int

    def __post_init__(self) -> None:
        if not (0.0 <= self.fraction <= 1.0):
            raise ValueError(
                f"fraction {self.fraction} is outside [0.0, 1.0]"
            )
        if not self.dataset:
            raise ValueError("dataset must not be empty")


@dataclass(frozen=True, slots=True)
class Cp2CellPaths:
    """Resolved canonical paths for one CP2 experiment cell."""

    cell: Cp2CellId
    run_dir: Path
    poisoned_scores: Path
    threshold_deltas: Path
    cell_metrics: Path
    seed_record: Path
    provenance: Path
    run_done: Path
    run_in_progress: Path


@dataclass(frozen=True, slots=True)
class Cp2Layout:
    """Canonical artifact layout for CP2 runs.

    All path construction goes through this class. ``base_dir`` is the
    repository-level ``outputs/`` directory.
    """

    base_dir: Path

    @property
    def cp2_root(self) -> Path:
        """Root for all CP2 outputs: <base_dir>/conference_calibration_poisoning/"""
        return self.base_dir / CP2_OUTPUT_ROOT

    def _fraction_segment(self, fraction: float) -> str:
        return f"f_{fraction:.2f}"

    def _scope_segment(self, scope: PoisoningTargetScope) -> str:
        return f"scope_{scope.value}"

    def _training_seed_segment(self, seed: int) -> str:
        return f"train_{seed}"

    def _poisoning_seed_segment(self, seed: int) -> str:
        return f"poison_{seed}"

    def run_dir(self, cell: Cp2CellId) -> Path:
        """Return the canonical run directory for one CP2 experiment cell."""
        return (
            self.cp2_root
            / cell.scale.value
            / cell.dataset
            / cell.policy.value
            / cell.objective.value
            / cell.source.value
            / self._fraction_segment(cell.fraction)
            / self._scope_segment(cell.target_scope)
            / self._training_seed_segment(cell.training_seed)
            / self._poisoning_seed_segment(cell.poisoning_seed)
        )

    def cell_paths(self, cell: Cp2CellId) -> Cp2CellPaths:
        """Return all canonical file paths for one CP2 experiment cell."""
        rd = self.run_dir(cell)
        return Cp2CellPaths(
            cell=cell,
            run_dir=rd,
            poisoned_scores=rd / Cp2RunFile.POISONED_SCORES,
            threshold_deltas=rd / Cp2RunFile.THRESHOLD_DELTAS,
            cell_metrics=rd / Cp2RunFile.CELL_METRICS,
            seed_record=rd / Cp2RunFile.SEED_RECORD,
            provenance=rd / Cp2RunFile.PROVENANCE,
            run_done=rd / Cp2RunFile.RUN_DONE,
            run_in_progress=rd / Cp2RunFile.RUN_IN_PROGRESS,
        )

    def project_audit_report(self) -> Path:
        return self.cp2_root / Cp2ManifestFile.PROJECT_AUDIT_REPORT

    def clean_score_artifacts_manifest(self) -> Path:
        return self.cp2_root / Cp2ManifestFile.CLEAN_SCORE_ARTIFACTS

    def nbaiot_mvp_manifest(self) -> Path:
        return self.cp2_root / Cp2ManifestFile.NBAIOT_MVP_MANIFEST

    def paper_figure_manifest(self) -> Path:
        return self.cp2_root / Cp2ManifestFile.PAPER_FIGURE_MANIFEST
