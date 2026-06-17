"""B1 — Global-mean threshold: τ_global = (1/K_elig)×Στᵢ over eligible clients; Calibration-Pending clients receive τ_global."""

from __future__ import annotations

import numpy as np

from datp.core.identity import BaselineRunId
from datp.core.types import ThresholdResult
from datp.thresholding.eligibility import (
    build_threshold_result,
    compute_client_thresholds,
    compute_tau_global,
    identify_eligible,
)


def compute(
    client_errors: dict[str, np.ndarray],
    n_min: int,
    q: float,
    run: BaselineRunId,
) -> ThresholdResult:
    eligible, pending = identify_eligible(client_errors, n_min=n_min)
    client_taus = compute_client_thresholds(client_errors, eligible, q=q)
    tau_global = compute_tau_global(client_taus)

    eligible_map = dict.fromkeys(eligible, tau_global)

    return build_threshold_result(
        run=run,
        tau_global=tau_global,
        eligible_thresholds=eligible_map,
        pending_clients=pending,
        b3_metadata=None,
        b4_metadata=None,
    )
