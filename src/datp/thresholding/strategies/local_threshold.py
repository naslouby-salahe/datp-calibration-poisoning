"""Per-client threshold: tau_i = percentile_q(E_i) for eligible clients; Calibration-Pending clients receive tau_global."""

from __future__ import annotations

import numpy as np

from datp.core.identity import PolicyRunId
from datp.core.types import ThresholdResult
from datp.thresholding.eligibility import (
    build_threshold_result,
    compute_client_thresholds,
    identify_eligible,
)


def compute(
    client_errors: dict[str, np.ndarray],
    n_min: int,
    tau_global: float,
    q: float,
    run: PolicyRunId,
) -> ThresholdResult:
    eligible, pending = identify_eligible(client_errors, n_min=n_min)
    client_taus = compute_client_thresholds(client_errors, eligible, q=q)

    return build_threshold_result(
        run=run,
        tau_global=tau_global,
        eligible_thresholds=client_taus,
        pending_clients=pending,
        cluster_metadata=None,
    )
