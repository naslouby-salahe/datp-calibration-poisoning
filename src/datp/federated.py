from __future__ import annotations

import contextlib
import ctypes
import gc
import json
import math
import os
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, TypedDict, cast

import numpy as np
import pandas as pd
import polars as pl
import psutil
import torch
import torch.nn as nn
from flwr.client import Client, ClientApp, NumPyClient
from flwr.common import (
    Context,
    EvaluateIns,
    EvaluateRes,
    FitIns,
    FitRes,
    NDArrays,
    Parameters,
    Scalar,
    ndarrays_to_parameters,
    parameters_to_ndarrays,
)
from flwr.server import ServerApp, ServerConfig
from flwr.server.client_manager import ClientManager
from flwr.server.client_proxy import ClientProxy
from flwr.server.serverapp_components import ServerAppComponents
from flwr.server.strategy import FedAvg
from flwr.simulation.run_simulation import BackendConfig, run_simulation

from datp import configure_runtime_env
from datp.artifacts import ArtifactLayout
from datp.config import ConvergenceConfig, DatpConfig, ExperimentStage, MachineConfig
from datp.core import TrainingCellId, get_logger, resolve_device, set_seeds
from datp.data import (
    ClientData,
    ClientMetricKey,
    FederatedTensorLabel,
    Split,
    dataset_for_stage,
    filename_for_split,
    read_artifact,
    split_path,
    validate_client_data,
    validate_tensor_input,
)
from datp.enums import (
    ArtifactFile,
    ConvergenceStatus,
    ConvergenceSummaryKey,
    DeviceType,
    FederatedRoundStage,
)
from datp.modeling import Autoencoder, validate_model_on_cuda
from datp.scoring import score_clients
from datp.types import (
    BatchSize,
    ByteCount,
    ClientId,
    EpochCount,
    FeatureCount,
    GpuShare,
    LearningRate,
    NarrativeText,
    ParameterVector,
    RandomSeed,
    RoundCount,
    RoundIndex,
    SampleCount,
    ScoreValue,
    ScoreVector,
    SignedCount,
    Threshold,
)

logger = get_logger(__name__)


class _TorchArrayFactory(Protocol):
    def from_numpy(self, ndarray: ParameterVector) -> torch.Tensor: ...


def get_parameters(model: nn.Module) -> list[ParameterVector]:
    return [p.detach().cpu().numpy().copy() for p in model.parameters()]


def set_parameters(model: nn.Module, parameters: list[ParameterVector]) -> None:
    params_list = list(model.parameters())
    if len(params_list) != len(parameters):
        raise ValueError(
            f"Parameter count mismatch: {len(params_list)} vs {len(parameters)}"
        )
    with torch.no_grad():
        for i, (param, arr) in enumerate(zip(params_list, parameters, strict=True)):
            if tuple(param.shape) != tuple(arr.shape):
                raise ValueError(
                    f"Shape mismatch at index {i}: {param.shape} vs {arr.shape}"
                )
            param.copy_(
                cast(_TorchArrayFactory, torch)
                .from_numpy(arr)
                .to(dtype=param.dtype, device=param.device)
            )


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

    def should_stop(self, server_round: RoundIndex) -> bool:
        if self._converged_round is not None:
            return True
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
            return True
        return False


