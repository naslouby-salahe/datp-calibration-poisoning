from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from datp.artifacts.poison_names import EPS_NUM, MATERIALITY_FACTOR
from datp.attacks.score_containers import ScoreCollection
from datp.attacks.types import ThresholdPairBase
from datp.core.enums import ThresholdPolicy

_DELTA_TAU_REL_EPS: float = EPS_NUM
_IQR_P25: float = 25.0
_IQR_P75: float = 75.0
_DELTA_TAU_FLOOR_FACTOR: float = 0.01


@dataclass(frozen=True, slots=True)
class DeltaTauEntry:
    """Per-victim threshold shift for one policy."""

    client_id: str
    policy: ThresholdPolicy
    tau_clean: float
    tau_pois: float
    delta_tau: float
    delta_tau_rel: float
    delta_tau_scale: float
    is_significant: bool


def _per_client_raw_scale(clean_cal: np.ndarray) -> tuple[float, bool]:
    iqr = float(
        np.percentile(clean_cal, _IQR_P75) - np.percentile(clean_cal, _IQR_P25)
    )
    if iqr > 0.0:
        return MATERIALITY_FACTOR * iqr, False

    mad = float(np.median(np.abs(clean_cal - np.median(clean_cal))))
    if mad > 0.0:
        return MATERIALITY_FACTOR * mad, False

    sorted_unique = np.unique(clean_cal)
    diffs = np.diff(sorted_unique)
    pos_diffs = diffs[diffs > 0.0]
    if pos_diffs.size > 0:
        return MATERIALITY_FACTOR * float(pos_diffs.min()), False

    return math.nan, True


def compute_delta_tau(
    collection: ScoreCollection,
    pair: ThresholdPairBase,
) -> dict[str, DeltaTauEntry]:
    raw_scales: dict[str, float] = {}
    degenerate: set[str] = set()
    iqrs: list[float] = []

    for cid in collection.eligible_ids:
        clean_cal = collection.for_client(cid).cal
        raw_scale, is_deg = _per_client_raw_scale(clean_cal)
        raw_scales[cid] = raw_scale
        if is_deg:
            degenerate.add(cid)
        iqr_i = float(
            np.percentile(clean_cal, _IQR_P75) - np.percentile(clean_cal, _IQR_P25)
        )
        iqrs.append(iqr_i)

    iqr_floor = _DELTA_TAU_FLOOR_FACTOR * float(np.median(iqrs)) if iqrs else 0.0

    result: dict[str, DeltaTauEntry] = {}
    for cid in collection.eligible_ids:
        tc = pair.thresholds_clean[cid]
        tp = pair.thresholds_pois[cid]
        dt = tp - tc
        dt_rel = dt / max(abs(tc), _DELTA_TAU_REL_EPS)

        if cid in degenerate:
            scale = math.nan
            is_sig = False
        else:
            scale = max(raw_scales[cid], iqr_floor)
            is_sig = abs(dt) >= scale

        result[cid] = DeltaTauEntry(
            client_id=cid,
            policy=pair.policy,
            tau_clean=tc,
            tau_pois=tp,
            delta_tau=dt,
            delta_tau_rel=dt_rel,
            delta_tau_scale=scale,
            is_significant=is_sig,
        )
    return result
