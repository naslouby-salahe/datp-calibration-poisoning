from __future__ import annotations

import numpy as np

from datp.attacks.poison_enums import AttackerObjective


def poison_calibration_errors(
    errors: np.ndarray,
    *,
    attack_rate: float,
    objective: AttackerObjective,
    shift_magnitude: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Return a copy of *errors* with a fraction poisoned by shifting.

    QUARANTINED: shift_magnitude injection violates REPLACE_FIXED_BUDGET protocol.
    Replacement target: CP2-T027 (REPLACE_FIXED_BUDGET injector).

    For THRESHOLD_RAISE the attacker injects high-error (benign-looking) samples
    so the threshold rises and attacks go undetected.
    For THRESHOLD_LOWER the attacker injects low-error samples so the threshold
    drops and legitimate traffic is flagged (availability attack).
    """
    if not (0.0 < attack_rate <= 1.0):
        raise ValueError(f"attack_rate must be in (0, 1], got {attack_rate}")

    poisoned = errors.copy()
    n = len(poisoned)
    n_poison = max(1, int(round(n * attack_rate)))
    indices = rng.choice(n, size=n_poison, replace=False)

    if objective == AttackerObjective.THRESHOLD_RAISE:
        poisoned[indices] = poisoned[indices] + shift_magnitude
    else:
        poisoned[indices] = np.maximum(0.0, poisoned[indices] - shift_magnitude)

    return poisoned
