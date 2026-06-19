"""B1/B2 threshold recomputation under calibration poisoning.

Thin adapter over the inherited thresholding strategies. Accepts a clean
ScoreCollection and a poisoned calibration dict, and returns typed
clean/poisoned threshold pairs.

Eligibility is fixed from the clean collection (cardinality is preserved under
REPLACE_FIXED_BUDGET, so eligible/pending partition never changes).

B1 (global): tau_global = mean of per-client eligible percentiles.
  Poisoning one victim shifts the global mean.
B2 (personalized): each eligible client has its own percentile threshold.
  Poisoning one victim changes only that victim's threshold.

Pending clients receive tau_global in both policies.
"""

from __future__ import annotations

import numpy as np

from datp.attacks.score_containers import ScoreCollection
from datp.attacks.enums import ThresholdPolicy
from datp.attacks.types import PoisonedCalibrationSet, ThresholdPairBase
from datp.core.enums import Baseline
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
    eligible_ids: tuple[str, ...], tau: float, strategy: Baseline
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


def compute_b1_pair(
    collection: ScoreCollection,
    poisoned_cal_set: PoisonedCalibrationSet | dict[str, np.ndarray],
    q: float,
) -> ThresholdPair:
    """Compute B1 (global) threshold pair from clean vs poisoned cal.

    B1 tau_global = (1/K_elig) × Σ τᵢ over eligible clients.
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

    # B1: all eligible clients share tau_global; per-client dict is uniform.
    thresholds_clean = _uniform_thresholds(eligible_ids, tau_global_clean, Baseline.B1)
    thresholds_pois = _uniform_thresholds(eligible_ids, tau_global_pois, Baseline.B1)

    return ThresholdPair(
        policy=ThresholdPolicy.B1_GLOBAL,
        tau_global_clean=tau_global_clean,
        tau_global_pois=tau_global_pois,
        thresholds_clean=thresholds_clean,
        thresholds_pois=thresholds_pois,
    )


def compute_b2_pair(
    collection: ScoreCollection,
    poisoned_cal_set: PoisonedCalibrationSet | dict[str, np.ndarray],
    q: float,
    tau_global_clean: float,
) -> ThresholdPair:
    """Compute B2 (personalized) threshold pair from clean vs poisoned cal.

    B2: each eligible client has τᵢ = percentile_q(cal_i).
    Poisoning victim v only changes τ_v; other clients are unchanged.
    tau_global_clean is the B1 global threshold (used as fallback for pending;
    it is also the reference tau_global for B2 — computed from B1).
    tau_global_pois for B2 is recomputed (mean of poisoned per-client taus).

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
        policy=ThresholdPolicy.B2_PERSONALIZED,
        tau_global_clean=tau_global_clean,
        tau_global_pois=tau_global_pois,
        thresholds_clean=taus_clean,
        thresholds_pois=taus_pois,
    )
