from __future__ import annotations

import pytest

from datp.core.enums import Baseline
from datp.reporting.validation import validate_main_body_role


def test_all_baselines_accepted() -> None:
    """Every Baseline currently in the enum is in MAIN_BODY_BASELINES."""
    validate_main_body_role(list(Baseline))


def test_b1_b2_b3_b4_accepted() -> None:
    """Typical main-body threshold-ladder baselines pass."""
    validate_main_body_role([Baseline.B1, Baseline.B2, Baseline.B3, Baseline.B4])


def test_b0_accepted() -> None:
    """B0 (centralized reference) is permitted in main-body tables."""
    validate_main_body_role([Baseline.B0])


def test_rejects_non_baseline_value() -> None:
    """Defense-in-depth: non-Baseline values are rejected at runtime.

    Even though the type signature is ``Sequence[Baseline]``, Python does not
    enforce it at runtime. The function rejects non-Baseline objects via the
    ``MAIN_BODY_BASELINES`` membership check.
    """
    with pytest.raises(ValueError, match="not permitted"):
        validate_main_body_role(["not_a_baseline"])  # type: ignore[list-item]


def test_mixed_valid_and_invalid_raises() -> None:
    """When any element is not in MAIN_BODY_BASELINES the whole list is rejected."""
    with pytest.raises(ValueError, match="not permitted"):
        validate_main_body_role([Baseline.B1, "b_unknown"])  # type: ignore[list-item]
