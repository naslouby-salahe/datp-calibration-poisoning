"""Validates all experiment cells before any training starts; blocked on first config error."""

from __future__ import annotations

from datp.config.compose import ComposeError, compose_config
from datp.config.models import DatpConfig
from datp.core.identity import PolicyRunId


def validate_sweep(
    cells: list[PolicyRunId],
) -> tuple[list[str], dict[PolicyRunId, DatpConfig]]:
    errors: list[str] = []
    configs: dict[PolicyRunId, DatpConfig] = {}

    for cell in cells:
        label = cell.label()
        try:
            cfg = compose_config(
                stage=cell.cell.stage,
                policy=cell.policy,
                seed=cell.cell.seed,
            )
            configs[cell] = cfg
        except ComposeError as exc:
            errors.append(f"{label}: {exc}")

    if errors:
        return errors, {}
    return errors, configs
