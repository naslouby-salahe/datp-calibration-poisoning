"""Flower NumPyClient wrapping local AE training and calibration evaluation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import torch
from flwr.client import NumPyClient

from datp.federated.local_training import evaluate_benign, train_local
from datp.federated.parameters import get_parameters, set_parameters
from datp.federated.types import ClientMetricKey, validate_tensor_input
from datp.modeling.autoencoder import Autoencoder

if TYPE_CHECKING:
    from datp.config.models import DatpConfig


class DatpClient(NumPyClient):
    """Per-client federated worker that trains and evaluates a local autoencoder."""

    def __init__(
        self,
        cid: str,
        model: Autoencoder,
        train_data: torch.Tensor,
        cal_data: torch.Tensor,
        cfg: DatpConfig,
    ) -> None:
        """Initialize with client ID, model, training/calibration tensors, and config."""
        validate_tensor_input(train_data, "train_data", cid)
        validate_tensor_input(cal_data, "cal_data", cid)
        self.cid = cid
        self.model = model
        self.train_data = train_data
        self.cal_data = cal_data
        self._local_epochs = cfg.federation.local_epochs
        self._batch_size = cfg.machine.batch_size_train
        self._lr = cfg.model.lr

    def get_parameters(self, config: dict[str, Any]) -> list[np.ndarray]:
        """Return current model parameters as numpy arrays."""
        return get_parameters(self.model)

    def fit(
        self, parameters: list[np.ndarray], config: dict[str, Any]
    ) -> tuple[list[np.ndarray], int, dict[str, Any]]:
        """Run local training for the configured number of epochs."""
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
        self, parameters: list[np.ndarray], config: dict[str, Any]
    ) -> tuple[float, int, dict[str, Any]]:
        """Evaluate MSE reconstruction loss on local calibration data."""
        set_parameters(self.model, parameters)
        loss = evaluate_benign(self.model, self.cal_data)
        return loss, len(self.cal_data), {ClientMetricKey.VAL_LOSS: loss}
