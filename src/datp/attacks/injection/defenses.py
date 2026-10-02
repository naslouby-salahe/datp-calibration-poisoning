
from __future__ import annotations
from datp.types import (
    PoisonFraction,
    RecordKey,
    ScoreVector,
)

from math import floor
from typing import assert_never

import numpy as np

from datp.attacks.enums import PoisoningDefense
from datp.attacks.score_containers import (
    ClientScores,
    ClientScoresById,
    ScoreCollection,
)


def trimmed_calibration(cal: ScoreVector, trim_fraction: PoisonFraction) -> ScoreVector:
    if not 0.0 <= trim_fraction < 0.5:
        raise ValueError(f"trim_fraction must be in [0, 0.5); got {trim_fraction}")
    if cal.ndim != 1:
        raise ValueError(f"cal must be 1-D; got shape {cal.shape}")

    k = floor(trim_fraction * cal.size)
    if k == 0:
        return cal.copy()

    return np.sort(cal)[k:-k].copy()


def build_defended_collection(
    collection: ScoreCollection, trim_fraction: PoisonFraction
) -> ScoreCollection:
    defended_clients = ClientScoresById(
        ClientScores(
            client_id=cid,
            cal=trimmed_calibration(c.cal, trim_fraction),
            test_benign=c.test_benign,
            test_attack=c.test_attack,
        )
        for cid, c in collection.clients.items()
    )
    return ScoreCollection(clients=defended_clients, n_min=collection.n_min)


def defend_poisoned_cal(
    poisoned_cal: dict[RecordKey, ScoreVector], trim_fraction: PoisonFraction
) -> dict[RecordKey, ScoreVector]:
    return {
        cid: trimmed_calibration(cal, trim_fraction)
        for cid, cal in poisoned_cal.items()
    }


def apply_defense(
    collection: ScoreCollection,
    poisoned_cal: dict[RecordKey, ScoreVector],
    *,
    defense: PoisoningDefense,
    trim_fraction: PoisonFraction,
) -> tuple[ScoreCollection, dict[RecordKey, ScoreVector]]:
    if defense == PoisoningDefense.NONE:
        return collection, poisoned_cal
    elif defense == PoisoningDefense.TRIMMED_CALIBRATION:
        return (
            build_defended_collection(collection, trim_fraction),
            defend_poisoned_cal(poisoned_cal, trim_fraction),
        )
    else:
        assert_never(defense)
