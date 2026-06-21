"""GLOBAL_THRESHOLD/LOCAL_THRESHOLD threshold recomputation under calibration poisoning.

Thin adapter over the inherited thresholding strategies. Accepts a clean
ScoreCollection and a poisoned calibration dict, and returns typed
clean/poisoned threshold pairs.

Eligibility is fixed from the clean collection (cardinality is preserved under
REPLACE_FIXED_BUDGET, so eligible/pending partition never changes).

GLOBAL_THRESHOLD: tau_global = mean of per-client eligible percentiles.
  Poisoning one victim shifts the global mean.
LOCAL_THRESHOLD: each eligible client has its own percentile threshold.
  Poisoning one victim changes only that victim's threshold.

Pending clients receive tau_global in both policies.
"""

from __future__ import annotations

import numpy as np

from datp.attacks.score_containers import ScoreCollection
from datp.attacks.enums import ThresholdPolicy
from datp.attacks.types import PoisonedCalibrationSet, ThresholdPairBase
from datp.core.types import ClientThreshold
from datp.thresholding.eligibility import (
    CalibrationErrorSet,
    ClientThresholdsCollection,
    EligibilityResult,
    compute_client_thresholds,
    compute_tau_global,
)


ThresholdPair = ThresholdPairBase


def _error_set_from_collection(collection: ScoreCollection) -> CalibrationErrorSet:
    return CalibrationErrorSet.from_mapping(collection.eligible_cal_dict())


def _error_set_from_poisoned(
    poisoned_cal_set: PoisonedCalibrationSet, eligible_ids: tuple[str, ...]
) -> CalibrationErrorSet:
    return CalibrationErrorSet.from_mapping(
        {cid: poisoned_cal_set.for_client(cid).cal for cid in eligible_ids}
    )


def _uniform_thresholds(
    eligible_ids: tuple[str, ...], tau: float, strategy: ThresholdPolicy
) -> ClientThresholdsCollection:
    return ClientThresholdsCollection(
        entries=tuple(
            ClientThreshold(
                client_id=cid,
                threshold=tau,
                calibration_pending=False,
                strategy=strategy,
            )
            for cid in eligible_ids
        )
    )


def compute_global_pair(
    collection: ScoreCollection,
    poisoned_cal_set: PoisonedCalibrationSet | dict[str, np.ndarray],
    q: float,
) -> ThresholdPair:
    """Compute GLOBAL_THRESHOLD threshold pair from clean vs poisoned cal.

    GLOBAL_THRESHOLD tau_global = (1/K_elig) × Σ τᵢ over eligible clients.
    When a victim's cal is poisoned, their τᵢ changes, shifting tau_global.
    All clients (eligible and pending) receive the same tau_global.

    poisoned_cal must contain entries for all eligible clients; values for
    non-victim eligible clients are expected to equal their clean cal.
    """
    if not isinstance(poisoned_cal_set, PoisonedCalibrationSet):
        poisoned_cal_set = PoisonedCalibrationSet.from_mapping(poisoned_cal_set)
    eligible_ids = collection.eligible_ids
    eligibility = EligibilityResult(eligible_ids=eligible_ids, pending_ids=())

    taus_clean = compute_client_thresholds(
        _error_set_from_collection(collection), eligibility, q=q
    )
    tau_global_clean = compute_tau_global(taus_clean)

    taus_pois = compute_client_thresholds(
        _error_set_from_poisoned(poisoned_cal_set, eligible_ids), eligibility, q=q
    )
    tau_global_pois = compute_tau_global(taus_pois)

    # GLOBAL_THRESHOLD: all eligible clients share tau_global; per-client dict is uniform.
    thresholds_clean = _uniform_thresholds(eligible_ids, tau_global_clean, ThresholdPolicy.GLOBAL_THRESHOLD)
    thresholds_pois = _uniform_thresholds(eligible_ids, tau_global_pois, ThresholdPolicy.GLOBAL_THRESHOLD)

    return ThresholdPair(
        policy=ThresholdPolicy.GLOBAL_THRESHOLD,
        tau_global_clean=tau_global_clean,
        tau_global_pois=tau_global_pois,
        thresholds_clean=thresholds_clean,
        thresholds_pois=thresholds_pois,
    )


def compute_local_pair(
    collection: ScoreCollection,
    poisoned_cal_set: PoisonedCalibrationSet | dict[str, np.ndarray],
    q: float,
    tau_global_clean: float,
) -> ThresholdPair:
    """Compute LOCAL_THRESHOLD threshold pair from clean vs poisoned cal.

    LOCAL_THRESHOLD: each eligible client has τᵢ = percentile_q(cal_i).
    Poisoning victim v only changes τ_v; other clients are unchanged.
    tau_global_clean is the GLOBAL_THRESHOLD threshold (used as fallback for pending;
    it is also the reference tau_global for LOCAL_THRESHOLD — computed from GLOBAL_THRESHOLD).
    tau_global_pois for LOCAL_THRESHOLD is recomputed (mean of poisoned per-client taus).

    poisoned_cal must contain entries for all eligible clients.
    """
    if not isinstance(poisoned_cal_set, PoisonedCalibrationSet):
        poisoned_cal_set = PoisonedCalibrationSet.from_mapping(poisoned_cal_set)
    eligible_ids = collection.eligible_ids
    eligibility = EligibilityResult(eligible_ids=eligible_ids, pending_ids=())

    taus_clean = compute_client_thresholds(
        _error_set_from_collection(collection), eligibility, q=q
    )

    taus_pois = compute_client_thresholds(
        _error_set_from_poisoned(poisoned_cal_set, eligible_ids), eligibility, q=q
    )

    tau_global_pois = compute_tau_global(taus_pois)

    return ThresholdPair(
        policy=ThresholdPolicy.LOCAL_THRESHOLD,
        tau_global_clean=tau_global_clean,
        tau_global_pois=tau_global_pois,
        thresholds_clean=taus_clean,
        thresholds_pois=taus_pois,
    )