def save_convergence_artifacts(
    out_dir: Path, monitor: ConvergenceMonitor, conv_cfg: ConvergenceConfig
) -> None:
    loss_history = monitor.loss_history
    converged_round = monitor.converged_round
    curve_path = out_dir / ArtifactFile.CONVERGENCE_CURVE
    summary_path = out_dir / ArtifactFile.CONVERGENCE_SUMMARY
    df = pd.DataFrame(
        [
            {"round": i, "fedavg_weighted_benign_val_loss": loss}
            for i, loss in enumerate(loss_history, start=1)
        ]
    )
    curve_tmp = curve_path.with_suffix(".csv.tmp")
    summary_tmp = summary_path.with_suffix(".json.tmp")
    df.to_csv(curve_tmp, index=False)
    summary_tmp.write_text(
        json.dumps(
            {
                ConvergenceSummaryKey.ROUNDS_INITIAL: conv_cfg.rounds_initial,
                ConvergenceSummaryKey.ROUNDS_MAX: conv_cfg.rounds_max,
                ConvergenceSummaryKey.RELATIVE_THRESHOLD: conv_cfg.relative_threshold,
                ConvergenceSummaryKey.WINDOW: conv_cfg.window,
                ConvergenceSummaryKey.ACTUAL_ROUNDS: len(loss_history),
                ConvergenceSummaryKey.CONVERGENCE_ROUND: converged_round,
                ConvergenceSummaryKey.CONVERGENCE_CRITERION: monitor.latest_relative_change,
                ConvergenceSummaryKey.CONVERGENCE_STATUS: ConvergenceStatus.CONVERGED
                if converged_round is not None
                else ConvergenceStatus.NOT_CONVERGED,
                ConvergenceSummaryKey.WEIGHTED_LOSS: loss_history,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    curve_tmp.rename(curve_path)
    summary_tmp.rename(summary_path)


TRAINING_SPLITS: tuple[Split, ...] = (Split.TRAIN, Split.CAL)
ALL_SPLITS: tuple[Split, ...] = tuple(Split)


def release_freed_heap() -> None:
    gc.collect()
    with contextlib.suppress(OSError, AttributeError):
        ctypes.CDLL("libc.so.6").malloc_trim(0)


def discover_client_dirs(prepared_dir: Path) -> list[Path]:
    client_dirs = sorted(
        d
        for d in prepared_dir.iterdir()
        if d.is_dir() and split_path(d, Split.TRAIN).exists()
    )
    if not client_dirs:
        raise FileNotFoundError(f"No client directories found in {prepared_dir}")
    return client_dirs


def load_client_artifact(client_dir: Path, split: Split) -> pl.DataFrame:
    path = split_path(client_dir, split)
    if not path.exists():
        raise FileNotFoundError(f"Missing {path.name} in {client_dir}")
    return read_artifact(path)


def df_to_tensor(df: pl.DataFrame | ScoreVector, device: torch.device) -> torch.Tensor:
    values = df.to_numpy() if isinstance(df, pl.DataFrame) else np.asarray(df)
    return torch.tensor(values, dtype=torch.float32, device=device)


def load_single_client_training_data(
    client_dir: Path, device: torch.device
) -> tuple[torch.Tensor, torch.Tensor]:
    train_t = df_to_tensor(load_client_artifact(client_dir, Split.TRAIN), device)
    cal_t = df_to_tensor(load_client_artifact(client_dir, Split.CAL), device)
    release_freed_heap()
    return train_t, cal_t


def load_client_data(
    prepared_dir: Path, device: torch.device, splits: Sequence[Split]
) -> dict[ClientId, ClientData]:
    client_dirs = discover_client_dirs(prepared_dir)
    splits_set = frozenset(splits)

    first_train_df = load_client_artifact(client_dirs[0], Split.TRAIN)
    n_features = first_train_df.shape[1]
    if n_features == 0:
        raise ValueError(f"Train artifact has 0 columns in {client_dirs[0]}")

    empty = torch.empty(0, n_features, dtype=torch.float32, device=device)

    def _load_or_empty(
        cdir: Path, split: Split, override_df: pl.DataFrame | None = None
    ) -> torch.Tensor:
        if split not in splits_set:
            return empty
        df = (
            override_df
            if override_df is not None
            else load_client_artifact(cdir, split)
        )
        return df_to_tensor(df, device)

    client_data: dict[ClientId, ClientData] = {}
    for i, cdir in enumerate(client_dirs):
        client_data[ClientId(cdir.name)] = ClientData(
            train=_load_or_empty(cdir, Split.TRAIN, first_train_df if i == 0 else None),
            val=_load_or_empty(cdir, Split.CAL),
            test_benign=_load_or_empty(cdir, Split.TEST_BENIGN),
            test_attack=_load_or_empty(cdir, Split.TEST_ATTACK),
        )

    del first_train_df
    return client_data


class _Loss(Protocol):
    def backward(self) -> None: ...
    def item(self) -> float: ...


class _Optimizer(Protocol):
    def zero_grad(self) -> None: ...
    def step(self) -> None: ...


def train_local(
    model: Autoencoder,
    data: torch.Tensor,
    *,
    epochs: EpochCount,
    batch_size: BatchSize,
    lr: LearningRate,
) -> ScoreValue:
    if epochs < 1 or batch_size < 1:
        raise ValueError(
            f"epochs and batch_size must be >= 1 (got {epochs}, {batch_size})"
        )
    if data.numel() == 0:
        raise ValueError("training data must be non-empty")
    optimizer = cast(
        _Optimizer, torch.optim.Adam(model.parameters(), lr=lr, weight_decay=0.0)
    )
    last_loss = math.nan
    n = len(data)

    for _ in range(epochs):
        indices = torch.randperm(n, device=data.device)
        epoch_loss = 0.0
        n_batches = 0

        for start in range(0, n, batch_size):
            batch = data[indices[start : start + batch_size]]
            optimizer.zero_grad()
            loss = cast(_Loss, model.reconstruction_loss(batch))
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
            n_batches += 1

        last_loss = epoch_loss / max(n_batches, 1)

    if not math.isfinite(last_loss):
        raise RuntimeError(f"Training produced non-finite loss: {last_loss}")
    return last_loss


def evaluate_benign(model: Autoencoder, cal_data: torch.Tensor) -> ScoreValue:
    if cal_data.numel() == 0:
        raise ValueError("calibration data must be non-empty")
    model.eval()
    with torch.inference_mode():
        return model.reconstruction_loss(cal_data).item()


class DatpClient(NumPyClient):
    def __init__(
        self,
        cid: NarrativeText,
        model: Autoencoder,
        train_data: torch.Tensor,
        cal_data: torch.Tensor,
        cfg: DatpConfig,
    ) -> None:
        client_id = ClientId(cid)
        validate_tensor_input(train_data, FederatedTensorLabel.TRAIN_DATA, client_id)
        validate_tensor_input(
            cal_data, FederatedTensorLabel.CALIBRATION_DATA, client_id
        )
        self.cid = client_id
        self.model = model
        self.train_data = train_data
        self.cal_data = cal_data
        self._local_epochs = cfg.federation.local_epochs
        self._batch_size = cfg.machine.batch_size_train
        self._lr = cfg.model.lr

    def get_parameters(self, config: dict[str, Scalar]) -> NDArrays:
        return get_parameters(self.model)

    def fit(
        self, parameters: NDArrays, config: dict[str, Scalar]
    ) -> tuple[NDArrays, SampleCount, dict[str, Scalar]]:
        set_parameters(self.model, parameters)
        self.model.train()
        last_loss = train_local(
            self.model,
            self.train_data,
            epochs=self._local_epochs,
            batch_size=self._batch_size,
            lr=self._lr,
        )
        return (
            get_parameters(self.model),
            len(self.train_data),
            {ClientMetricKey.TRAIN_LOSS: last_loss},
        )

    def evaluate(
        self, parameters: NDArrays, config: dict[str, Scalar]
    ) -> tuple[float, SampleCount, dict[str, Scalar]]:
        set_parameters(self.model, parameters)
        loss = evaluate_benign(self.model, self.cal_data)
        return loss, len(self.cal_data), {ClientMetricKey.VAL_LOSS: loss}


def build_model(cfg: DatpConfig) -> Autoencoder:
    return Autoencoder(
        input_dim=cfg.model.input_dim,
        hidden_dims=cfg.model.encoder_dims,
        activation=cfg.model.activation,
        use_bn=cfg.model.use_bn,
    )


def _seed_worker(base_seed: RandomSeed, partition_id: SignedCount) -> None:
    set_seeds(RandomSeed(base_seed ^ partition_id))


def _client_ids(
    client_data: dict[ClientId, ClientData], prepared_dir: Path | None
) -> list[ClientId]:
    if prepared_dir is not None:
        return sorted(ClientId(d.name) for d in discover_client_dirs(prepared_dir))
    if not client_data:
        raise ValueError("No non-empty client_data or valid prepared_dir provided")
    return sorted(client_data)


def validate_prepared_splits(
    prepared_dir: Path, client_ids: Sequence[ClientId]
) -> None:
    required = tuple(filename_for_split(s) for s in Split) + (ArtifactFile.SCALER,)
    for cid in client_ids:
        client_dir = prepared_dir / cid
        if not client_dir.is_dir():
            raise FileNotFoundError(f"Missing client directory: {client_dir}")
        missing = [name for name in required if not (client_dir / name).exists()]
        if missing:
            raise FileNotFoundError(
                f"Missing prepared artifacts for {cid}: {', '.join(missing)}"
            )


@dataclass(frozen=True, slots=True)
class ClientFactoryConfig:
    client_ids: list[ClientId]
    cfg: DatpConfig
    device: torch.device
    seed: RandomSeed
    prepared_dir: Path | None = None


def _instantiate_client(
    factory_cfg: ClientFactoryConfig,
    client_id: ClientId,
    train_data: torch.Tensor,
    cal_data: torch.Tensor,
) -> Client:
    model = build_model(factory_cfg.cfg).to(factory_cfg.device)
    if factory_cfg.cfg.machine.require_cuda:
        validate_model_on_cuda(model)
    return DatpClient(
        cid=client_id,
        model=model,
        train_data=train_data,
        cal_data=cal_data,
        cfg=factory_cfg.cfg,
    ).to_client()


def make_client_fn(
    client_data: dict[ClientId, ClientData], factory_cfg: ClientFactoryConfig
) -> Callable[[Context], Client]:
    if factory_cfg.prepared_dir is not None:
        client_dir_map = {
            ClientId(d.name): d for d in discover_client_dirs(factory_cfg.prepared_dir)
        }
        missing = [cid for cid in factory_cfg.client_ids if cid not in client_dir_map]
        if missing:
            raise FileNotFoundError(f"Prepared directories missing for {missing}")

        def _prepared_client_fn(context: Context) -> Client:
            idx = int(context.node_config["partition-id"])
            _seed_worker(factory_cfg.seed, idx)
            cid = factory_cfg.client_ids[idx]
            train_t, cal_t = load_single_client_training_data(
                client_dir_map[cid], factory_cfg.device
            )
            return _instantiate_client(factory_cfg, cid, train_t, cal_t)

        return _prepared_client_fn

    def _inline_client_fn(context: Context) -> Client:
        idx = int(context.node_config["partition-id"])
        _seed_worker(factory_cfg.seed, idx)
        cid = factory_cfg.client_ids[idx]
        splits = client_data[cid]
        return _instantiate_client(
            factory_cfg,
            cid,
            splits.train.to(factory_cfg.device, non_blocking=True),
            splits.val.to(factory_cfg.device, non_blocking=True),
        )

    return _inline_client_fn


_RAY_MEMORY_ENV_KEY = "RAY_memory_usage_threshold"
_BYTES_PER_MIB = 1024**2


class ClientResources(TypedDict):
    num_cpus: ScoreValue
    num_gpus: GpuShare


def ensure_ray_memory_threshold(threshold: Threshold) -> None:
    current = os.environ.get(_RAY_MEMORY_ENV_KEY)
    if current is None:
        os.environ[_RAY_MEMORY_ENV_KEY] = str(threshold)
        return
    try:
        val = float(current)
    except ValueError as exc:
        raise RuntimeError(f"{_RAY_MEMORY_ENV_KEY} invalid float: {current}") from exc
    if val > threshold:
        raise RuntimeError(f"{_RAY_MEMORY_ENV_KEY} too high: {val} > {threshold}")


def _available_ram_mib() -> ByteCount:
    return psutil.virtual_memory().available // _BYTES_PER_MIB


def check_object_store_capacity(object_store_mb: ByteCount) -> None:
    available_ram_mb = _available_ram_mib()
    if object_store_mb > available_ram_mb:
        raise RuntimeError(
            f"Configured Ray object-store ({object_store_mb} MiB) exceeds available RAM ({available_ram_mb} MiB)"
        )


def derive_client_resources(machine: MachineConfig) -> ClientResources:
    if machine.max_concurrent_override is not None:
        max_concurrent = machine.max_concurrent_override
    else:
        available_ram_gb = _available_ram_mib() / 1024
        max_concurrent = max(
            1,
            math.floor(
                (available_ram_gb - machine.reserve_ram_gb) / machine.per_client_ram_gb
            ),
        )

    cpu_count = os.cpu_count()
    if cpu_count is None:
        raise RuntimeError("Cannot determine CPU count")

    num_cpus_per_actor = max(1, math.ceil(cpu_count / max_concurrent))
    num_gpus = machine.ray_num_gpus_per_client if machine.require_cuda else 0.0
    return {"num_cpus": float(num_cpus_per_actor), "num_gpus": num_gpus}


class DatpFedAvg(FedAvg):
    def __init__(
        self,
        cfg: DatpConfig,
        initial_parameters: Parameters,
        num_clients: SampleCount,
    ) -> None:
        super().__init__(
            fraction_fit=1.0,
            fraction_evaluate=1.0,
            min_fit_clients=num_clients,
            min_evaluate_clients=num_clients,
            min_available_clients=num_clients,
            initial_parameters=initial_parameters,
            fit_metrics_aggregation_fn=lambda _: {},
        )
        conv = cfg.federation.convergence
        self._monitor = ConvergenceMonitor(
            conv.rounds_initial, conv.rounds_max, conv.relative_threshold, conv.window
        )
        self._stopped = False
        self._latest_parameters: NDArrays | None = None

    @property
    def convergence_monitor(self) -> ConvergenceMonitor:
        return self._monitor

    @property
    def stopped(self) -> bool:
        return self._stopped

    @property
    def latest_parameters(self) -> NDArrays | None:
        return self._latest_parameters

    def _raise_if_failures(
        self,
        stage: FederatedRoundStage,
        server_round: RoundIndex,
        failures: Sequence[tuple[ClientProxy, FitRes | EvaluateRes] | BaseException],
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
    ) -> tuple[Parameters | None, dict[str, Scalar]]:
        self._raise_if_failures(FederatedRoundStage.FIT, server_round, failures)
        aggregated = super().aggregate_fit(server_round, results, failures)
        if not aggregated or not aggregated[0]:
            return None, aggregated[1] if aggregated else {}

        params, fit_metrics = aggregated
        assert params is not None
        self._latest_parameters = parameters_to_ndarrays(params)
        return params, fit_metrics

    def configure_fit(
        self,
        server_round: RoundIndex,
        parameters: Parameters,
        client_manager: ClientManager,
    ) -> list[tuple[ClientProxy, FitIns]]:
        if self._stopped:
            return []
        return super().configure_fit(server_round, parameters, client_manager)

    def configure_evaluate(
        self,
        server_round: RoundIndex,
        parameters: Parameters,
        client_manager: ClientManager,
    ) -> list[tuple[ClientProxy, EvaluateIns]]:
        if self._stopped:
            return []
        return super().configure_evaluate(server_round, parameters, client_manager)

    def aggregate_evaluate(
        self,
        server_round: RoundIndex,
        results: list[tuple[ClientProxy, EvaluateRes]],
        failures: list[tuple[ClientProxy, EvaluateRes] | BaseException],
    ) -> tuple[ScoreValue | None, dict[str, Scalar]]:
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

        if self._monitor.should_stop(server_round):
            self._stopped = True

        return weighted_loss, {"weighted_val_loss": weighted_loss}


@dataclass(frozen=True, slots=True)
class TrainingResult:
    stage: ExperimentStage
    seed: RandomSeed
    converged_round: RoundIndex | None
    total_rounds: RoundCount
    score_dir: Path
    loss_history: list[ScoreValue]


def _run_flower_simulation(
    cfg: DatpConfig,
    client_fn: Callable[[Context], Client],
    strategy: DatpFedAvg,
    num_clients: SampleCount,
) -> None:
    configure_runtime_env()
    ensure_ray_memory_threshold(cfg.runtime.ray_memory_threshold)
    client_resources = derive_client_resources(cfg.machine)
    check_object_store_capacity(cfg.machine.ray_object_store_mb)
    run_simulation(
        num_supernodes=num_clients,
        client_app=ClientApp(client_fn=client_fn),
        server_app=ServerApp(
            server_fn=lambda _: ServerAppComponents(
                strategy=strategy,
                config=ServerConfig(
                    num_rounds=cfg.federation.convergence.rounds_max,
                    round_timeout=cfg.federation.convergence.round_timeout_s,
                ),
            )
        ),
        backend_config=cast(
            BackendConfig,
            {
                "init_args": {
                    "num_cpus": max(
                        1, (os.cpu_count() or 1) // cfg.runtime.sweep_workers
                    ),
                    "object_store_memory": cfg.machine.ray_object_store_mb
                    * _BYTES_PER_MIB,
                },
                "client_resources": client_resources,
            },
        ),
    )


def _scoring_data(
    client_data: dict[ClientId, ClientData],
    prepared_dir: Path | None,
    expected_dim: FeatureCount,
) -> dict[ClientId, ClientData]:
    data = (
        load_client_data(
            prepared_dir, device=torch.device(DeviceType.CPU), splits=ALL_SPLITS
        )
        if prepared_dir is not None
        else client_data
    )
    for client_id, splits in data.items():
        validate_client_data(splits, client_id, expected_dim=expected_dim)
    return data


def _score_dir(
    stage: ExperimentStage,
    seed: RandomSeed,
    base_dir: Path | None,
    output_layout: ArtifactLayout | None,
) -> Path:
    if output_layout is not None:
        layout = output_layout
    elif base_dir is not None:
        layout = ArtifactLayout(base_dir=base_dir, stage=stage)
    else:
        raise ValueError("base_dir or output_layout required")
    return layout.score_cell(TrainingCellId(stage=stage, seed=seed)).score_dir


def run_fl_training(
    cfg: DatpConfig,
    client_data: dict[ClientId, ClientData],
    seed: RandomSeed,
    *,
    base_dir: Path | None = None,
    prepared_dir: Path | None = None,
    output_layout: ArtifactLayout | None = None,
) -> TrainingResult:
    if cfg.stage is None:
        raise ValueError("stage must be set in config")
    stage = cfg.stage
    score_base = _score_dir(stage, seed, base_dir, output_layout)

    client_ids = _client_ids(client_data, prepared_dir)
    if prepared_dir is not None:
        validate_prepared_splits(prepared_dir, client_ids)

    device = resolve_device(cfg.machine.require_cuda)
    set_seeds(seed)
    model = build_model(cfg).to(device)
    strategy = DatpFedAvg(
        cfg,
        ndarrays_to_parameters(get_parameters(model)),
        len(client_ids),
    )
    monitor: ConvergenceMonitor = strategy.convergence_monitor

    client_fn = make_client_fn(
        client_data,
        ClientFactoryConfig(
            client_ids=client_ids,
            cfg=cfg,
            device=device,
            seed=seed,
            prepared_dir=prepared_dir,
        ),
    )
    _run_flower_simulation(cfg, client_fn, strategy, len(client_ids))
    total_rounds = monitor.num_recorded
    converged_round = monitor.converged_round
    logger.info(
        "federated training completed",
        total_rounds=total_rounds,
        converged_round=converged_round,
        stopped=strategy.stopped,
    )
    if strategy.latest_parameters is None:
        raise RuntimeError("Final aggregated parameters unavailable")
    set_parameters(model, strategy.latest_parameters)

    score_clients(
        model=model,
        client_data=_scoring_data(client_data, prepared_dir, cfg.model.input_dim),
        score_base=score_base,
        stage=stage,
        seed=seed,
        dataset=dataset_for_stage(stage),
        scoring_batch_size=cfg.machine.scoring_batch_size,
    )
    save_convergence_artifacts(score_base, monitor, cfg.federation.convergence)

    return TrainingResult(
        stage=stage,
        seed=seed,
        converged_round=converged_round,
        total_rounds=total_rounds,
        score_dir=score_base,
        loss_history=monitor.loss_history,
    )
