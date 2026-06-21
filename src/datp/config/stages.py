"""Stage-scoped configuration for the calibration-poisoning experiments.

Each stage maps to a fixed dataset, an authorization gate, and a flag indicating
whether experiment execution is permitted. Heavy stages require explicit gate
authorization; no stage triggers a run by default.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from datp.core.enums import DatasetID


class ExperimentStage(enum.StrEnum):
    """Canonical execution stages, ordered from lightest to heaviest."""

    FINAL_AUDIT = "final_audit"
    SYNTHETIC_SMOKE = "synthetic_smoke"
    NBAIOT_MAIN = "nbaiot_main"
    NBAIOT_FULL_OPTIONAL = "nbaiot_full_optional"
    STRETCH_DIAGNOSTIC_ONLY = "stretch_diagnostic_only"


@dataclass(frozen=True, slots=True)
class ExperimentStageConfig:
    """Metadata for one execution stage.

    Attributes:
        stage: Canonical stage identifier.
        dataset: Target dataset, or None for cross-dataset stages.
        allow_run: Whether this stage may trigger experiment execution.
            False until this stage's gate is satisfied, then flipped to True
            for exactly that stage.
        gate: Authorization gate that must be resolved before a run is
            permitted (a short domain label).
        description: Human-readable summary for CLI output.
    """

    stage: ExperimentStage
    dataset: DatasetID | None
    allow_run: bool
    gate: str | None
    description: str


# ---------------------------------------------------------------------------
# Canonical stage registry — one entry per ExperimentStage value.
# ---------------------------------------------------------------------------

_STAGE_CONFIGS: dict[ExperimentStage, ExperimentStageConfig] = {
    ExperimentStage.FINAL_AUDIT: ExperimentStageConfig(
        stage=ExperimentStage.FINAL_AUDIT,
        dataset=None,
        allow_run=False,
        gate="final_audit_pass",
        description="Protocol audit and provenance validation before execution.",
    ),
    ExperimentStage.SYNTHETIC_SMOKE: ExperimentStageConfig(
        stage=ExperimentStage.SYNTHETIC_SMOKE,
        dataset=None,
        allow_run=True,
        gate="smoke_diagnostics_signoff",
        description="Synthetic invariant validation; must pass before N-BaIoT main.",
    ),
    ExperimentStage.NBAIOT_MAIN: ExperimentStageConfig(
        stage=ExperimentStage.NBAIOT_MAIN,
        dataset=DatasetID.NBAIOT,
        allow_run=True,
        gate="nbaiot_main_run_lock",
        description="Primary N-BaIoT single-client calibration-poisoning experiment.",
    ),
    ExperimentStage.NBAIOT_FULL_OPTIONAL: ExperimentStageConfig(
        stage=ExperimentStage.NBAIOT_FULL_OPTIONAL,
        dataset=DatasetID.NBAIOT,
        allow_run=False,
        gate="full_scope_continue_decision",
        description="Optional multi-client extension (pairs and triples).",
    ),
    ExperimentStage.STRETCH_DIAGNOSTIC_ONLY: ExperimentStageConfig(
        stage=ExperimentStage.STRETCH_DIAGNOSTIC_ONLY,
        dataset=DatasetID.CICIOT2023,
        allow_run=False,
        gate="ciciot_feasibility_decision",
        description="Optional CICIoT2023 pseudo-client diagnostic contrast.",
    ),
}


def get_stage_config(stage: ExperimentStage) -> ExperimentStageConfig:
    """Return the canonical config for a stage."""
    return _STAGE_CONFIGS[stage]


def all_stage_configs() -> list[ExperimentStageConfig]:
    """Return all stage configs in canonical stage order."""
    return [_STAGE_CONFIGS[s] for s in ExperimentStage]
