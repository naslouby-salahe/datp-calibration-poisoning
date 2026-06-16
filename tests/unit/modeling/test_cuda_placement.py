from __future__ import annotations

import pytest
import torch

from datp.core.enums import Activation, DeviceType
from datp.modeling.autoencoder import Autoencoder, validate_model_on_cuda


class TestValidateModelOnCuda:
    def test_cpu_model_raises(self) -> None:
        model = Autoencoder(
            input_dim=10, hidden_dims=[8, 4], activation=Activation.RELU, use_bn=False
        )
        assert next(model.parameters()).device == torch.device(DeviceType.CPU)
        with pytest.raises(RuntimeError, match="not CUDA"):
            validate_model_on_cuda(model)

    def test_error_mentions_parameter_name(self) -> None:
        model = Autoencoder(
            input_dim=10, hidden_dims=[8, 4], activation=Activation.RELU, use_bn=False
        )
        with pytest.raises(RuntimeError, match=r"Parameter '.*'"):
            validate_model_on_cuda(model)

    def test_cuda_model_passes(self) -> None:
        model = Autoencoder(
            input_dim=10, hidden_dims=[8, 4], activation=Activation.RELU, use_bn=False
        ).cuda()
        validate_model_on_cuda(model) # Should not raise
