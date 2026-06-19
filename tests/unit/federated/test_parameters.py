# SPDX-License-Identifier: Proprietary
"""Tests for datp.federated.parameters — shape/dtype/device safety."""

from __future__ import annotations

import numpy as np
import pytest
import torch
import torch.nn as nn

from datp.core.enums import Activation, DeviceType
from datp.federated.parameters import get_parameters, set_parameters
from datp.modeling.autoencoder import Autoencoder


def _make_model() -> Autoencoder:
    return Autoencoder(
        input_dim=4, hidden_dims=[3, 2], activation=Activation.RELU, use_bn=False
    )


class TestGetParameters:
    def test_returns_list_of_ndarrays(self) -> None:
        model = _make_model()
        params = get_parameters(model)
        assert isinstance(params, list)
        assert all(isinstance(p, np.ndarray) for p in params)

    def test_returns_copies(self) -> None:
        model = _make_model()
        params = get_parameters(model)
        params[0][:] = 999.0
        model_params = list(model.parameters())
        assert not np.allclose(model_params[0].detach().cpu().numpy(), 999.0)


class TestSetParameters:
    def test_round_trip(self) -> None:
        model = _make_model()
        original = get_parameters(model)
        # Modify model
        with torch.no_grad():
            for p in model.parameters():
                p.fill_(0.0)
        # Restore
        set_parameters(model, original)
        restored = get_parameters(model)
        for orig, rest in zip(original, restored, strict=True):
            np.testing.assert_array_almost_equal(orig, rest)

    def test_dtype_cast(self) -> None:
        model = _make_model()
        params = get_parameters(model)
        # Convert to float64
        params_f64 = [p.astype(np.float64) for p in params]
        set_parameters(model, params_f64)
        for p in model.parameters():
            assert p.dtype == torch.float32

    def test_shape_mismatch_raises(self) -> None:
        model = _make_model()
        params = get_parameters(model)
        params[0] = np.zeros((99, 99), dtype=np.float32)
        with pytest.raises(ValueError, match="Shape mismatch"):
            set_parameters(model, params)

    def test_count_mismatch_raises(self) -> None:
        model = _make_model()
        params = get_parameters(model)
        with pytest.raises(ValueError, match="Parameter count mismatch"):
            set_parameters(model, params[:1])


class TestSetParametersDevice:
    def test_stays_on_cpu(self) -> None:
        model = _make_model()
        params = get_parameters(model)
        set_parameters(model, params)
        for p in model.parameters():
            assert p.device == torch.device(DeviceType.CPU)

    def test_preserves_original_device(self) -> None:
        model = _make_model()
        original_devices = [p.device for p in model.parameters()]
        params = get_parameters(model)
        set_parameters(model, params)
        for p, orig_device in zip(model.parameters(), original_devices, strict=True):
            assert p.device == orig_device


class TestEmptyModel:
    def test_get_parameters_empty_model(self) -> None:
        model = nn.Sequential()  # zero parameters
        params = get_parameters(model)
        assert params == []

    def test_set_parameters_empty_model(self) -> None:
        model = nn.Sequential()
        set_parameters(model, [])
        # No exception raised; model unchanged
