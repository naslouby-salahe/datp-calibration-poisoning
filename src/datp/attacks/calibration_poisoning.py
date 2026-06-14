from __future__ import annotations

import enum
from enum import auto

import numpy as np


class PoisoningObjective(enum.StrEnum):
    """What the attacker aims to achieve by poisoning the calibration set."""

    RAISE_THRESHOLD = auto()
    LOWER_THRESHOLD = auto()


def poison_calibration_errors(
    errors: np.ndarray,
    *,
    attack_rate: float,
    objective: PoisoningObjective,
    shift_magnitude: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Return a copy of *errors* with a fraction poisoned by shifting.

    For RAISE_THRESHOLD the attacker injects high-error (benign-looking) samples
    so the threshold rises and attacks go undetected.
    For LOWER_THRESHOLD the attacker injects low-error samples so the threshold
    drops and legitimate traffic is flagged (availability attack).
    """
    if not (0.0 < attack_rate <= 1.0):
        raise ValueError(f"attack_rate must be in (0, 1], got {attack_rate}")

    poisoned = errors.copy()
    n = len(poisoned)
    n_poison = max(1, int(round(n * attack_rate)))
    indices = rng.choice(n, size=n_poison, replace=False)

    if objective == PoisoningObjective.RAISE_THRESHOLD:
        poisoned[indices] = poisoned[indices] + shift_magnitude
    else:
        poisoned[indices] = np.maximum(0.0, poisoned[indices] - shift_magnitude)

    return poisoned
