
from __future__ import annotations
from datp.types import (
    NarrativeText,
    PoisonFraction,
    ScoreVector,
)

from collections.abc import Iterable

import numpy as np

from datp.attacks.constants import (
    NBAIOT_FULL_OPTIONAL_SWEEP_FRACTION_SET,
    NBAIOT_MAIN_SWEEP_FRACTION_SET,
)
from datp.attacks.enums import (
    AttackerObjective,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    objective_for_source,
)
from datp.config.models import ExperimentStage
from datp.core.enums import ScoringStage


class GuardrailError(ValueError):
    pass


def assert_no_inplace_mutation(
    original: ScoreVector,
    after: ScoreVector,
    label: NarrativeText = "calibration array",
) -> None:
    if not np.array_equal(original, after):
        raise GuardrailError(f"Clean {label} was mutated in place. Operate on a copy.")


def assert_reservoir_not_test_or_training(reservoir_source: ScoringStage) -> None:
    if reservoir_source in {ScoringStage.TEST_BENIGN, ScoringStage.TEST_ATTACK}:
        raise GuardrailError(f"Reservoir source {reservoir_source!r} is forbidden.")


def assert_fractions_in_locked_grid(
    fractions: Iterable[PoisonFraction],
    stage: ExperimentStage,
) -> None:
    allowed = (
        NBAIOT_FULL_OPTIONAL_SWEEP_FRACTION_SET
        if stage == ExperimentStage.NBAIOT_FULL_OPTIONAL
        else NBAIOT_MAIN_SWEEP_FRACTION_SET
    )
    if invalid := set(fractions) - set(allowed):
        raise GuardrailError(
            f"Fractions {invalid} are not in the locked grid for stage {stage!r}."
        )


def assert_bounded_scale_requires_single_client(
    stage: ExperimentStage,
    target_scope: PoisoningTargetScope,
) -> None:
    if (
        stage == ExperimentStage.NBAIOT_MAIN
        and target_scope != PoisoningTargetScope.SINGLE_CLIENT
    ):
        raise GuardrailError(
            f"NBAIOT_MAIN requires SINGLE_CLIENT target scope; got {target_scope!r}."
        )


def assert_valid_source_objective_pair(
    source: PoisoningSourceStrategy,
    objective: AttackerObjective,
) -> None:
    if (expected := objective_for_source(source)) is not None and objective != expected:
        raise GuardrailError(
            f"Source {source!r} requires objective {expected!r}; got {objective!r}."
        )
