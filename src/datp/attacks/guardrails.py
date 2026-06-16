"""Runtime scientific guardrails for calibration poisoning.

Each guardrail function asserts one protocol invariant and raises
``GuardrailError`` (a ``ValueError``) on violation. Call these at
poisoning-logic boundaries — never inside tight loops.

Guardrails do NOT swallow exceptions or silently return False.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from datp.attacks.poison_enums import (
    BOUNDED_SWEEP_FRACTIONS,
    ExperimentScale,
    ThresholdPolicy,
)


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

_FORBIDDEN_RESERVOIR_TERMS: frozenset[str] = frozenset({"test", "training", "train"})


def assert_reservoir_not_test_or_training(reservoir_label: str) -> None:
    """Raise if ``reservoir_label`` implies test or training scores.

    Reservoirs must be victim-local benign *calibration* scores only.
    Test scores must never influence the reservoir. Training scores are not
    a calibration pool.

    Args:
        reservoir_label: A string identifying the reservoir source
            (e.g., a stage name, file path component, or enum value).

    Raises:
        GuardrailError: If any forbidden term appears in the label.
    """
    lower = reservoir_label.lower()
    for term in _FORBIDDEN_RESERVOIR_TERMS:
        if term in lower:
            raise GuardrailError(
                f"Calibration-poisoning guardrail: reservoir label {reservoir_label!r} "
                f"contains forbidden term {term!r}. "
                "Reservoirs must be victim-local benign calibration scores only — "
                "test and training scores are excluded."
            )


# ---------------------------------------------------------------------------
# Policy guardrail (B3 excluded)
# ---------------------------------------------------------------------------


def assert_policy_not_b3(policy: ThresholdPolicy) -> None:
    """Raise if ``policy`` is B3, which is excluded.

    B3 (conformal threshold) is not part of the default policy enum.
    This is a defence-in-depth check; the enum itself cannot represent B3.

    Raises:
        GuardrailError: If the policy string contains "b3".
    """
    if "b3" in str(policy).lower():
        raise GuardrailError(
            f"Calibration-poisoning guardrail: policy {policy!r} is B3. "
            "B3 is excluded from the ThresholdPolicy enum and must not "
            "be selected as a default policy."
        )


# ---------------------------------------------------------------------------
# Fraction-grid guardrail
# ---------------------------------------------------------------------------

_FULL_FRACTIONS: frozenset[float] = frozenset(BOUNDED_SWEEP_FRACTIONS) | {0.05}


def assert_fractions_in_locked_grid(
    fractions: Sequence[float],
    scale: ExperimentScale,
) -> None:
    """Raise if any fraction is outside the locked grid for ``scale``.

    bounded fraction grid: {0, 0.10, 0.20, 0.40}.
    Full scope adds 0.05 (conditional on the full-scope CONTINUE decision).
    Smoke/Stretch use the bounded fraction grid.

    Args:
        fractions: The fraction values to validate.
        scale: The experiment scale; determines the allowed grid.

    Raises:
        GuardrailError: If any fraction is not in the allowed grid.
    """
    if scale == ExperimentScale.FULL:
        allowed = _FULL_FRACTIONS
    else:
        allowed = frozenset(BOUNDED_SWEEP_FRACTIONS)
    for f in fractions:
        if not any(abs(f - a) < 1e-9 for a in allowed):
            raise GuardrailError(
                f"Calibration-poisoning guardrail: fraction {f} is not in the locked grid "
                f"{sorted(allowed)} for scale {scale!r}. "
                "Do not introduce new fractions without a scientific ticket."
            )


# ---------------------------------------------------------------------------
# bounded sweep scope guardrail (SINGLE_CLIENT required)
# ---------------------------------------------------------------------------


def assert_bounded_scale_requires_single_client(
    scale: ExperimentScale,
    target_scope_value: str,
) -> None:
    """Raise if BOUNDED scale is paired with a non-SINGLE_CLIENT target scope.

    Args:
        scale: The experiment scale.
        target_scope_value: The string value of the PoisoningTargetScope enum.

    Raises:
        GuardrailError: If scale is bounded sweep but scope is not SINGLE_CLIENT.
    """
    if scale == ExperimentScale.BOUNDED and target_scope_value != "single_client":
        raise GuardrailError(
            f"Calibration-poisoning guardrail: BOUNDED scale requires SINGLE_CLIENT target scope; "
            f"got {target_scope_value!r}. Multi-client and all-client scopes "
            "are diagnostic-only and must not be used in bounded runs."
        )
