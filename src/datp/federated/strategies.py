# SPDX-License-Identifier: Proprietary
"""FedAvg strategy weighted by local benign dataset size; convergence monitoring."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from flwr.common import (
    EvaluateIns,
    FitIns,
    NDArrays,
    Parameters,
    Scalar,
    parameters_to_ndarrays,
)
from flwr.server.client_proxy import ClientProxy
from flwr.server.strategy import FedAvg

from datp.checkpointing.enums import CheckpointConvergenceMode
from datp.config.models import CheckpointProtocolConfig, DatpConfig
from datp.core.logging import get_logger
from datp.federated.checkpoints import save_params_snapshot
from datp.federated.convergence import ConvergenceMonitor

logger = get_logger(__name__)

_PROC_SELF_STATUS = Path("/proc/self/status")
_KIB_PER_MIB = 1024
_RSS_UNAVAILABLE = -1.0


def _get_rss_mb() -> float:
    try:
        with _PROC_SELF_STATUS.open() as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / _KIB_PER_MIB
    except (OSError, ValueError):
        return _RSS_UNAVAILABLE
    return _RSS_UNAVAILABLE


_UNIDENTIFIED_CLIENT = "<unidentified>"


@dataclass(frozen=True, slots=True)
class ParticipationFailureReport:
    """Per-client diagnostics for a full-participation violation in one FL round."""

    stage: str
    server_round: int
    successful_ids: tuple[str, ...]
    failed_ids: tuple[str, ...]
    reasons: tuple[str, ...]

    @property
    def message(self) -> str:
        return (
            f"FL round {self.server_round}: {len(self.failed_ids)} client(s) failed "
            f"during {self.stage}; full participation required — aborting. "
            f"successful={len(self.successful_ids)} {list(self.successful_ids)}; "
            f"failed={len(self.failed_ids)} {list(self.failed_ids)}; "
            f"reasons={list(self.reasons)}"
        )


def _build_participation_failure_report(
    *,
    stage: str,
    server_round: int,
    results: list[tuple[ClientProxy, Any]],
    failures: list[tuple[ClientProxy, Any] | BaseException],
) -> ParticipationFailureReport:
    successful_ids = tuple(sorted(proxy.cid for proxy, _ in results))
    failed_ids: list[str] = []
    reasons: list[str] = []
    for item in failures:
        if isinstance(item, BaseException):
            failed_ids.append(_UNIDENTIFIED_CLIENT)
            reasons.append(f"{_UNIDENTIFIED_CLIENT}: {type(item).__name__}: {item}")
            continue
        proxy, res = item
        cid = proxy.cid
        failed_ids.append(cid)
        status = getattr(res, "status", None)
        reason = getattr(status, "message", None) or getattr(status, "code", None)
        reasons.append(
            f"{cid}: {reason}" if reason else f"{cid}: returned failure status"
        )
    return ParticipationFailureReport(
        stage=stage,
        server_round=server_round,
        successful_ids=successful_ids,
        failed_ids=tuple(failed_ids),
        reasons=tuple(reasons),
    )


@dataclass(frozen=True, slots=True)
class FedAvgConfig:
    """Constructor parameters for DatpFedAvg."""

    convergence_monitor: ConvergenceMonitor
    round_timeout_s: float
    fraction_fit: float
    fraction_evaluate: float
    min_fit_clients: int
    min_evaluate_clients: int
    min_available_clients: int
    initial_parameters: Parameters | None = None
    checkpoint_milestones: tuple[int, ...] = ()
    convergence_mode: CheckpointConvergenceMode = CheckpointConvergenceMode.EARLY_STOP
    checkpoint_disk_dirs: dict[int, Path] | None = None


class DatpFedAvg(FedAvg):
    def __init__(self, config: FedAvgConfig) -> None:
        super().__init__(
            fraction_fit=config.fraction_fit,
            fraction_evaluate=config.fraction_evaluate,
            min_fit_clients=config.min_fit_clients,
            min_evaluate_clients=config.min_evaluate_clients,
            min_available_clients=config.min_available_clients,
            initial_parameters=config.initial_parameters,
            fit_metrics_aggregation_fn=lambda _: {},
        )
        self._monitor = config.convergence_monitor
        self._round_timeout_s = config.round_timeout_s
        self._round_start_time: float | None = None
        self._stopped = False
        self._latest_parameters: NDArrays | None = None
        self._checkpoint_milestones = frozenset(config.checkpoint_milestones)
        self._parameter_snapshots: dict[int, NDArrays] = {}
        self._convergence_mode = config.convergence_mode
        self._checkpoint_disk_dirs: dict[int, Path] = config.checkpoint_disk_dirs or {}

    @property
    def convergence_monitor(self) -> ConvergenceMonitor:
        return self._monitor

    @property
    def stopped(self) -> bool:
        return self._stopped

    @property
    def latest_parameters(self) -> NDArrays | None:
        return self._latest_parameters

    @property
    def parameter_snapshots(self) -> dict[int, NDArrays]:
        return self._parameter_snapshots.copy()

    def _raise_if_failures(
        self,
        stage: str,
        server_round: int,
        results: list[tuple[ClientProxy, Any]],
        failures: list[tuple[ClientProxy, Any] | BaseException],
    ) -> None:
        if not failures:
            return
        report = _build_participation_failure_report(
            stage=stage,
            server_round=server_round,
            results=results,
            failures=failures,
        )
        logger.error(
            "full participation violated",
            round=server_round,
            stage=stage,
            successful=len(report.successful_ids),
            failed=len(report.failed_ids),
            failed_ids=list(report.failed_ids),
            reasons=list(report.reasons),
        )
        raise RuntimeError(report.message)

    def _check_stopped(self, stage: str, server_round: int) -> bool:
        if self._stopped:
            logger.info(f"convergence reached, skipping {stage}", round=server_round)
            return True
        return False

    def aggregate_fit(
        self,
        server_round: int,
        results: list[tuple[ClientProxy, Any]],
        failures: list[tuple[ClientProxy, Any] | BaseException],
    ) -> tuple[Parameters | None, dict[str, Scalar]]:
        self._raise_if_failures("fit", server_round, results, failures)
        aggregated = super().aggregate_fit(server_round, results, failures)
        if aggregated is None:
            return None, {}
        params, fit_metrics = aggregated
        if params is None:
            return None, fit_metrics
        self._latest_parameters = parameters_to_ndarrays(params)
        if server_round in self._checkpoint_milestones:
            self._parameter_snapshots[server_round] = [
                ndarray.copy() for ndarray in self._latest_parameters
            ]
            if server_round in self._checkpoint_disk_dirs:
                save_params_snapshot(
                    self._parameter_snapshots[server_round],
                    self._checkpoint_disk_dirs[server_round],
                )
        return params, fit_metrics

    def configure_fit(
        self,
        server_round: int,
        parameters: Parameters,
        client_manager: Any,
    ) -> list[tuple[ClientProxy, FitIns]]:
        if self._check_stopped("fit", server_round):
            return []
        self._round_start_time = time.monotonic()
        return super().configure_fit(server_round, parameters, client_manager)

    def configure_evaluate(
        self,
        server_round: int,
        parameters: Parameters,
        client_manager: Any,
    ) -> list[tuple[ClientProxy, EvaluateIns]]:
        if self._check_stopped("evaluate", server_round):
            return []
        return super().configure_evaluate(server_round, parameters, client_manager)

    def _record_round_timing(self, server_round: int) -> None:
        if self._round_start_time is None:
            return
        elapsed = time.monotonic() - self._round_start_time
        rss_mb = _get_rss_mb()
        logger.info(
            "round complete",
            round=server_round,
            elapsed_s=round(elapsed, 1),
            rss_mb=round(rss_mb, 0),
        )
        if elapsed > self._round_timeout_s:
            logger.warning(
                "round exceeded timeout",
                round=server_round,
                elapsed_s=round(elapsed, 1),
                timeout_s=self._round_timeout_s,
            )

    def _compute_weighted_loss(
        self,
        server_round: int,
        results: list[tuple[ClientProxy, Any]],
    ) -> float | None:
        total_examples = 0
        weighted_loss_sum = 0.0
        for _, evaluate_res in results:
            num_examples = evaluate_res.num_examples
            loss = evaluate_res.loss
            weighted_loss_sum += loss * num_examples
            total_examples += num_examples
        if total_examples == 0:
            logger.warning("total_examples=0 in aggregate_evaluate", round=server_round)
            return None
        return weighted_loss_sum / total_examples

    def aggregate_evaluate(
        self,
        server_round: int,
        results: list[tuple[ClientProxy, Any]],
        failures: list[tuple[ClientProxy, Any] | BaseException],
    ) -> tuple[float | None, dict[str, Scalar]]:
        self._raise_if_failures("evaluate", server_round, results, failures)
        if not results:
            logger.warning("no evaluate results received", round=server_round)
            return None, {}

        self._record_round_timing(server_round)

        weighted_loss = self._compute_weighted_loss(server_round, results)
        if weighted_loss is None:
            return None, {}

        self._monitor.record(server_round, weighted_loss)

        stop_on_convergence = (
            self._convergence_mode == CheckpointConvergenceMode.EARLY_STOP
        )
        if self._monitor.should_stop(
            server_round, stop_on_convergence=stop_on_convergence
        ):
            self._stopped = True
            logger.info(
                "convergence signal, requesting stop",
                round=server_round,
                converged_round=self._monitor.converged_round,
            )

        return weighted_loss, {"weighted_val_loss": weighted_loss}

    @classmethod
    def from_config(
        cls,
        cfg: DatpConfig,
        *,
        initial_parameters: Parameters,
        num_clients: int,
        effective_rounds_max: int,
        checkpoint_disk_dirs: dict[int, Path] | None = None,
    ) -> DatpFedAvg:
        conv = cfg.federation.convergence
        monitor = ConvergenceMonitor(
            rounds_initial=conv.rounds_initial,
            rounds_max=effective_rounds_max,
            relative_threshold=conv.relative_threshold,
            window=conv.window,
        )
        checkpoint_cfg = cfg.checkpoint_protocol
        checkpoint_milestones = (
            checkpoint_cfg.milestones
            if isinstance(checkpoint_cfg, CheckpointProtocolConfig)
            and checkpoint_cfg.enabled
            else ()
        )
        convergence_mode = (
            checkpoint_cfg.convergence_mode
            if isinstance(checkpoint_cfg, CheckpointProtocolConfig)
            and checkpoint_cfg.enabled
            else CheckpointConvergenceMode.EARLY_STOP
        )

        return cls(
            FedAvgConfig(
                convergence_monitor=monitor,
                round_timeout_s=conv.round_timeout_s,
                fraction_fit=1.0,
                fraction_evaluate=1.0,
                min_fit_clients=num_clients,
                min_evaluate_clients=num_clients,
                min_available_clients=num_clients,
                initial_parameters=initial_parameters,
                checkpoint_milestones=checkpoint_milestones,
                convergence_mode=convergence_mode,
                checkpoint_disk_dirs=checkpoint_disk_dirs,
            )
        )
