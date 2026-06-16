"""Calibration-set defenses applied before threshold derivation.

The only locked defense is TRIMMED_CALIBRATION: a symmetric trim that drops the
top and bottom ``trim_fraction`` of each client's calibration scores before the
threshold quantile and before B4 fingerprinting. The defense is applied
uniformly to every client (eligible and pending) and to both clean and poisoned
calibration. Clean arrays are never mutated in place.

The defense transforms the inputs to the existing threshold-recompute pipeline
(a defended ScoreCollection and a defended poisoned-cal dict); the threshold
logic itself is unchanged, so trimming necessarily precedes both the percentile
and the B4 fingerprint.
"""

from __future__ import annotations

import math
from typing import assert_never

import numpy as np

from datp.attacks.poison_enums import PoisoningDefense
from datp.attacks.score_containers import ClientScores, ScoreCollection


def trimmed_calibration(cal: np.ndarray, trim_fraction: float) -> np.ndarray:
    """Return a symmetrically trimmed copy of ``cal``.

    Drops ``floor(trim_fraction * n)`` values from each tail (by value) before
    returning the remaining middle. The input is never mutated. ``trim_fraction``
    must be in [0, 0.5); 0 returns an exact copy.
    """
    if not (0.0 <= trim_fraction < 0.5):
        raise ValueError(f"trim_fraction must be in [0, 0.5); got {trim_fraction}")
    if cal.ndim != 1:
        raise ValueError(f"cal must be 1-D; got shape {cal.shape}")
    n = cal.shape[0]
    k = math.floor(trim_fraction * n)
    if k == 0:
        return cal.copy()
    ordered = np.sort(cal)
    return ordered[k : n - k].copy()


def build_defended_collection(
    collection: ScoreCollection, trim_fraction: float
) -> ScoreCollection:
    """Return a collection whose calibration arrays are trimmed; test arrays kept.

    Eligibility is recomputed from the trimmed cardinality (a client could in
    principle drop below ``n_min`` after trimming — that is the honest cost of
    the defense and is reported, not hidden).
    """
    defended_clients = {
        cid: ClientScores(
            client_id=cid,
            cal=trimmed_calibration(c.cal, trim_fraction),
            test_benign=c.test_benign,
            test_attack=c.test_attack,
        )
        for cid, c in collection.clients.items()
    }
    return ScoreCollection(clients=defended_clients, n_min=collection.n_min)


def defend_poisoned_cal(
    poisoned_cal: dict[str, np.ndarray], trim_fraction: float
) -> dict[str, np.ndarray]:
    """Return a trimmed copy of every entry in a poisoned-cal dict."""
    return {
        cid: trimmed_calibration(cal, trim_fraction)
        for cid, cal in poisoned_cal.items()
    }


def apply_defense(
    collection: ScoreCollection,
    poisoned_cal: dict[str, np.ndarray],
    *,
    defense: PoisoningDefense,
    trim_fraction: float,
) -> tuple[ScoreCollection, dict[str, np.ndarray]]:
    """Return (collection, poisoned_cal) transformed for the given defense.

    NONE returns the inputs unchanged. TRIMMED_CALIBRATION returns a defended
    collection and a defended poisoned-cal dict ready for the existing
    threshold-recompute pipeline.
    """
    if defense == PoisoningDefense.NONE:
        return collection, poisoned_cal
    if defense == PoisoningDefense.TRIMMED_CALIBRATION:
        return (
            build_defended_collection(collection, trim_fraction),
            defend_poisoned_cal(poisoned_cal, trim_fraction),
        )
    assert_never(defense)
