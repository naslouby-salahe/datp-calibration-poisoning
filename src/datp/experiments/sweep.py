"""NBAIOT_MAIN sweep orchestration: matrix building, validation, and group execution."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from datp.artifacts.existence import results_exist
from datp.artifacts.layout import ArtifactLayout
from datp.config.compose import (
    BASE_CONFIG,
    ComposeError,
    compose_config,
    write_resolved_config,
)
from datp.config.models import DatpConfig
from datp.config.models import ExperimentStage
from datp.core.enums import CONTROLLED_POLICIES, ThresholdPolicy
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
from datp.experiments.executor import (
    PipelineRequest,
    SharedTrainingExecutor,
    ThresholdEvaluationExecutor,
)
from datp.experiments.models import PolicyRunStatus, SweepStep
from datp.experiments.stages.prepare_data import (
    PreparedDataRequest,
    ensure_prepared_data,
)

logger = get_logger(__name__)


@dataclass(slots=True)
class SweepResult:
    """Mutable tally of sweep outcomes: total, completed, skipped, and failed cells."""

    total: int = 0
    completed: int = 0
    skipped: int = 0
    failed: int = 0


def validate_sweep(
    cells: list[PolicyRunId],
) -> tuple[list[str], dict[PolicyRunId, DatpConfig]]:
    """Validate the experiment matrix by composing configs for every cell."""
    errors: list[str] = []
    configs: dict[PolicyRunId, DatpConfig] = {}
    for cell in cells:
        try:
            configs[cell] = compose_config(
                stage=cell.cell.stage, policy=cell.policy, seed=cell.cell.seed
            )
        except ComposeError as exc:
            errors.append(f"{cell.label()}: {exc}")
    return errors, configs


def build_experiment_matrix() -> list[PolicyRunId]:
    """Build the Cartesian product of controlled policies times seeds for NBAIOT_MAIN."""
    return [
        PolicyRunId(
            cell=TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=seed),
            policy=policy,
        )
        for policy in sorted(CONTROLLED_POLICIES)
        for seed in BASE_CONFIG.experiment.seeds
    ]


def _run_sweep_groups(
    groups: dict[TrainingCellId, list[PolicyRunId]],
    pre_composed_configs: dict[PolicyRunId, DatpConfig],
    base_dir: Path,
    result: SweepResult,
    data_root: Path,
) -> None:
    total_groups = len(groups)
    for group_idx, (key, group_cells) in enumerate(
        sorted(groups.items(), key=lambda kv: (kv[0].stage.value, kv[0].seed)), start=1
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
                key,
                group_cells,
                pre_composed_configs,
                base_dir,
                result,
                group_idx,
                total_groups,
                data_root,
            )


def _log_sweep_metrics(result: SweepResult, total_elapsed: float) -> None:
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


def run_sweep(
    *, dry_run: bool, base_dir: Path, data_root: Path | None = None
) -> SweepResult:
    """Orchestrate the full sweep: build matrix, validate, group, and execute."""
    t_start = time.monotonic()
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
        console.print_dry_run_summary(len(cells))
        return result

    init_tracking(
        experiment_name=BASE_CONFIG.tracking.experiment_name,
        tracking_uri=BASE_CONFIG.tracking.tracking_uri,
    )

    groups: dict[TrainingCellId, list[PolicyRunId]] = defaultdict(list)
    for cell in cells:
        groups[cell.shared_training_key()].append(cell)

    _run_sweep_groups(
        groups,
        pre_composed_configs,
        base_dir,
        result,
        data_root if data_root is not None else base_dir,
    )
    total_elapsed = time.monotonic() - t_start
    _log_sweep_metrics(result, total_elapsed)
    console.print_sweep_summary(result, total_elapsed)
    return result


def _cell_is_done(cell: PolicyRunId, base_dir: Path) -> bool:
    ckpt_proto = BASE_CONFIG.checkpoint_protocol
    if (
        ckpt_proto is not None
        and ckpt_proto.enabled
        and cell.policy in CONTROLLED_POLICIES
    ):
        layout = ArtifactLayout(base_dir=base_dir, stage=cell.stage)
        return all(
            layout.policy_run_for_round(cell, r).metrics_path.exists()
            for r in ckpt_proto.milestones
        )
    return results_exist(cell.policy, cell.stage, cell.seed, base_dir=base_dir)


def _account_skip(cell: PolicyRunId, result: SweepResult) -> None:
    logger.info("skipping completed cell", cell=cell.audit_id())
    result.skipped += 1
    console.print_policy_result(cell.policy, PolicyRunStatus.SKIPPED, 0.0)


def _process_group(
    key: TrainingCellId,
    group_cells: list[PolicyRunId],
    pre_composed_configs: dict[PolicyRunId, DatpConfig],
    base_dir: Path,
    result: SweepResult,
    group_idx: int,
    total_groups: int,
    data_root: Path,
) -> None:
    console.print_group_header(
        key.stage, key.seed, len(group_cells), group_idx, total_groups
    )
    pending_cells = [c for c in group_cells if not _cell_is_done(c, base_dir)]

    if not pending_cells:
        for cell in group_cells:
            _account_skip(cell, result)
        return

    if not _prepare_group_data(
        key.stage, key.seed, pending_cells, group_cells, result, data_root
    ):
        return

    pending_fl: list[PolicyRunId] = []
    for cell in group_cells:
        if _cell_is_done(cell, base_dir):
            _account_skip(cell, result)
        else:
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
    result: SweepResult,
    data_root: Path,
) -> bool:
    try:
        ensure_prepared_data(
            PreparedDataRequest(
                stage=stage, seed=seed, cfg=BASE_CONFIG, base_dir=data_root
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


def _enabled_checkpoint_rounds(cfg: DatpConfig) -> tuple[int | None, ...]:
    return (
        tuple(cfg.checkpoint_protocol.milestones)
        if cfg.checkpoint_protocol and cfg.checkpoint_protocol.enabled
        else (None,)
    )


def _run_checkpoint_round(
    trainer: SharedTrainingExecutor,
    evaluator: ThresholdEvaluationExecutor,
    key: TrainingCellId,
    group_cells: list[PolicyRunId],
    checkpoint_round: int | None,
    cfg: DatpConfig,
    base_dir: Path,
    prepared_dir: Path,
    pre_composed_configs: dict[PolicyRunId, DatpConfig],
) -> tuple[int, int]:
    context_request = PipelineRequest(
        key=key,
        policy=ThresholdPolicy.GLOBAL_THRESHOLD,
        cfg=cfg,
        base_dir=base_dir,
        prepared_dir=prepared_dir,
        checkpoint_round=checkpoint_round,
    )
    try:
        ctx = trainer.build_context(context_request)
    except Exception:
        logger.exception(
            "shared group setup failed",
            stage=key.stage,
            seed=key.seed,
            checkpoint_round=checkpoint_round,
            n_failed=len(group_cells),
        )
        for cell in group_cells:
            console.print_policy_result(cell.policy, PolicyRunStatus.FAILED, 0.0)
        return 0, len(group_cells)

    completed, failed = 0, 0
    for cell in group_cells:
        t0 = time.monotonic()
        cell_request = PipelineRequest(
            key=key,
            policy=cell.policy,
            cfg=pre_composed_configs[cell],
            base_dir=base_dir,
            prepared_dir=prepared_dir,
            checkpoint_round=checkpoint_round,
        )
        try:
            evaluator.run(cell_request, ctx)
            console.print_policy_result(
                cell.policy, PolicyRunStatus.DONE, time.monotonic() - t0
            )
            completed += 1
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
            failed += 1
    return completed, failed


def _run_shared_fl_group(
    group_cells: list[PolicyRunId],
    pre_composed_configs: dict[PolicyRunId, DatpConfig],
    base_dir: Path,
    data_root: Path | None = None,
) -> tuple[int, int]:
    first_cell = group_cells[0]
    stage, seed = first_cell.stage, first_cell.seed
    cfg = pre_composed_configs[first_cell]

    from datp.data.catalog import dataset_for_stage
    from datp.data.paths import processed_root

    effective_base = data_root if data_root is not None else base_dir
    prepared_dir = processed_root(dataset_for_stage(stage), base_dir=effective_base)
    checkpoint_rounds = _enabled_checkpoint_rounds(cfg)

    for cell in group_cells:
        for r in checkpoint_rounds:
            if r is not None:
                output_dir = (
                    ArtifactLayout(base_dir=base_dir, stage=cell.stage)
                    .policy_run_for_round(cell, r)
                    .result_dir
                )
            else:
                output_dir = (
                    ArtifactLayout(base_dir=base_dir, stage=cell.stage)
                    .policy_run(cell)
                    .result_dir
                )
            write_resolved_config(pre_composed_configs[cell], output_dir)

    key = TrainingCellId(stage=stage, seed=seed)
    set_seeds(seed)

    trainer = SharedTrainingExecutor(
        step_fn=console.print_step, checkpoint_status_fn=console.print_checkpoint_status
    )
    evaluator = ThresholdEvaluationExecutor(step_fn=console.print_step)

    completed, failed = 0, 0
    for checkpoint_round in checkpoint_rounds:
        c, f = _run_checkpoint_round(
            trainer,
            evaluator,
            key,
            group_cells,
            checkpoint_round,
            cfg,
            base_dir,
            prepared_dir,
            pre_composed_configs,
        )
        completed += c
        failed += f

    return completed, failed
