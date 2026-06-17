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

from dataclasses import dataclass

import numpy as np

from datp.attacks.score_containers import ScoreCollection
from datp.core.poison_enums import ThresholdPolicy
from datp.thresholding.eligibility import (
    compute_client_thresholds,
    compute_tau_global,
)


@dataclass(frozen=True, slots=True)
class ThresholdPair:
    """Clean and poisoned threshold pair for one policy over all clients.

    thresholds_clean / thresholds_pois: eligible-client-indexed thresholds.
    Pending clients receive tau_global (not stored here; access via
    tau_global_clean / tau_global_pois).
    """

    policy: ThresholdPolicy
    tau_global_clean: float
    tau_global_pois: float
    thresholds_clean: dict[str, float]
    thresholds_pois: dict[str, float]


def compute_b1_pair(
    collection: ScoreCollection,
    poisoned_cal: dict[str, np.ndarray],
    q: float,
) -> ThresholdPair:
    """Compute B1 (global) threshold pair from clean vs poisoned cal.

    B1 tau_global = (1/K_elig) × Σ τᵢ over eligible clients.
    When a victim's cal is poisoned, their τᵢ changes, shifting tau_global.
    All clients (eligible and pending) receive the same tau_global.

    poisoned_cal must contain entries for all eligible clients; values for
    non-victim eligible clients are expected to equal their clean cal.
    """
    eligible_ids = list(collection.eligible_ids)

    clean_cal = collection.eligible_cal_dict()
    taus_clean = compute_client_thresholds(clean_cal, eligible_ids, q=q)
    tau_global_clean = compute_tau_global(taus_clean)

    pois_eligible_cal = {cid: poisoned_cal[cid] for cid in eligible_ids}
    taus_pois = compute_client_thresholds(pois_eligible_cal, eligible_ids, q=q)
    tau_global_pois = compute_tau_global(taus_pois)

    # B1: all eligible clients share tau_global; per-client dict is uniform.
    thresholds_clean = dict.fromkeys(eligible_ids, tau_global_clean)
    thresholds_pois = dict.fromkeys(eligible_ids, tau_global_pois)

    return ThresholdPair(
        policy=ThresholdPolicy.B1_GLOBAL,
        tau_global_clean=tau_global_clean,
        tau_global_pois=tau_global_pois,
        thresholds_clean=thresholds_clean,
        thresholds_pois=thresholds_pois,
    )


def compute_b2_pair(
    collection: ScoreCollection,
    poisoned_cal: dict[str, np.ndarray],
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
    eligible_ids = list(collection.eligible_ids)

    clean_cal = collection.eligible_cal_dict()
    taus_clean = compute_client_thresholds(clean_cal, eligible_ids, q=q)

    pois_eligible_cal = {cid: poisoned_cal[cid] for cid in eligible_ids}
    taus_pois = compute_client_thresholds(pois_eligible_cal, eligible_ids, q=q)

    tau_global_pois = compute_tau_global(taus_pois)

    return ThresholdPair(
        policy=ThresholdPolicy.B2_PERSONALIZED,
        tau_global_clean=tau_global_clean,
        tau_global_pois=tau_global_pois,
        thresholds_clean=dict(taus_clean),
        thresholds_pois=dict(taus_pois),
    )
