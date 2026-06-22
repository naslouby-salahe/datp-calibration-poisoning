from __future__ import annotations

import logging
import tempfile
import warnings
from dataclasses import dataclass

import lightning.pytorch as pl
import torch
from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint
from lightning_utilities.core import rank_zero as lightning_rank_zero
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

_TRAINING_BACKEND = "lightning"
_KEY_TRAIN_LOSS = TrackingMetricKey.TRAIN_LOSS
_KEY_VAL_LOSS = TrackingMetricKey.VAL_LOSS


def _should_log_epoch_progress(
    completed_epochs: int,
    max_epochs: int,
    *,
    interval: int,
) -> bool:
    return (
        completed_epochs == 1
        or completed_epochs == max_epochs
        or completed_epochs % interval == 0
    )


def _quiet_lightning_console_logging() -> None:
    # Suppresses Lightning console chatter while preserving datp-cp structured logs.
    for name in (
        "lightning",
        "lightning.fabric",
        "lightning.fabric.utilities.rank_zero",
        "lightning.pytorch",
        "lightning.pytorch.utilities.rank_zero",
        "lightning_utilities.core.rank_zero",
        "pytorch_lightning",
    ):
        logging.getLogger(name).setLevel(logging.WARNING)
    lightning_rank_zero.log.setLevel(logging.WARNING)


def _metric_value(metric: torch.Tensor | int | float | None) -> float | None:
    if metric is None:
        return None
    if isinstance(metric, torch.Tensor):
        return float(metric.detach().cpu().item())
    if isinstance(metric, (int, float)):
        return float(metric)
    return None


@dataclass(frozen=True, slots=True)
class _AEModuleConfig:
    """Constructor parameters for _AELightningModule."""

    lr: float
    max_epochs: int
    tracking_namespace: str | None
    training_progress_interval: int


class _AELightningModule(pl.LightningModule):
    def __init__(self, model: Autoencoder, config: _AEModuleConfig) -> None:
        super().__init__()
        self.model = model
        self.lr = config.lr
        self.max_epochs = config.max_epochs
        self.tracking_namespace = config.tracking_namespace
        self.training_progress_interval = config.training_progress_interval
        self.completed_epochs = 0

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.model(x)

    def _compute_loss(
        self, batch: tuple[torch.Tensor], log_key: TrackingMetricKey
    ) -> torch.Tensor:
        x = batch[0]
        loss = self.model.reconstruction_loss(x)
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
        return self._compute_loss(batch, _KEY_TRAIN_LOSS)

    def validation_step(
        self, batch: tuple[torch.Tensor], _batch_idx: int
    ) -> torch.Tensor:
        return self._compute_loss(batch, _KEY_VAL_LOSS)

    def on_train_epoch_end(self) -> None:
        self.completed_epochs += 1
        payload = {
            _KEY_TRAIN_LOSS: _metric_value(
                self.trainer.callback_metrics.get(_KEY_TRAIN_LOSS.value)
            ),
            _KEY_VAL_LOSS: _metric_value(
                self.trainer.callback_metrics.get(_KEY_VAL_LOSS.value)
            ),
        }
        if _should_log_epoch_progress(
            self.completed_epochs,
            self.max_epochs,
            interval=self.training_progress_interval,
        ):
            logger.info(
                "ae training epoch complete",
                backend=_TRAINING_BACKEND,
                epoch=self.completed_epochs,
                max_epochs=self.max_epochs,
                train_loss=payload[_KEY_TRAIN_LOSS],
                val_loss=payload[_KEY_VAL_LOSS],
            )
        if self.tracking_namespace is None:
            return
        log_metrics(
            TrackingMetrics(
                tuple(
                    TrackingMetric(key, value)
                    for key, value in payload.items()
                    if value is not None
                )
            ),
            step=self.completed_epochs,
            prefix=self.tracking_namespace,
        )

    def configure_optimizers(self) -> torch.optim.Optimizer:
        return torch.optim.Adam(self.model.parameters(), lr=self.lr, weight_decay=0.0)


def _build_data_loaders(
    train_tensor: torch.Tensor,
    val_tensor: torch.Tensor,
    batch_size: int,
    device: torch.device,
) -> tuple[DataLoader, DataLoader]:
    pin_memory = device.type == DeviceType.CUDA
    train_loader = DataLoader(
        TensorDataset(train_tensor.detach().cpu()),
        batch_size=batch_size,
        shuffle=True,
        pin_memory=pin_memory,
        num_workers=0,
        persistent_workers=False,
    )
    val_loader = DataLoader(
        TensorDataset(val_tensor.detach().cpu()),
        batch_size=max(1, min(batch_size, len(val_tensor))),
        shuffle=False,
        pin_memory=pin_memory,
        num_workers=0,
        persistent_workers=False,
    )
    return train_loader, val_loader


