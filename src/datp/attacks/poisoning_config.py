from __future__ import annotations

from dataclasses import dataclass

from datp.attacks.poison_enums import AttackerObjective


@dataclass(frozen=True, slots=True)
class CalibrationPoisoningConfig:
    """Configuration for a calibration-set poisoning experiment cell.

    QUARANTINED: attack_rate/shift_magnitude schema violates CP2 protocol.
    Replacement target: CP2-T017/T027 (fraction + REPLACE_FIXED_BUDGET config).
    """

    attack_rate: float
    objective: AttackerObjective
    shift_magnitude: float
    seed: int = 0

    def __post_init__(self) -> None:
        if not (0.0 < self.attack_rate <= 1.0):
            raise ValueError(f"attack_rate must be in (0, 1], got {self.attack_rate}")
        if self.shift_magnitude < 0.0:
            raise ValueError(
                f"shift_magnitude must be >= 0, got {self.shift_magnitude}"
            )
