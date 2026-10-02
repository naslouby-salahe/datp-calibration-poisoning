from __future__ import annotations

from datp.types import (
    ClientCount,
    ClientId,
    FeatureCount,
    NarrativeText,
    RandomSeed,
    RoundCount,
    RoundIndex,
    ScoreValue,
)


from dataclasses import dataclass
from pathlib import Path
from typing import cast

import torch
from flwr.client import ClientApp
from flwr.common import Scalar, ndarrays_to_parameters
from flwr.server import ServerApp, ServerConfig
from flwr.server.serverapp_components import ServerAppComponents
from flwr.simulation.run_simulation import BackendConfig, run_simulation

from datp import configure_runtime_env
from datp.artifacts.lifecycle import RunLifecycle
from datp.artifacts.names import ArtifactDir, ArtifactFile
from datp.config.models import CheckpointProtocolConfig, DatpConfig
from datp.config.models import ExperimentStage
from datp.core.device import resolve_device
from datp.core.enums import DeviceType
from datp.core.logging import get_logger
from datp.core.seeds import set_seeds
from datp.core.tracking import (
    TrackingMetric,
    TrackingMetricKey,
    TrackingParam,
    TrackingParamKey,
    log_artifact,
    log_metrics,
    log_params,
)
from datp.data.catalog import dataset_for_stage
from datp.federated.catalog import TrainingClientCatalog
from datp.federated.communication import build_comm_summary, compute_model_bytes
from datp.federated.checkpoints import (
    ConvergenceSnapshot,
    load_params_snapshot,
    save_checkpoint,
    save_convergence_artifacts,
)
from datp.federated.clients import DatpClient
from datp.federated.convergence import ConvergenceMonitor
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
from datp.federated.types import ClientData, validate_client_data
from datp.modeling.autoencoder import Autoencoder
from datp.scoring.generation import score_clients

logger = get_logger(__name__)


def _artifact_root_from_path(path: Path, anchor: ArtifactDir) -> Path:
    if anchor not in path.parts:
        raise ValueError(f"Path lacks anchor {anchor}: {path}")
    idx = path.parts.index(anchor)
    return Path(path.anchor) if idx == 0 else Path(*path.parts[:idx])


def _checkpoint_protocol_enabled(
    cfg: DatpConfig, ckpt_dir: Path, score_base: Path
) -> bool:
    ckpt_cfg = cfg.checkpoint_protocol
    return (
        isinstance(ckpt_cfg, CheckpointProtocolConfig)
        and ckpt_cfg.enabled
        and ArtifactDir.CHECKPOINTS in ckpt_dir.parts
        and ArtifactDir.SCORES in score_base.parts
    )


@dataclass(frozen=True, slots=True)
class SimClientConfig:

    client_cls: type[DatpClient] = DatpClient
    client_extra_kwargs: dict[str, Scalar] | None = None
    encoder_only: bool = False
    score_after: bool = True


@dataclass(frozen=True, slots=True)
class TrainingResult:

    stage: ExperimentStage
    seed: RandomSeed
    converged_round: RoundIndex | None
    total_rounds: RoundCount
    checkpoint_dir: Path
    score_dir: Path
    loss_history: list[ScoreValue]


def validate_stage(cfg: DatpConfig) -> ExperimentStage:
    if cfg.stage is None:
        raise ValueError("stage must be set in config")
    return cfg.stage


def load_scoring_data(
    client_data: dict[ClientId, ClientData] | None,
    prepared_dir: Path | None,
    expected_dim: FeatureCount,
) -> dict[ClientId, ClientData]:
    if prepared_dir is not None:
        data = load_client_data(
            prepared_dir, device=torch.device(DeviceType.CPU), splits=ALL_SPLITS
        )
    elif client_data:
        data = client_data
    else:
        raise ValueError("No scoring data source provided")

    for client_id, splits in data.items():
        validate_client_data(splits, client_id, expected_dim=expected_dim)
    return data


@dataclass(frozen=True, slots=True)
class FlSimulationRequest:

    cfg: DatpConfig
    client_data: dict[ClientId, ClientData] | None
    seed: RandomSeed
    model_cls: type[Autoencoder]
    ckpt_dir: Path
    score_base: Path
    label: NarrativeText
    prepared_dir: Path | None = None
    client_config: SimClientConfig = SimClientConfig()


