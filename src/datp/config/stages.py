"""Stage-scoped configuration for the calibration-poisoning experiments.

Each stage maps to a fixed (scale, dataset) pair, an authorization gate, and a
flag indicating whether experiment execution is permitted. Heavy stages require
explicit gate authorization; no stage triggers a run by default.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from datp.core.poison_enums import ExperimentScale
from datp.data.catalog import DatasetID


class ExperimentStage(enum.StrEnum):
    """Canonical execution stages, ordered from lightest to heaviest."""

    COMMON = "common"
    AUDIT_READONLY = "audit_readonly"
    NBAIOT_SMOKE = "nbaiot_smoke"
    NBAIOT_BOUNDED = "nbaiot_bounded"
    NBAIOT_FULL = "nbaiot_full"
    CICIOT2023_STRETCH = "ciciot2023_stretch"
    PAPER_FIGURES = "paper_figures"


@dataclass(frozen=True, slots=True)
class ExperimentStageConfig:
    """Metadata for one execution stage.

    Attributes:
        stage: Canonical stage identifier.
        scale: Experiment scale, or None for non-execution stages.
        dataset: Target dataset, or None for cross-dataset stages.
        allow_run: Whether this stage may trigger experiment execution.
            False until this stage's gate is satisfied, then flipped to True
            for exactly that stage. The N-BaIoT smoke and bounded stages are
            enabled; the full, stretch, and paper-figure stages remain gated.
        gate: Authorization gate that must be resolved before a run is
            permitted (a short domain label). None means no additional gate.
        description: Human-readable summary for CLI output.
    """

    stage: ExperimentStage
    scale: ExperimentScale | None
    dataset: DatasetID | None
    allow_run: bool
    gate: str | None
    description: str


# ---------------------------------------------------------------------------
# Canonical stage registry — one entry per ExperimentStage value.
# ---------------------------------------------------------------------------

_STAGE_CONFIGS: dict[ExperimentStage, ExperimentStageConfig] = {
    ExperimentStage.COMMON: ExperimentStageConfig(
        stage=ExperimentStage.COMMON,
        scale=None,
        dataset=None,
        allow_run=False,
        gate=None,
        description="Shared constants and settings; no experiment execution.",
    ),
    ExperimentStage.AUDIT_READONLY: ExperimentStageConfig(
        stage=ExperimentStage.AUDIT_READONLY,
        scale=None,
        dataset=None,
        allow_run=False,
        gate=None,
        description="Read-only artifact audit; validates provenance, no writes.",
    ),
    ExperimentStage.NBAIOT_SMOKE: ExperimentStageConfig(
        stage=ExperimentStage.NBAIOT_SMOKE,
        scale=ExperimentScale.SMOKE,
        dataset=DatasetID.NBAIOT,
        allow_run=True,
        gate="smoke_diagnostics_signoff",
        description=(
            "N-BaIoT real-data smoke diagnostics (scale=SMOKE; one-seed/"
            "one-victim and one-seed/all-victims) validating the pipeline "
            "end-to-end on real clean scores. No paper-quality results."
        ),
    ),
    ExperimentStage.NBAIOT_BOUNDED: ExperimentStageConfig(
        stage=ExperimentStage.NBAIOT_BOUNDED,
        scale=ExperimentScale.BOUNDED,
        dataset=DatasetID.NBAIOT,
        allow_run=True,
        gate="bounded_run_lock",
        description=(
            "N-BaIoT bounded run (scale=BOUNDED, fractions={0,0.10,0.20,0.40}, "
            "5 seed pairs, policies B1/B2/B4) over the locked 1620-cell "
            "matrix with per-seed mu_flag_threshold fixed from clean data. "
            "Primary bounded result set, restricted to exactly this matrix."
        ),
    ),
    ExperimentStage.NBAIOT_FULL: ExperimentStageConfig(
        stage=ExperimentStage.NBAIOT_FULL,
        scale=ExperimentScale.FULL,
        dataset=DatasetID.NBAIOT,
        allow_run=False,
        gate="full_scope_continue_decision",
        description=(
            "N-BaIoT full run (scale=FULL, adds fraction=0.05). "
            "Requires a CONTINUE decision on the full-scope gate."
        ),
    ),
    ExperimentStage.CICIOT2023_STRETCH: ExperimentStageConfig(
        stage=ExperimentStage.CICIOT2023_STRETCH,
        scale=ExperimentScale.STRETCH,
        dataset=DatasetID.CICIOT2023,
        allow_run=False,
        gate="ciciot_feasibility_decision",
        description=(
            "CICIoT2023 stretch run (scale=STRETCH). "
            "Requires a CONTINUE decision on the feasibility gate."
        ),
    ),
    ExperimentStage.PAPER_FIGURES: ExperimentStageConfig(
        stage=ExperimentStage.PAPER_FIGURES,
        scale=None,
        dataset=None,
        allow_run=False,
        gate="final_analysis_authorization",
        description=(
            "Generate paper figures and tables from the final analysis. "
            "Blocked until final-analysis authorization."
        ),
    ),
}


def get_stage_config(stage: ExperimentStage) -> ExperimentStageConfig:
    """Return the canonical config for a stage."""
    return _STAGE_CONFIGS[stage]


def all_stage_configs() -> list[ExperimentStageConfig]:
    """Return all stage configs in canonical stage order."""
    return [_STAGE_CONFIGS[s] for s in ExperimentStage]
