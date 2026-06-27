"""FedAvg strategy with convergence monitoring and checkpoint snapshotting."""

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
from datp.federated.checkpoints import save_params_snapshot
from datp.federated.convergence import ConvergenceMonitor


@dataclass(frozen=True, slots=True)
class FedAvgBuildRequest:
    """Input bundle to construct a DatpFedAvg strategy from configuration."""

    initial_parameters: Parameters
    num_clients: int
    effective_rounds_max: int
    checkpoint_disk_dirs: dict[int, Path] | None


@dataclass(frozen=True, slots=True)
class FedAvgConfig:
    """Immutable configuration for DatpFedAvg hyperparameters and callbacks."""

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
    """FedAvg variant that snapshots parameters at milestones and stops on convergence."""

    def __init__(self, config: FedAvgConfig) -> None:
        """Initialize with convergence monitoring and checkpoint snapshots."""
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
        """The convergence monitor driving early stopping."""
        return self._monitor

    @property
    def stopped(self) -> bool:
        """Whether training has been stopped by convergence or max rounds."""
        return self._stopped

    @property
    def latest_parameters(self) -> NDArrays | None:
        """The most recently aggregated model parameters."""
        return self._latest_parameters

    @property
    def parameter_snapshots(self) -> dict[int, NDArrays]:
        """Shallow copy of milestone parameter snapshots keyed by round."""
        return self._parameter_snapshots.copy()

    def _raise_if_failures(
        self,
        stage: str,
        server_round: int,
        failures: list[tuple[ClientProxy, Any] | BaseException],
    ) -> None:
        """Raise a RuntimeError listing all failed clients for the round."""
        if not failures:
            return
        failed_ids = []
        for item in failures:
            if isinstance(item, BaseException):
                failed_ids.append("<unidentified>")
            else:
                failed_ids.append(item[0].cid)
        raise RuntimeError(
            f"FL round {server_round}: {len(failures)} failures during {stage}. Failed clients: {failed_ids}"
        )

    def aggregate_fit(
        self,
        server_round: int,
        results: list[tuple[ClientProxy, Any]],
        failures: list[tuple[ClientProxy, Any] | BaseException],
    ) -> tuple[Parameters | None, dict[str, Scalar]]:
        """Aggregate fit results and snapshot parameters at checkpoint milestones."""
        self._raise_if_failures("fit", server_round, failures)
        aggregated = super().aggregate_fit(server_round, results, failures)
        if not aggregated or not aggregated[0]:
            return None, aggregated[1] if aggregated else {}

        params, fit_metrics = aggregated
        assert params is not None
        self._latest_parameters = parameters_to_ndarrays(params)

        if server_round in self._checkpoint_milestones:
            self._parameter_snapshots[server_round] = [
                arr.copy() for arr in self._latest_parameters
            ]
            if server_round in self._checkpoint_disk_dirs:
                save_params_snapshot(
                    self._parameter_snapshots[server_round],
                    self._checkpoint_disk_dirs[server_round],
                )

        return params, fit_metrics

    def configure_fit(
        self, server_round: int, parameters: Parameters, client_manager: Any
    ) -> list[tuple[ClientProxy, FitIns]]:
        """Skip fit configuration when training has stopped."""
        if self._stopped:
            return []
        self._round_start_time = time.monotonic()
        return super().configure_fit(server_round, parameters, client_manager)

    def configure_evaluate(
        self, server_round: int, parameters: Parameters, client_manager: Any
    ) -> list[tuple[ClientProxy, EvaluateIns]]:
        """Skip evaluation configuration when training has stopped."""
        if self._stopped:
            return []
        return super().configure_evaluate(server_round, parameters, client_manager)

    def aggregate_evaluate(
        self,
        server_round: int,
        results: list[tuple[ClientProxy, Any]],
        failures: list[tuple[ClientProxy, Any] | BaseException],
    ) -> tuple[float | None, dict[str, Scalar]]:
        """Aggregate evaluation losses and feed weighted loss to the convergence monitor."""
        self._raise_if_failures("evaluate", server_round, failures)
        if not results:
            return None, {}

        total_examples = sum(res.num_examples for _, res in results)
        if total_examples == 0:
            return None, {}

        weighted_loss = (
            sum(res.loss * res.num_examples for _, res in results) / total_examples
        )
        self._monitor.record(weighted_loss)

        if self._monitor.should_stop(
            server_round,
            stop_on_convergence=self._convergence_mode
            == CheckpointConvergenceMode.EARLY_STOP,
        ):
            self._stopped = True

        return weighted_loss, {"weighted_val_loss": weighted_loss}

    @classmethod
    def from_config(cls, cfg: DatpConfig, req: FedAvgBuildRequest) -> DatpFedAvg:
        """Build a DatpFedAvg strategy from configuration and a build request."""
        conv = cfg.federation.convergence
        monitor = ConvergenceMonitor(
            conv.rounds_initial,
            req.effective_rounds_max,
            conv.relative_threshold,
            conv.window,
        )

        ckpt_cfg = cfg.checkpoint_protocol
        ckpt_milestones: tuple[int, ...] = ()
        ckpt_conv_mode = CheckpointConvergenceMode.EARLY_STOP
        if isinstance(ckpt_cfg, CheckpointProtocolConfig) and ckpt_cfg.enabled:
            ckpt_milestones = ckpt_cfg.milestones
            ckpt_conv_mode = ckpt_cfg.convergence_mode

        return cls(
            FedAvgConfig(
                convergence_monitor=monitor,
                round_timeout_s=conv.round_timeout_s,
                fraction_fit=1.0,
                fraction_evaluate=1.0,
                min_fit_clients=req.num_clients,
                min_evaluate_clients=req.num_clients,
                min_available_clients=req.num_clients,
                initial_parameters=req.initial_parameters,
                checkpoint_milestones=ckpt_milestones,
                convergence_mode=ckpt_conv_mode,
                checkpoint_disk_dirs=req.checkpoint_disk_dirs,
            )
        )
