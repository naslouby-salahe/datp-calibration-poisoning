# SPDX-License-Identifier: Proprietary
"""Checkpoint persistence: atomic writes for model state and convergence artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from flwr.common import NDArrays

from datp.artifacts.names import ArtifactFile
from datp.checkpointing.enums import ConvergenceStatus, ConvergenceSummaryKey
from datp.config.models import ConvergenceConfig
from datp.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ConvergenceSnapshot:
    """Bundled convergence state ready for serialization."""

    loss_history: list[float]
    converged_round: int | None
    criterion_value: float | None


def save_checkpoint(model: nn.Module, ckpt_dir: Path) -> Path:
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    ckpt_file = ckpt_dir / ArtifactFile.MODEL_CHECKPOINT

    tmp_file = ckpt_file.with_suffix(".pt.tmp")
    torch.save(model.state_dict(), tmp_file)
    tmp_file.rename(ckpt_file)

    logger.info("checkpoint saved", path=str(ckpt_file))
    return ckpt_file


def save_params_snapshot(params: NDArrays, ckpt_dir: Path) -> Path:
    """Atomically persist raw FL parameters as a numpy archive for crash resilience.

    Written at each milestone round so a mid-training reboot does not lose progress.
    The file is consumed by :func:`load_params_snapshot` during crash recovery before
    the final model.pt reconstruction step in ``_save_checkpoint_protocol_artifacts``.
    """
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    snap_file = ckpt_dir / ArtifactFile.PARAMS_SNAPSHOT
    tmp_file = (
        ckpt_dir / "params_writing.npz"
    )  # .npz suffix prevents numpy appending a second one
    np.savez(str(tmp_file), *params)
    tmp_file.rename(snap_file)
    logger.info("params snapshot saved", path=str(snap_file), n_arrays=len(params))
    return snap_file


def load_params_snapshot(ckpt_dir: Path) -> NDArrays | None:
    """Load raw FL parameters saved by :func:`save_params_snapshot`, or return None."""
    snap_file = ckpt_dir / ArtifactFile.PARAMS_SNAPSHOT
    if not snap_file.exists():
        return None
    archive = np.load(str(snap_file))
    params: NDArrays = [archive[k] for k in sorted(archive.files)]
    logger.info("params snapshot loaded", path=str(snap_file), n_arrays=len(params))
    return params


def save_convergence_artifacts(
    ckpt_dir: Path,
    snapshot: ConvergenceSnapshot,
    conv_cfg: ConvergenceConfig,
) -> None:
    curve_path = ckpt_dir / ArtifactFile.CONVERGENCE_CURVE
    summary_path = ckpt_dir / ArtifactFile.CONVERGENCE_SUMMARY

    rows = [
        {"round": index, "fedavg_weighted_benign_val_loss": loss}
        for index, loss in enumerate(snapshot.loss_history, start=1)
    ]
    df = pd.DataFrame(rows)

    curve_tmp = curve_path.with_suffix(".csv.tmp")
    summary_tmp = summary_path.with_suffix(".json.tmp")

    df.to_csv(curve_tmp, index=False)
    summary_tmp.write_text(
        json.dumps(
            {
                ConvergenceSummaryKey.ROUNDS_INITIAL: conv_cfg.rounds_initial,
                ConvergenceSummaryKey.ROUNDS_MAX: conv_cfg.rounds_max,
                ConvergenceSummaryKey.RELATIVE_THRESHOLD: conv_cfg.relative_threshold,
                ConvergenceSummaryKey.WINDOW: conv_cfg.window,
                ConvergenceSummaryKey.ACTUAL_ROUNDS: len(snapshot.loss_history),
                ConvergenceSummaryKey.CONVERGENCE_ROUND: snapshot.converged_round,
                ConvergenceSummaryKey.CONVERGENCE_CRITERION: snapshot.criterion_value,
                ConvergenceSummaryKey.CONVERGENCE_STATUS: ConvergenceStatus.CONVERGED
                if snapshot.converged_round is not None
                else ConvergenceStatus.NOT_CONVERGED,
                ConvergenceSummaryKey.WEIGHTED_LOSS: snapshot.loss_history,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    curve_tmp.rename(curve_path)
    summary_tmp.rename(summary_path)

    logger.info(
        "convergence artifacts saved",
        curve=str(curve_path),
        summary=str(summary_path),
        rounds=len(snapshot.loss_history),
    )
