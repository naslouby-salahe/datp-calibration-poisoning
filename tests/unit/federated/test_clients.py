# SPDX-License-Identifier: Proprietary
"""Tests for DatpClient — shared FL client with no baseline-specific branching."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import torch

from datp.core.enums import Activation
from datp.core.seeds import set_seeds
from datp.federated.clients import DatpClient
from datp.federated.parameters import get_parameters
from datp.federated.types import ClientMetricKey
from datp.modeling.autoencoder import Autoencoder


def _make_ae(input_dim: int = 4, hidden_dims: list[int] | None = None) -> Autoencoder:
    return Autoencoder(
        input_dim=input_dim,
        hidden_dims=hidden_dims or [3, 2],
        activation=Activation.RELU,
        use_bn=False,
    )


def _mock_cfg(local_epochs: int = 1, lr: float = 0.01, batch_size: int = 8) -> MagicMock:
    cfg = MagicMock()
    cfg.federation.local_epochs = local_epochs
    cfg.machine.batch_size_train = batch_size
    cfg.model.lr = lr
    return cfg


# ── Construction & config storage ────────────────────────────────────────


class TestDatpClientConstruction:
    def test_stores_cid(self) -> None:
        client = DatpClient(
            cid="c0",
            model=_make_ae(),
            train_data=torch.randn(16, 4),
            val_data=torch.randn(8, 4),
            cfg=_mock_cfg(),
        )
        assert client.cid == "c0"

    def test_stores_config_derived_values(self) -> None:
        client = DatpClient(
            cid="c0",
            model=_make_ae(),
            train_data=torch.randn(16, 4),
            val_data=torch.randn(8, 4),
            cfg=_mock_cfg(local_epochs=3, lr=0.05, batch_size=16),
        )
        assert client._local_epochs == 3
        assert client._batch_size == 16
        assert client._lr == 0.05


# ── Shape validation (reject bad tensors before training) ────────────────


class TestDatpClientShapeValidation:
    def test_rejects_1d_train_data(self) -> None:
        model = _make_ae()
        with pytest.raises(ValueError, match="train_data must be 2-D"):
            DatpClient(
                cid="c0",
                model=model,
                train_data=torch.randn(16),
                val_data=torch.randn(8, 4),
                cfg=_mock_cfg(),
            )

    def test_rejects_3d_val_data(self) -> None:
        model = _make_ae()
        with pytest.raises(ValueError, match="val_data must be 2-D"):
            DatpClient(
                cid="c1",
                model=model,
                train_data=torch.randn(16, 4),
                val_data=torch.randn(8, 4, 2),
                cfg=_mock_cfg(),
            )

    def test_rejects_empty_train_data(self) -> None:
        model = _make_ae()
        with pytest.raises(ValueError, match="train_data must be non-empty"):
            DatpClient(
                cid="c0",
                model=model,
                train_data=torch.empty(0, 4),
                val_data=torch.randn(8, 4),
                cfg=_mock_cfg(),
            )

    def test_rejects_nan_train_data(self) -> None:
        model = _make_ae()
        data = torch.randn(16, 4)
        data[0, 0] = float("nan")
        with pytest.raises(ValueError, match="non-finite"):
            DatpClient(
                cid="c0",
                model=model,
                train_data=data,
                val_data=torch.randn(8, 4),
                cfg=_mock_cfg(),
            )

    def test_error_includes_module_prefix_and_cid(self) -> None:
        model = _make_ae()
        with pytest.raises(ValueError, match=r"\[federated\.types\].*client client_xyz"):
            DatpClient(
                cid="client_xyz",
                model=model,
                train_data=torch.randn(16),
                val_data=torch.randn(8, 4),
                cfg=_mock_cfg(),
            )


# ── get_parameters ───────────────────────────────────────────────────────


class TestDatpClientGetParameters:
    def test_returns_model_parameters_as_ndarrays(self) -> None:
        model = _make_ae()
        client = DatpClient(
            cid="c0",
            model=model,
            train_data=torch.randn(16, 4),
            val_data=torch.randn(8, 4),
            cfg=_mock_cfg(),
        )
        params = client.get_parameters({})
        assert isinstance(params, list)
        assert all(isinstance(p, __import__("numpy").ndarray) for p in params)
        assert len(params) == sum(1 for _ in model.parameters())

    def test_result_matches_get_parameters_helper(self) -> None:
        model = _make_ae()
        client = DatpClient(
            cid="c0",
            model=model,
            train_data=torch.randn(16, 4),
            val_data=torch.randn(8, 4),
            cfg=_mock_cfg(),
        )
        direct = get_parameters(model)
        via_client = client.get_parameters({})
        for a, b in zip(direct, via_client, strict=True):
            assert (a == b).all()


# ── fit ──────────────────────────────────────────────────────────────────


class TestDatpClientFit:
    def test_returns_params_count_and_train_loss(self) -> None:
        model = _make_ae()
        client = DatpClient(
            cid="c0",
            model=model,
            train_data=torch.randn(16, 4),
            val_data=torch.randn(8, 4),
            cfg=_mock_cfg(local_epochs=2),
        )
        initial_params = get_parameters(model)
        result_params, n_train, metrics = client.fit(initial_params, {})

        assert n_train == 16
        assert ClientMetricKey.TRAIN_LOSS in metrics
        assert isinstance(metrics[ClientMetricKey.TRAIN_LOSS], float)
        assert not torch.isnan(torch.tensor(metrics[ClientMetricKey.TRAIN_LOSS]))
        assert len(result_params) == len(initial_params)

    def test_updates_model_parameters(self) -> None:
        model = _make_ae()
        client = DatpClient(
            cid="c0",
            model=model,
            train_data=torch.randn(32, 4),
            val_data=torch.randn(8, 4),
            cfg=_mock_cfg(local_epochs=3),
        )
        params_before = get_parameters(model)
        client.fit(params_before, {})
        params_after = get_parameters(model)

        any_changed = any(
            not (a == b).all()
            for a, b in zip(params_before, params_after, strict=True)
        )
        assert any_changed, "Model parameters should change after fit"

    def test_sets_model_to_train_mode(self) -> None:
        model = _make_ae()
        model.eval()
        client = DatpClient(
            cid="c0",
            model=model,
            train_data=torch.randn(16, 4),
            val_data=torch.randn(8, 4),
            cfg=_mock_cfg(local_epochs=1),
        )
        client.fit(get_parameters(model), {})
        assert model.training, "Model should be in train mode after fit"


# ── evaluate ─────────────────────────────────────────────────────────────


class TestDatpClientEvaluate:
    def test_returns_loss_count_and_val_loss_key(self) -> None:
        model = _make_ae()
        client = DatpClient(
            cid="c0",
            model=model,
            train_data=torch.randn(16, 4),
            val_data=torch.randn(8, 4),
            cfg=_mock_cfg(),
        )
        loss, count, metrics = client.evaluate(get_parameters(model), {})

        assert count == 8
        assert loss > 0.0
        assert ClientMetricKey.VAL_LOSS in metrics
        assert metrics[ClientMetricKey.VAL_LOSS] == loss

    def test_sets_model_to_eval_mode(self) -> None:
        model = _make_ae()
        model.train()
        client = DatpClient(
            cid="c0",
            model=model,
            train_data=torch.randn(16, 4),
            val_data=torch.randn(8, 4),
            cfg=_mock_cfg(),
        )
        client.evaluate(get_parameters(model), {})
        assert not model.training, "Model should be in eval mode after evaluate"

    def test_evaluate_does_not_change_model_parameters(self) -> None:
        model = _make_ae()
        client = DatpClient(
            cid="c0",
            model=model,
            train_data=torch.randn(16, 4),
            val_data=torch.randn(8, 4),
            cfg=_mock_cfg(),
        )
        params_before = get_parameters(model)
        client.evaluate(params_before, {})
        params_after = get_parameters(model)
        for a, b in zip(params_before, params_after, strict=True):
            assert (a == b).all(), "Evaluate should not modify model parameters"


# ── Determinism ──────────────────────────────────────────────────────────


class TestDatpClientDeterminism:
    def test_same_seed_same_fit_result(self) -> None:
        import copy

        set_seeds(42)
        model_a = _make_ae()
        data = torch.randn(16, 4)
        val_data = torch.randn(8, 4)

        model_b = copy.deepcopy(model_a)

        client_a = DatpClient(
            cid="c0",
            model=model_a,
            train_data=data,
            val_data=val_data,
            cfg=_mock_cfg(local_epochs=2),
        )
        client_b = DatpClient(
            cid="c0",
            model=model_b,
            train_data=data,
            val_data=val_data,
            cfg=_mock_cfg(local_epochs=2),
        )

        set_seeds(42)
        _, _, m_a = client_a.fit(get_parameters(model_a), {})
        set_seeds(42)
        _, _, m_b = client_b.fit(get_parameters(model_b), {})

        assert m_a[ClientMetricKey.TRAIN_LOSS] == pytest.approx(m_b[ClientMetricKey.TRAIN_LOSS], abs=1e-6)
