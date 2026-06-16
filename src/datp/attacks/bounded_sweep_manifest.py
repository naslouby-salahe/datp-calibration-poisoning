"""Typed schema for the bounded N-BaIoT manifest+results artifact.

The filename is locked (``ManifestFile.NBAIOT_BOUNDED_SWEEP_MANIFEST`` =
``nbaiot_bounded_sweep_manifest.json``, see ``PoisonLayout.nbaiot_bounded_sweep_manifest()``). One
file holds run-level provenance plus the full embedded results array for the
locked 1620-cell matrix — there is no per-victim directory tree for the
bounded sweep. This is architecturally distinct from ``RunManifest``
(``CellId``/``PoisonLayout.cell_paths()``), which is the full-scope, per-cell
manifest and has no victim dimension of its
own. No change to that schema was made or is needed here.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

from datp.attacks.poison_enums import (
    AttackerObjective,
    CalibrationInjectionRule,
    ExperimentScale,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ThresholdPolicy,
)
from datp.attacks.run_manifest import (
    RESERVOIR_MODE,
    ProvenanceRecord,
    SeedRecordModel,
)


class BoundedSweepResultRow(BaseModel):
    """One bounded cell result.

    Carries the victim's own Δτ family entry, fleet-FPR dispersion metrics,
    the AUROC-invariance check outcome, and blast-radius/spillover summaries
    — enough to audit, evaluate kill-triggers, and
    drift-check without re-running the pipeline.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    policy: ThresholdPolicy
    source: PoisoningSourceStrategy
    objective: AttackerObjective | None
    fraction: float
    target_scope: PoisoningTargetScope
    victim_id: str
    training_seed: int
    poisoning_seed: int
    seed_record: SeedRecordModel

    delta_tau: float
    delta_tau_rel: float
    is_victim_significant: bool

    cv_fpr: float
    mean_fpr: float
    coverage_ratio: float
    n_eligible: int
    mu_flag_triggered: bool

    auroc_invariant: bool

    blast_fraction: float
    n_blast_significant: int
    n_spillover: int
    n_non_victims: int


class BoundedSweepManifest(BaseModel):
    """Run-level provenance + embedded results array for the bounded N-BaIoT."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1"
    generated_at_utc: str
    dataset: str = "nbaiot"
    scale: ExperimentScale = ExperimentScale.BOUNDED
    injection_rule: CalibrationInjectionRule = (
        CalibrationInjectionRule.REPLACE_FIXED_BUDGET
    )
    target_scope: PoisoningTargetScope = PoisoningTargetScope.SINGLE_CLIENT
    reservoir_mode: str = RESERVOIR_MODE
    provenance: ProvenanceRecord

    policies: tuple[ThresholdPolicy, ...]
    sources: tuple[PoisoningSourceStrategy, ...]
    fractions: tuple[float, ...]
    training_seeds: tuple[int, ...]
    poisoning_seeds: tuple[int, ...]

    mu_flag_threshold_by_training_seed: dict[int, float]

    n_cells: int
    results: tuple[BoundedSweepResultRow, ...]

    @model_validator(mode="after")
    def _check_consistency(self) -> "BoundedSweepManifest":
        if len(self.training_seeds) != len(self.poisoning_seeds):
            raise ValueError("training_seeds and poisoning_seeds must be paired 1:1")
        if len(self.results) != self.n_cells:
            raise ValueError(
                f"n_cells={self.n_cells} does not match len(results)={len(self.results)}"
            )
        if set(self.mu_flag_threshold_by_training_seed) != set(self.training_seeds):
            raise ValueError(
                "mu_flag_threshold_by_training_seed must have exactly one entry "
                "per training seed"
            )
        return self
