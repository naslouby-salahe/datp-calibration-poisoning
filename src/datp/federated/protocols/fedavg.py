"""Entry point for running FedAvg FL training with artifact layout support."""

from __future__ import annotations

from typing import TYPE_CHECKING

from datp.artifacts.layout import ArtifactLayout
from datp.core.identity import TrainingCellId
from datp.federated.simulation import (
    FlSimulationRequest,
    run_fl_simulation,
    validate_stage,
)

if TYPE_CHECKING:
    from pathlib import Path

    from datp.config.models import DatpConfig
    from datp.federated.simulation import TrainingResult
    from datp.federated.types import ClientData


def run_fl_training(
    cfg: DatpConfig,
    client_data: dict[str, ClientData],
    seed: int,
    *,
    base_dir: Path | None = None,
    prepared_dir: Path | None = None,
    output_layout: ArtifactLayout | None = None,
) -> TrainingResult:
    """Run FedAvg federated training with automatic artifact-layout routing."""
    stage = validate_stage(cfg)
    if output_layout is not None:
        layout = output_layout
    elif base_dir is not None:
        layout = ArtifactLayout(base_dir=base_dir, stage=stage)
    else:
        raise ValueError("base_dir or output_layout required")

    cell = TrainingCellId(stage=stage, seed=seed)
    model_cls = __import__(
        "datp.modeling.autoencoder", fromlist=["Autoencoder"]
    ).Autoencoder

    return run_fl_simulation(
        FlSimulationRequest(
            cfg=cfg,
            client_data=client_data,
            seed=seed,
            model_cls=model_cls,
            ckpt_dir=layout.checkpoint_dir(cell),
            score_base=layout.score_cell(cell).score_dir,
            label="FL",
            prepared_dir=prepared_dir,
        )
    )
