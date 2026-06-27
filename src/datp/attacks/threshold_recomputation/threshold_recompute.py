"""Global and local threshold recomputation from poisoned calibration sets."""

from __future__ import annotations

import numpy as np

from datp.attacks.score_containers import ScoreCollection
from datp.attacks.types import PoisonedCalibrationSet, ThresholdPairBase
from datp.core.enums import ThresholdPolicy
from datp.core.types import ClientThreshold
from datp.thresholding.eligibility import (
    CalibrationErrorSet,
    ClientThresholdsCollection,
    EligibilityResult,
    compute_client_thresholds,
    compute_tau_global,
)

ThresholdPair = (
    ThresholdPairBase  # Convenience alias used throughout the attacks package
)


def get_threshold_data(
    collection: ScoreCollection,
    poisoned_cal: PoisonedCalibrationSet | dict[str, np.ndarray],
    q: float,
) -> tuple[ClientThresholdsCollection, ClientThresholdsCollection, tuple[str, ...]]:
    """Compute clean and poisoned per-client threshold collections at quantile q."""
    if not isinstance(poisoned_cal, PoisonedCalibrationSet):
        poisoned_cal = PoisonedCalibrationSet.from_mapping(poisoned_cal)

    eligible_ids = collection.eligible_ids
    eligibility = EligibilityResult(eligible_ids=eligible_ids, pending_ids=())

    taus_clean = compute_client_thresholds(
        CalibrationErrorSet.from_mapping(collection.eligible_cal_dict()),
        eligibility,
        q=q,
    )
    taus_pois = compute_client_thresholds(
        CalibrationErrorSet.from_mapping(
            {cid: poisoned_cal.for_client(cid).cal for cid in eligible_ids}
        ),
        eligibility,
        q=q,
    )
    return taus_clean, taus_pois, eligible_ids


def build_uniform_collection(
    eligible_ids: tuple[str, ...], tau: float
) -> ClientThresholdsCollection:
    """Build a ClientThresholdsCollection with a uniform threshold for all eligible clients."""
    return ClientThresholdsCollection(
        entries=tuple(
            ClientThreshold(
                client_id=cid,
                threshold=tau,
                calibration_pending=False,
                strategy=ThresholdPolicy.GLOBAL_THRESHOLD,
            )
            for cid in eligible_ids
        )
    )


def compute_global_pair(
    collection: ScoreCollection,
    poisoned_cal_set: PoisonedCalibrationSet | dict[str, np.ndarray],
    q: float,
) -> ThresholdPair:
    """Compute clean and poisoned global-threshold pairs."""
    taus_clean, taus_pois, eligible_ids = get_threshold_data(
        collection, poisoned_cal_set, q
    )

    tau_global_clean = compute_tau_global(taus_clean)
    tau_global_pois = compute_tau_global(taus_pois)

    return ThresholdPair(
        policy=ThresholdPolicy.GLOBAL_THRESHOLD,
        tau_global_clean=tau_global_clean,
        tau_global_pois=tau_global_pois,
        thresholds_clean=build_uniform_collection(eligible_ids, tau_global_clean),
        thresholds_pois=build_uniform_collection(eligible_ids, tau_global_pois),
    )


def compute_local_pair(
    collection: ScoreCollection,
    poisoned_cal_set: PoisonedCalibrationSet | dict[str, np.ndarray],
    q: float,
    tau_global_clean: float,
) -> ThresholdPair:
    """Compute clean and poisoned local-threshold pairs."""
    taus_clean, taus_pois, _ = get_threshold_data(collection, poisoned_cal_set, q)

    return ThresholdPair(
        policy=ThresholdPolicy.LOCAL_THRESHOLD,
        tau_global_clean=tau_global_clean,
        tau_global_pois=compute_tau_global(taus_pois),
        thresholds_clean=taus_clean,
        thresholds_pois=taus_pois,
    )
