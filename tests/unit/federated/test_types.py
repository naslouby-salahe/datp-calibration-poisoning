# SPDX-License-Identifier: Proprietary
"""Tests for datp.federated.types — ClientData validation helpers."""

from __future__ import annotations

import pytest
import torch

from datp.federated.types import (
    ClientData,
    validate_client_data,
    validate_feature_dim,
    validate_tensor_2d,
    validate_tensor_finite,
    validate_tensor_input,
    validate_tensor_non_empty,
)


class TestValidateTensor2D:
    def test_valid_2d(self) -> None:
        validate_tensor_2d(torch.randn(10, 4), "data", "c0")

    def test_1d_raises(self) -> None:
        with pytest.raises(ValueError, match="must be 2-D"):
            validate_tensor_2d(torch.randn(10), "data", "c0")

    def test_3d_raises(self) -> None:
        with pytest.raises(ValueError, match="must be 2-D"):
            validate_tensor_2d(torch.randn(2, 3, 4), "data", "c0")


class TestValidateTensorNonEmpty:
    def test_non_empty_passes(self) -> None:
        validate_tensor_non_empty(torch.randn(10, 4), "data", "c0")

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="must be non-empty"):
            validate_tensor_non_empty(torch.empty(0, 4), "data", "c0")


class TestValidateTensorFinite:
    def test_finite_passes(self) -> None:
        validate_tensor_finite(torch.randn(10, 4), "data", "c0")

    def test_nan_raises(self) -> None:
        data = torch.randn(10, 4)
        data[0, 0] = float("nan")
        with pytest.raises(ValueError, match="non-finite"):
            validate_tensor_finite(data, "data", "c0")

    def test_inf_raises(self) -> None:
        data = torch.randn(10, 4)
        data[0, 0] = float("inf")
        with pytest.raises(ValueError, match="non-finite"):
            validate_tensor_finite(data, "data", "c0")


class TestValidateFeatureDim:
    def test_correct_dim_passes(self) -> None:
        validate_feature_dim(torch.randn(10, 4), 4, "data", "c0")

    def test_wrong_dim_raises(self) -> None:
        with pytest.raises(ValueError, match="feature dimension mismatch"):
            validate_feature_dim(torch.randn(10, 4), 5, "data", "c0")


class TestValidateClientData:
    def test_valid_passes(self) -> None:
        cd = ClientData(
            train=torch.randn(16, 4),
            val=torch.randn(8, 4),
            test_benign=torch.randn(8, 4),
            test_attack=torch.randn(8, 4),
        )
        validate_client_data(cd, "c0", expected_dim=4)

    def test_wrong_dim_raises(self) -> None:
        cd = ClientData(
            train=torch.randn(16, 5),
            val=torch.randn(8, 4),
            test_benign=torch.randn(8, 4),
            test_attack=torch.randn(8, 4),
        )
        with pytest.raises(ValueError, match="feature dimension mismatch"):
            validate_client_data(cd, "c0", expected_dim=4)


class TestValidateTensorInput:
    def test_valid_passes(self) -> None:
        validate_tensor_input(torch.randn(16, 4), "data", "c0", expected_dim=4)

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            validate_tensor_input(torch.empty(0, 4), "data", "c0")

    def test_nan_raises(self) -> None:
        data = torch.randn(16, 4)
        data[0, 0] = float("nan")
        with pytest.raises(ValueError, match="non-finite"):
            validate_tensor_input(data, "data", "c0")

    def test_1d_raises(self) -> None:
        with pytest.raises(ValueError, match="must be 2-D"):
            validate_tensor_input(torch.randn(10), "data", "c0")

    def test_wrong_dim_raises(self) -> None:
        with pytest.raises(ValueError, match="feature dimension mismatch"):
            validate_tensor_input(torch.randn(16, 5), "data", "c0", expected_dim=4)
