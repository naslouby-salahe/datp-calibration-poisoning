from __future__ import annotations

from datp.core.enums import Activation
from datp.modeling.autoencoder import Autoencoder


def make_cuda_validation_model() -> Autoencoder:
    return Autoencoder(
        input_dim=10,
        hidden_dims=[8, 4],
        activation=Activation.RELU,
        use_bn=False,
    )