@dataclass(frozen=True, slots=True)
class SimulationArtifacts:

    ckpt_dir_by_round: dict[RoundIndex, Path]
    strategy: DatpFedAvg
    param_module: torch.nn.Module
    model: Autoencoder


def _save_simulation_artifacts(
    artifacts: SimulationArtifacts,
    snapshot: ConvergenceSnapshot,
    req: FlSimulationRequest,
    protocol_enabled: bool,
) -> None:
    if artifacts.strategy.latest_parameters is None:
        raise RuntimeError("Final aggregated parameters unavailable")
    if protocol_enabled:
        for r, c_dir in sorted(artifacts.ckpt_dir_by_round.items()):
            params = artifacts.strategy.parameter_snapshots.get(
                r
            ) or load_params_snapshot(c_dir)
            if params is None:
                raise RuntimeError(f"Missing params snapshot for round {r}")
            set_parameters(artifacts.param_module, params)
            save_checkpoint(artifacts.model, c_dir)
            save_convergence_artifacts(c_dir, snapshot, req.cfg.federation.convergence)
    else:
        set_parameters(artifacts.param_module, artifacts.strategy.latest_parameters)
        save_checkpoint(artifacts.model, req.ckpt_dir)
        save_convergence_artifacts(
            req.ckpt_dir, snapshot, req.cfg.federation.convergence
        )


