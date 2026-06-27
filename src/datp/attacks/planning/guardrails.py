"""Scientific guardrails: mutation checks, fraction grids, and source-objective validity."""

from __future__ import annotations

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
    """Raised when a guardrail assertion fails."""


def assert_no_inplace_mutation(
    original: np.ndarray,
    after: np.ndarray,
    label: str = "calibration array",
) -> None:
    """Raise if the array was mutated in-place rather than operating on a copy."""
    if not np.array_equal(original, after):
        raise GuardrailError(f"Clean {label} was mutated in place. Operate on a copy.")


def assert_reservoir_not_test_or_training(reservoir_source: ScoringStage) -> None:
    """Raise if the reservoir source is test-benign or test-attack data."""
    if reservoir_source in {ScoringStage.TEST_BENIGN, ScoringStage.TEST_ATTACK}:
        raise GuardrailError(f"Reservoir source {reservoir_source!r} is forbidden.")


def assert_fractions_in_locked_grid(
    fractions: Iterable[float],
    stage: ExperimentStage,
) -> None:
    """Raise if any fraction is not in the locked grid for the given stage."""
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
    """Raise if NBAIOT_MAIN stage is used with a non-single-client target scope."""
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
    """Raise if the source strategy does not imply the given attacker objective."""
    if (expected := objective_for_source(source)) is not None and objective != expected:
        raise GuardrailError(
            f"Source {source!r} requires objective {expected!r}; got {objective!r}."
        )
