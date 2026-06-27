"""Per-client delta-tau computation with materiality-scaled significance."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from datp.attacks.constants import EPS_NUM, MATERIALITY_FACTOR
from datp.attacks.score_containers import ScoreCollection
from datp.attacks.types import ThresholdPairBase
from datp.core.enums import ThresholdPolicy
from datp.statistics.aggregates import iqr


@dataclass(frozen=True, slots=True)
class DeltaTauEntry:
    """Per-client operating-point delta with materiality-scaled significance flag."""

    client_id: str
    policy: ThresholdPolicy
    tau_clean: float
    tau_pois: float
    delta_tau: float
    delta_tau_rel: float
    delta_tau_scale: float
    is_significant: bool


def _per_client_raw_scale(clean_cal: np.ndarray, iqr: float) -> float:
    """Compute the materiality scale for a client: IQR, then MAD, then min-spacing fallback."""
    if iqr > 0.0:
        return MATERIALITY_FACTOR * iqr

    mad = float(np.median(np.abs(clean_cal - np.median(clean_cal))))
    if mad > 0.0:
        return MATERIALITY_FACTOR * mad

    diffs = np.diff(np.unique(clean_cal))
    pos_diffs = diffs[diffs > 0.0]
    if pos_diffs.size > 0:
        return MATERIALITY_FACTOR * float(pos_diffs.min())

    return math.nan


def compute_delta_tau(
    collection: ScoreCollection,
    pair: ThresholdPairBase,
) -> dict[str, DeltaTauEntry]:
    """Compute per-client delta-tau entries with materiality-scaled significance flags."""
    raw_scales: dict[str, float] = {}
    iqrs: list[float] = []

    for cid in collection.eligible_ids:
        clean_cal = collection.for_client(cid).cal
        iqr_val = iqr(clean_cal)
        iqrs.append(iqr_val)
        raw_scales[cid] = _per_client_raw_scale(clean_cal, iqr_val)

    iqr_floor = 0.01 * float(np.median(iqrs)) if iqrs else 0.0
    result: dict[str, DeltaTauEntry] = {}

    for cid in collection.eligible_ids:
        tc = pair.thresholds_clean[cid]
        tp = pair.thresholds_pois[cid]
        dt = tp - tc
        raw_scale = raw_scales[cid]

        if math.isnan(raw_scale):
            scale, is_sig = math.nan, False
        else:
            scale = max(raw_scale, iqr_floor)
            is_sig = abs(dt) >= scale

        result[cid] = DeltaTauEntry(
            client_id=cid,
            policy=pair.policy,
            tau_clean=tc,
            tau_pois=tp,
            delta_tau=dt,
            delta_tau_rel=dt / max(abs(tc), EPS_NUM),
            delta_tau_scale=scale,
            is_significant=is_sig,
        )

    return result
