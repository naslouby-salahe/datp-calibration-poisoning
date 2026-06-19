# SPDX-License-Identifier: Proprietary
"""Convergence criterion: relative change between consecutive window means of FedAvg-weighted benign validation loss."""

from __future__ import annotations

import math
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datp.config.models import DatpConfig

from datp.core.errors import fmt
from datp.core.logging import get_logger

logger = get_logger(__name__)

_MODULE = "federated.convergence"


class ConvergenceMonitor:
    """Detects convergence by comparing mean loss of two consecutive windows.

    Criterion:
        previous_window_mean = mean(losses[-(2*window) : -window])
        current_window_mean = mean(losses[-window:])
        relative_change = |current_window_mean - previous_window_mean| / |previous_window_mean|

    Convergence fires when relative_change < relative_threshold.
    Requires at least 2 * window recorded losses before evaluation can begin.
    """

    def __init__(
        self,
        rounds_initial: int,
        rounds_max: int,
        relative_threshold: float,
        window: int,
    ) -> None:
        if rounds_initial < 1:
            raise ValueError(
                fmt(_MODULE, "rounds_initial must be >= 1", ">= 1", str(rounds_initial))
            )
        if rounds_max < rounds_initial:
            raise ValueError(
                fmt(
                    _MODULE,
                    "rounds_max must be >= rounds_initial",
                    f">= {rounds_initial}",
                    str(rounds_max),
                )
            )
        if window < 2:
            raise ValueError(fmt(_MODULE, "window must be >= 2", ">= 2", str(window)))
        self._rounds_initial = rounds_initial
        self._rounds_max = rounds_max
        self._relative_threshold = relative_threshold
        self._window = window
        self._losses: deque[float] = deque(maxlen=rounds_max)
        self._converged_round: int | None = None
        self._latest_relative_change: float | None = None

    @property
    def converged_round(self) -> int | None:
        return self._converged_round

    @property
    def num_recorded(self) -> int:
        return len(self._losses)

    @property
    def loss_history(self) -> list[float]:
        return list(self._losses)

    @property
    def latest_relative_change(self) -> float | None:
        return self._latest_relative_change

    def record(self, server_round: int, weighted_loss: float) -> None:
        if not math.isfinite(weighted_loss):
            raise ValueError(
                fmt(
                    _MODULE,
                    "Non-finite loss recorded",
                    "finite float",
                    repr(weighted_loss),
                )
            )
        self._losses.append(weighted_loss)
        logger.debug(
            "loss recorded",
            round=server_round,
            weighted_val_loss=weighted_loss,
            n_recorded=len(self._losses),
        )

    def should_stop(
        self, server_round: int, *, stop_on_convergence: bool = True
    ) -> bool:
        if self._converged_round is not None:
            return stop_on_convergence

        if server_round >= self._rounds_max:
            logger.info(
                "reached rounds_max, stopping",
                round=server_round,
                rounds_max=self._rounds_max,
            )
            return True

        if server_round < self._rounds_initial:
            return False

        n = len(self._losses)
        required = 2 * self._window
        if n < required:
            return False

        losses_list = list(self._losses)
        previous_window = losses_list[-(2 * self._window) : -self._window]
        current_window = losses_list[-self._window :]

        prev_mean = sum(previous_window) / len(previous_window)
        curr_mean = sum(current_window) / len(current_window)

        if abs(prev_mean) < 1e-12:
            rel_change = 0.0
        else:
            rel_change = abs(curr_mean - prev_mean) / abs(prev_mean)
        self._latest_relative_change = rel_change

        if rel_change < self._relative_threshold:
            self._converged_round = server_round
            logger.info(
                "convergence detected",
                round=server_round,
                rel_change=rel_change,
                threshold=self._relative_threshold,
                window=self._window,
                prev_window_mean=prev_mean,
                curr_window_mean=curr_mean,
            )
            return stop_on_convergence

        return False

    @classmethod
    def from_config(cls, cfg: "DatpConfig") -> "ConvergenceMonitor":
        conv = cfg.federation.convergence
        return cls(
            rounds_initial=conv.rounds_initial,
            rounds_max=conv.rounds_max,
            relative_threshold=conv.relative_threshold,
            window=conv.window,
        )
