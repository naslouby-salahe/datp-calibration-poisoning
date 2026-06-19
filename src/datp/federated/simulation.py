# SPDX-License-Identifier: Proprietary
"""Shared FL simulation orchestration — train once per (regime, seed, α); score artifacts produced afterward."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import torch
import torch.nn as nn
from flwr.client import Client, ClientApp
from flwr.common import Context, NDArrays, Parameters, ndarrays_to_parameters
from flwr.common.telemetry import EventType
from flwr.server import ServerApp, ServerConfig
from flwr.server.serverapp_components import ServerAppComponents
from flwr.simulation.run_simulation import BackendConfig, _run_simulation

from datp import configure_runtime_env
from datp.artifacts.lifecycle import RunLifecycle
from datp.artifacts.names import ArtifactDir, ArtifactFile
from datp.config.models import CheckpointProtocolConfig, DatpConfig
from datp.core.device import resolve_device
from datp.core.enums import DeviceType, Regime
from datp.core.errors import fmt
from datp.core.logging import get_logger
from datp.core.seeds import set_seeds
from datp.core.tracking import (
    TrackingMetric,
    TrackingMetricKey,
    TrackingMetrics,
    TrackingParam,
    TrackingParamKey,
    TrackingParams,
    log_artifact,
    log_metrics,
    log_params,
)
from datp.data.regimes.catalog import dataset_for_regime
from datp.federated.catalog import TrainingClientCatalog
from datp.federated.checkpoints import (
    ConvergenceSnapshot,
    load_params_snapshot,
    save_checkpoint,
    save_convergence_artifacts,
)
from datp.federated.clients import DatpClient
from datp.federated.convergence import ConvergenceMonitor
from datp.federated.data_loading import (
    ALL_SPLITS,
    load_client_data,
)
from datp.federated.factories import build_model, make_client_fn
from datp.federated.parameters import get_parameters, set_parameters
from datp.federated.runtime import (
    RayClientResourceRequest,
    check_object_store_capacity,
    derive_client_resources,
    ensure_ray_memory_threshold,
)
from datp.federated.strategies import DatpFedAvg
from datp.federated.types import ClientData
from datp.modeling.autoencoder import Autoencoder
from datp.scoring.generation import score_clients

logger = get_logger(__name__)

_MODULE = "training.simulation"


def _artifact_root_from_path(path: Path, anchor: ArtifactDir) -> Path:
    parts = path.parts
    anchor_value = anchor.value
    if anchor_value not in parts:
        raise ValueError(
            fmt(_MODULE, "Artifact path lacks expected anchor", anchor_value, str(path))
        )
    anchor_index = parts.index(anchor_value)
    if anchor_index == 0:
        return Path(path.anchor)
    return Path(*parts[:anchor_index])


def _checkpoint_protocol_enabled(
    cfg: DatpConfig, ckpt_dir: Path, score_base: Path
) -> bool:
    checkpoint_cfg = cfg.checkpoint_protocol
    return (
        isinstance(checkpoint_cfg, CheckpointProtocolConfig)
        and checkpoint_cfg.enabled
        and ArtifactDir.CHECKPOINTS.value in ckpt_dir.parts
        and ArtifactDir.SCORES.value in score_base.parts
    )


@dataclass(frozen=True, slots=True)
class SimClientConfig:
    """Per-simulation client and scoring options."""

    client_cls: type[DatpClient] = DatpClient
    client_extra_kwargs: dict[str, object] | None = None
    encoder_only: bool = False
    score_after: bool = True


@dataclass(frozen=True, slots=True)
class TrainingResult:
    regime: Regime
    seed: int
    alpha: float | None
    converged_round: int | None
    total_rounds: int
    checkpoint_dir: Path
    score_dir: Path
    loss_history: list[float]


@dataclass(frozen=True, slots=True)
class _CheckpointSaveContext:
    """Bundled parameters for checkpoint artifact saving helpers."""

    model: nn.Module
    param_module: nn.Module
    strategy: DatpFedAvg
    monitor: ConvergenceMonitor
    cfg: DatpConfig
    lifecycle: RunLifecycle
    total_rounds: int


@dataclass(frozen=True, slots=True)
class _CheckpointProtocolContext:
    """Bundled parameters for checkpoint-protocol scoring."""

    model: Autoencoder
    param_module: nn.Module
    strategy: DatpFedAvg
    checkpoint_cfg: CheckpointProtocolConfig
    ckpt_dir_by_round: dict[int, Path]
    scoring_data: dict[str, ClientData]
    score_base: Path
    regime: Regime
    seed: int
    alpha: float | None
    cfg: DatpConfig


def validate_regime(cfg: DatpConfig) -> Regime:
    regime = cfg.regime
    if regime is None:
        raise ValueError(
            fmt(
                _MODULE, "regime must be set in config", "non-null regime", repr(regime)
            )
        )
    return regime


def _init_model_and_params(
    cfg: DatpConfig,
    model_cls: type[Autoencoder],
    device: torch.device,
    encoder_only: bool,
) -> tuple[Autoencoder, nn.Module, Parameters]:
    """Build model on device; return (model, param_module, initial_parameters).

    param_module is model.encoder when encoder_only=True, else the full model.
    """
    model = build_model(cfg, model_cls)
    model.to(device)
    param_module: nn.Module = model.encoder if encoder_only else model
    return model, param_module, ndarrays_to_parameters(get_parameters(param_module))


def _execute_flower_simulation(
    cfg: DatpConfig,
    client_fn: Callable[[Context], Client],
    num_clients: int,
    strategy: DatpFedAvg | None,
    label: str,
    effective_rounds_max: int,
) -> None:
    """Configure Ray, run Flower simulation; Ray lifecycle managed by the backend."""
    configure_runtime_env()
    ensure_ray_memory_threshold(cfg.runtime.ray_memory_threshold)
    client_resources = derive_client_resources(
        RayClientResourceRequest(
            per_client_ram_gb=cfg.machine.per_client_ram_gb,
            reserve_ram_gb=cfg.machine.reserve_ram_gb,
            max_concurrent_override=cfg.machine.max_concurrent_override,
            require_cuda=cfg.machine.require_cuda,
            num_gpus_per_client=cfg.machine.ray_num_gpus_per_client,
        )
    )
    object_store_preflight = check_object_store_capacity(
        cfg.machine.ray_object_store_mb
    )
    logger.info(
        "ray object-store preflight",
        object_store_mb=object_store_preflight["object_store_mb"],
        available_ram_mb=object_store_preflight["available_ram_mb"],
    )
    object_store_bytes = cfg.machine.ray_object_store_mb * 1024 * 1024
    num_rounds = effective_rounds_max
    round_timeout = cfg.federation.convergence.round_timeout_s

    def server_fn(_: Context) -> ServerAppComponents:
        return ServerAppComponents(
            strategy=strategy,
            config=ServerConfig(num_rounds=num_rounds, round_timeout=round_timeout),
        )

    _run_simulation(
        num_supernodes=num_clients,
        client_app=ClientApp(client_fn=client_fn),
        server_app=ServerApp(server_fn=server_fn),
        backend_config=cast(
            BackendConfig,
            {
                "init_args": {"object_store_memory": object_store_bytes},
                "client_resources": client_resources,
            },
        ),
        exit_event=EventType.PYTHON_API_RUN_SIMULATION_LEAVE,
    )
    logger.info("ray shutdown after FL simulation", label=label)


def _convergence_snapshot(monitor: ConvergenceMonitor) -> ConvergenceSnapshot:
    return ConvergenceSnapshot(
        loss_history=monitor.loss_history,
        converged_round=monitor.converged_round,
        criterion_value=monitor.latest_relative_change,
    )


def _save_training_artifacts(ctx: _CheckpointSaveContext, ckpt_dir: Path) -> None:
    """Restore aggregated parameters, save checkpoint and convergence artifacts."""
    final_params = ctx.strategy.latest_parameters
    if final_params is None:
        raise RuntimeError(
            fmt(
                _MODULE,
                "Final aggregated parameters unavailable after FL simulation — "
                "cannot save checkpoint from untrained/initial model",
                "non-null strategy.latest_parameters",
                "None",
            )
        )
    set_parameters(ctx.param_module, final_params)
    save_checkpoint(ctx.model, ckpt_dir)
    save_convergence_artifacts(
        ckpt_dir, _convergence_snapshot(ctx.monitor), ctx.cfg.federation.convergence
    )
    ctx.lifecycle.last_completed_round = ctx.total_rounds


def _resolve_params_for_round(
    checkpoint_round: int,
    strategy: DatpFedAvg,
    ckpt_dir_by_round: dict[int, Path],
) -> NDArrays:
    """Return params snapshot for a checkpoint round: in-memory preferred, disk fallback."""
    in_memory = strategy.parameter_snapshots
    if checkpoint_round in in_memory:
        return in_memory[checkpoint_round]
    disk_params = load_params_snapshot(ckpt_dir_by_round[checkpoint_round])
    if disk_params is None:
        raise RuntimeError(
            fmt(
                _MODULE,
                "Missing checkpoint milestone parameter snapshots (neither in memory nor on disk)",
                str(sorted(ckpt_dir_by_round)),
                str(checkpoint_round),
            )
        )
    logger.info(
        "crash recovery: loaded params snapshot from disk",
        round=checkpoint_round,
        path=str(ckpt_dir_by_round[checkpoint_round]),
    )
    return disk_params


def _save_checkpoint_protocol_artifacts(
    ctx: _CheckpointSaveContext,
    ckpt_dir_by_round: dict[int, Path],
) -> None:
    params_by_round: dict[int, NDArrays] = {
        checkpoint_round: _resolve_params_for_round(
            checkpoint_round, ctx.strategy, ckpt_dir_by_round
        )
        for checkpoint_round in ckpt_dir_by_round
    }
    snapshot = _convergence_snapshot(ctx.monitor)
    for checkpoint_round, ckpt_dir in sorted(ckpt_dir_by_round.items()):
        set_parameters(ctx.param_module, params_by_round[checkpoint_round])
        save_checkpoint(ctx.model, ckpt_dir)
        save_convergence_artifacts(ckpt_dir, snapshot, ctx.cfg.federation.convergence)
    ctx.lifecycle.last_completed_round = ctx.total_rounds


def load_scoring_data(
    client_data: dict[str, ClientData] | None,
    prepared_dir: Path | None,
) -> dict[str, ClientData]:
    """Resolve scoring data: reload from disk when prepared_dir was used; otherwise return existing."""
    if prepared_dir is not None:
        return load_client_data(
            prepared_dir, device=torch.device(DeviceType.CPU), splits=ALL_SPLITS
        )
    if client_data:
        return client_data
    raise ValueError(
        fmt(_MODULE, "No scoring data source", "client_data or prepared_dir", "neither")
    )


def _checkpoint_dirs_by_round(
    checkpoint_cfg: CheckpointProtocolConfig | None,
    protocol_enabled: bool,
    ckpt_dir: Path,
    regime: Regime,
    seed: int,
    alpha: float | None,
) -> dict[int, Path]:
    if checkpoint_cfg is None or not protocol_enabled:
        return {}

    from datp.artifacts.layout import ArtifactLayout
    from datp.core.identity import TrainingCellId

    layout = ArtifactLayout(
        base_dir=_artifact_root_from_path(ckpt_dir, ArtifactDir.CHECKPOINTS),
        regime=regime,
    )
    cell = TrainingCellId(regime=regime, seed=seed, alpha=alpha)
    return {
        round_count: layout.checkpoint_dir_for_round(cell, round_count)
        for round_count in checkpoint_cfg.milestones
    }


def _params_for_checkpoint_round(
    checkpoint_round: int,
    strategy: DatpFedAvg,
    ckpt_dir_by_round: dict[int, Path],
) -> NDArrays:
    if checkpoint_round in strategy.parameter_snapshots:
        return strategy.parameter_snapshots[checkpoint_round]
    round_params = load_params_snapshot(ckpt_dir_by_round[checkpoint_round])
    if round_params is None:
        raise RuntimeError(
            fmt(
                _MODULE,
                "Missing scoring snapshot (neither in memory nor on disk)",
                str(checkpoint_round),
                "None",
            )
        )
    return round_params


def _score_checkpoint_protocol_rounds(ctx: _CheckpointProtocolContext) -> None:
    from datp.artifacts.layout import ArtifactLayout
    from datp.core.identity import TrainingCellId

    score_layout = ArtifactLayout(
        base_dir=_artifact_root_from_path(ctx.score_base, ArtifactDir.SCORES),
        regime=ctx.regime,
    )
    score_cell = TrainingCellId(regime=ctx.regime, seed=ctx.seed, alpha=ctx.alpha)
    for checkpoint_round in ctx.checkpoint_cfg.milestones:
        round_params = _params_for_checkpoint_round(
            checkpoint_round, ctx.strategy, ctx.ckpt_dir_by_round
        )
        set_parameters(ctx.param_module, round_params)
        round_score_base = score_layout.score_cell_for_round(
            score_cell, checkpoint_round
        ).score_dir
        round_ckpt = (
            ctx.ckpt_dir_by_round[checkpoint_round] / ArtifactFile.MODEL_CHECKPOINT
        )
        score_clients(
            model=ctx.model,
            client_data=ctx.scoring_data,
            score_base=round_score_base,
            regime=ctx.regime,
            seed=ctx.seed,
            alpha=ctx.alpha,
            dataset=dataset_for_regime(ctx.regime),
            checkpoint_path=round_ckpt,
            checkpoint_round=checkpoint_round,
            scoring_batch_size=ctx.cfg.machine.scoring_batch_size,
        )


def run_fl_simulation(
    cfg: DatpConfig,
    client_data: dict[str, ClientData] | None,
    seed: int,
    alpha: float | None,
    *,
    model_cls: type[Autoencoder],
    ckpt_dir: Path,
    score_base: Path,
    label: str,
    prepared_dir: Path | None = None,
    client_config: SimClientConfig = SimClientConfig(),
) -> TrainingResult:
    regime = validate_regime(cfg)
    checkpoint_cfg = cfg.checkpoint_protocol
    protocol_enabled = _checkpoint_protocol_enabled(cfg, ckpt_dir, score_base)
    effective_rounds_max = (
        checkpoint_cfg.max_rounds
        if (checkpoint_cfg is not None and protocol_enabled)
        else cfg.federation.convergence.rounds_max
    )

    catalog = TrainingClientCatalog(
        client_data=client_data,
        prepared_dir=prepared_dir,
    )

    if prepared_dir is not None:
        catalog.validate_prepared_splits()

    device = resolve_device(cfg.machine.require_cuda)
    set_seeds(seed)

    model, param_module, initial_parameters = _init_model_and_params(
        cfg, model_cls, device, client_config.encoder_only
    )

    client_ids = catalog.client_ids
    num_clients = catalog.num_clients
    logger.info(
        "starting FL training",
        label=label,
        regime=regime,
        seed=seed,
        alpha=alpha,
        n_clients=num_clients,
    )

    ckpt_dir_by_round = _checkpoint_dirs_by_round(
        checkpoint_cfg, protocol_enabled, ckpt_dir, regime, seed, alpha
    )

    strategy = DatpFedAvg.from_config(
        cfg,
        initial_parameters=initial_parameters,
        num_clients=num_clients,
        effective_rounds_max=effective_rounds_max,
        checkpoint_disk_dirs=ckpt_dir_by_round or None,
    )
    monitor = strategy.convergence_monitor
    converged_round: int | None = None
    total_rounds = 0

    with RunLifecycle(ckpt_dir, seed=seed) as lifecycle:
        client_fn = make_client_fn(
            (client_data or {}) if prepared_dir is None else {},
            client_ids,
            cfg,
            device,
            prepared_dir=prepared_dir,
            model_cls=model_cls,
            client_cls=client_config.client_cls,
            extra_kwargs=client_config.client_extra_kwargs,
            seed=seed,
        )

        _execute_flower_simulation(
            cfg, client_fn, num_clients, strategy, label, effective_rounds_max
        )

        total_rounds = monitor.num_recorded
        converged_round = monitor.converged_round
        logger.info(
            "FL training complete",
            label=label,
            total_rounds=total_rounds,
            converged_round=converged_round,
        )

        save_ctx = _CheckpointSaveContext(
            model=model,
            param_module=param_module,
            strategy=strategy,
            monitor=monitor,
            cfg=cfg,
            lifecycle=lifecycle,
            total_rounds=total_rounds,
        )
        if protocol_enabled:
            _save_checkpoint_protocol_artifacts(save_ctx, ckpt_dir_by_round)
        else:
            _save_training_artifacts(save_ctx, ckpt_dir)

    if client_config.score_after:
        scoring_data = load_scoring_data(client_data, prepared_dir)
        if protocol_enabled:
            assert checkpoint_cfg is not None
            _score_checkpoint_protocol_rounds(
                _CheckpointProtocolContext(
                    model=model,
                    param_module=param_module,
                    strategy=strategy,
                    checkpoint_cfg=checkpoint_cfg,
                    ckpt_dir_by_round=ckpt_dir_by_round,
                    scoring_data=scoring_data,
                    score_base=score_base,
                    regime=regime,
                    seed=seed,
                    alpha=alpha,
                    cfg=cfg,
                )
            )
        else:
            score_clients(
                model=model,
                client_data=scoring_data,
                score_base=score_base,
                regime=regime,
                seed=seed,
                alpha=alpha,
                dataset=dataset_for_regime(regime),
                checkpoint_path=ckpt_dir / ArtifactFile.MODEL_CHECKPOINT,
                checkpoint_round=None,
                scoring_batch_size=cfg.machine.scoring_batch_size,
            )

    log_params(
        TrackingParams(
            (
                TrackingParam(TrackingParamKey.REGIME, regime),
                TrackingParam(TrackingParamKey.SEED, seed),
                TrackingParam(TrackingParamKey.ROUNDS_MAX, effective_rounds_max),
                TrackingParam(TrackingParamKey.LABEL, label),
            )
        )
    )
    log_metrics(
        TrackingMetrics(
            (
                TrackingMetric(
                    TrackingMetricKey.CONVERGED_ROUND,
                    float(converged_round)
                    if converged_round is not None
                    else float(total_rounds),
                ),
                TrackingMetric(TrackingMetricKey.TOTAL_ROUNDS, total_rounds),
            )
        ),
        step=None,
        prefix=None,
    )
    ckpt_file = ckpt_dir / ArtifactFile.MODEL_CHECKPOINT
    if ckpt_file.exists():
        log_artifact(ckpt_file, artifact_path=None)

    return TrainingResult(
        regime=regime,
        seed=seed,
        alpha=alpha,
        converged_round=converged_round,
        total_rounds=total_rounds,
        checkpoint_dir=ckpt_dir,
        score_dir=score_base,
        loss_history=monitor.loss_history,
    )
