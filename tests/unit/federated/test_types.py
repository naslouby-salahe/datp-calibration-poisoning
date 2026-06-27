"""Tests verifying client tensor data shapes, NaN/Inf bounds, and schema validations."""

from __future__ import annotations

import pytest
import torch

from datp.federated.types import (
    ClientData,
    validate_client_data,
    validate_tensor_input,
)


class TestValidateTensorInput:
    """Tests verifying single tensor shape and finite value validation guards."""

    def test_valid_2d_passes(self) -> None:
        """Verify that a valid 2-D tensor successfully passes validation."""
        validate_tensor_input(torch.randn(10, 4), "data", "c0")

    def test_1d_raises(self) -> None:
        """Verify ValueError is raised if the input tensor is 1-D."""
        with pytest.raises(ValueError, match="must be 2-D"):
            validate_tensor_input(torch.randn(10), "data", "c0")

    def test_3d_raises(self) -> None:
        """Verify ValueError is raised if the input tensor is 3-D."""
        with pytest.raises(ValueError, match="must be 2-D"):
            validate_tensor_input(torch.randn(2, 3, 4), "data", "c0")

    def test_empty_raises(self) -> None:
        """Verify ValueError is raised if the input tensor is empty."""
        with pytest.raises(ValueError, match="non-empty"):
            validate_tensor_input(torch.empty(0, 4), "data", "c0")

    def test_nan_raises(self) -> None:
        """Verify ValueError is raised if the input tensor contains NaN values."""
        data = torch.randn(10, 4)
        data[0, 0] = float("nan")
        with pytest.raises(ValueError, match="non-finite"):
            validate_tensor_input(data, "data", "c0")

    def test_inf_raises(self) -> None:
        """Verify ValueError is raised if the input tensor contains positive infinity."""
        data = torch.randn(10, 4)
        data[0, 0] = float("inf")
        with pytest.raises(ValueError, match="non-finite"):
            validate_tensor_input(data, "data", "c0")

    def test_correct_expected_dim_passes(self) -> None:
        """Verify that validation passes when the column dimension matches the expected value."""
        validate_tensor_input(torch.randn(10, 4), "data", "c0", expected_dim=4)

    def test_wrong_expected_dim_raises(self) -> None:
        """Verify ValueError is raised if the column dimension mismatches the expected value."""
        with pytest.raises(ValueError, match="expected dimension"):
            validate_tensor_input(torch.randn(10, 4), "data", "c0", expected_dim=5)


class TestValidateClientData:
    """Tests verifying multi-split ClientData structure schema validation."""

    def test_valid_passes(self) -> None:
        """Verify validation passes for complete ClientData containing valid splits."""
        cd = ClientData(
            train=torch.randn(16, 4),
            val=torch.randn(8, 4),
            test_benign=torch.randn(8, 4),
            test_attack=torch.randn(8, 4),
        )
        validate_client_data(cd, "c0", expected_dim=4)

    def test_wrong_dim_raises(self) -> None:
        """Verify ValueError is raised if any split has columns mismatches."""
        cd = ClientData(
            train=torch.randn(16, 5),
            val=torch.randn(8, 4),
            test_benign=torch.randn(8, 4),
            test_attack=torch.randn(8, 4),
        )
        with pytest.raises(ValueError, match="expected dimension"):
            validate_client_data(cd, "c0", expected_dim=4)
