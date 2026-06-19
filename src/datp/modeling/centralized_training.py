from __future__ import annotations

import logging
import tempfile
import warnings

import lightning.pytorch as pl
import torch
from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint
from lightning_utilities.core import rank_zero as lightning_rank_zero
from torch.utils.data import DataLoader, TensorDataset

from datp.core.enums import DeviceType
from datp.core.logging import get_logger
from datp.core.tracking import log_metrics
from datp.modeling.autoencoder import Autoencoder

logger = get_logger(__name__)

_TRAINING_BACKEND = "lightning"
_KEY_TRAIN_LOSS = "train_loss"
_KEY_VAL_LOSS = "val_loss"


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
    # Suppresses Lightning console chatter while preserving DATP structured logs.
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


class _AELightningModule(pl.LightningModule):
    def __init__(
        self,
        model: Autoencoder,
        *,
        lr: float,
        max_epochs: int,
        tracking_namespace: str | None,
        training_progress_interval: int,
    ) -> None:
        super().__init__()
        self.model = model
        self.lr = lr
        self.max_epochs = max_epochs
        self.tracking_namespace = tracking_namespace
        self.training_progress_interval = training_progress_interval
        self.completed_epochs = 0

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.model(x)

    def training_step(
        self, batch: tuple[torch.Tensor], _batch_idx: int
    ) -> torch.Tensor:
        x = batch[0]
        loss = self.model.reconstruction_loss(x)
        self.log(
            _KEY_TRAIN_LOSS,
            loss,
            on_step=False,
            on_epoch=True,
            prog_bar=False,
            logger=False,
        )
        return loss

    def validation_step(
        self, batch: tuple[torch.Tensor], _batch_idx: int
    ) -> torch.Tensor:
        x = batch[0]
        loss = self.model.reconstruction_loss(x)
        self.log(
            _KEY_VAL_LOSS,
            loss,
            on_step=False,
            on_epoch=True,
            prog_bar=False,
            logger=False,
        )
        return loss

    def on_train_epoch_end(self) -> None:
        self.completed_epochs += 1
        payload = {
            _KEY_TRAIN_LOSS: _metric_value(
                self.trainer.callback_metrics.get(_KEY_TRAIN_LOSS)
            ),
            _KEY_VAL_LOSS: _metric_value(
                self.trainer.callback_metrics.get(_KEY_VAL_LOSS)
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
            {key: value for key, value in payload.items() if value is not None},
            step=self.completed_epochs,
            prefix=self.tracking_namespace,
        )

    def configure_optimizers(self) -> torch.optim.Optimizer:
        return torch.optim.Adam(self.model.parameters(), lr=self.lr, weight_decay=0.0)


def train_ae(
    model: Autoencoder,
    train_tensor: torch.Tensor,
    val_tensor: torch.Tensor,
    epochs: int,
    patience: int,
    lr: float,
    batch_size: int,
    device: torch.device,
    *,
    tracking_namespace: str | None,
    training_progress_interval: int,
) -> tuple[Autoencoder, int]:
    logger.info(
        "starting ae training",
        backend=_TRAINING_BACKEND,
        epochs=epochs,
        patience=patience,
        batch_size=batch_size,
        device=str(device),
    )

    # num_workers=0: in-memory TensorDataset — workers add overhead, not throughput.
    _pin_memory = device.type == DeviceType.CUDA
    train_loader = DataLoader(
        TensorDataset(train_tensor.detach().cpu()),
        batch_size=batch_size,
        shuffle=True,
        pin_memory=_pin_memory,
        num_workers=0,
        persistent_workers=False,
    )
    val_loader = DataLoader(
        TensorDataset(val_tensor.detach().cpu()),
        batch_size=max(1, min(batch_size, len(val_tensor))),
        shuffle=False,
        pin_memory=_pin_memory,
        num_workers=0,
        persistent_workers=False,
    )
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
    _quiet_lightning_console_logging()

    lightning_module = _AELightningModule(
        model=model.cpu(),
        lr=lr,
        max_epochs=epochs,
        tracking_namespace=tracking_namespace,
        training_progress_interval=training_progress_interval,
    )

    with tempfile.TemporaryDirectory(prefix="datp_lightning_") as tmp_dir:
        checkpoint_callback = ModelCheckpoint(
            dirpath=tmp_dir,
            monitor=_KEY_VAL_LOSS,
            mode="min",
            save_top_k=1,
            save_weights_only=False,
        )
        early_stopping = EarlyStopping(
            monitor=_KEY_VAL_LOSS,
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

        if checkpoint_callback.best_model_path:
            checkpoint = torch.load(
                checkpoint_callback.best_model_path,
                map_location=DeviceType.CPU,
                weights_only=True,
            )
            lightning_module.load_state_dict(checkpoint["state_dict"])

    best_val_loss = _metric_value(checkpoint_callback.best_model_score)
    epochs_run = lightning_module.completed_epochs
    if tracking_namespace is not None:
        summary_metrics = {"epochs_run": float(epochs_run)}
        if best_val_loss is not None:
            summary_metrics["best_val_loss"] = best_val_loss
        log_metrics(summary_metrics, step=epochs_run, prefix=tracking_namespace)

    logger.info(
        "ae training complete",
        backend=_TRAINING_BACKEND,
        epochs_run=epochs_run,
        best_val_loss=best_val_loss,
    )
    return lightning_module.model.to(device), epochs_run
