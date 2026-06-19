"""B3 — Family-mean threshold (Regime A only): τ_f = (1/|elig in f|)×Στᵢ within device family; Calibration-Pending clients receive τ_global."""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from datp.core.enums import Regime
from datp.core.errors import fmt
from datp.core.identity import BaselineRunId
from datp.core.regime import enforce_regime
from datp.core.types import B3FamilyInfo, B3FamilyInfoTuple, B3Metadata, ThresholdResult
from datp.thresholding.eligibility import (
    build_threshold_result,
    compute_client_thresholds,
    identify_eligible,
)
from datp.thresholding.thresholds import arithmetic_mean_threshold

_MODULE = "thresholding.b3_family"
_MISSING_CLIENT_SAMPLE_SIZE = 5


@enforce_regime(Regime.A)
def compute(
    client_errors: dict[str, np.ndarray],
    n_min: int,
    tau_global: float,
    family_map: dict[str, str],
    q: float,
    *,
    regime: Regime,  # noqa: ARG001 - consumed by @enforce_regime decorator
    run: BaselineRunId,
) -> ThresholdResult:
    eligible, pending = identify_eligible(client_errors, n_min=n_min)
    client_taus = compute_client_thresholds(client_errors, eligible, q=q)

    missing = set(client_errors.keys()) - set(family_map.keys())
    if missing:
        raise ValueError(
            fmt(
                _MODULE,
                "Missing family mapping",
                "all client IDs in family_map",
                f"{len(missing)} unmapped: {sorted(missing)[:_MISSING_CLIENT_SAMPLE_SIZE]}",
            )
        )

    family_taus: dict[str, list[float]] = defaultdict(list)
    for cid in eligible:
        family = family_map[cid]
        family_taus[family].append(client_taus[cid])

    tau_per_family: dict[str, float] = {}
    for family, taus in family_taus.items():
        tau_per_family[family] = arithmetic_mean_threshold(taus)

    eligible_map = {cid: tau_per_family[family_map[cid]] for cid in eligible}

    family_info: dict[str, B3FamilyInfo] = {}
    for family, taus in family_taus.items():
        family_info[family] = B3FamilyInfo(
            family_name=family,
            tau_family=tau_per_family[family],
            eligible_count=len(taus),
            members=tuple(cid for cid in eligible if family_map[cid] == family),
            threshold_variance=float(np.var(taus, ddof=1)) if len(taus) > 1 else 0.0,
            singleton=len(taus) == 1,
        )

    return build_threshold_result(
        run=run,
        tau_global=tau_global,
        eligible_thresholds=eligible_map,
        pending_clients=pending,
        b3_metadata=B3Metadata(family_info=B3FamilyInfoTuple(family_info.values())),
        b4_metadata=None,
    )
