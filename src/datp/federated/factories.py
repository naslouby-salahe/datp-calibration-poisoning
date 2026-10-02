from __future__ import annotations

from datp.types import (
    ClientId,
    RandomSeed,
    SignedCount,
)


from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import torch
from flwr.client import Client
from flwr.common import Context, Scalar

from datp.config.models import DatpConfig
from datp.core.seeds import set_seeds
from datp.federated.clients import DatpClient
from datp.federated.data_loading import (
    discover_client_dirs,
    load_single_client_training_data,
)
from datp.federated.types import ClientData
from datp.modeling.autoencoder import Autoencoder, validate_model_on_cuda


def build_model(
    cfg: DatpConfig, model_cls: type[Autoencoder] = Autoencoder
) -> Autoencoder:
    return model_cls(
        input_dim=cfg.model.input_dim,
        hidden_dims=cfg.model.encoder_dims,
        activation=cfg.model.activation,
        use_bn=cfg.model.use_bn,
    )


def _seed_worker(base_seed: RandomSeed | None, partition_id: SignedCount) -> None:
    if base_seed is not None:
        set_seeds(RandomSeed(base_seed ^ partition_id))


@dataclass(frozen=True, slots=True)
class ClientFactoryConfig:

    client_ids: list[ClientId]
    cfg: DatpConfig
    device: torch.device
    prepared_dir: Path | None = None
    model_cls: type[Autoencoder] = Autoencoder
    client_cls: type[DatpClient] = DatpClient
    extra_kwargs: dict[str, Scalar] | None = None
    seed: RandomSeed | None = None


def _instantiate_client(
    factory_cfg: ClientFactoryConfig,
    client_id: ClientId,
    train_data: torch.Tensor,
    cal_data: torch.Tensor,
) -> Client:
    model = build_model(factory_cfg.cfg, factory_cfg.model_cls).to(factory_cfg.device)
    if factory_cfg.cfg.machine.require_cuda:
        validate_model_on_cuda(model)
    return factory_cfg.client_cls(
        cid=client_id,
        model=model,
        train_data=train_data,
        cal_data=cal_data,
        cfg=factory_cfg.cfg,
        **(factory_cfg.extra_kwargs or {}),
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
