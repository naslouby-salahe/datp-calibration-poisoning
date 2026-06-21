# SPDX-License-Identifier: Proprietary
"""Shared FL client; no policy-specific branching — all threshold policies train the same encoder."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import torch
from flwr.client import NumPyClient

from datp.federated.local_training import evaluate_benign, train_local
from datp.federated.parameters import get_parameters, set_parameters
from datp.federated.types import (
    ClientMetricKey,
    validate_tensor_input,
)
from datp.modeling.autoencoder import Autoencoder

if TYPE_CHECKING:
    from datp.config.models import DatpConfig


class DatpClient(NumPyClient):
    def __init__(
        self,
        cid: str,
        model: Autoencoder,
        train_data: torch.Tensor,
        val_data: torch.Tensor,
        cfg: DatpConfig,
    ) -> None:
        validate_tensor_input(train_data, "train_data", cid)
        validate_tensor_input(val_data, "val_data", cid)
        self.cid = cid
        self.model = model
        self.train_data = train_data
        self.val_data = val_data

        self._local_epochs: int = cfg.federation.local_epochs
        self._batch_size: int = cfg.machine.batch_size_train
        self._lr: float = cfg.model.lr

    def get_parameters(self, config: dict[str, Any]) -> list[np.ndarray]:  # noqa: ARG002
        return get_parameters(self.model)

    def fit(
        self,
        parameters: list[np.ndarray],
        config: dict[str, Any],  # noqa: ARG002
    ) -> tuple[list[np.ndarray], int, dict[str, Any]]:
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
        self,
        parameters: list[np.ndarray],
        config: dict[str, Any],  # noqa: ARG002
    ) -> tuple[float, int, dict[str, Any]]:
        """Benign-only validation — never evaluated on attack data."""
        set_parameters(self.model, parameters)
        loss = evaluate_benign(self.model, self.val_data)
        return loss, len(self.val_data), {ClientMetricKey.VAL_LOSS: loss}
