"""Top-level FL simulation orchestration with checkpoint and scoring hooks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import torch
from flwr.client import ClientApp
from flwr.common import ndarrays_to_parameters
from flwr.common.telemetry import EventType
from flwr.server import ServerApp, ServerConfig
from flwr.server.serverapp_components import ServerAppComponents
from flwr.simulation.run_simulation import BackendConfig, _run_simulation

from datp import configure_runtime_env
from datp.artifacts.lifecycle import RunLifecycle
from datp.artifacts.names import ArtifactDir, ArtifactFile
from datp.config.models import CheckpointProtocolConfig, DatpConfig
from datp.config.models import ExperimentStage
from datp.core.device import resolve_device
from datp.core.enums import DeviceType
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
from datp.data.catalog import dataset_for_stage
from datp.federated.catalog import TrainingClientCatalog
from datp.federated.checkpoints import (
    ConvergenceSnapshot,
    load_params_snapshot,
    save_checkpoint,
    save_convergence_artifacts,
)
from datp.federated.clients import DatpClient
from datp.federated.data_loading import ALL_SPLITS, load_client_data
from datp.federated.factories import ClientFactoryConfig, build_model, make_client_fn
from datp.federated.parameters import get_parameters, set_parameters
from datp.federated.runtime import (
    RayClientResourceRequest,
    check_object_store_capacity,
    derive_client_resources,
    ensure_ray_memory_threshold,
)
from datp.federated.strategies import DatpFedAvg, FedAvgBuildRequest
from datp.federated.types import ClientData
from datp.modeling.autoencoder import Autoencoder
from datp.scoring.generation import score_clients


def _artifact_root_from_path(path: Path, anchor: ArtifactDir) -> Path:
    """Find the artifact base directory by locating an anchor directory in the path."""
    if anchor.value not in path.parts:
        raise ValueError(f"Path lacks anchor {anchor.value}: {path}")
    idx = path.parts.index(anchor.value)
    return Path(path.anchor) if idx == 0 else Path(*path.parts[:idx])


def _checkpoint_protocol_enabled(
    cfg: DatpConfig, ckpt_dir: Path, score_base: Path
) -> bool:
    """Check whether the checkpoint protocol is active for this run."""
    ckpt_cfg = cfg.checkpoint_protocol
    return (
        isinstance(ckpt_cfg, CheckpointProtocolConfig)
        and ckpt_cfg.enabled
        and ArtifactDir.CHECKPOINTS.value in ckpt_dir.parts
        and ArtifactDir.SCORES.value in score_base.parts
    )


@dataclass(frozen=True, slots=True)
class SimClientConfig:
    """Configuration for the client class, extra kwargs, and scoring behavior in an FL simulation."""

    client_cls: type[DatpClient] = DatpClient
    client_extra_kwargs: dict[str, object] | None = None
    encoder_only: bool = False
    score_after: bool = True


@dataclass(frozen=True, slots=True)
class TrainingResult:
    """Record of a completed FL training run: stage, seed, convergence, and output directories."""

    stage: ExperimentStage
    seed: int
    converged_round: int | None
    total_rounds: int
    checkpoint_dir: Path
    score_dir: Path
    loss_history: list[float]


def validate_stage(cfg: DatpConfig) -> ExperimentStage:
    """Extract and validate the experiment stage from config."""
    if cfg.stage is None:
        raise ValueError("stage must be set in config")
    return cfg.stage


def load_scoring_data(
    client_data: dict[str, ClientData] | None, prepared_dir: Path | None
) -> dict[str, ClientData]:
    """Resolve scoring data from prepared directory or in-memory client data."""
    if prepared_dir is not None:
        return load_client_data(
            prepared_dir, device=torch.device(DeviceType.CPU), splits=ALL_SPLITS
        )
    if client_data:
        return client_data
    raise ValueError("No scoring data source provided")


@dataclass(frozen=True, slots=True)
class FlSimulationRequest:
    """Request bundle carrying all inputs needed to run a single FL simulation."""

    cfg: DatpConfig
    client_data: dict[str, ClientData] | None
    seed: int
    model_cls: type[Autoencoder]
    ckpt_dir: Path
    score_base: Path
    label: str
    prepared_dir: Path | None = None
    client_config: SimClientConfig = SimClientConfig()


@dataclass(frozen=True, slots=True)
class SimulationArtifacts:
    """Bundle of mutable simulation products created during training rounds."""

    ckpt_dir_by_round: dict[int, Path]
    strategy: DatpFedAvg
    param_module: torch.nn.Module
    model: Autoencoder


def _save_simulation_artifacts(
    artifacts: SimulationArtifacts,
    snapshot: ConvergenceSnapshot,
    req: FlSimulationRequest,
    protocol_enabled: bool,
) -> None:
    """Persist model checkpoints and convergence artifacts after training."""
    if artifacts.strategy.latest_parameters is None:
        raise RuntimeError("Final aggregated parameters unavailable")
    if protocol_enabled:
        for r, c_dir in sorted(artifacts.ckpt_dir_by_round.items()):
            params = artifacts.strategy.parameter_snapshots.get(r) or load_params_snapshot(c_dir)
            if params is None:
                raise RuntimeError(f"Missing params snapshot for round {r}")
            set_parameters(artifacts.param_module, params)
            save_checkpoint(artifacts.model, c_dir)
            save_convergence_artifacts(c_dir, snapshot, req.cfg.federation.convergence)
    else:
        set_parameters(artifacts.param_module, artifacts.strategy.latest_parameters)
        save_checkpoint(artifacts.model, req.ckpt_dir)
        save_convergence_artifacts(req.ckpt_dir, snapshot, req.cfg.federation.convergence)


def _score_after_simulation(
    req: FlSimulationRequest,
    artifacts: SimulationArtifacts,
) -> None:
    """Run client scoring after FL simulation, respecting checkpoint protocol milestones."""
    if not req.client_config.score_after:
        return
    stage = validate_stage(req.cfg)
    protocol_enabled = _checkpoint_protocol_enabled(req.cfg, req.ckpt_dir, req.score_base)
    ckpt_cfg = req.cfg.checkpoint_protocol
    scoring_data = load_scoring_data(req.client_data, req.prepared_dir)
    if protocol_enabled and isinstance(ckpt_cfg, CheckpointProtocolConfig):
        from datp.artifacts.layout import ArtifactLayout
        from datp.core.identity import TrainingCellId

        score_layout = ArtifactLayout(
            base_dir=_artifact_root_from_path(req.score_base, ArtifactDir.SCORES),
            stage=stage,
        )
        score_cell = TrainingCellId(stage=stage, seed=req.seed)
        for r in ckpt_cfg.milestones:
            params = artifacts.strategy.parameter_snapshots.get(r) or load_params_snapshot(
                artifacts.ckpt_dir_by_round[r]
            )
            if params is None:
                raise RuntimeError(f"Missing scoring snapshot for round {r}")
            set_parameters(artifacts.param_module, params)
            score_clients(
                model=artifacts.model,
                client_data=scoring_data,
                score_base=score_layout.score_cell_for_round(score_cell, r).score_dir,
                stage=stage,
                seed=req.seed,
                dataset=dataset_for_stage(stage),
                checkpoint_path=artifacts.ckpt_dir_by_round[r] / ArtifactFile.MODEL_CHECKPOINT,
                checkpoint_round=r,
                scoring_batch_size=req.cfg.machine.scoring_batch_size,
            )
    else:
        score_clients(
            model=artifacts.model,
            client_data=scoring_data,
            score_base=req.score_base,
            stage=stage,
            seed=req.seed,
            dataset=dataset_for_stage(stage),
            checkpoint_path=req.ckpt_dir / ArtifactFile.MODEL_CHECKPOINT,
            checkpoint_round=None,
            scoring_batch_size=req.cfg.machine.scoring_batch_size,
        )


def run_fl_simulation(req: FlSimulationRequest) -> TrainingResult:
    """Execute a full FL simulation: setup, training rounds, checkpointing, and scoring."""
    stage = validate_stage(req.cfg)
    protocol_enabled = _checkpoint_protocol_enabled(
        req.cfg, req.ckpt_dir, req.score_base
    )
    ckpt_cfg = req.cfg.checkpoint_protocol
    eff_rounds_max = (
        ckpt_cfg.max_rounds
        if protocol_enabled and ckpt_cfg
        else req.cfg.federation.convergence.rounds_max
    )

    catalog = TrainingClientCatalog(
        client_data=req.client_data, prepared_dir=req.prepared_dir
    )
    if req.prepared_dir is not None:
        catalog.validate_prepared_splits()

    device = resolve_device(req.cfg.machine.require_cuda)
    set_seeds(req.seed)

    model = build_model(req.cfg, req.model_cls).to(device)
    param_module = model.encoder if req.client_config.encoder_only else model
    initial_parameters = ndarrays_to_parameters(get_parameters(param_module))

    ckpt_dir_by_round: dict[int, Path] = {}
    if protocol_enabled and isinstance(ckpt_cfg, CheckpointProtocolConfig):
        from datp.artifacts.layout import ArtifactLayout
        from datp.core.identity import TrainingCellId

        layout = ArtifactLayout(
            base_dir=_artifact_root_from_path(req.ckpt_dir, ArtifactDir.CHECKPOINTS),
            stage=stage,
        )
        cell = TrainingCellId(stage=stage, seed=req.seed)
        ckpt_dir_by_round = {
            r: layout.checkpoint_dir_for_round(cell, r) for r in ckpt_cfg.milestones
        }

    strategy = DatpFedAvg.from_config(
        req.cfg,
        FedAvgBuildRequest(
            initial_parameters=initial_parameters,
            num_clients=catalog.num_clients,
            effective_rounds_max=eff_rounds_max,
            checkpoint_disk_dirs=ckpt_dir_by_round or None,
        ),
    )
    monitor = strategy.convergence_monitor

    with RunLifecycle(req.ckpt_dir, seed=req.seed) as lifecycle:
        client_fn = make_client_fn(
            req.client_data or {} if req.prepared_dir is None else {},
            ClientFactoryConfig(
                client_ids=catalog.client_ids,
                cfg=req.cfg,
                device=device,
                prepared_dir=req.prepared_dir,
                model_cls=req.model_cls,
                client_cls=req.client_config.client_cls,
                extra_kwargs=req.client_config.client_extra_kwargs,
                seed=req.seed,
            ),
        )

        configure_runtime_env()
        ensure_ray_memory_threshold(req.cfg.runtime.ray_memory_threshold)
        client_resources = derive_client_resources(
            RayClientResourceRequest(
                per_client_ram_gb=req.cfg.machine.per_client_ram_gb,
                reserve_ram_gb=req.cfg.machine.reserve_ram_gb,
                max_concurrent_override=req.cfg.machine.max_concurrent_override,
                require_cuda=req.cfg.machine.require_cuda,
                num_gpus_per_client=req.cfg.machine.ray_num_gpus_per_client,
            )
        )
        check_object_store_capacity(req.cfg.machine.ray_object_store_mb)

        _run_simulation(
            num_supernodes=catalog.num_clients,
            client_app=ClientApp(client_fn=client_fn),
            server_app=ServerApp(
                server_fn=lambda _: ServerAppComponents(
                    strategy=strategy,
                    config=ServerConfig(
                        num_rounds=eff_rounds_max,
                        round_timeout=req.cfg.federation.convergence.round_timeout_s,
                    ),
                )
            ),
            backend_config=cast(
                BackendConfig,
                {
                    "init_args": {
                        "object_store_memory": req.cfg.machine.ray_object_store_mb
                        * 1024
                        * 1024
                    },
                    "client_resources": client_resources,
                },
            ),
            exit_event=EventType.PYTHON_API_RUN_SIMULATION_LEAVE,
        )

        total_rounds = monitor.num_recorded
        converged_round = monitor.converged_round

        snapshot = ConvergenceSnapshot(
            loss_history=monitor.loss_history,
            converged_round=converged_round,
            criterion_value=monitor.latest_relative_change,
        )
        artifacts = SimulationArtifacts(
            ckpt_dir_by_round=ckpt_dir_by_round,
            strategy=strategy,
            param_module=param_module,
            model=model,
        )
        _save_simulation_artifacts(artifacts, snapshot, req, protocol_enabled)
        lifecycle.last_completed_round = total_rounds

    _score_after_simulation(req, artifacts)

    log_params(
        TrackingParams(
            (
                TrackingParam(TrackingParamKey.STAGE, stage),
                TrackingParam(TrackingParamKey.SEED, req.seed),
                TrackingParam(TrackingParamKey.ROUNDS_MAX, eff_rounds_max),
                TrackingParam(TrackingParamKey.LABEL, req.label),
            )
        )
    )
    log_metrics(
        TrackingMetrics(
            (
                TrackingMetric(
                    TrackingMetricKey.CONVERGED_ROUND,
                    float(
                        converged_round if converged_round is not None else total_rounds
                    ),
                ),
                TrackingMetric(TrackingMetricKey.TOTAL_ROUNDS, total_rounds),
            )
        ),
        step=None,
        prefix=None,
    )
    ckpt_file = req.ckpt_dir / ArtifactFile.MODEL_CHECKPOINT
    if ckpt_file.exists():
        log_artifact(ckpt_file, artifact_path=None)

    return TrainingResult(
        stage=stage,
        seed=req.seed,
        converged_round=converged_round,
        total_rounds=total_rounds,
        checkpoint_dir=req.ckpt_dir,
        score_dir=req.score_base,
        loss_history=monitor.loss_history,
    )
