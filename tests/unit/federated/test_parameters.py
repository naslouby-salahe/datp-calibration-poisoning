"""Tests verifying model parameter weight state serialization and restoration helper routines."""

from __future__ import annotations

import numpy as np
import pytest
import torch
import torch.nn as nn

from datp.core.enums import Activation, DeviceType
from datp.federated.parameters import get_parameters, set_parameters
from datp.modeling.autoencoder import Autoencoder


def _make_model() -> Autoencoder:
    """Helper to build a default Autoencoder model for tests."""
    return Autoencoder(
        input_dim=4, hidden_dims=[3, 2], activation=Activation.RELU, use_bn=False
    )


class TestGetParameters:
    """Tests verifying get_parameters behavior and copies security."""

    def test_returns_list_of_ndarrays(self) -> None:
        """Verify that get_parameters returns a list of NumPy float arrays."""
        model = _make_model()
        params = get_parameters(model)
        assert isinstance(params, list)
        assert all(isinstance(p, np.ndarray) for p in params)

    def test_returns_copies(self) -> None:
        """Verify that modifying the returned numpy arrays does not affect the model parameters."""
        model = _make_model()
        params = get_parameters(model)
        params[0][:] = 999.0
        model_params = list(model.parameters())
        assert not np.allclose(model_params[0].detach().cpu().numpy(), 999.0)


class TestSetParameters:
    """Tests verifying set_parameters behavior and validations."""

    def test_round_trip(self) -> None:
        """Verify that set_parameters successfully restores weight values after zeroing."""
        model = _make_model()
        original = get_parameters(model)

        with torch.no_grad():
            for p in model.parameters():
                p.fill_(0.0)

        set_parameters(model, original)
        restored = get_parameters(model)
        for orig, rest in zip(original, restored, strict=True):
            np.testing.assert_array_almost_equal(orig, rest)

    def test_dtype_cast(self) -> None:
        """Verify that setting float64 parameters casts back to the model's float32 type."""
        model = _make_model()
        params = get_parameters(model)

        params_f64 = [p.astype(np.float64) for p in params]
        set_parameters(model, params_f64)
        for p in model.parameters():
            assert p.dtype == torch.float32

    def test_shape_mismatch_raises(self) -> None:
        """Verify ValueError is raised if parameter array shape mismatches model parameter shape."""
        model = _make_model()
        params = get_parameters(model)
        params[0] = np.zeros((99, 99), dtype=np.float32)
        with pytest.raises(ValueError, match="Shape mismatch"):
            set_parameters(model, params)

    def test_count_mismatch_raises(self) -> None:
        """Verify ValueError is raised if parameter array count mismatches model parameter count."""
        model = _make_model()
        params = get_parameters(model)
        with pytest.raises(ValueError, match="Parameter count mismatch"):
            set_parameters(model, params[:1])


class TestSetParametersDevice:
    """Tests verifying PyTorch device safety inside parameter setter."""

    def test_stays_on_cpu(self) -> None:
        """Verify parameters set on a CPU model stay on the CPU device."""
        model = _make_model()
        params = get_parameters(model)
        set_parameters(model, params)
        for p in model.parameters():
            assert p.device == torch.device(DeviceType.CPU)

    def test_preserves_original_device(self) -> None:
        """Verify that set_parameters preserves the original device of all parameter tensors."""
        model = _make_model()
        original_devices = [p.device for p in model.parameters()]
        params = get_parameters(model)
        set_parameters(model, params)
        for p, orig_device in zip(model.parameters(), original_devices, strict=True):
            assert p.device == orig_device


class TestEmptyModel:
    """Tests verifying serialization behaviour of empty models (e.g. empty Sequential)."""

    def test_get_parameters_empty_model(self) -> None:
        """Verify get_parameters returns an empty list for models with no parameters."""
        model = nn.Sequential()
        params = get_parameters(model)
        assert params == []

    def test_set_parameters_empty_model(self) -> None:
        """Verify set_parameters is a no-op when setting an empty parameters list on a model with no parameters."""
        model = nn.Sequential()
        set_parameters(model, [])
