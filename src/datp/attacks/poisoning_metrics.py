from __future__ import annotations

from dataclasses import dataclass

from datp.attacks.poison_enums import AttackerObjective
from datp.core.enums import Baseline


@dataclass(frozen=True, slots=True)
class PoisoningEffect:
    """Comparison of clean vs poisoned threshold for one baseline/client.

    QUARANTINED: relative_shift uses shift_magnitude framing (wrong protocol).
    Replacement target: CP2-T033 (Δτ, Δτ_rel, δ_{τ,i} metric engine).
    """

    baseline: Baseline
    client_id: str
    clean_threshold: float
    poisoned_threshold: float
    objective: AttackerObjective

    @property
    def absolute_shift(self) -> float:
        return self.poisoned_threshold - self.clean_threshold

    @property
    def relative_shift(self) -> float:
        if self.clean_threshold == 0.0:
            return float("inf")
        return self.absolute_shift / self.clean_threshold


@dataclass(frozen=True, slots=True)
class PoisoningExperimentResult:
    """Aggregated poisoning experiment result across all clients and baselines.

    QUARANTINED: attack_rate/shift_magnitude fields violate CP2 protocol.
    Replacement target: CP2-T027/T033.
    """

    attack_rate: float
    shift_magnitude: float
    objective: AttackerObjective
    effects: list[PoisoningEffect]

    def mean_absolute_shift(self, baseline: Baseline) -> float:
        relevant = [e.absolute_shift for e in self.effects if e.baseline == baseline]
        if not relevant:
            return 0.0
        return sum(relevant) / len(relevant)
