from __future__ import annotations

import pytest
import torch

from datp.core.enums import DeviceType
from datp.modeling.autoencoder import validate_model_on_cuda
from tests.fixtures.cuda_model import make_cuda_validation_model


class TestValidateModelOnCuda:
    def test_cpu_model_raises(self) -> None:
        model = make_cuda_validation_model()
        assert next(model.parameters()).device == torch.device(DeviceType.CPU)
        with pytest.raises(RuntimeError, match="not CUDA"):
            validate_model_on_cuda(model)

    def test_error_mentions_parameter_name(self) -> None:
        model = make_cuda_validation_model()
        with pytest.raises(RuntimeError, match=r"Parameter '.*'"):
            validate_model_on_cuda(model)

    def test_cuda_model_passes(self) -> None:
        model = make_cuda_validation_model().cuda()
        validate_model_on_cuda(model) # Should not raise
