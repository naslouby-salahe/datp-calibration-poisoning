# SPDX-License-Identifier: Proprietary
"""Model builder and Flower client factory — single implementation for all protocols."""

from __future__ import annotations

from collections.abc import Callable
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
    """Seed the Ray worker process so worker-side randomness (e.g. torch.randperm
    in the local training loop) is reproducible across runs.

    Mixing the partition id avoids identical shuffles across partitions.
    """
    if base_seed is None:
        return
    set_seeds(base_seed ^ partition_id)


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
    _extra = extra_kwargs or {}

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
            _seed_worker(seed, idx)
            client_id = client_ids[idx]
            train_t, cal_t = load_single_client_training_data(
                client_dir_map[client_id], device
            )
            model = build_model(cfg, model_cls)
            model.to(device)
            return client_cls(
                cid=client_id,
                model=model,
                train_data=train_t,
                val_data=cal_t,
                cfg=cfg,
                **_extra,
            ).to_client()

        return _prepared_client_fn

    def client_fn(context: Context) -> Client:
        idx = int(context.node_config["partition-id"])
        _seed_worker(seed, idx)
        client_id = client_ids[idx]
        splits = client_data[client_id]
        model = build_model(cfg, model_cls)
        model.to(device)
        return client_cls(
            cid=client_id,
            model=model,
            train_data=splits.train.to(device, non_blocking=True),
            val_data=splits.val.to(device, non_blocking=True),
            cfg=cfg,
            **_extra,
        ).to_client()

    return client_fn
