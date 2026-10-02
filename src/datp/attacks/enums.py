
from __future__ import annotations

import enum

__all__ = [
    "AttackerObjective",
    "ClaimClassification",
    "CalibrationInjectionRule",
    "DIAGNOSTIC_ONLY_SOURCES",
    "PoisoningDefense",
    "PoisoningKnowledge",
    "PoisoningSourceStrategy",
    "PoisoningTargetScope",
    "ReservoirMode",
    "ReservoirDraw",
    "ReservoirStatus",
    "SplitSemantics",
    "SYNTHESIZED_DRAWS",
    "is_diagnostic_source",
    "objective_for_source",
]


class AttackerObjective(enum.StrEnum):

    THRESHOLD_RAISE = "threshold_raise"
    THRESHOLD_LOWER = "threshold_lower"


class ClaimClassification(enum.StrEnum):

    CALIBRATION_INSTABILITY = "calibration_instability"
    FULL_VULNERABILITY = "full_vulnerability"
    MECHANISM_ONLY = "mechanism_only"
    NULL_OR_CONDITIONAL = "null_or_conditional"


class ThresholdScaleScenario(enum.StrEnum):

    RAW_CLEAN = "raw_clean"
    RAW_POISONED = "raw_pois"
    NORMALIZED_CLEAN = "norm_clean"
    NORMALIZED_POISONED = "norm_pois"


class PoisoningSourceStrategy(enum.StrEnum):

    RANDOM_BENIGN = "random_benign"
    HIGH_SCORE_BENIGN = "high_score_benign"
    LOW_SCORE_BENIGN = "low_score_benign"
    LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY = (
        "low_score_targeted_removal_diagnostic_only"
    )


class CalibrationInjectionRule(enum.StrEnum):

    REPLACE_FIXED_BUDGET = "replace_fixed_budget"


class SplitSemantics(enum.StrEnum):

    CHRONOLOGICAL_BENIGN_ONLY_60_1_20_1_18 = (
        "chronological_benign_only_60_1_20_1_18"
    )


class ReservoirMode(enum.StrEnum):

    VICTIM_LOCAL_BENIGN_CAL_SOURCE_PRECEDENCE_RULE_2 = (
        "victim_local_benign_cal_source_precedence_rule_2"
    )


class ManifestProvenanceSource(enum.StrEnum):
    NBAIOT_MAIN_SWEEP = "nbaiot_main_manifest"


class ReservoirDraw(enum.StrEnum):

    WITH_REPLACEMENT = "with_replacement"
    WITHOUT_REPLACEMENT = "without_replacement"
    DISJOINT_RESERVOIR = "disjoint_reservoir"
    INTERPOLATED_TAIL = "interpolated_tail"


class SeedAggregationMethod(enum.StrEnum):

    MEAN = "mean"
    MAXIMUM = "max"


SYNTHESIZED_DRAWS: frozenset[ReservoirDraw] = frozenset(
    {ReservoirDraw.INTERPOLATED_TAIL}
)


class PoisoningKnowledge(enum.StrEnum):

    GRAY_BOX_SCORE_ACCESS = "gray_box_score_access"


class PoisoningTargetScope(enum.StrEnum):

    SINGLE_CLIENT = "single_client"
    MULTI_CLIENT = "multi_client"


class PoisoningDefense(enum.StrEnum):

    NONE = "none"
    TRIMMED_CALIBRATION = "trimmed_calibration"


class ReservoirStatus(enum.StrEnum):

    FEASIBLE = "feasible"
    INFEASIBLE_DEGENERATE_TAIL = "infeasible_degenerate_tail"


DIAGNOSTIC_ONLY_SOURCES: frozenset[PoisoningSourceStrategy] = frozenset(
    {
        PoisoningSourceStrategy.LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY,
    }
)


def objective_for_source(
    source: PoisoningSourceStrategy,
) -> AttackerObjective | None:
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
    return source in DIAGNOSTIC_ONLY_SOURCES
