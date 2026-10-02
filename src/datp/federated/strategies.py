from __future__ import annotations

from datp.types import (
    ClientId,
    DurationSeconds,
    Index,
    NarrativeText,
    PoisonFraction,
    RecordKey,
    RoundCount,
    RoundIndex,
    SampleCount,
    ScoreValue,
    SignedCount,
)


from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from flwr.common import (
    EvaluateRes,
    EvaluateIns,
    FitRes,
    FitIns,
    NDArrays,
    Parameters,
    Scalar,
    parameters_to_ndarrays,
)
from flwr.server.client_proxy import ClientProxy
from flwr.server.client_manager import ClientManager
from flwr.server.strategy import FedAvg

from datp.checkpointing.enums import CheckpointConvergenceMode
from datp.config.models import (
    CheckpointProtocolConfig,
    DatpConfig,
)
from datp.federated.checkpoints import save_params_snapshot
from datp.federated.convergence import ConvergenceMonitor
from datp.federated.enums import FederatedRoundStage


@dataclass(frozen=True, slots=True)
class FedAvgBuildRequest:

    initial_parameters: Parameters
    num_clients: SampleCount
    effective_rounds_max: RoundCount
    checkpoint_disk_dirs: dict[RoundIndex, Path] | None


@dataclass(frozen=True, slots=True)
class FedAvgConfig:

    convergence_monitor: ConvergenceMonitor
    round_timeout_s: DurationSeconds
    fraction_fit: PoisonFraction
    fraction_evaluate: PoisonFraction
    min_fit_clients: SignedCount
    min_evaluate_clients: SignedCount
    min_available_clients: SignedCount
    initial_parameters: Parameters | None = None
    checkpoint_milestones: tuple[SignedCount, ...] = ()
    convergence_mode: CheckpointConvergenceMode = CheckpointConvergenceMode.EARLY_STOP
    checkpoint_disk_dirs: dict[RoundIndex, Path] | None = None


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
    def parameter_snapshots(self) -> dict[Index, NDArrays]:
        return self._parameter_snapshots.copy()

    def _raise_if_failures(
        self,
        stage: FederatedRoundStage,
        server_round: RoundIndex,
        failures: Sequence[
            tuple[ClientProxy, FitRes | EvaluateRes] | BaseException
        ],
    ) -> None:
        if not failures:
            return
        failed_ids: list[ClientId | NarrativeText] = []
        for item in failures:
            if isinstance(item, BaseException):
                failed_ids.append("<unidentified>")
            else:
                failed_ids.append(ClientId(item[0].cid))
        raise RuntimeError(
            f"FL round {server_round}: {len(failures)} failures during {stage}. Failed clients: {failed_ids}"
        )

    def aggregate_fit(
        self,
        server_round: RoundIndex,
        results: list[tuple[ClientProxy, FitRes]],
        failures: list[tuple[ClientProxy, FitRes] | BaseException],
    ) -> tuple[Parameters | None, dict[RecordKey, Scalar]]:
        self._raise_if_failures(FederatedRoundStage.FIT, server_round, failures)
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
        self, server_round: RoundIndex, parameters: Parameters, client_manager: ClientManager
    ) -> list[tuple[ClientProxy, FitIns]]:
        if self._stopped:
            return []
        return super().configure_fit(server_round, parameters, client_manager)

    def configure_evaluate(
        self, server_round: RoundIndex, parameters: Parameters, client_manager: ClientManager
    ) -> list[tuple[ClientProxy, EvaluateIns]]:
        if self._stopped:
            return []
        return super().configure_evaluate(server_round, parameters, client_manager)

    def aggregate_evaluate(
        self,
        server_round: RoundIndex,
        results: list[tuple[ClientProxy, EvaluateRes]],
        failures: list[tuple[ClientProxy, EvaluateRes] | BaseException],
    ) -> tuple[ScoreValue | None, dict[RecordKey, Scalar]]:
        self._raise_if_failures(FederatedRoundStage.EVALUATE, server_round, failures)
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
        monitor = ConvergenceMonitor.from_config(
            cfg, rounds_max=req.effective_rounds_max
        )

        ckpt_cfg = cfg.checkpoint_protocol
        ckpt_milestones: tuple[SignedCount, ...] = ()
        ckpt_conv_mode = CheckpointConvergenceMode.EARLY_STOP
        if isinstance(ckpt_cfg, CheckpointProtocolConfig) and ckpt_cfg.enabled:
            ckpt_milestones = ckpt_cfg.milestones
            ckpt_conv_mode = ckpt_cfg.convergence_mode

        return cls(
            FedAvgConfig(
                convergence_monitor=monitor,
                round_timeout_s=cfg.federation.convergence.round_timeout_s,
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
