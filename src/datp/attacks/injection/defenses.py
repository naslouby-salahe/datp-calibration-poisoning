"""Calibration-set defenses: trimming and defended-collection construction."""

from __future__ import annotations

from typing import assert_never

import numpy as np

from datp.attacks.enums import PoisoningDefense
from datp.attacks.score_containers import (
    ClientScores,
    ClientScoresTuple,
    ScoreCollection,
)


def trimmed_calibration(cal: np.ndarray, trim_fraction: float) -> np.ndarray:
    """Return the calibration array with symmetric trim-fraction tails removed."""
    if not 0.0 <= trim_fraction < 0.5:
        raise ValueError(f"trim_fraction must be in [0, 0.5); got {trim_fraction}")
    if cal.ndim != 1:
        raise ValueError(f"cal must be 1-D; got shape {cal.shape}")

    k = int(trim_fraction * cal.size)
    if k == 0:
        return cal.copy()

    return np.sort(cal)[k:-k].copy()


def build_defended_collection(
    collection: ScoreCollection, trim_fraction: float
) -> ScoreCollection:
    """Build a new ScoreCollection with trimmed calibration scores."""
    defended_clients = ClientScoresTuple(
        ClientScores(
            client_id=cid,
            cal=trimmed_calibration(c.cal, trim_fraction),
            test_benign=c.test_benign,
            test_attack=c.test_attack,
        )
        for cid, c in collection.iter_clients()
    )
    return ScoreCollection(clients=defended_clients, n_min=collection.n_min)


def defend_poisoned_cal(
    poisoned_cal: dict[str, np.ndarray], trim_fraction: float
) -> dict[str, np.ndarray]:
    """Apply trimming defense to each client's poisoned calibration array."""
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
    """Apply the selected defense to both the collection and poisoned calibration."""
    if defense == PoisoningDefense.NONE:
        return collection, poisoned_cal
    elif defense == PoisoningDefense.TRIMMED_CALIBRATION:
        return (
            build_defended_collection(collection, trim_fraction),
            defend_poisoned_cal(poisoned_cal, trim_fraction),
        )
    else:
        assert_never(defense)
