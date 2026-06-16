"""CP2-specific enums — canonical, single home for all attack/experiment protocol enums.

Do not duplicate in other modules; import from here.
"""

from __future__ import annotations

import enum


class ThresholdPolicy(enum.StrEnum):
    """CP2 default threshold policies.

    B3 (family threshold) is excluded by protocol — it is DATP substrate only.
    """

    B1_GLOBAL = "b1_global"
    B2_PERSONALIZED = "b2_personalized"
    B4_CLUSTER = "b4_cluster"


class AttackerObjective(enum.StrEnum):
    """What the attacker aims to achieve by poisoning the calibration set.

    Replaces the retired legacy PoisoningObjective enum.
    """

    THRESHOLD_RAISE = "threshold_raise"
    THRESHOLD_LOWER = "threshold_lower"


class PoisoningSourceStrategy(enum.StrEnum):
    """Reservoir sampling strategy for poisoned-value selection.

    All sources are victim-local. Test scores are never a reservoir.
    """

    RANDOM_BENIGN = "random_benign"
    HIGH_SCORE_BENIGN = "high_score_benign"
    LOW_SCORE_BENIGN = "low_score_benign"
    LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY = (
        "low_score_targeted_removal_diagnostic_only"
    )


class CalibrationInjectionRule(enum.StrEnum):
    """How poisoned values replace calibration entries.

    REPLACE_FIXED_BUDGET: m_i = max(1, round(f * n_i)) positions replaced with
    values resampled with replacement from the victim-local reservoir.
    Cardinality n_i is preserved. No shift_magnitude.
    """

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


class ExperimentScale(enum.StrEnum):
    """Experiment execution scale gate."""

    SMOKE = "smoke"
    MVP = "mvp"
    FULL = "full"
    STRETCH = "stretch"


class AuditDisposition(enum.StrEnum):
    """Audit verdict for a code artifact during Phase-A review."""

    KEEP_CORE = "keep_core"
    REFACTOR_CORE = "refactor_core"
    QUARANTINE_JOURNAL = "quarantine_journal"
    REMOVE_STALE = "remove_stale"
    BLOCK_UNSAFE = "block_unsafe"


# Locked MVP fraction grid — do not extend without a ticket.
CP2_MVP_FRACTIONS: tuple[float, ...] = (0.0, 0.10, 0.20, 0.40)

# Default CP2 threshold policies in iteration order.
CP2_DEFAULT_POLICIES: tuple[ThresholdPolicy, ...] = (
    ThresholdPolicy.B1_GLOBAL,
    ThresholdPolicy.B2_PERSONALIZED,
    ThresholdPolicy.B4_CLUSTER,
)

# MVP objectives.
CP2_MVP_OBJECTIVES: tuple[AttackerObjective, ...] = (
    AttackerObjective.THRESHOLD_RAISE,
    AttackerObjective.THRESHOLD_LOWER,
)

# MVP source strategies.
CP2_MVP_SOURCES: tuple[PoisoningSourceStrategy, ...] = (
    PoisoningSourceStrategy.RANDOM_BENIGN,
    PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
    PoisoningSourceStrategy.LOW_SCORE_BENIGN,
)
