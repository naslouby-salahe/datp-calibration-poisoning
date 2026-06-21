from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

import pytest

from datp.reporting.validation import validate_main_body_role


def test_all_baselines_accepted() -> None:
    """Every ThresholdPolicy currently in the enum is in MAIN_BODY_BASELINES."""
    validate_main_body_role(list(ThresholdPolicy))


def test_global_local_cluster_deprecated_accepted() -> None:
    """Typical main-body threshold-ladder baselines (GLOBAL_THRESHOLD, LOCAL_THRESHOLD, CLUSTER_THRESHOLD) pass."""
    validate_main_body_role([ThresholdPolicy.GLOBAL_THRESHOLD, ThresholdPolicy.LOCAL_THRESHOLD, ThresholdPolicy.CLUSTER_THRESHOLD, ThresholdPolicy.CLUSTER_THRESHOLD])


def test_b0_accepted() -> None:
    """B0 (centralized reference) is permitted in main-body tables."""
    validate_main_body_role([ThresholdPolicy.GLOBAL_THRESHOLD])


def test_rejects_non_baseline_value() -> None:
    """Defense-in-depth: non-ThresholdPolicy values are rejected at runtime.

    Even though the type signature is ``Sequence[ThresholdPolicy]``, Python does not
    enforce it at runtime. The function rejects non-ThresholdPolicy objects via the
    ``MAIN_BODY_BASELINES`` membership check.
    """
    with pytest.raises(ValueError, match="not permitted"):
        validate_main_body_role(["not_a_baseline"])  # type: ignore[list-item]


def test_mixed_valid_and_invalid_raises() -> None:
    """When any element is not in MAIN_BODY_BASELINES the whole list is rejected."""
    with pytest.raises(ValueError, match="not permitted"):
        validate_main_body_role([ThresholdPolicy.GLOBAL_THRESHOLD, "b_unknown"])  # type: ignore[list-item]
