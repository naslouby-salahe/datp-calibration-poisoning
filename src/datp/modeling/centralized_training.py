"""Centralized autoencoder training via PyTorch Lightning with early stopping."""

from __future__ import annotations

import logging
import tempfile
import warnings
from dataclasses import dataclass

import lightning.pytorch as pl
import torch
from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint
from torch.utils.data import DataLoader, TensorDataset

from datp.core.enums import DeviceType
from datp.core.logging import get_logger
from datp.core.tracking import (
    TrackingMetric,
    TrackingMetricKey,
    TrackingMetrics,
    log_metrics,
)
from datp.modeling.autoencoder import Autoencoder

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class TrainAEConfig:
    """Hyperparameters and runtime options for centralized AE training."""

    epochs: int
    patience: int
    lr: float
    batch_size: int
    tracking_namespace: str | None
    training_progress_interval: int


class _AELightningModule(pl.LightningModule):
    """Lightning wrapper for AE training with per-epoch logging."""

    def __init__(self, model: Autoencoder, config: TrainAEConfig) -> None:
        super().__init__()
        self.model = model
        self.config = config
        self.completed_epochs = 0

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Delegate forward pass to the wrapped autoencoder."""
        return self.model(x)

    def _compute_loss(
        self, batch: tuple[torch.Tensor], log_key: TrackingMetricKey
    ) -> torch.Tensor:
        """Compute reconstruction loss and log it under the given metric key."""
        loss = self.model.reconstruction_loss(batch[0])
        self.log(
            log_key.value,
            loss,
            on_step=False,
            on_epoch=True,
            prog_bar=False,
            logger=False,
        )
        return loss

    def training_step(
        self, batch: tuple[torch.Tensor], _batch_idx: int
    ) -> torch.Tensor:
        """Single training step: compute and log train loss."""
        return self._compute_loss(batch, TrackingMetricKey.TRAIN_LOSS)

    def validation_step(
        self, batch: tuple[torch.Tensor], _batch_idx: int
    ) -> torch.Tensor:
        """Single validation step: compute and log validation loss."""
        return self._compute_loss(batch, TrackingMetricKey.VAL_LOSS)

    def on_train_epoch_end(self) -> None:
        """Log progress at configured intervals and after the last epoch."""
        self.completed_epochs += 1
        metrics = self.trainer.callback_metrics
        t_loss = metrics.get(TrackingMetricKey.TRAIN_LOSS.value)
        v_loss = metrics.get(TrackingMetricKey.VAL_LOSS.value)

        t_val = float(t_loss.item()) if t_loss is not None else None
        v_val = float(v_loss.item()) if v_loss is not None else None

        if (
            self.completed_epochs in (1, self.config.epochs)
            or self.completed_epochs % self.config.training_progress_interval == 0
        ):
            logger.info(
                "ae training epoch complete",
                backend="lightning",
                epoch=self.completed_epochs,
                max_epochs=self.config.epochs,
                train_loss=t_val,
                val_loss=v_val,
            )

        if self.config.tracking_namespace and t_val is not None and v_val is not None:
            log_metrics(
                TrackingMetrics(
                    (
                        TrackingMetric(TrackingMetricKey.TRAIN_LOSS, t_val),
                        TrackingMetric(TrackingMetricKey.VAL_LOSS, v_val),
                    )
                ),
                step=self.completed_epochs,
                prefix=self.config.tracking_namespace,
            )

    def configure_optimizers(self) -> torch.optim.Optimizer:
        """Return an Adam optimizer with the configured learning rate."""
        return torch.optim.Adam(
            self.model.parameters(), lr=self.config.lr, weight_decay=0.0
        )


def train_ae(
    model: Autoencoder,
    train_tensor: torch.Tensor,
    val_tensor: torch.Tensor,
    device: torch.device,
    config: TrainAEConfig,
) -> tuple[Autoencoder, int]:
    """Train an autoencoder centrally via PyTorch Lightning with early stopping."""
    logger.info(
        "starting ae training",
        backend="lightning",
        epochs=config.epochs,
        patience=config.patience,
        batch_size=config.batch_size,
        device=str(device),
    )

    warnings.filterwarnings("ignore")
    for name in ("lightning", "pytorch_lightning", "lightning_utilities"):
        logging.getLogger(name).setLevel(logging.ERROR)

    pin = device.type == DeviceType.CUDA
    loader_kwargs = {"pin_memory": pin, "num_workers": 0, "persistent_workers": False}

    train_loader = DataLoader(
        TensorDataset(train_tensor.detach().cpu()),
        batch_size=config.batch_size,
        shuffle=True,
        **loader_kwargs,
    )
    val_loader = DataLoader(
        TensorDataset(val_tensor.detach().cpu()),
        batch_size=max(1, min(config.batch_size, len(val_tensor))),
        shuffle=False,
        **loader_kwargs,
    )

    lightning_module = _AELightningModule(model.cpu(), config)

    with tempfile.TemporaryDirectory(prefix="datp_lightning_") as tmp_dir:
        ckpt_cb = ModelCheckpoint(
            dirpath=tmp_dir,
            monitor=TrackingMetricKey.VAL_LOSS.value,
            mode="min",
            save_top_k=1,
        )
        trainer = pl.Trainer(
            accelerator="gpu" if pin else "cpu",
            devices=1,
            deterministic=True,
            max_epochs=config.epochs,
            logger=False,
            enable_progress_bar=False,
            enable_model_summary=False,
            callbacks=[
                EarlyStopping(
                    monitor=TrackingMetricKey.VAL_LOSS.value,
                    mode="min",
                    patience=config.patience,
                ),
                ckpt_cb,
            ],
            default_root_dir=tmp_dir,
            num_sanity_val_steps=0,
        )
        trainer.fit(
            lightning_module, train_dataloaders=train_loader, val_dataloaders=val_loader
        )

        if ckpt_cb.best_model_path:
            lightning_module.load_state_dict(
                torch.load(
                    ckpt_cb.best_model_path,
                    map_location=DeviceType.CPU,
                    weights_only=True,
                )["state_dict"]
            )

    best_loss = (
        float(ckpt_cb.best_model_score.item())
        if ckpt_cb.best_model_score is not None
        else None
    )

    if config.tracking_namespace:
        summary = [
            TrackingMetric(
                TrackingMetricKey.EPOCHS_RUN, lightning_module.completed_epochs
            )
        ]
        if best_loss is not None:
            summary.append(TrackingMetric(TrackingMetricKey.BEST_VAL_LOSS, best_loss))
        log_metrics(
            TrackingMetrics(tuple(summary)),
            step=lightning_module.completed_epochs,
            prefix=config.tracking_namespace,
        )

    logger.info(
        "ae training complete",
        backend="lightning",
        epochs_run=lightning_module.completed_epochs,
        best_val_loss=best_loss,
    )

    return lightning_module.model.to(device), lightning_module.completed_epochs
