from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

import pytest

from datp.reporting.validation import validate_main_body_role


def test_all_policies_accepted() -> None:
    validate_main_body_role(list(ThresholdPolicy))


def test_main_body_policies_pass_validation() -> None:
    validate_main_body_role(
        [
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        ]
    )


def test_global_threshold_accepted() -> None:
    validate_main_body_role([ThresholdPolicy.GLOBAL_THRESHOLD])


def test_rejects_invalid_policy_value() -> None:
    with pytest.raises(ValueError, match="not permitted"):
        validate_main_body_role(["not_a_policy"])  # type: ignore[list-item]


def test_mixed_valid_and_invalid_raises() -> None:
    """When any element is not in MAIN_BODY_BASELINES the whole list is rejected."""
    with pytest.raises(ValueError, match="not permitted"):
        validate_main_body_role([ThresholdPolicy.GLOBAL_THRESHOLD, "b_unknown"])  # type: ignore[list-item]
