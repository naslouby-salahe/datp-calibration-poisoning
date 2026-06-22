from __future__ import annotations

import numpy as np
import torch

from datp.modeling.autoencoder import Autoencoder


def compute_reconstruction_errors(
    model: Autoencoder, data: torch.Tensor, batch_size: int | None = None
) -> np.ndarray:
    effective_batch = batch_size if batch_size is not None else data.shape[0]
    model.eval()
    n = data.shape[0]
    if n == 0:
        return np.array([], dtype=np.float32)
    all_errors: list[np.ndarray] = []
    with torch.inference_mode():
        for start in range(0, n, effective_batch):
            batch = data[start : start + effective_batch]
            errors = model.reconstruction_error(batch)
            all_errors.append(errors.cpu().numpy().astype(np.float32))
    return np.concatenate(all_errors)
