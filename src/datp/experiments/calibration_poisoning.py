from __future__ import annotations

import numpy as np

from datp.attacks.calibration_poisoning import PoisoningObjective, poison_calibration_errors
from datp.attacks.poisoning_config import CalibrationPoisoningConfig
from datp.attacks.poisoning_metrics import PoisoningEffect, PoisoningExperimentResult
from datp.config.models import ThresholdConfig
from datp.core.enums import Baseline, Regime
from datp.thresholding.thresholds import arithmetic_mean_threshold, derive_threshold, percentile_threshold

_POISONING_BASELINES = (Baseline.B1, Baseline.B2, Baseline.B4)


def _tau_global_from_errors(
    client_errors: dict[str, np.ndarray],
    q: float,
) -> float:
    """Compute global B1 threshold as arithmetic mean of per-client percentiles."""
    per_client = [percentile_threshold(errs, q) for errs in client_errors.values() if len(errs) > 0]
    if not per_client:
        return 0.0
    return arithmetic_mean_threshold(per_client)


def run_poisoning_experiment(
    client_errors: dict[str, np.ndarray],
    config: CalibrationPoisoningConfig,
    threshold_cfg: ThresholdConfig,
    regime: Regime,
    seed: int = 0,
    alpha: float | None = None,
) -> PoisoningExperimentResult:
    """Compare clean vs poisoned thresholds for B1, B2, and B4.

    Outputs are isolated under outputs/conference_calibration_poisoning/.
    This function is pure (no IO) and returns a result object.
    """
    rng = np.random.default_rng(config.seed)

    poisoned_errors: dict[str, np.ndarray] = {
        cid: poison_calibration_errors(
            errs,
            attack_rate=config.attack_rate,
            objective=config.objective,
            shift_magnitude=config.shift_magnitude,
            rng=rng,
        )
        for cid, errs in client_errors.items()
    }

    clean_tau_global = _tau_global_from_errors(client_errors, threshold_cfg.q)
    poisoned_tau_global = _tau_global_from_errors(poisoned_errors, threshold_cfg.q)

    effects: list[PoisoningEffect] = []

    for baseline in _POISONING_BASELINES:
        clean_result = derive_threshold(
            baseline,
            client_errors,
            threshold_cfg.n_min,
            threshold_cfg.q,
            clean_tau_global,
            regime,
            threshold_cfg=threshold_cfg,
            seed=seed,
            alpha=alpha,
        )
        poisoned_result = derive_threshold(
            baseline,
            poisoned_errors,
            threshold_cfg.n_min,
            threshold_cfg.q,
            poisoned_tau_global,
            regime,
            threshold_cfg=threshold_cfg,
            seed=seed,
            alpha=alpha,
        )

        clean_by_client = {ct.client_id: ct.threshold for ct in clean_result.client_thresholds}
        poisoned_by_client = {ct.client_id: ct.threshold for ct in poisoned_result.client_thresholds}

        for client_id in clean_by_client:
            if client_id in poisoned_by_client:
                effects.append(
                    PoisoningEffect(
                        baseline=baseline,
                        client_id=client_id,
                        clean_threshold=clean_by_client[client_id],
                        poisoned_threshold=poisoned_by_client[client_id],
                        objective=config.objective,
                    )
                )

    return PoisoningExperimentResult(
        attack_rate=config.attack_rate,
        shift_magnitude=config.shift_magnitude,
        objective=config.objective,
        effects=effects,
    )
