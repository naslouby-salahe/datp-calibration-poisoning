"""Per-client delta-tau computation with materiality-scaled significance."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from datp.attacks.constants import EPS_NUM, IQR_FLOOR_FACTOR, MATERIALITY_FACTOR
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
    scale_base: float
    iqr_median: float
    is_significant: bool


def per_client_scale_base(clean_cal: np.ndarray, iqr: float) -> float:
    """Return the unscaled materiality base for a client: IQR, then MAD, then min-spacing fallback."""
    if iqr > 0.0:
        return iqr

    mad = float(np.median(np.abs(clean_cal - np.median(clean_cal))))
    if mad > 0.0:
        return mad

    diffs = np.diff(np.unique(clean_cal))
    pos_diffs = diffs[diffs > 0.0]
    if pos_diffs.size > 0:
        return float(pos_diffs.min())

    return math.nan


def materiality_scale(
    scale_base: float, iqr_median: float, factor: float, floor_factor: float
) -> float:
    """Return the materiality scale for a base value, or NaN when the base is undefined."""
    if math.isnan(scale_base):
        return math.nan
    return max(factor * scale_base, floor_factor * iqr_median)


def compute_delta_tau(
    collection: ScoreCollection,
    pair: ThresholdPairBase,
) -> dict[str, DeltaTauEntry]:
    """Compute per-client delta-tau entries with materiality-scaled significance flags."""
    bases: dict[str, float] = {}
    iqrs: list[float] = []

    for cid in collection.eligible_ids:
        clean_cal = collection.for_client(cid).cal
        iqr_val = iqr(clean_cal)
        iqrs.append(iqr_val)
        bases[cid] = per_client_scale_base(clean_cal, iqr_val)

    iqr_median = float(np.median(iqrs)) if iqrs else 0.0
    result: dict[str, DeltaTauEntry] = {}

    for cid in collection.eligible_ids:
        tc = pair.thresholds_clean[cid]
        tp = pair.thresholds_pois[cid]
        dt = tp - tc
        base = bases[cid]
        scale = materiality_scale(
            base, iqr_median, MATERIALITY_FACTOR, IQR_FLOOR_FACTOR
        )
        is_sig = not math.isnan(scale) and abs(dt) >= scale

        result[cid] = DeltaTauEntry(
            client_id=cid,
            policy=pair.policy,
            tau_clean=tc,
            tau_pois=tp,
            delta_tau=dt,
            delta_tau_rel=dt / max(abs(tc), EPS_NUM),
            delta_tau_scale=scale,
            scale_base=base,
            iqr_median=iqr_median,
            is_significant=is_sig,
        )

    return result
