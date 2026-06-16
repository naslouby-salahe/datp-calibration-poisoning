from __future__ import annotations

import logging

import pytest
import torch
from lightning_utilities.core import rank_zero as lightning_rank_zero

from datp.core.enums import Activation, DeviceType
from datp.modeling.autoencoder import Autoencoder
from datp.modeling.centralized_training import (
    _AELightningModule,
    _metric_value,
    _quiet_lightning_console_logging,
    _should_log_epoch_progress,
)


@pytest.mark.parametrize(
    ("completed_epochs", "max_epochs", "expected"),
    [
        (1, 200, True),
        (2, 200, False),
        (10, 200, True),
        (19, 200, False),
        (20, 200, True),
        (37, 37, True),
    ],
)
def test_should_log_epoch_progress_cadence(
    completed_epochs: int,
    max_epochs: int,
    expected: bool,
) -> None:
    assert (
        _should_log_epoch_progress(completed_epochs, max_epochs, interval=10)
        is expected
    )


def test_quiet_lightning_console_logging_sets_rank_zero_warning_level() -> None:
    lightning_rank_zero.log.setLevel(logging.INFO)

    _quiet_lightning_console_logging()

    assert lightning_rank_zero.log.level == logging.WARNING


class TestMetricValue:
    def test_none_returns_none(self) -> None:
        assert _metric_value(None) is None

    def test_int_returns_float(self) -> None:
        assert _metric_value(42) == 42.0

    def test_float_returns_float(self) -> None:
        assert _metric_value(3.14) == 3.14

    def test_tensor_returns_float(self) -> None:
        t = torch.tensor(2.718, requires_grad=True)
        result = _metric_value(t)
        assert isinstance(result, float)
        assert result == pytest.approx(2.718)

    def test_cuda_tensor_detaches_and_moves_to_cpu(self) -> None:
        if not torch.cuda.is_available():
            pytest.skip("CUDA not available")
        t = torch.tensor(1.0, device=DeviceType.CUDA, requires_grad=True)
        result = _metric_value(t)
        assert isinstance(result, float)
        assert result == 1.0

    def test_unknown_type_returns_none(self) -> None:
        assert _metric_value("not a metric") is None # type: ignore[arg-type]


class TestAELightningModule:
    @staticmethod
    def _dummy_model() -> Autoencoder:
        return Autoencoder(
            input_dim=8,
            hidden_dims=[4, 2],
            activation=Activation.RELU,
            use_bn=False,
        )

    def test_construction(self) -> None:
        model = self._dummy_model()
        lm = _AELightningModule(
            model=model,
            lr=0.001,
            max_epochs=10,
            tracking_namespace=None,
            training_progress_interval=5,
        )
        assert lm.model is model
        assert lm.lr == 0.001
        assert lm.max_epochs == 10
        assert lm.completed_epochs == 0

    def test_forward_delegates_to_model(self) -> None:
        model = self._dummy_model()
        lm = _AELightningModule(
            model=model,
            lr=0.001,
            max_epochs=10,
            tracking_namespace=None,
            training_progress_interval=5,
        )
        x = torch.randn(4, 8)
        out = lm(x)
        assert out.shape == (4, 8)

    def test_configure_optimizers_returns_adam(self) -> None:
        model = self._dummy_model()
        lm = _AELightningModule(
            model=model,
            lr=0.001,
            max_epochs=10,
            tracking_namespace=None,
            training_progress_interval=5,
        )
        opt = lm.configure_optimizers()
        assert isinstance(opt, torch.optim.Adam)
        assert opt.defaults["lr"] == 0.001
        assert opt.defaults["weight_decay"] == 0.0