def _suppress_lightning_warnings() -> None:
    warnings.filterwarnings(
        "ignore",
        message=".*does not have many workers.*",
        category=UserWarning,
    )
    warnings.filterwarnings(
        "ignore",
        message=".*isinstance.*LeafSpec.*deprecated.*",
        category=DeprecationWarning,
    )
    warnings.filterwarnings(
        "ignore",
        message=".*LeafSpec.*deprecated.*",
        category=FutureWarning,
    )


def _run_lightning_training(
    lightning_module: _AELightningModule,
    train_loader: DataLoader,
    val_loader: DataLoader,
    epochs: int,
    patience: int,
    device: torch.device,
    tmp_dir: str,
) -> ModelCheckpoint:
    checkpoint_callback = ModelCheckpoint(
        dirpath=tmp_dir,
        monitor=_KEY_VAL_LOSS.value,
        mode="min",
        save_top_k=1,
        save_weights_only=False,
    )
    early_stopping = EarlyStopping(
        monitor=_KEY_VAL_LOSS.value,
        mode="min",
        patience=patience,
        min_delta=0.0,
    )
    trainer = pl.Trainer(
        accelerator="gpu" if device.type == DeviceType.CUDA else DeviceType.CPU,
        devices=1,
        deterministic=True,
        max_epochs=epochs,
        logger=False,
        enable_progress_bar=False,
        enable_model_summary=False,
        enable_checkpointing=True,
        callbacks=[early_stopping, checkpoint_callback],
        default_root_dir=tmp_dir,
        num_sanity_val_steps=0,
    )
    trainer.fit(
        lightning_module, train_dataloaders=train_loader, val_dataloaders=val_loader
    )
    return checkpoint_callback


@dataclass(frozen=True, slots=True)
class TrainAEConfig:
    """Hyperparameters and runtime options for train_ae."""

    epochs: int
    patience: int
    lr: float
    batch_size: int
    tracking_namespace: str | None
    training_progress_interval: int


def _restore_best_checkpoint(
    lightning_module: _AELightningModule,
    checkpoint_callback: ModelCheckpoint,
) -> None:
    if not checkpoint_callback.best_model_path:
        return
    checkpoint = torch.load(
        checkpoint_callback.best_model_path,
        map_location=DeviceType.CPU,
        weights_only=True,
    )
    lightning_module.load_state_dict(checkpoint["state_dict"])


def _log_training_summary(
    epochs_run: int,
    best_val_loss: float | None,
    tracking_namespace: str | None,
) -> None:
    if tracking_namespace is None:
        return
    summary_metrics = [TrackingMetric(TrackingMetricKey.EPOCHS_RUN, epochs_run)]
    if best_val_loss is not None:
        summary_metrics.append(
            TrackingMetric(TrackingMetricKey.BEST_VAL_LOSS, best_val_loss)
        )
    log_metrics(
        TrackingMetrics(tuple(summary_metrics)),
        step=epochs_run,
        prefix=tracking_namespace,
    )


def train_ae(
    model: Autoencoder,
    train_tensor: torch.Tensor,
    val_tensor: torch.Tensor,
    device: torch.device,
    config: TrainAEConfig,
) -> tuple[Autoencoder, int]:
    logger.info(
        "starting ae training",
        backend=_TRAINING_BACKEND,
        epochs=config.epochs,
        patience=config.patience,
        batch_size=config.batch_size,
        device=str(device),
    )

    train_loader, val_loader = _build_data_loaders(
        train_tensor, val_tensor, config.batch_size, device
    )
    _suppress_lightning_warnings()
    _quiet_lightning_console_logging()

    lightning_module = _AELightningModule(
        model=model.cpu(),
        config=_AEModuleConfig(
            lr=config.lr,
            max_epochs=config.epochs,
            tracking_namespace=config.tracking_namespace,
            training_progress_interval=config.training_progress_interval,
        ),
    )

    with tempfile.TemporaryDirectory(prefix="datp_lightning_") as tmp_dir:
        checkpoint_callback = _run_lightning_training(
            lightning_module,
            train_loader,
            val_loader,
            config.epochs,
            config.patience,
            device,
            tmp_dir,
        )
        _restore_best_checkpoint(lightning_module, checkpoint_callback)

    best_val_loss = _metric_value(checkpoint_callback.best_model_score)
    epochs_run = lightning_module.completed_epochs
    _log_training_summary(epochs_run, best_val_loss, config.tracking_namespace)

    logger.info(
        "ae training complete",
        backend=_TRAINING_BACKEND,
        epochs_run=epochs_run,
        best_val_loss=best_val_loss,
    )
    return lightning_module.model.to(device), epochs_run
