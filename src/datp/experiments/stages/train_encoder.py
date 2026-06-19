from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from filelock import FileLock, Timeout

from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactFile
from datp.config.models import CheckpointProtocolConfig
from datp.core.enums import DeviceType
from datp.core.errors import fmt, fmt_missing
from datp.core.logging import get_logger
from datp.experiments.enums import SweepStep
from datp.experiments.models import PipelineRequest

logger = get_logger(__name__)
_MODULE = "experiments.stages.train_encoder"


def ensure_fl_checkpoint(
    request: PipelineRequest,
    *,
    step_fn: Callable[[SweepStep, str], None] | None,
    checkpoint_status_fn: Callable[[bool, Path], None] | None,
    lock_timeout: float,
) -> None:
    """Run FL training iff the shared checkpoint is missing; holds a per-checkpoint-directory file lock to prevent duplicate training across parallel sweep processes."""
    key = request.key
    layout = ArtifactLayout(base_dir=request.base_dir, regime=key.regime)
    ckpt_dir = layout.checkpoint_dir(key)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    ckpt_file = ckpt_dir / ArtifactFile.MODEL_CHECKPOINT

    alpha_label = f" alpha={key.alpha:g}" if key.alpha is not None else ""
    label = f"regime={key.regime} seed={key.seed}{alpha_label}"

    if step_fn is not None:
        step_fn(SweepStep.CHECK_CHECKPOINT, label)

    lock_path = ckpt_dir / ".train.lock"
    try:
        lock = FileLock(str(lock_path), timeout=lock_timeout)
    except OSError as exc:  # pragma: no cover
        raise RuntimeError(
            fmt(_MODULE, "Cannot create file lock", str(lock_path), str(exc))
        ) from exc

    try:
        with lock:
            _ensure_fl_checkpoint_locked(
                request=request,
                layout=layout,
                ckpt_dir=ckpt_dir,
                ckpt_file=ckpt_file,
                label=label,
                step_fn=step_fn,
                checkpoint_status_fn=checkpoint_status_fn,
            )
    except Timeout:  # pragma: no cover
        raise RuntimeError(
            fmt(
                _MODULE,
                f"Timed out waiting for checkpoint lock after {lock_timeout:.0f}s",
                "lock acquired",
                str(lock_path),
            )
        )


def _protocol_enabled(request: PipelineRequest) -> bool:
    checkpoint_cfg = request.cfg.checkpoint_protocol
    return (
        isinstance(checkpoint_cfg, CheckpointProtocolConfig) and checkpoint_cfg.enabled
    )


def _score_only_recovery(
    request: PipelineRequest,
    ckpt_dir: Path,
    ckpt_file: Path,
) -> None:
    """Score-only recovery when checkpoint exists but scoring was interrupted."""
    import torch

    from datp.data.regimes.catalog import dataset_for_regime
    from datp.federated.data_loading import ALL_SPLITS, load_client_data
    from datp.scoring.generation import load_model_from_checkpoint, score_clients

    key = request.key
    score_base = (
        ArtifactLayout(base_dir=request.base_dir, regime=key.regime)
        .score_cell(key)
        .score_dir
    )
    scoring_data = load_client_data(
        request.prepared_dir, device=torch.device(DeviceType.CPU), splits=ALL_SPLITS
    )
    model = load_model_from_checkpoint(
        request.cfg,
        ckpt_dir=ckpt_dir,
        require_cuda=request.cfg.machine.require_cuda,
    )
    score_clients(
        model=model,
        client_data=scoring_data,
        score_base=score_base,
        regime=key.regime,
        seed=key.seed,
        alpha=key.alpha,
        dataset=dataset_for_regime(key.regime),
        checkpoint_path=ckpt_file,
        checkpoint_round=request.checkpoint_round,
        scoring_batch_size=request.cfg.machine.scoring_batch_size,
    )


def _handle_non_protocol_checkpoint(
    request: PipelineRequest,
    ckpt_dir: Path,
    ckpt_file: Path,
) -> None:
    """Validate scoring completeness for an existing checkpoint; run score-only recovery if scoring was interrupted."""
    from datp.scoring.generation import validate_scoring_manifest

    key = request.key
    score_base = (
        ArtifactLayout(base_dir=request.base_dir, regime=key.regime)
        .score_cell(key)
        .score_dir
    )
    try:
        validate_scoring_manifest(score_base)
        logger.info(
            "checkpoint exists, skipping training",
            regime=key.regime,
            seed=key.seed,
            alpha=key.alpha,
        )
        return
    except (FileNotFoundError, ValueError):
        pass
    logger.info(
        "checkpoint exists but scoring incomplete; running score-only recovery",
        regime=key.regime,
        seed=key.seed,
        alpha=key.alpha,
    )
    _score_only_recovery(request, ckpt_dir, ckpt_file)


