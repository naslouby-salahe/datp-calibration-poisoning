"""Sweep orchestration: enumerate, validate, and run controlled policy cells."""

from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from datp.artifacts.existence import results_exist
from datp.artifacts.layout import ArtifactLayout
from datp.config.compose import BASE_CONFIG, write_resolved_config
from datp.config.models import DatpConfig
from datp.config.stages import ExperimentStage
from datp.core.enums import CONTROLLED_POLICIES
from datp.experiments.enums import PolicyRunStatus
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.core.logging import get_logger
from datp.core.seeds import set_seeds
from datp.core.tracking import (
    TrackingMetric,
    TrackingMetricKey,
    TrackingMetrics,
    TrackingParam,
    TrackingParamKey,
    TrackingParams,
    init_tracking,
    log_metrics,
    tracking_run,
)
from datp.experiments import console
from datp.experiments.enums import SweepStep
from datp.experiments.executor import (
    PipelineRequest,
    SharedTrainingExecutor,
    ThresholdEvaluationExecutor,
)
from datp.experiments.models import SharedPipelineContext
from datp.experiments.stages.prepare_data import (
    PreparedDataRequest,
    ensure_prepared_data,
)
from datp.experiments.validator import validate_sweep

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class _GroupContext:
    key: TrainingCellId
    group_cells: list[PolicyRunId]
    pre_composed_configs: dict[PolicyRunId, DatpConfig]
    base_dir: Path
    result: SweepResult
    group_idx: int
    total_groups: int
    data_root: Path


def build_experiment_matrix() -> list[PolicyRunId]:
    seeds = list(BASE_CONFIG.experiment.seeds)
    cells: list[PolicyRunId] = []
    stage = ExperimentStage.NBAIOT_MAIN
    for policy in sorted(CONTROLLED_POLICIES):
        for seed in seeds:
            cells.append(
                PolicyRunId(
                    cell=TrainingCellId(stage=stage, seed=seed),
                    policy=policy,
                )
            )
    return cells


@dataclass(slots=True)
class SweepResult:
    total: int = 0
    completed: int = 0
    skipped: int = 0
    failed: int = 0


def run_sweep(
    *,
    dry_run: bool,
    base_dir: Path,
    data_root: Path | None = None,
) -> SweepResult:
    """Orchestrate a full experiment sweep; blocks and exits on pre-validation failure."""
    t_start = time.monotonic()

    init_tracking(
        experiment_name=BASE_CONFIG.tracking.experiment_name,
        tracking_uri=BASE_CONFIG.tracking.tracking_uri,
    )

    console.print_step(SweepStep.BUILD_MATRIX, detail="")
    cells = build_experiment_matrix()
    result = SweepResult(total=len(cells))

    console.print_sweep_banner(len(cells), str(base_dir))

    console.print_step(SweepStep.VALIDATE_MATRIX, detail="")
    errors, pre_composed_configs = validate_sweep(cells)
    if errors:
        for err in errors:
            logger.error("pre-validation failure", error=str(err))
        raise SystemExit(f"Sweep blocked: {len(errors)} config validation error(s)")

    if dry_run:
        _print_dry_run_summary(cells)
        return result

    groups: dict[TrainingCellId, list[PolicyRunId]] = defaultdict(list)
    for cell in cells:
        groups[cell.shared_training_key()].append(cell)

    _data_root = data_root if data_root is not None else base_dir
    total_groups = len(groups)
    for group_idx, (key, group_cells) in enumerate(
        sorted(groups.items(), key=lambda kv: _sort_key(kv[0])),
        start=1,
    ):
        with tracking_run(
            run_name=f"{key.stage}_seed{key.seed}",
            params=TrackingParams(
                (
                    TrackingParam(TrackingParamKey.STAGE, key.stage),
                    TrackingParam(TrackingParamKey.SEED, key.seed),
                )
            ),
            tags=None,
        ):
            _process_group(
                _GroupContext(
                    key=key,
                    group_cells=group_cells,
                    pre_composed_configs=pre_composed_configs,
                    base_dir=base_dir,
                    result=result,
                    group_idx=group_idx,
                    total_groups=total_groups,
                    data_root=_data_root,
                )
            )

    total_elapsed = time.monotonic() - t_start
    log_metrics(
        TrackingMetrics(
            (
                TrackingMetric(TrackingMetricKey.SWEEP_TOTAL, result.total),
                TrackingMetric(TrackingMetricKey.SWEEP_COMPLETED, result.completed),
                TrackingMetric(TrackingMetricKey.SWEEP_SKIPPED, result.skipped),
                TrackingMetric(TrackingMetricKey.SWEEP_FAILED, result.failed),
                TrackingMetric(TrackingMetricKey.SWEEP_ELAPSED_S, total_elapsed),
            )
        ),
        step=None,
        prefix=None,
    )
    console.print_sweep_summary(result, total_elapsed)
    return result


