"""CP2 stage-scoped configuration layout.

Each CP2 stage maps to a fixed (scale, dataset) pair, a gate requirement,
and a flag indicating whether experiment execution is permitted. Heavy stages
require explicit gate authorization; no stage triggers a run by default in
Phase B.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from datp.attacks.poison_enums import ExperimentScale


class Cp2Stage(enum.StrEnum):
    """Canonical CP2 execution stages, ordered from lightest to heaviest."""

    COMMON = "common"
    AUDIT_READONLY = "audit_readonly"
    NBAIOT_SMOKE = "nbaiot_smoke"
    NBAIOT_MVP = "nbaiot_mvp"
    NBAIOT_FULL = "nbaiot_full"
    CICIOT2023_STRETCH = "ciciot2023_stretch"
    PAPER_FIGURES = "paper_figures"


@dataclass(frozen=True, slots=True)
class Cp2StageConfig:
    """Metadata for one CP2 execution stage.

    Attributes:
        stage: Canonical stage identifier.
        scale: Experiment scale, or None for non-execution stages.
        dataset: Target dataset, or None for cross-dataset stages.
        allow_run: Whether this stage may trigger experiment execution.
            False until this stage's own ``gate`` ticket is actually
            complete, then flipped to True for exactly that stage — not a
            blanket Phase-B/CP2-T056 switch. NBAIOT_SMOKE (gate CP2-T043)
            and NBAIOT_MVP (gate CP2-T044) are True because those tickets
            are done; NBAIOT_FULL/CICIOT2023_STRETCH/PAPER_FIGURES remain
            False because FB3/FB4/CP2-T057 are not yet satisfied.
        gate: Authorization gate required before allow_run is meaningful
            (e.g. "FB3", "FB4", "CP2-T056"). None means no additional gate.
        description: Human-readable summary for CLI output.
    """

    stage: Cp2Stage
    scale: ExperimentScale | None
    dataset: str | None
    allow_run: bool
    gate: str | None
    description: str


# ---------------------------------------------------------------------------
# Canonical stage registry — one entry per Cp2Stage value.
# ---------------------------------------------------------------------------

_STAGE_CONFIGS: dict[Cp2Stage, Cp2StageConfig] = {
    Cp2Stage.COMMON: Cp2StageConfig(
        stage=Cp2Stage.COMMON,
        scale=None,
        dataset=None,
        allow_run=False,
        gate=None,
        description="Shared CP2 constants and settings; no experiment execution.",
    ),
    Cp2Stage.AUDIT_READONLY: Cp2StageConfig(
        stage=Cp2Stage.AUDIT_READONLY,
        scale=None,
        dataset=None,
        allow_run=False,
        gate=None,
        description="Read-only artifact audit; validates provenance, no writes.",
    ),
    Cp2Stage.NBAIOT_SMOKE: Cp2StageConfig(
        stage=Cp2Stage.NBAIOT_SMOKE,
        scale=ExperimentScale.SMOKE,
        dataset="nbaiot",
        allow_run=True,
        gate="CP2-T043",
        description=(
            "N-BaIoT real-data smoke diagnostics (scale=SMOKE; one-seed/"
            "one-victim and one-seed/all-victims) validating pipeline "
            "end-to-end on real clean scores. No paper-quality results. "
            "Phase E gate — distinct from the Phase G CP2-T056 final "
            "experiment. CP2-T043 complete (2026-06-16): directionally "
            "correct, feasible, real-data diagnostics — allow_run=True."
        ),
    ),
    Cp2Stage.NBAIOT_MVP: Cp2StageConfig(
        stage=Cp2Stage.NBAIOT_MVP,
        scale=ExperimentScale.MVP,
        dataset="nbaiot",
        allow_run=True,
        gate="CP2-T044",
        description=(
            "N-BaIoT bounded MVP run (scale=MVP, fractions={0,0.10,0.20,0.40}, "
            "5 seed pairs, policies B1/B2/B4). "
            "Primary Phase E result set — gated by CP2-T044 (run plan locked "
            "+ mu_flag_threshold fixed from clean data), not by CP2-T056: "
            "CP2-T056 depends on CP2-T049, which depends on these MVP "
            "results, so CP2-T056 cannot be a prerequisite for this stage. "
            "CP2-T044 complete (2026-06-16): 1620-cell bounded matrix locked, "
            "per-seed mu_flag_threshold locked, multi-seed stability "
            "confirmed — allow_run=True, restricted to exactly this matrix."
        ),
    ),
    Cp2Stage.NBAIOT_FULL: Cp2StageConfig(
        stage=Cp2Stage.NBAIOT_FULL,
        scale=ExperimentScale.FULL,
        dataset="nbaiot",
        allow_run=False,
        gate="FB3",
        description=(
            "N-BaIoT full run (scale=FULL, adds fraction=0.05). "
            "Gated by FB3 MVP-result gate; requires FB3 CONTINUE decision."
        ),
    ),
    Cp2Stage.CICIOT2023_STRETCH: Cp2StageConfig(
        stage=Cp2Stage.CICIOT2023_STRETCH,
        scale=ExperimentScale.STRETCH,
        dataset="ciciot2023",
        allow_run=False,
        gate="FB4",
        description=(
            "CICIoT2023 stretch run (scale=STRETCH). "
            "Gated by FB4 feasibility gate; requires FB4 CONTINUE decision."
        ),
    ),
    Cp2Stage.PAPER_FIGURES: Cp2StageConfig(
        stage=Cp2Stage.PAPER_FIGURES,
        scale=None,
        dataset=None,
        allow_run=False,
        gate="CP2-T057",
        description=(
            "Generate CP2 paper figures and tables from final analysis. "
            "Blocked until CP2-T057 analysis authorization."
        ),
    ),
}


def get_stage_config(stage: Cp2Stage) -> Cp2StageConfig:
    """Return the canonical config for a CP2 stage."""
    return _STAGE_CONFIGS[stage]


def all_stage_configs() -> list[Cp2StageConfig]:
    """Return all stage configs in canonical stage order."""
    return [_STAGE_CONFIGS[s] for s in Cp2Stage]
