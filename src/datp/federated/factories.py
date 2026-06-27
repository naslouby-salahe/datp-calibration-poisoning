"""Client-factory and model-construction helpers for FL simulations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from flwr.client import Client
from flwr.common import Context

from datp.config.models import DatpConfig
from datp.core.seeds import set_seeds
from datp.federated.clients import DatpClient
from datp.federated.data_loading import (
    discover_client_dirs,
    load_single_client_training_data,
)
from datp.federated.types import ClientData
from datp.modeling.autoencoder import Autoencoder


def build_model(
    cfg: DatpConfig, model_cls: type[Autoencoder] = Autoencoder
) -> Autoencoder:
    """Instantiate an autoencoder from configuration."""
    return model_cls(
        input_dim=cfg.model.input_dim,
        hidden_dims=cfg.model.encoder_dims,
        activation=cfg.model.activation,
        use_bn=cfg.model.use_bn,
    )


def _seed_worker(base_seed: int | None, partition_id: int) -> None:
    """Set deterministic seeds for a worker, XOR-ing partition id into the base seed."""
    if base_seed is not None:
        set_seeds(base_seed ^ partition_id)


@dataclass(frozen=True, slots=True)
class ClientFactoryConfig:
    """Configuration bundle for creating FL clients: IDs, config, device, and model class."""

    client_ids: list[str]
    cfg: DatpConfig
    device: torch.device
    prepared_dir: Path | None = None
    model_cls: type[Autoencoder] = Autoencoder
    client_cls: type[DatpClient] = DatpClient
    extra_kwargs: dict[str, Any] | None = None
    seed: int | None = None


def _instantiate_client(
    factory_cfg: ClientFactoryConfig,
    client_id: str,
    train_data: torch.Tensor,
    cal_data: torch.Tensor,
) -> Client:
    """Build, move to device, and wrap a single client."""
    model = build_model(factory_cfg.cfg, factory_cfg.model_cls).to(factory_cfg.device)
    return factory_cfg.client_cls(
        cid=client_id,
        model=model,
        train_data=train_data,
        cal_data=cal_data,
        cfg=factory_cfg.cfg,
        **(factory_cfg.extra_kwargs or {}),
    ).to_client()


def make_client_fn(
    client_data: dict[str, ClientData], factory_cfg: ClientFactoryConfig
) -> Callable[[Context], Client]:
    """Return a Flower client_fn that instantiates clients lazily per partition."""
    if factory_cfg.prepared_dir is not None:
        client_dir_map = {
            d.name: d for d in discover_client_dirs(factory_cfg.prepared_dir)
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
