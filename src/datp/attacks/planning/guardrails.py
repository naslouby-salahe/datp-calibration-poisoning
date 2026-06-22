"""Runtime scientific guardrails for calibration poisoning.

Each guardrail function asserts one protocol invariant and raises
``GuardrailError`` (a ``ValueError``) on violation. Call these at
poisoning-logic boundaries — never inside tight loops.

Guardrails do NOT swallow exceptions or silently return False.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np

from datp.attacks.constants import (
    NBAIOT_MAIN_SWEEP_FRACTION_SET,
    NBAIOT_FULL_OPTIONAL_SWEEP_FRACTION_SET,
)
from datp.attacks.enums import (
    AttackerObjective,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    objective_for_source,
)
from datp.core.enums import ThresholdPolicy
from datp.core.enums import ScoringStage
from datp.config.stages import ExperimentStage


class GuardrailError(ValueError):
    """Raised when a protocol guardrail is violated at runtime."""


# ---------------------------------------------------------------------------
# No-in-place-mutation guardrail
# ---------------------------------------------------------------------------


def assert_no_inplace_mutation(
    original: np.ndarray,
    after: np.ndarray,
    label: str = "calibration array",
) -> None:
    """Raise if ``original`` was mutated in place by checking equality with ``after``.

    Pass the *original* array (before any operation) and the same array object
    *after* the operation. If they differ, the operation mutated in place.

    Args:
        original: A copy taken before the operation (or the reference before).
        after: The same array object after the operation.
        label: Name used in the error message for context.

    Raises:
        GuardrailError: If the arrays are not equal (in-place mutation detected).
    """
    if not np.array_equal(original, after):
        raise GuardrailError(
            f"Calibration-poisoning guardrail: clean {label} was mutated in place. "
            "Always operate on a copy (arr.copy()); never modify the original."
        )


# ---------------------------------------------------------------------------
# Reservoir-source guardrail
# ---------------------------------------------------------------------------


def assert_reservoir_not_test_or_training(reservoir_source: ScoringStage) -> None:
    """Raise if ``reservoir_source`` is a test stage.

    Reservoirs must be victim-local benign *calibration* scores only.
    Test scores must never influence the reservoir. Training scores are not
    a calibration pool.

    Args:
        reservoir_source: Scoring stage used for reservoir construction.

    Raises:
        GuardrailError: If any forbidden term appears in the label.
    """
    if reservoir_source in (ScoringStage.TEST_BENIGN, ScoringStage.TEST_ATTACK):
        raise GuardrailError(
            f"Calibration-poisoning guardrail: reservoir source {reservoir_source!r} "
            "is forbidden. Reservoirs must be victim-local benign calibration scores only."
        )


# ---------------------------------------------------------------------------
# Policy validity guardrail
# ---------------------------------------------------------------------------


def assert_valid_policy(policy: ThresholdPolicy) -> None:
    """Raise if policy is not one of the three valid calibration-poisoning policies."""
    valid = frozenset(ThresholdPolicy)
    if policy not in valid:
        raise GuardrailError(
            f"Calibration-poisoning guardrail: policy {policy!r} is not valid. "
            f"Valid policies: {sorted(valid)}"
        )


# ---------------------------------------------------------------------------
# Fraction-grid guardrail
# ---------------------------------------------------------------------------


def assert_fractions_in_locked_grid(
    fractions: Iterable[float],
    stage: ExperimentStage,
) -> None:
    """Raise if any fraction is outside the locked grid for ``stage``.

    bounded fraction grid: {0, 0.10, 0.20, 0.40}.
    Full scope adds 0.05 (conditional on the full optional CONTINUE decision).
    Smoke/Stretch use the bounded fraction grid.

    Args:
        fractions: The fraction values to validate.
        stage: The experiment stage; determines the allowed grid.

    Raises:
        GuardrailError: If any fraction is not in the allowed grid.
    """
    allowed = (
        NBAIOT_FULL_OPTIONAL_SWEEP_FRACTION_SET
        if stage == ExperimentStage.NBAIOT_FULL_OPTIONAL
        else NBAIOT_MAIN_SWEEP_FRACTION_SET
    )
    invalid = [f for f in fractions if f not in allowed]
    if invalid:
        raise GuardrailError(
            f"Calibration-poisoning guardrail: fractions {invalid!r} are not in the locked grid "
            f"{sorted(allowed)} for stage {stage!r}. "
            "Fractions are fixed by the locked scientific protocol grid."
        )


# ---------------------------------------------------------------------------
# bounded sweep scope guardrail (SINGLE_CLIENT required)
# ---------------------------------------------------------------------------


def assert_bounded_scale_requires_single_client(
    stage: ExperimentStage,
    target_scope: PoisoningTargetScope,
) -> None:
    """Raise if NBAIOT_MAIN stage is paired with a non-SINGLE_CLIENT target scope.

    Args:
        stage: The experiment stage.
        target_scope_value: The string value of the PoisoningTargetScope enum.

    Raises:
        GuardrailError: If stage is bounded sweep but scope is not SINGLE_CLIENT.
    """
    if (
        stage == ExperimentStage.NBAIOT_MAIN
        and target_scope != PoisoningTargetScope.SINGLE_CLIENT
    ):
        raise GuardrailError(
            f"Calibration-poisoning guardrail: NBAIOT_MAIN stage requires SINGLE_CLIENT target scope; "
            f"got {target_scope!r}. Multi-client and all-client scopes "
            "are diagnostic-only and must not be used in bounded runs."
        )


# ---------------------------------------------------------------------------
# Source-objective cross-validation guardrail
# ---------------------------------------------------------------------------


def assert_valid_source_objective_pair(
    source: PoisoningSourceStrategy,
    objective: AttackerObjective,
) -> None:
    """Raise if source and objective are an invalid combination.

    HIGH_SCORE_BENIGN is locked to THRESHOLD_RAISE.
    LOW_SCORE_BENIGN is locked to THRESHOLD_LOWER.
    RANDOM_BENIGN is valid under both objectives (negative control).
    Diagnostic sources are excluded from this check (they are gated elsewhere).

    Raises:
        GuardrailError: On any invalid (source, objective) pair.
    """
    expected = objective_for_source(source)
    if expected is not None and objective != expected:
        raise GuardrailError(
            f"Calibration-poisoning guardrail: source {source!r} requires "
            f"objective {expected!r}; got {objective!r}. "
            f"Invalid source-objective combination."
        )