def _score_after_simulation(
    req: FlSimulationRequest,
    artifacts: SimulationArtifacts,
) -> None:
    if not req.client_config.score_after:
        return
    stage = validate_stage(req.cfg)
    protocol_enabled = _checkpoint_protocol_enabled(
        req.cfg, req.ckpt_dir, req.score_base
    )
    ckpt_cfg = req.cfg.checkpoint_protocol
    scoring_data = load_scoring_data(
        req.client_data, req.prepared_dir, expected_dim=req.cfg.model.input_dim
    )
    if protocol_enabled and isinstance(ckpt_cfg, CheckpointProtocolConfig):
        from datp.artifacts.layout import ArtifactLayout
        from datp.core.identity import TrainingCellId

        score_layout = ArtifactLayout(
            base_dir=_artifact_root_from_path(req.score_base, ArtifactDir.SCORES),
            stage=stage,
        )
        score_cell = TrainingCellId(stage=stage, seed=RandomSeed(req.seed))
        for r in ckpt_cfg.milestones:
            params = artifacts.strategy.parameter_snapshots.get(
                r
            ) or load_params_snapshot(artifacts.ckpt_dir_by_round[r])
            if params is None:
                raise RuntimeError(f"Missing scoring snapshot for round {r}")
            set_parameters(artifacts.param_module, params)
            score_clients(
                model=artifacts.model,
                client_data=scoring_data,
                score_base=score_layout.score_cell(score_cell, r).score_dir,
                stage=stage,
                seed=req.seed,
                dataset=dataset_for_stage(stage),
                checkpoint_path=artifacts.ckpt_dir_by_round[r]
                / ArtifactFile.MODEL_CHECKPOINT,
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


def _checkpoint_dirs(
    req: FlSimulationRequest,
    stage: ExperimentStage,
    protocol_enabled: bool,
) -> dict[RoundIndex, Path]:
    ckpt_cfg = req.cfg.checkpoint_protocol
    if not protocol_enabled or not isinstance(ckpt_cfg, CheckpointProtocolConfig):
        return {}

    from datp.artifacts.layout import ArtifactLayout
    from datp.core.identity import TrainingCellId

    layout = ArtifactLayout(
        base_dir=_artifact_root_from_path(req.ckpt_dir, ArtifactDir.CHECKPOINTS),
        stage=stage,
    )
    cell = TrainingCellId(stage=stage, seed=req.seed)
    return {round_index: layout.checkpoint_dir(cell, round_index) for round_index in ckpt_cfg.milestones}


def _run_flower_simulation(
    req: FlSimulationRequest,
    catalog: TrainingClientCatalog,
    device: torch.device,
    strategy: DatpFedAvg,
    rounds_max: RoundCount,
) -> None:
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
    run_simulation(
        num_supernodes=catalog.num_clients,
        client_app=ClientApp(client_fn=client_fn),
        server_app=ServerApp(
            server_fn=lambda _: ServerAppComponents(
                strategy=strategy,
                config=ServerConfig(
                    num_rounds=rounds_max,
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
    )


def _log_communication_estimate(
    total_rounds: RoundCount,
    model: torch.nn.Module,
    num_clients: ClientCount,
) -> None:
    parameter_count = sum(parameter.size for parameter in get_parameters(model))
    communication = build_comm_summary(
        total_rounds=total_rounds,
        model_bytes=compute_model_bytes(parameter_count),
        num_clients=num_clients,
        k_eligible=num_clients,
    )
    logger.info(
        "federated communication estimated",
        model_bytes=communication.training.model_bytes,
        total_rounds=communication.training.total_rounds,
        client_count=communication.training.num_clients,
        training_uplink_bytes=communication.training.total_uplink_bytes,
        training_downlink_bytes=communication.training.total_downlink_bytes,
        threshold_uplink_bytes={
            policy: values.server_uplink_payload_bytes
            for policy, values in communication.threshold_calibration.items()
        },
        threshold_downlink_bytes={
            policy: values.server_downlink_payload_bytes
            for policy, values in communication.threshold_calibration.items()
        },
    )


def _log_training_tracking(
    req: FlSimulationRequest,
    stage: ExperimentStage,
    rounds_max: RoundCount,
    total_rounds: RoundCount,
    converged_round: RoundIndex | None,
) -> None:
    log_params(
        (
            TrackingParam(TrackingParamKey.STAGE, stage),
            TrackingParam(TrackingParamKey.SEED, req.seed),
            TrackingParam(TrackingParamKey.ROUNDS_MAX, rounds_max),
            TrackingParam(TrackingParamKey.LABEL, req.label),
        )
    )
    log_metrics(
        (
            TrackingMetric(
                TrackingMetricKey.CONVERGED_ROUND,
                float(converged_round if converged_round is not None else total_rounds),
            ),
            TrackingMetric(TrackingMetricKey.TOTAL_ROUNDS, total_rounds),
        ),
        step=None,
        prefix=None,
    )
    ckpt_file = req.ckpt_dir / ArtifactFile.MODEL_CHECKPOINT
    if ckpt_file.exists():
        log_artifact(ckpt_file, artifact_path=None)


def run_fl_simulation(req: FlSimulationRequest) -> TrainingResult:
    stage = validate_stage(req.cfg)
    protocol_enabled = _checkpoint_protocol_enabled(
        req.cfg, req.ckpt_dir, req.score_base
    )
    ckpt_cfg = req.cfg.checkpoint_protocol
    effective_rounds_max = (
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
    parameter_module = model.encoder if req.client_config.encoder_only else model
    initial_parameters = ndarrays_to_parameters(get_parameters(parameter_module))
    checkpoint_dirs = _checkpoint_dirs(req, stage, protocol_enabled)
    strategy: DatpFedAvg = DatpFedAvg.from_config(
        req.cfg,
        FedAvgBuildRequest(
            initial_parameters=initial_parameters,
            num_clients=catalog.num_clients,
            effective_rounds_max=effective_rounds_max,
            checkpoint_disk_dirs=checkpoint_dirs or None,
        ),
    )
    monitor: ConvergenceMonitor = strategy.convergence_monitor
    artifacts = SimulationArtifacts(
        ckpt_dir_by_round=checkpoint_dirs,
        strategy=strategy,
        param_module=parameter_module,
        model=model,
    )

    with RunLifecycle(req.ckpt_dir, seed=req.seed) as lifecycle:
        _run_flower_simulation(req, catalog, device, strategy, effective_rounds_max)
        total_rounds = monitor.num_recorded
        converged_round = monitor.converged_round
        logger.info(
            "federated training completed",
            total_rounds=total_rounds,
            converged_round=converged_round,
            stopped=strategy.stopped,
        )
        _log_communication_estimate(total_rounds, parameter_module, catalog.num_clients)
        snapshot = ConvergenceSnapshot(
            loss_history=monitor.loss_history,
            converged_round=converged_round,
            criterion_value=monitor.latest_relative_change,
        )
        _save_simulation_artifacts(artifacts, snapshot, req, protocol_enabled)
        lifecycle.last_completed_round = total_rounds

    _score_after_simulation(req, artifacts)
    _log_training_tracking(
        req, stage, effective_rounds_max, total_rounds, converged_round
    )

    return TrainingResult(
        stage=stage,
        seed=req.seed,
        converged_round=converged_round,
        total_rounds=total_rounds,
        checkpoint_dir=req.ckpt_dir,
        score_dir=req.score_base,
        loss_history=monitor.loss_history,
    )
