# SPDX-License-Identifier: Proprietary
"""Model builder and Flower client factory — single implementation for all protocols."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from flwr.client import Client
from flwr.common import Context

from datp.config.models import DatpConfig
from datp.core.errors import fmt
from datp.core.seeds import set_seeds
from datp.federated.clients import DatpClient
from datp.federated.data_loading import (
    discover_client_dirs,
    load_single_client_training_data,
)
from datp.federated.types import ClientData
from datp.modeling.autoencoder import Autoencoder

_MODULE = "federated.factories"


def build_model(
    cfg: DatpConfig, model_cls: type[Autoencoder] = Autoencoder
) -> Autoencoder:
    """Construct an Autoencoder from config.

    The default ``model_cls`` is the standard ``Autoencoder``; protocol
    runners using custom protocol-specific models may pass the class explicitly.
    """
    return model_cls(
        input_dim=cfg.model.input_dim,
        hidden_dims=cfg.model.encoder_dims,
        activation=cfg.model.activation,
        use_bn=cfg.model.use_bn,
    )


def _seed_worker(base_seed: int | None, partition_id: int) -> None:
    """Seed the Ray worker process for reproducible worker-side randomness.

    Mixing the partition id avoids identical shuffles across partitions.
    """
    if base_seed is None:
        return
    set_seeds(base_seed ^ partition_id)


@dataclass(frozen=True, slots=True)
class ClientFactoryConfig:
    """Bundled options for make_client_fn."""

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
    val_data: torch.Tensor,
) -> Client:
    model = build_model(factory_cfg.cfg, factory_cfg.model_cls)
    model.to(factory_cfg.device)
    extra = factory_cfg.extra_kwargs or {}
    return factory_cfg.client_cls(
        cid=client_id,
        model=model,
        train_data=train_data,
        val_data=val_data,
        cfg=factory_cfg.cfg,
        **extra,
    ).to_client()


def make_client_fn(
    client_data: dict[str, ClientData],
    client_ids: list[str],
    cfg: DatpConfig,
    device: torch.device,
    *,
    prepared_dir: Path | None = None,
    model_cls: type[Autoencoder] = Autoencoder,
    client_cls: type[DatpClient] = DatpClient,
    extra_kwargs: dict[str, Any] | None = None,
    seed: int | None = None,
) -> Callable[[Context], Client]:
    """Build a Flower client_fn that maps partition-id to a DatpClient subclass.

    Args:
        client_data: mapping of client_id -> ClientData (train/val tensors).
        client_ids: ordered client IDs matching partition indices.
        cfg: experiment config.
        device: torch device for model and data.
        prepared_dir: if set, loads data lazily from disk per-client.
        model_cls: autoencoder class to construct.
        client_cls: DatpClient subclass to instantiate.
        extra_kwargs: additional keyword arguments passed to client_cls.__init__
            (e.g., mu for proximal regularization).
        seed: when provided, the Ray worker process is seeded on each client_fn
            entry (mixed with partition-id) so worker-side randomness (e.g.
            torch.randperm in batch shuffling) is reproducible across runs.
    """
    factory_cfg = ClientFactoryConfig(
        client_ids=client_ids,
        cfg=cfg,
        device=device,
        prepared_dir=prepared_dir,
        model_cls=model_cls,
        client_cls=client_cls,
        extra_kwargs=extra_kwargs,
        seed=seed,
    )

    if prepared_dir is not None:
        client_dir_map: dict[str, Path] = {
            d.name: d for d in discover_client_dirs(prepared_dir)
        }
        missing = [cid for cid in client_ids if cid not in client_dir_map]
        if missing:
            raise FileNotFoundError(
                fmt(
                    _MODULE,
                    "Prepared client directories missing for declared client_ids",
                    f"all client_ids present in {prepared_dir}",
                    f"missing={missing}, available={sorted(client_dir_map.keys())}",
                )
            )

        def _prepared_client_fn(context: Context) -> Client:
            idx = int(context.node_config["partition-id"])
            _seed_worker(factory_cfg.seed, idx)
            client_id = factory_cfg.client_ids[idx]
            train_t, cal_t = load_single_client_training_data(
                client_dir_map[client_id], factory_cfg.device
            )
            return _instantiate_client(factory_cfg, client_id, train_t, cal_t)

        return _prepared_client_fn

    def client_fn(context: Context) -> Client:
        idx = int(context.node_config["partition-id"])
        _seed_worker(factory_cfg.seed, idx)
        client_id = factory_cfg.client_ids[idx]
        splits = client_data[client_id]
        return _instantiate_client(
            factory_cfg,
            client_id,
            splits.train.to(factory_cfg.device, non_blocking=True),
            splits.val.to(factory_cfg.device, non_blocking=True),
        )

    return client_fn
