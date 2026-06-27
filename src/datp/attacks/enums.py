"""Attack protocol enums and small enum-derived predicates."""

from __future__ import annotations

import enum

__all__ = [
    "AttackerObjective",
    "CalibrationInjectionRule",
    "DIAGNOSTIC_ONLY_KNOWLEDGE",
    "DIAGNOSTIC_ONLY_SCOPES",
    "DIAGNOSTIC_ONLY_SOURCES",
    "PoisoningDefense",
    "PoisoningKnowledge",
    "PoisoningSourceStrategy",
    "PoisoningTargetScope",
    "ReservoirStatus",
    "is_diagnostic_knowledge",
    "is_diagnostic_scope",
    "is_diagnostic_source",
    "objective_for_source",
]


class AttackerObjective(enum.StrEnum):
    """What the attacker aims to achieve by poisoning the calibration set."""

    THRESHOLD_RAISE = "threshold_raise"
    THRESHOLD_LOWER = "threshold_lower"


class PoisoningSourceStrategy(enum.StrEnum):
    """Reservoir sampling strategy for poisoned-value selection."""

    RANDOM_BENIGN = "random_benign"
    HIGH_SCORE_BENIGN = "high_score_benign"
    LOW_SCORE_BENIGN = "low_score_benign"
    LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY = (
        "low_score_targeted_removal_diagnostic_only"
    )


class CalibrationInjectionRule(enum.StrEnum):
    """How poisoned values replace calibration entries."""

    REPLACE_FIXED_BUDGET = "replace_fixed_budget"


class PoisoningKnowledge(enum.StrEnum):
    """Attacker knowledge model."""

    GRAY_BOX_SCORE_ACCESS = "gray_box_score_access"
    WHITE_BOX_DIAGNOSTIC_ONLY = "white_box_diagnostic_only"


class PoisoningTargetScope(enum.StrEnum):
    """Which clients the attacker targets in one poisoning pass."""

    SINGLE_CLIENT = "single_client"
    MULTI_CLIENT = "multi_client"
    ALL_CLIENTS_DIAGNOSTIC_ONLY = "all_clients_diagnostic_only"


class PoisoningDefense(enum.StrEnum):
    """Defense applied to the calibration set before threshold derivation, if any."""

    NONE = "none"
    TRIMMED_CALIBRATION = "trimmed_calibration"


class ReservoirStatus(enum.StrEnum):
    """Outcome of reservoir construction for a victim client."""

    FEASIBLE = "feasible"
    INFEASIBLE_DEGENERATE_TAIL = "infeasible_degenerate_tail"


DIAGNOSTIC_ONLY_SOURCES: frozenset[PoisoningSourceStrategy] = frozenset(
    {
        PoisoningSourceStrategy.LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY,
    }
)

DIAGNOSTIC_ONLY_SCOPES: frozenset[PoisoningTargetScope] = frozenset(
    {
        PoisoningTargetScope.ALL_CLIENTS_DIAGNOSTIC_ONLY,
    }
)

DIAGNOSTIC_ONLY_KNOWLEDGE: frozenset[PoisoningKnowledge] = frozenset(
    {
        PoisoningKnowledge.WHITE_BOX_DIAGNOSTIC_ONLY,
    }
)


def objective_for_source(
    source: PoisoningSourceStrategy,
) -> AttackerObjective | None:
    """Return the implied attacker objective for a source strategy, or None if unconstrained."""
    match source:
        case PoisoningSourceStrategy.HIGH_SCORE_BENIGN:
            return AttackerObjective.THRESHOLD_RAISE
        case (
            PoisoningSourceStrategy.LOW_SCORE_BENIGN
            | PoisoningSourceStrategy.LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY
        ):
            return AttackerObjective.THRESHOLD_LOWER
        case _:
            return None


def is_diagnostic_source(source: PoisoningSourceStrategy) -> bool:
    """Return True if *source* is a diagnostic-only variant."""
    return source in DIAGNOSTIC_ONLY_SOURCES


def is_diagnostic_scope(scope: PoisoningTargetScope) -> bool:
    """Return True if *scope* is a diagnostic-only variant."""
    return scope in DIAGNOSTIC_ONLY_SCOPES


def is_diagnostic_knowledge(knowledge: PoisoningKnowledge) -> bool:
    """Return True if *knowledge* is a diagnostic-only variant."""
    return knowledge in DIAGNOSTIC_ONLY_KNOWLEDGE
