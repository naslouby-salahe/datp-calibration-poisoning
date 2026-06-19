from __future__ import annotations

import pytest
import torch

from datp.core.enums import Activation
from datp.core.seeds import set_seeds
from datp.modeling.autoencoder import Autoencoder

# N-BaIoT reference config: 115 → 80 → 40 → 20 → 40 → 80 → 115
NBAIOT_INPUT_DIM = 115
NBAIOT_HIDDEN = [80, 40, 20]

# CICIoT2023 reference config: 39 → 32 → 16 → 8 → 16 → 32 → 39
CICIOT_INPUT_DIM = 39
CICIOT_HIDDEN = [32, 16, 8]


class TestAutoencoderShape:
    def test_forward_shape_nbaiot(self) -> None:
        model = Autoencoder(
            NBAIOT_INPUT_DIM, NBAIOT_HIDDEN, activation=Activation.RELU, use_bn=False
        )
        x = torch.randn(32, NBAIOT_INPUT_DIM)
        out = model(x)
        assert out.shape == x.shape

    def test_forward_shape_ciciot(self) -> None:
        model = Autoencoder(
            CICIOT_INPUT_DIM, CICIOT_HIDDEN, activation=Activation.RELU, use_bn=False
        )
        x = torch.randn(32, CICIOT_INPUT_DIM)
        out = model(x)
        assert out.shape == x.shape

    def test_encode_bottleneck_dim(self) -> None:
        model = Autoencoder(
            NBAIOT_INPUT_DIM, NBAIOT_HIDDEN, activation=Activation.RELU, use_bn=False
        )
        x = torch.randn(16, NBAIOT_INPUT_DIM)
        z = model.encode(x)
        assert z.shape == (16, NBAIOT_HIDDEN[-1])

    def test_bottleneck_property(self) -> None:
        model = Autoencoder(
            NBAIOT_INPUT_DIM, NBAIOT_HIDDEN, activation=Activation.RELU, use_bn=False
        )
        assert model.bottleneck_dim == 20


class TestReconstructionError:
    def test_error_shape(self) -> None:
        model = Autoencoder(
            NBAIOT_INPUT_DIM, NBAIOT_HIDDEN, activation=Activation.RELU, use_bn=False
        )
        x = torch.randn(64, NBAIOT_INPUT_DIM)
        err = model.reconstruction_error(x)
        assert err.shape == (64,)

    def test_error_nonnegative(self) -> None:
        model = Autoencoder(
            CICIOT_INPUT_DIM, CICIOT_HIDDEN, activation=Activation.RELU, use_bn=False
        )
        x = torch.randn(32, CICIOT_INPUT_DIM)
        err = model.reconstruction_error(x)
        assert (err >= 0).all()


class TestParameterCount:
    @staticmethod
    def _count_params(model: Autoencoder) -> int:
        return sum(p.numel() for p in model.parameters())

    def test_nbaiot_param_count(self) -> None:
        model = Autoencoder(
            NBAIOT_INPUT_DIM, NBAIOT_HIDDEN, activation=Activation.RELU, use_bn=False
        )
        count = self._count_params(model)
        # Spec: ~26,400 — allow ±5 % tolerance for bias terms
        assert 25_000 <= count <= 28_000, (
            f"N-BaIoT param count {count} out of expected range"
        )

    def test_ciciot_param_count(self) -> None:
        model = Autoencoder(
            CICIOT_INPUT_DIM, CICIOT_HIDDEN, activation=Activation.RELU, use_bn=False
        )
        count = self._count_params(model)
        # Spec: ~3,776
        assert 3_500 <= count <= 4_100, (
            f"CICIoT param count {count} out of expected range"
        )


class TestActivation:
    def test_relu_activation(self) -> None:
        model = Autoencoder(
            NBAIOT_INPUT_DIM, NBAIOT_HIDDEN, activation=Activation.RELU, use_bn=False
        )
        acts = [m for m in model.encoder.modules() if isinstance(m, torch.nn.ReLU)]
        assert len(acts) > 0

    def test_custom_elu(self) -> None:
        model = Autoencoder(
            NBAIOT_INPUT_DIM, NBAIOT_HIDDEN, activation=Activation.ELU, use_bn=False
        )
        acts = [m for m in model.encoder.modules() if isinstance(m, torch.nn.ELU)]
        assert len(acts) > 0

    def test_empty_hidden_dims_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            Autoencoder(NBAIOT_INPUT_DIM, [], activation=Activation.RELU, use_bn=False)


class TestBatchNormScopeGuard:
    def test_use_bn_false_has_no_batchnorm(self) -> None:
        # Canonical federated setup runs without BatchNorm: averaging BN running
        # stats across clients under FedAvg is ill-defined. Lock the BN-free path.
        model = Autoencoder(
            NBAIOT_INPUT_DIM, NBAIOT_HIDDEN, activation=Activation.RELU, use_bn=False
        )
        bn = [m for m in model.modules() if isinstance(m, torch.nn.BatchNorm1d)]
        assert bn == []

    def test_use_bn_true_inserts_batchnorm(self) -> None:
        # The gate is genuine: use_bn=False is a deliberate choice, not a model
        # that simply cannot express BatchNorm.
        model = Autoencoder(
            NBAIOT_INPUT_DIM, NBAIOT_HIDDEN, activation=Activation.RELU, use_bn=True
        )
        bn = [m for m in model.modules() if isinstance(m, torch.nn.BatchNorm1d)]
        assert len(bn) > 0



class TestLossDecreases:
    def test_loss_decreases(self) -> None:
        set_seeds(42)
        model = Autoencoder(
            NBAIOT_INPUT_DIM, NBAIOT_HIDDEN, activation=Activation.RELU, use_bn=False
        )
        optimizer = torch.optim.Adam(
            model.parameters(),
            lr=1e-3,
            betas=(0.9, 0.999),
            eps=1e-8,
            weight_decay=0.0,
        )

        # Synthetic benign data
        x = torch.randn(100, NBAIOT_INPUT_DIM)

        losses: list[float] = []
        for _ in range(10):
            optimizer.zero_grad()
            x_hat = model(x)
            loss = torch.nn.functional.mse_loss(x_hat, x)
            loss.backward()
            optimizer.step()
            losses.append(loss.item())

        assert losses[-1] < losses[0], (
            f"Loss did not decrease: epoch 1 = {losses[0]:.6f}, "
            f"epoch 10 = {losses[-1]:.6f}"
        )
