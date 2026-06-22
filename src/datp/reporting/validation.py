from __future__ import annotations
from datp.core.enums import ThresholdPolicy

from collections.abc import Sequence

from datp.core.enums import MAIN_BODY_POLICIES


def validate_main_body_role(policies: Sequence[ThresholdPolicy]) -> None:
    for p in policies:
        if p not in MAIN_BODY_POLICIES:
            raise ValueError(
                f"[reporting] ThresholdPolicy '{p}' is not permitted in main-body "
                f"figures/tables. "
                f"Allowed: {sorted(p.value for p in MAIN_BODY_POLICIES)}"
            )
