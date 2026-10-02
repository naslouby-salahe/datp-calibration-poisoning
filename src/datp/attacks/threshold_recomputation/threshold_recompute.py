
from __future__ import annotations

from datp.attacks.score_containers import ScoreCollection
from datp.attacks.types import PoisonedCalibrationSet, ThresholdPairBase
from datp.core.enums import ClientStatus, ThresholdPolicy
from datp.core.types import (
    ClientThreshold,
)
from datp.types import (
    ClientId,
    Quantile,
    Threshold,
)
from datp.thresholding.eligibility import (
    CalibrationErrorSet,
    ClientCalibrationErrors,
    ClientThresholdsCollection,
    EligibilityResult,
    compute_client_thresholds,
    compute_tau_global,
)

def get_threshold_data(
    collection: ScoreCollection,
    poisoned_cal: PoisonedCalibrationSet,
    q: Quantile,
) -> tuple[ClientThresholdsCollection, ClientThresholdsCollection, tuple[ClientId, ...]]:
    eligible_ids = collection.eligible_ids
    eligibility = EligibilityResult(eligible_ids=eligible_ids, pending_ids=())

    taus_clean = compute_client_thresholds(
        collection.eligible_calibration_errors,
        eligibility,
        q=q,
    )
    taus_pois = compute_client_thresholds(
        CalibrationErrorSet(
            tuple(
                ClientCalibrationErrors(cid, poisoned_cal[cid].cal)
                for cid in eligible_ids
            )
        ),
        eligibility,
        q=q,
    )
    return taus_clean, taus_pois, eligible_ids


def build_uniform_collection(
    eligible_ids: tuple[ClientId, ...], tau: Threshold
) -> ClientThresholdsCollection:
    return ClientThresholdsCollection(
        entries=tuple(
            ClientThreshold(
                client_id=cid,
                threshold=tau,
                status=ClientStatus.ELIGIBLE,
                strategy=ThresholdPolicy.GLOBAL_THRESHOLD,
            )
            for cid in eligible_ids
        )
    )


def compute_global_pair(
    collection: ScoreCollection,
    poisoned_cal_set: PoisonedCalibrationSet,
    q: Quantile,
) -> ThresholdPairBase:
    taus_clean, taus_pois, eligible_ids = get_threshold_data(
        collection, poisoned_cal_set, q
    )

    tau_global_clean = compute_tau_global(taus_clean)
    tau_global_pois = compute_tau_global(taus_pois)

    return ThresholdPairBase(
        policy=ThresholdPolicy.GLOBAL_THRESHOLD,
        tau_global_clean=tau_global_clean,
        tau_global_pois=tau_global_pois,
        thresholds_clean=build_uniform_collection(eligible_ids, tau_global_clean),
        thresholds_pois=build_uniform_collection(eligible_ids, tau_global_pois),
    )


def compute_local_pair(
    collection: ScoreCollection,
    poisoned_cal_set: PoisonedCalibrationSet,
    q: Quantile,
    tau_global_clean: Threshold,
) -> ThresholdPairBase:
    taus_clean, taus_pois, _ = get_threshold_data(collection, poisoned_cal_set, q)

    return ThresholdPairBase(
        policy=ThresholdPolicy.LOCAL_THRESHOLD,
        tau_global_clean=tau_global_clean,
        tau_global_pois=compute_tau_global(taus_pois),
        thresholds_clean=taus_clean,
        thresholds_pois=taus_pois,
    )
