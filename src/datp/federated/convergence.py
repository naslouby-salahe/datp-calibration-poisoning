from __future__ import annotations

from datp.types import (
    RoundCount,
    RoundIndex,
    SampleCount,
    ScoreValue,
    Threshold,
)


import math
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datp.config.models import DatpConfig


class ConvergenceMonitor:

    def __init__(
        self,
        rounds_initial: RoundCount,
        rounds_max: RoundCount,
        relative_threshold: Threshold,
        window: RoundCount,
    ) -> None:
        if rounds_initial < 1 or rounds_max < rounds_initial or window < 2:
            raise ValueError(
                f"Invalid convergence settings: initial={rounds_initial}, max={rounds_max}, window={window}"
            )

        self._rounds_initial = rounds_initial
        self._rounds_max = rounds_max
        self._relative_threshold = relative_threshold
        self._window = window
        self._losses: deque[ScoreValue] = deque(maxlen=rounds_max)
        self._converged_round: RoundIndex | None = None
        self._latest_relative_change: ScoreValue | None = None

    @property
    def converged_round(self) -> RoundIndex | None:
        return self._converged_round

    @property
    def num_recorded(self) -> SampleCount:
        return len(self._losses)

    @property
    def loss_history(self) -> list[ScoreValue]:
        return list(self._losses)

    @property
    def latest_relative_change(self) -> ScoreValue | None:
        return self._latest_relative_change

    def record(self, weighted_loss: ScoreValue) -> None:
        if not math.isfinite(weighted_loss):
            raise ValueError(f"Non-finite loss recorded: {weighted_loss}")
        self._losses.append(weighted_loss)

    def should_stop(
        self, server_round: RoundIndex, *, stop_on_convergence: bool = True
    ) -> bool:
        if self._converged_round is not None:
            return stop_on_convergence
        if server_round >= self._rounds_max:
            return True
        if server_round < self._rounds_initial or len(self._losses) < 2 * self._window:
            return False

        losses_list = list(self._losses)
        prev_mean = sum(losses_list[-(2 * self._window) : -self._window]) / self._window
        curr_mean = sum(losses_list[-self._window :]) / self._window

        rel_change = (
            0.0
            if abs(prev_mean) < 1e-12
            else abs(curr_mean - prev_mean) / abs(prev_mean)
        )
        self._latest_relative_change = rel_change

        if rel_change < self._relative_threshold:
            self._converged_round = server_round
            return stop_on_convergence
        return False

    @classmethod
    def from_config(
        cls, cfg: DatpConfig, *, rounds_max: RoundCount | None = None
    ) -> ConvergenceMonitor:
        conv = cfg.federation.convergence
        return cls(
            conv.rounds_initial,
            rounds_max if rounds_max is not None else conv.rounds_max,
            conv.relative_threshold,
            conv.window,
        )
