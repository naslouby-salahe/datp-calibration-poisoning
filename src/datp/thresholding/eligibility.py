from __future__ import annotations

import numpy as np

from datp.core.errors import fmt
from datp.core.identity import BaselineRunId
from datp.core.types import (
    B3Metadata,
    B4Metadata,
    ClientThreshold,
    ThresholdMetadata,
    ThresholdResult,
)
from datp.thresholding.thresholds import (
    arithmetic_mean_threshold,
    percentile_threshold,
)


def identify_eligible(
    client_errors: dict[str, np.ndarray],
    n_min: int,
) -> tuple[list[str], list[str]]:
    eligible: list[str] = []
    pending: list[str] = []
    for cid, errors in client_errors.items():
        if errors.size >= n_min:
            eligible.append(cid)
        else:
            pending.append(cid)
    return eligible, pending


def compute_client_thresholds(
    client_errors: dict[str, np.ndarray],
    eligible: list[str],
    q: float,
) -> dict[str, float]:
    return {cid: percentile_threshold(client_errors[cid], q=q) for cid in eligible}


def compute_tau_global(
    client_taus: dict[str, float],
) -> float:
    """tau_global = (1/K_elig)×Στᵢ (B1 formula); never sample-weighted; raises ValueError if client_taus is empty."""
    if not client_taus:
        raise ValueError(
            fmt(
                "eligibility",
                "Cannot compute tau_global: no eligible clients",
                "at least 1 eligible client",
                "0",
            )
        )
    return arithmetic_mean_threshold(list(client_taus.values()))


def build_threshold_result(
    run: BaselineRunId,
    tau_global: float,
    eligible_thresholds: dict[str, float],
    pending_clients: list[str],
    b3_metadata: B3Metadata | None,
    b4_metadata: B4Metadata | None,
) -> ThresholdResult:
    thresholds: list[ClientThreshold] = []

    for cid, tau in eligible_thresholds.items():
        thresholds.append(
            ClientThreshold(
                client_id=cid,
                threshold=tau,
                calibration_pending=False,
                strategy=run.baseline,
            )
        )

    for cid in pending_clients:
        thresholds.append(
            ClientThreshold(
                client_id=cid,
                threshold=tau_global,
                calibration_pending=True,
                strategy=run.baseline,
            )
        )

    return ThresholdResult(
        run=run,
        tau_global=tau_global,
        client_thresholds=tuple(thresholds),
        metadata=ThresholdMetadata(b3=b3_metadata, b4=b4_metadata),
    )
