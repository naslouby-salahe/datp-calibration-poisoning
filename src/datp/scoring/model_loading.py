from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import torch

from datp.artifacts.names import ArtifactFile
from datp.core.device import resolve_device
from datp.core.errors import fmt
from datp.core.logging import get_logger
from datp.modeling.autoencoder import Autoencoder

if TYPE_CHECKING:
    from datp.config.models import DatpConfig

logger = get_logger(__name__)
_MODULE = "scoring.model_loading"


def load_model_from_checkpoint(
    cfg: "DatpConfig",
    *,
    ckpt_dir: Path,
    require_cuda: bool,
) -> Autoencoder:
    ckpt_file = ckpt_dir / ArtifactFile.MODEL_CHECKPOINT
    if not ckpt_file.exists():
        raise FileNotFoundError(
            fmt(_MODULE, "Checkpoint missing", str(ckpt_file), "missing file")
        )

    model = Autoencoder(
        input_dim=cfg.model.input_dim,
        hidden_dims=cfg.model.encoder_dims,
        activation=cfg.model.activation,
        use_bn=cfg.model.use_bn,
    )
    device = resolve_device(require_cuda)
    state_dict = torch.load(ckpt_file, map_location=device, weights_only=True)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    logger.info("loaded checkpoint", path=str(ckpt_file), device=str(device))
    return model
