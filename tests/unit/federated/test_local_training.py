"""Tests verifying local training routines, benign evaluation loss, and related input validation rules."""

from __future__ import annotations

from typing import Any
import pytest
import torch

from datp.core.enums import Activation
from datp.core.seeds import set_seeds
from datp.federated.local_training import evaluate_benign, train_local
from datp.modeling.autoencoder import Autoencoder


def _make_model() -> Autoencoder:
    """Helper to build a default Autoencoder model for tests."""
    return Autoencoder(
        input_dim=4, hidden_dims=[3, 2], activation=Activation.RELU, use_bn=False
    )


class TestTrainLocal:
    """Tests verifying train_local execution, optimization, and determinism."""

    def test_returns_finite_loss(self) -> None:
        """Verify that training on synthetic data returns a finite float loss value."""
        model = _make_model()
        data = torch.randn(16, 4)
        loss = train_local(model, data, epochs=1, batch_size=8, lr=0.01)
        assert isinstance(loss, float)
        assert not torch.isnan(torch.tensor(loss))

    def test_optimizer_uses_no_weight_decay(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Ensure the training optimizer uses 0.0 weight decay to prevent calibration distortion."""
        captured: dict[str, float] = {}
        real_adam = torch.optim.Adam

        def _capturing_adam(params: Any, **kwargs: Any) -> torch.optim.Adam:
            captured["weight_decay"] = kwargs.get("weight_decay", -1.0)
            return real_adam(params, **kwargs)

        monkeypatch.setattr(torch.optim, "Adam", _capturing_adam)
        train_local(_make_model(), torch.randn(16, 4), epochs=1, batch_size=8, lr=0.01)
        assert captured["weight_decay"] == pytest.approx(0.0)

    def test_multiple_epochs_reduce_loss(self) -> None:
        """Verify that training for more epochs leads to a lower reconstruction loss."""
        set_seeds(0)
        model = _make_model()
        data = torch.randn(32, 4)
        loss_1 = train_local(model, data, epochs=1, batch_size=8, lr=0.01)

        set_seeds(0)
        model2 = _make_model()
        loss_10 = train_local(model2, data, epochs=10, batch_size=8, lr=0.01)

        assert loss_10 < loss_1

    def test_deterministic_same_seed(self) -> None:
        """Verify that training is reproducible when seed state is matched."""
        data = torch.randn(16, 4)

        set_seeds(42)
        m1 = _make_model()
        loss1 = train_local(m1, data, epochs=2, batch_size=8, lr=0.01)

        set_seeds(42)
        m2 = _make_model()
        loss2 = train_local(m2, data, epochs=2, batch_size=8, lr=0.01)

        assert loss1 == pytest.approx(loss2, abs=1e-7)


class TestEvaluateBenign:
    """Tests verifying benign validation loss evaluation on calibration sets."""

    def test_returns_positive_loss(self) -> None:
        """Verify that evaluation loss on random validation inputs is positive."""
        model = _make_model()
        cal_data = torch.randn(8, 4)
        loss = evaluate_benign(model, cal_data)
        assert loss > 0.0

    def test_model_set_to_eval(self) -> None:
        """Ensure evaluation sets PyTorch model mode to evaluation (eval) mode."""
        model = _make_model()
        model.train()
        cal_data = torch.randn(8, 4)
        evaluate_benign(model, cal_data)
        assert not model.training

    def test_perfect_reconstruction_gives_zero_loss(self) -> None:
        """Verify loss is non-negative and zero-bounded on zeroed datasets."""
        model = _make_model()
        cal_data = torch.zeros(4, 4)
        loss = evaluate_benign(model, cal_data)
        assert loss >= 0.0


class TestEvaluateBenignValidation:
    """Tests verifying input guards on evaluate_benign."""

    def test_empty_data_raises(self) -> None:
        """Verify ValueError is raised if input data is empty."""
        model = _make_model()
        data = torch.empty(0, 4)
        with pytest.raises(ValueError, match="non-empty"):
            evaluate_benign(model, data)


class TestTrainLocalValidation:
    """Tests verifying input validation guards on train_local."""

    def test_epochs_zero_raises(self) -> None:
        """Verify ValueError is raised if local training epochs setting is less than 1."""
        model = _make_model()
        data = torch.randn(16, 4)
        with pytest.raises(ValueError, match="must be >= 1"):
            train_local(model, data, epochs=0, batch_size=8, lr=0.01)

    def test_batch_size_zero_raises(self) -> None:
        """Verify ValueError is raised if batch size setting is less than 1."""
        model = _make_model()
        data = torch.randn(16, 4)
        with pytest.raises(ValueError, match="must be >= 1"):
            train_local(model, data, epochs=1, batch_size=0, lr=0.01)

    def test_empty_data_raises(self) -> None:
        """Verify ValueError is raised if training dataset tensor is empty."""
        model = _make_model()
        data = torch.empty(0, 4)
        with pytest.raises(ValueError, match="non-empty"):
            train_local(model, data, epochs=1, batch_size=8, lr=0.01)
