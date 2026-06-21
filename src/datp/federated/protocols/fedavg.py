# SPDX-License-Identifier: Proprietary
"""FedAvg protocol entry point: train AE via FedAvg and produce score artifacts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from datp.artifacts.layout import ArtifactLayout
from datp.core.errors import fmt
from datp.core.identity import TrainingCellId
from datp.federated.simulation import run_fl_simulation, validate_stage

if TYPE_CHECKING:
    from pathlib import Path

    from datp.config.models import DatpConfig
    from datp.federated.simulation import TrainingResult
    from datp.federated.types import ClientData

_MODULE = "federated.protocols.fedavg"


def run_fl_training(
    cfg: DatpConfig,
    client_data: dict[str, ClientData],
    seed: int,
    *,
    base_dir: Path | None = None,
    prepared_dir: Path | None = None,
    output_layout: ArtifactLayout | None = None,
) -> TrainingResult:
    """Train AE via FedAvg and produce score artifacts (main FL entry point)."""
    stage = validate_stage(cfg)
    if output_layout is not None:
        layout = output_layout
    elif base_dir is not None:
        layout = ArtifactLayout(base_dir=base_dir, stage=stage)
    else:
        raise ValueError(
            fmt(
                _MODULE,
                "base_dir or output_layout required",
                "non-null base_dir or output_layout",
                f"base_dir={base_dir}, output_layout={output_layout}",
            )
        )

    cell = TrainingCellId(stage=stage, seed=seed)
    return run_fl_simulation(
        cfg,
        client_data,
        seed,
        model_cls=__import__(
            "datp.modeling.autoencoder", fromlist=["Autoencoder"]
        ).Autoencoder,
        ckpt_dir=layout.checkpoint_dir(cell),
        score_base=layout.score_cell(cell).score_dir,
        label="FL",
        prepared_dir=prepared_dir,
    )