def _cell_is_done(cell: PolicyRunId, base_dir: Path) -> bool:
    ckpt_proto = BASE_CONFIG.checkpoint_protocol
    checkpoint_protocol_active = ckpt_proto is not None and ckpt_proto.enabled
    cell_uses_checkpoint_path = cell.policy in CONTROLLED_POLICIES
    if checkpoint_protocol_active and cell_uses_checkpoint_path:
        layout = ArtifactLayout(base_dir=base_dir, stage=cell.stage)
        return all(
            layout.policy_run_for_round(cell, checkpoint_round).metrics_path.exists()
            for checkpoint_round in ckpt_proto.milestones  # type: ignore[union-attr]
        )
    return results_exist(cell.policy, cell.stage, cell.seed, base_dir=base_dir)


def _account_skip(cell: PolicyRunId, result: SweepResult) -> None:
    logger.info("skipping completed cell", cell=cell.audit_id())
    result.skipped += 1
    console.print_policy_result(cell.policy, PolicyRunStatus.SKIPPED, 0.0)


def _process_group(ctx: _GroupContext) -> None:
    key = ctx.key
    group_cells = ctx.group_cells
    pre_composed_configs = ctx.pre_composed_configs
    base_dir = ctx.base_dir
    result = ctx.result
    data_root = ctx.data_root

    console.print_group_header(
        key.stage,
        key.seed,
        len(group_cells),
        ctx.group_idx,
        ctx.total_groups,
    )

    pending_cells = [cell for cell in group_cells if not _cell_is_done(cell, base_dir)]
    if not pending_cells:
        for cell in group_cells:
            _account_skip(cell, result)
        return

    if not _prepare_group_data(
        key.stage,
        key.seed,
        pending_cells,
        group_cells,
        base_dir,
        result,
        data_root=data_root,
    ):
        return

    pending_fl: list[PolicyRunId] = []

    for cell in group_cells:
        if _cell_is_done(cell, base_dir):
            _account_skip(cell, result)
            continue
        pending_fl.append(cell)

    if pending_fl:
        completed, failed = _run_shared_fl_group(
            pending_fl, pre_composed_configs, base_dir, data_root=data_root
        )
        result.completed += completed
        result.failed += failed


def _prepare_group_data(
    stage: ExperimentStage,
    seed: int,
    pending_cells: list[PolicyRunId],
    group_cells: list[PolicyRunId],
    base_dir: Path,
    result: SweepResult,
    data_root: Path | None = None,
) -> bool:
    _data_root = data_root if data_root is not None else base_dir
    try:
        ensure_prepared_data(
            PreparedDataRequest(
                stage=stage,
                seed=seed,
                cfg=BASE_CONFIG,
                base_dir=_data_root,
            )
        )
        return True
    except Exception:
        logger.exception(
            "prepared data setup failed",
            stage=stage,
            seed=seed,
            n_failed=len(pending_cells),
        )
        for cell in pending_cells:
            result.failed += 1
            console.print_policy_result(cell.policy, PolicyRunStatus.FAILED, 0.0)
        for cell in group_cells:
            if cell not in pending_cells:
                _account_skip(cell, result)
        return False


def _sort_key(k: TrainingCellId) -> tuple[str, int]:
    return (k.stage.value, k.seed)


def _enabled_checkpoint_rounds(cfg: DatpConfig) -> tuple[int | None, ...]:
    ckpt_proto = cfg.checkpoint_protocol
    if ckpt_proto is not None and ckpt_proto.enabled:
        return tuple(ckpt_proto.milestones)
    return (None,)


def _write_group_resolved_configs(
    group_cells: list[PolicyRunId],
    pre_composed_configs: dict[PolicyRunId, DatpConfig],
    base_dir: Path,
    checkpoint_rounds: tuple[int | None, ...],
) -> None:
    for cell in group_cells:
        cell_cfg = pre_composed_configs[cell]
        for checkpoint_round in checkpoint_rounds:
            _write_cell_resolved_config(
                cell, cell_cfg, base_dir, checkpoint_round=checkpoint_round
            )


def _build_shared_context(
    trainer: SharedTrainingExecutor,
    request: PipelineRequest,
    group_cells: list[PolicyRunId],
    checkpoint_round: int | None,
) -> SharedPipelineContext | None:
    try:
        return trainer.build_context(request)
    except Exception:
        logger.exception(
            "shared group setup failed",
            stage=request.key.stage,
            seed=request.key.seed,
            checkpoint_round=checkpoint_round,
            n_failed=len(group_cells),
        )
        for cell in group_cells:
            console.print_policy_result(cell.policy, PolicyRunStatus.FAILED, 0.0)
        return None


