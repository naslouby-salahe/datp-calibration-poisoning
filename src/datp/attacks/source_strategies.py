"""Source strategy dispatch for calibration poisoning.

Three bounded sweep strategies:
  RANDOM_BENIGN — full victim pool (negative control, near-null criterion).
  HIGH_SCORE_BENIGN — upper tail_mass fraction → threshold rises.
  LOW_SCORE_BENIGN — lower tail_mass fraction → threshold lowers.

Diagnostic-only strategy (never in main matrix, never in gray-box claims):
  LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY — requires explicit allow_diagnostic=True.

Near-null criterion for RANDOM: |Δτ| ≤ delta_tau_null_threshold is an audit flag,
not an auto-kill. Evaluation logic decides whether to flag, not this module.
"""

from __future__ import annotations

import numpy as np

from datp.attacks.enums import (
    PoisoningSourceStrategy,
    is_diagnostic_source,
)
from datp.attacks.guardrails import assert_reservoir_not_test_or_training
from datp.attacks.reservoir import ReservoirResult, build_reservoir
from datp.core.enums import ScoringStage

# bounded source strategies — fixed by scientific protocol.
_BOUNDED_SOURCES: frozenset[PoisoningSourceStrategy] = frozenset(
    {
        PoisoningSourceStrategy.RANDOM_BENIGN,
        PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        PoisoningSourceStrategy.LOW_SCORE_BENIGN,
    }
)


# Diagnostic-only sources — gated behind allow_diagnostic.
def _select_reservoir(
    *,
    source: PoisoningSourceStrategy,
    clean_cal: np.ndarray,
    tail_mass: float,
    allow_diagnostic: bool = False,
    reservoir_stage: ScoringStage = ScoringStage.CAL,
) -> ReservoirResult:
    """Select the victim-local reservoir for the given source strategy.

    Raises DiagnosticSourceError if source is diagnostic-only and
    allow_diagnostic is False. This ensures diagnostic sources never silently
    enter the main experiment matrix.

    ``reservoir_stage`` must be ScoringStage.CAL; the guardrail asserts this
    so that test and training stages are rejected if accidentally passed.
    """
    assert_reservoir_not_test_or_training(reservoir_stage)
    if is_diagnostic_source(source) and not allow_diagnostic:
        raise DiagnosticSourceError(
            f"Source {source!r} is diagnostic-only. Pass allow_diagnostic=True "
            "to use it explicitly. It must not enter the bounded/full matrix."
        )
    return build_reservoir(clean_cal=clean_cal, source=source, tail_mass=tail_mass)


class DiagnosticSourceError(ValueError):
    """Raised when a diagnostic source is used without allow_diagnostic=True."""


def near_null_criterion(
    *,
    delta_tau: float,
    delta_tau_null_threshold: float,
) -> bool:
    """Audit flag for RANDOM_BENIGN near-null criterion.

    Returns True if |Δτ| ≤ delta_tau_null_threshold (near-null, as expected
    for a negative control). This is an AUDIT FLAG, not an auto-kill.
    The caller decides what to do with the result.

    Use this after RANDOM_BENIGN injection to verify the negative control behaves
    as expected. A False result should be logged as an anomaly for review.
    """
    return abs(delta_tau) <= delta_tau_null_threshold
