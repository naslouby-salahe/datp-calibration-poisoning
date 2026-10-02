from __future__ import annotations

from datp.types import (
    ClientId,
    NarrativeText,
    SampleCount,
)


from typing import TYPE_CHECKING

import torch
from flwr.client import NumPyClient
from flwr.common import NDArrays, Scalar

from datp.federated.local_training import evaluate_benign, train_local
from datp.federated.parameters import get_parameters, set_parameters
from datp.federated.types import (
    ClientMetricKey,
    FederatedTensorLabel,
    validate_tensor_input,
)
from datp.modeling.autoencoder import Autoencoder

if TYPE_CHECKING:
    from datp.config.models import DatpConfig


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
        validate_tensor_input(cal_data, FederatedTensorLabel.CALIBRATION_DATA, client_id)
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