def _run_fl_training(
    request: PipelineRequest,
    label: str,
    step_fn: Callable[[SweepStep, str], None] | None,
) -> None:
    import torch

    from datp.federated.data_loading import TRAINING_SPLITS, load_client_data
    from datp.federated.protocols.fedavg import run_fl_training

    if step_fn is not None:
        step_fn(SweepStep.TRAIN_FL, label)

    key = request.key
    client_data = load_client_data(
        request.prepared_dir,
        device=torch.device(DeviceType.CPU),
        splits=TRAINING_SPLITS,
    )
    run_fl_training(
        request.cfg,
        client_data,
        key.seed,
        key.alpha,
        base_dir=request.base_dir,
        prepared_dir=request.prepared_dir,
    )


def _ensure_fl_checkpoint_locked(
    *,
    request: PipelineRequest,
    layout: ArtifactLayout,
    ckpt_dir: Path,
    ckpt_file: Path,
    label: str,
    step_fn: Callable[[SweepStep, str], None] | None,
    checkpoint_status_fn: Callable[[bool, Path], None] | None,
) -> None:
    key = request.key
    protocol_enabled = _protocol_enabled(request)

    if checkpoint_status_fn is not None:
        checkpoint_status_fn(ckpt_file.exists(), ckpt_file)

    if protocol_enabled and _checkpoint_protocol_complete(request, layout):
        logger.info(
            "checkpoint protocol artifacts exist, skipping training",
            regime=key.regime,
            seed=key.seed,
            alpha=key.alpha,
        )
        return

    if protocol_enabled and _checkpoint_protocol_checkpoints_exist(request, layout):
        _recover_checkpoint_protocol_scores(request, layout)
        return

    if not protocol_enabled and ckpt_file.exists():
        _handle_non_protocol_checkpoint(request, ckpt_dir, ckpt_file)
        return  # scoring validated or recovered; skip training

    _run_fl_training(request, label, step_fn)


def _require_milestones(request: PipelineRequest) -> tuple[int, ...]:
    protocol = request.cfg.checkpoint_protocol
    if protocol is None:
        raise ValueError(fmt_missing(_MODULE, "configured checkpoint protocol"))
    return protocol.milestones


def _checkpoint_protocol_checkpoints_exist(
    request: PipelineRequest, layout: ArtifactLayout
) -> bool:
    key = request.key
    return all(
        (
            layout.checkpoint_dir_for_round(key, checkpoint_round)
            / ArtifactFile.MODEL_CHECKPOINT
        ).exists()
        for checkpoint_round in _require_milestones(request)
    )


def _checkpoint_protocol_complete(
    request: PipelineRequest, layout: ArtifactLayout
) -> bool:
    key = request.key
    return all(
        (
            layout.score_cell_for_round(key, checkpoint_round).manifest_path.exists()
            and (
                layout.checkpoint_dir_for_round(key, checkpoint_round)
                / ArtifactFile.MODEL_CHECKPOINT
            ).exists()
        )
        for checkpoint_round in _require_milestones(request)
    )


def _recover_checkpoint_protocol_scores(
    request: PipelineRequest, layout: ArtifactLayout
) -> None:
    import torch

    from datp.data.regimes.catalog import dataset_for_regime
    from datp.federated.data_loading import ALL_SPLITS, load_client_data
    from datp.scoring.generation import (
        load_model_from_checkpoint,
        score_clients,
        validate_scoring_manifest,
    )

    key = request.key
    scoring_data = load_client_data(
        request.prepared_dir, device=torch.device(DeviceType.CPU), splits=ALL_SPLITS
    )
    for checkpoint_round in _require_milestones(request):
        score_base = layout.score_cell_for_round(key, checkpoint_round).score_dir
        try:
            validate_scoring_manifest(score_base)
            continue
        except (FileNotFoundError, ValueError):
            pass
        round_ckpt_dir = layout.checkpoint_dir_for_round(key, checkpoint_round)
        model = load_model_from_checkpoint(
            request.cfg,
            ckpt_dir=round_ckpt_dir,
            require_cuda=request.cfg.machine.require_cuda,
        )
        score_clients(
            model=model,
            client_data=scoring_data,
            score_base=score_base,
            regime=key.regime,
            seed=key.seed,
            alpha=key.alpha,
            dataset=dataset_for_regime(key.regime),
            checkpoint_path=round_ckpt_dir / ArtifactFile.MODEL_CHECKPOINT,
            checkpoint_round=checkpoint_round,
            scoring_batch_size=request.cfg.machine.scoring_batch_size,
        )
