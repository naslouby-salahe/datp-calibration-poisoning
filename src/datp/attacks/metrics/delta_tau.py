from __future__ import annotations

from datp.types import (
    ClientId,
    ScoreValue,
    ScoreVector,
    SignedDelta,
    Threshold,
)


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

    client_id: ClientId
    policy: ThresholdPolicy
    tau_clean: Threshold
    tau_pois: Threshold
    delta_tau: SignedDelta
    delta_tau_rel: SignedDelta
    delta_tau_scale: SignedDelta
    scale_base: ScoreValue
    iqr_median: ScoreValue
    is_significant: bool


def per_client_scale_base(clean_cal: ScoreVector, iqr: ScoreValue) -> ScoreValue:
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
    scale_base: ScoreValue, iqr_median: ScoreValue, factor: ScoreValue, floor_factor: ScoreValue
) -> ScoreValue:
    if math.isnan(scale_base):
        return math.nan
    return max(factor * scale_base, floor_factor * iqr_median)


def compute_delta_tau(
    collection: ScoreCollection,
    pair: ThresholdPairBase,
) -> dict[ClientId, DeltaTauEntry]:
    bases: dict[ClientId, ScoreValue] = {}
    iqrs: list[ScoreValue] = []

    for cid in collection.eligible_ids:
        clean_cal = collection.clients[cid].cal
        iqr_val = iqr(clean_cal)
        iqrs.append(iqr_val)
        bases[cid] = per_client_scale_base(clean_cal, iqr_val)

    iqr_median = float(np.median(iqrs)) if iqrs else 0.0
    result: dict[ClientId, DeltaTauEntry] = {}

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