def _run_shared_cell_evaluation(
    evaluator: ThresholdEvaluationExecutor,
    cell: PolicyRunId,
    cell_cfg: DatpConfig,
    key: TrainingCellId,
    base_dir: Path,
    prepared_dir: Path,
    checkpoint_round: int | None,
    ctx: SharedPipelineContext,
) -> bool:
    t0 = time.monotonic()
    cell_request = PipelineRequest(
        key=key,
        policy=cell.policy,
        cfg=cell_cfg,
        base_dir=base_dir,
        prepared_dir=prepared_dir,
        checkpoint_round=checkpoint_round,
    )
    try:
        evaluator.run(cell_request, ctx)
        console.print_policy_result(
            cell.policy, PolicyRunStatus.DONE, time.monotonic() - t0
        )
        return True
    except Exception:
        logger.exception(
            "cell failed",
            policy=cell.policy,
            stage=key.stage,
            seed=key.seed,
            checkpoint_round=checkpoint_round,
        )
        console.print_policy_result(
            cell.policy, PolicyRunStatus.FAILED, time.monotonic() - t0
        )
        return False


def _run_shared_fl_group(
    group_cells: list[PolicyRunId],
    pre_composed_configs: dict[PolicyRunId, DatpConfig],
    base_dir: Path,
    data_root: Path | None = None,
) -> tuple[int, int]:
    """Run shared FL training once for this group; all cells share the same checkpoint (train-once rule)."""
    _data_root = data_root if data_root is not None else base_dir
    first_cell = group_cells[0]
    stage = first_cell.stage
    seed = first_cell.seed
    cfg = pre_composed_configs[first_cell]
    from datp.data.paths import processed_root
    from datp.data.catalog import dataset_for_stage

    prepared_dir = processed_root(dataset_for_stage(stage), base_dir=_data_root)

    checkpoint_rounds = _enabled_checkpoint_rounds(cfg)
    _write_group_resolved_configs(
        group_cells, pre_composed_configs, base_dir, checkpoint_rounds
    )

    key = TrainingCellId(stage=stage, seed=seed)
    set_seeds(seed)
    trainer = SharedTrainingExecutor(
        step_fn=console.print_step,
        checkpoint_status_fn=console.print_checkpoint_status,
    )
    evaluator = ThresholdEvaluationExecutor(step_fn=console.print_step)

    completed = 0
    failed = 0
    for checkpoint_round in checkpoint_rounds:
        round_completed, round_failed = _run_checkpoint_round(
            trainer=trainer,
            evaluator=evaluator,
            group_cells=group_cells,
            pre_composed_configs=pre_composed_configs,
            key=key,
            cfg=cfg,
            base_dir=base_dir,
            prepared_dir=prepared_dir,
            checkpoint_round=checkpoint_round,
        )
        completed += round_completed
        failed += round_failed

    return completed, failed


def _run_checkpoint_round(
    *,
    trainer: SharedTrainingExecutor,
    evaluator: ThresholdEvaluationExecutor,
    group_cells: list[PolicyRunId],
    pre_composed_configs: dict[PolicyRunId, DatpConfig],
    key: TrainingCellId,
    cfg: DatpConfig,
    base_dir: Path,
    prepared_dir: Path,
    checkpoint_round: int | None,
) -> tuple[int, int]:
    context_request = PipelineRequest(
        key=key,
        policy=ThresholdPolicy.GLOBAL_THRESHOLD,
        cfg=cfg,
        base_dir=base_dir,
        prepared_dir=prepared_dir,
        checkpoint_round=checkpoint_round,
    )
    ctx = _build_shared_context(trainer, context_request, group_cells, checkpoint_round)
    if ctx is None:
        return 0, len(group_cells)
    completed = 0
    failed = 0
    for cell in group_cells:
        cell_cfg = pre_composed_configs[cell]
        if _run_shared_cell_evaluation(
            evaluator,
            cell,
            cell_cfg,
            key=key,
            base_dir=base_dir,
            prepared_dir=prepared_dir,
            checkpoint_round=checkpoint_round,
            ctx=ctx,
        ):
            completed += 1
        else:
            failed += 1
    return completed, failed


def _write_cell_resolved_config(
    cell: PolicyRunId,
    cfg: DatpConfig,
    base_dir: Path,
    *,
    checkpoint_round: int | None,
) -> Path:
    layout = ArtifactLayout(base_dir=base_dir, stage=cell.stage)
    output_dir = (
        layout.policy_run_for_round(cell, checkpoint_round).result_dir
        if checkpoint_round is not None
        else layout.policy_run(cell).result_dir
    )
    return write_resolved_config(cfg, output_dir)


def _print_dry_run_summary(cells: list[PolicyRunId]) -> None:
    console.print_dry_run_summary(len(cells))
