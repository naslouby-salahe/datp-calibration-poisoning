from __future__ import annotations

import enum
import multiprocessing
import os
import time
from collections import defaultdict
from collections.abc import Mapping
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from datp.artifacts import ArtifactLayout, RunLifecycle, write_json_atomic
from datp.config import (
    BASE_CONFIG,
    ConfigError,
    DatpConfig,
    ExperimentStage,
    run_config,
    write_resolved_config,
)
from datp.core import (
    PolicyRunId,
    TrainingCellId,
    configure_logging,
    get_logger,
    hash_file,
    hash_jsonable,
    set_seeds,
)
from datp.data import (
    PartitionManifest,
    Split,
    assert_no_csv_artifacts,
    audit_partitions,
    dataset_for_stage,
    dataset_spec,
    filename_for_split,
    load_scaler,
    prepare_nbaiot,
    processed_root,
    raw_root,
    run_schema_audit,
    split_path,
)
from datp.enums import (
    CONTROLLED_POLICIES,
    ArtifactDir,
    ArtifactFile,
    DeviceType,
    ProvenanceSentinel,
    ThresholdPolicy,
)
from datp.evaluation import evaluate_policy_run
from datp.scoring import (
    ScoreProvider,
    ScoringManifest,
    load_main_cal_errors,
    validate_scoring_manifest,
)
from datp.thresholding import (
    ClientThresholdsCollection,
    MetricsBuildRequest,
    SweepMetrics,
    ThresholdDerivation,
    build_metrics_dict,
    compute_client_thresholds,
    compute_tau_global,
    derive_threshold,
    identify_eligible,
    results_exist,
)
from datp.types import (
    ArtifactName,
    ClientId,
    ContentHash,
    DurationSeconds,
    FeatureCount,
    Index,
    NarrativeText,
    RandomSeed,
    SampleCount,
    ScoreValue,
    ScoreVector,
    SignedCount,
    Threshold,
    WorkerCount,
)


class SweepStep(enum.StrEnum):
    BUILD_MATRIX = "build_matrix"
    VALIDATE_MATRIX = "validate_matrix"
    TRAIN_FL = "train_fl"
    LOAD_CAL_SCORES = "load_cal_scores"
    COMPUTE_ELIGIBILITY = "compute_eligibility"
    COMPUTE_TAU_GLOBAL = "compute_tau_global"
    INIT_SCORE_PROVIDER = "init_score_provider"
    DERIVE_THRESHOLD = "derive_threshold"
    EVALUATE = "evaluate"
    WRITE_METRICS = "write_metrics"
    SWEEP_COMPLETE = "sweep_complete"


class PolicyRunStatus(enum.StrEnum):
    DONE = "done"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(slots=True)
class SweepResult:
    total: SampleCount = 0
    completed: SignedCount = 0
    skipped: SignedCount = 0
    failed: SignedCount = 0


@dataclass(frozen=True, slots=True)
class PipelineRequest:
    key: TrainingCellId
    policy: ThresholdPolicy
    cfg: DatpConfig
    base_dir: Path
    prepared_dir: Path


@dataclass(slots=True)
class SharedPipelineContext:
    key: TrainingCellId
    client_errors: dict[ClientId, ScoreVector]
    eligible: tuple[ClientId, ...]
    pending: tuple[ClientId, ...]
    client_taus: ClientThresholdsCollection | Mapping[ClientId, ScoreValue]
    tau_global: Threshold
    score_provider: ScoreProvider
    model_identity: ContentHash


console = Console()


_SWEEP_STEP_LABELS = {
    SweepStep.BUILD_MATRIX: "Build experiment matrix",
    SweepStep.VALIDATE_MATRIX: "Validate sweep matrix",
    SweepStep.TRAIN_FL: "Train FL model",
    SweepStep.LOAD_CAL_SCORES: "Load calibration scores",
    SweepStep.COMPUTE_ELIGIBILITY: "Compute client eligibility",
    SweepStep.COMPUTE_TAU_GLOBAL: "Compute tau_global",
    SweepStep.INIT_SCORE_PROVIDER: "Initialize score provider",
    SweepStep.DERIVE_THRESHOLD: "Derive threshold",
    SweepStep.EVALUATE: "Evaluate policy",
    SweepStep.WRITE_METRICS: "Write metrics",
    SweepStep.SWEEP_COMPLETE: "Sweep complete",
}


_STATUS_SYMBOLS = {
    PolicyRunStatus.DONE: "[green]✓[/green]",
    PolicyRunStatus.SKIPPED: "[dim]→[/dim]",
    PolicyRunStatus.FAILED: "[red]✗[/red]",
}


def print_sweep_banner(cell_count: SampleCount, base_dir: ArtifactName) -> None:
    lines = [
        f"Stage: [cyan]NBAIOT_MAIN[/cyan] Cells: [cyan]{cell_count}[/cyan]",
        f"Output: [dim]{base_dir}[/dim]",
    ]
    console.print(
        Panel("\n".join(lines), title="[bold]datp-cp Sweep[/bold]", border_style="cyan")
    )


def print_step(step: SweepStep, detail: NarrativeText) -> None:
    detail_str = f" [dim]{detail}[/dim]" if detail else ""
    console.print(
        f" [dim][{step}][/dim] [bold]{_SWEEP_STEP_LABELS[step]}[/bold]{detail_str}"
    )


def print_group_header(
    stage: ExperimentStage,
    seed: RandomSeed,
    group_size: SignedCount,
    current: SignedCount,
    total: SampleCount,
) -> None:
    progress = f"[{current}/{total}]"
    console.print(
        f"\n[bold yellow]{'─' * 56}[/bold yellow]\n[bold yellow] Group {progress}[/bold yellow] stage={stage} seed={seed} [dim]({group_size} cells)[/dim]"
    )


def print_policy_result(
    policy: ThresholdPolicy, status: PolicyRunStatus, elapsed_s: DurationSeconds
) -> None:
    elapsed_str = f"[dim]({elapsed_s:.1f}s)[/dim]" if elapsed_s > 0 else ""
    console.print(
        f" {_STATUS_SYMBOLS[status]} [bold]{policy.upper()}[/bold] {elapsed_str}"
    )


def print_sweep_summary(result: SweepResult, elapsed_s: DurationSeconds) -> None:
    table = Table(title="Sweep Summary", border_style="green")
    table.add_column("Metric", style="bold")
    table.add_column("Value")
    table.add_row("Total", str(result.total))
    table.add_row("Completed", f"[green]{result.completed}[/green]")
    table.add_row("Skipped", f"[dim]{result.skipped}[/dim]")
    failed_style = "red" if result.failed > 0 else ""
    table.add_row(
        "Failed",
        f"[{failed_style}]{result.failed}[/{failed_style}]"
        if failed_style
        else str(result.failed),
    )
    table.add_row("Duration", f"{elapsed_s:.1f}s")
    console.print(table)


logger = get_logger(__name__)


_MODULE = "experiments.stages.prepare_data"


_REQUIRED_CLIENT_ARTIFACTS = tuple(filename_for_split(s) for s in Split) + (
    ArtifactFile.SCALER,
)


@dataclass(frozen=True, slots=True)
class PreparedDataRequest:
    stage: ExperimentStage
    seed: RandomSeed
    cfg: DatpConfig
    base_dir: Path


def ensure_prepared_data(request: PreparedDataRequest) -> Path:
    dataset_id = dataset_for_stage(request.stage)
    prepared_dir = processed_root(dataset_id, base_dir=request.base_dir)
    manifest_file = prepared_dir / ArtifactFile.MANIFEST

    if manifest_file.exists():
        _verify_existing_prepared_data(request, prepared_dir, manifest_file)
        return prepared_dir

    logger.info(
        "processed data missing; running preparation",
        stage=request.stage,
        seed=request.seed,
        prepared_dir=str(prepared_dir),
    )
    _prepare(request)
    _verify_existing_prepared_data(request, prepared_dir, manifest_file)
    return prepared_dir


def _prepare(request: PreparedDataRequest) -> None:
    cfg = request.cfg
    dataset_id = dataset_for_stage(request.stage)
    raw_dir = raw_root(dataset_id, base_dir=request.base_dir)
    output_dir = processed_root(dataset_id, base_dir=request.base_dir)
    partition_results = prepare_nbaiot(
        raw_dir=raw_dir,
        output_dir=output_dir,
        n_min=cfg.threshold.n_min,
        seed=request.seed,
        test_balance_policy=cfg.dataset.nbaiot_test_balance,
    )
    audit_partitions(
        partition_results,
        request.stage,
        request.base_dir,
        cfg.threshold.n_min,
    )


def _verify_existing_prepared_data(
    request: PreparedDataRequest, prepared_dir: Path, manifest_file: Path
) -> None:
    dataset_id = dataset_for_stage(request.stage)
    manifest: PartitionManifest = PartitionManifest.load(manifest_file)
    raw_base_dir = raw_root(dataset_id, base_dir=request.base_dir)
    manifest.verify_hashes(raw_base_dir)
    _verify_client_artifacts(prepared_dir, dataset_spec(dataset_id).feature_count)
    assert_no_csv_artifacts(prepared_dir)
    logger.info(
        "processed data verified; reusing",
        stage=request.stage,
        seed=request.seed,
        prepared_dir=str(prepared_dir),
    )


def _verify_client_artifacts(prepared_dir: Path, feature_count: FeatureCount) -> None:
    if not prepared_dir.is_dir():
        raise RuntimeError(
            f"[{_MODULE}] Prepared directory missing. Expected: {prepared_dir}. Got: not found."
        )

    client_dirs = sorted(
        d
        for d in prepared_dir.iterdir()
        if d.is_dir() and split_path(d, Split.TRAIN).exists()
    )
    if not client_dirs:
        raise RuntimeError(
            f"[{_MODULE}] Prepared clients missing. Expected: at least one client directory. Got: 0."
        )

    for client_dir in client_dirs:
        missing = [
            name
            for name in _REQUIRED_CLIENT_ARTIFACTS
            if not (client_dir / name).exists()
        ]
        if missing:
            raise RuntimeError(
                f"[{_MODULE}] Prepared client {client_dir.name} incomplete. "
                f"Expected: {', '.join(_REQUIRED_CLIENT_ARTIFACTS)}. "
                f"Got missing: {', '.join(missing)}."
            )
        scaler = load_scaler(client_dir / ArtifactFile.SCALER)
        if scaler.n_features_in_ != feature_count:
            raise RuntimeError(
                f"[{_MODULE}] Scaler feature count mismatch for {client_dir.name}: "
                f"expected {feature_count}, got {scaler.n_features_in_}."
            )
        for split in Split:
            run_schema_audit(split_path(client_dir, split), feature_count)


def ensure_trained_scores(request: PipelineRequest) -> ScoringManifest:
    key = request.key
    score_base = (
        ArtifactLayout(base_dir=request.base_dir, stage=key.stage)
        .score_cell(key)
        .score_dir
    )
    try:
        manifest = validate_scoring_manifest(score_base)
    except (FileNotFoundError, ValueError):
        _run_fl_training(request, key.label())
        return validate_scoring_manifest(score_base)
    logger.info("scores exist, skipping training", stage=key.stage, seed=key.seed)
    return manifest


def _run_fl_training(request: PipelineRequest, label: NarrativeText) -> None:
    import torch

    from datp.federated import TRAINING_SPLITS, load_client_data, run_fl_training

    print_step(SweepStep.TRAIN_FL, label)

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
        base_dir=request.base_dir,
        prepared_dir=request.prepared_dir,
    )


def build_shared_context(request: PipelineRequest) -> SharedPipelineContext:
    key = request.key
    cfg = request.cfg

    scoring_manifest = ensure_trained_scores(request)

    print_step(SweepStep.LOAD_CAL_SCORES, "")
    client_errors = load_main_cal_errors(key.stage, key.seed, request.base_dir)

    print_step(SweepStep.COMPUTE_ELIGIBILITY, "")
    eligibility = identify_eligible(client_errors, n_min=cfg.threshold.n_min)

    print_step(SweepStep.COMPUTE_TAU_GLOBAL, "")
    client_taus = compute_client_thresholds(
        client_errors, eligibility, q=cfg.threshold.q
    )
    tau_global = compute_tau_global(client_taus)

    print_step(SweepStep.INIT_SCORE_PROVIDER, "")
    layout = ArtifactLayout(base_dir=request.base_dir, stage=key.stage)
    score_provider = ScoreProvider(layout.score_cell(key).score_dir)

    return SharedPipelineContext(
        key=key,
        client_errors=client_errors,
        eligible=eligibility.eligible_ids,
        pending=eligibility.pending_ids,
        client_taus=client_taus,
        tau_global=tau_global,
        score_provider=score_provider,
        model_identity=scoring_manifest.model_hash,
    )


def evaluate_policy(
    request: PipelineRequest, ctx: SharedPipelineContext
) -> SweepMetrics:
    policy = request.policy
    cfg = request.cfg
    layout = ArtifactLayout(base_dir=request.base_dir, stage=ctx.key.stage)
    run = PolicyRunId(cell=ctx.key, policy=policy)
    res_dir = layout.policy_run(run).result_dir

    with RunLifecycle(res_dir, policy=policy, seed=ctx.key.seed):
        print_step(SweepStep.DERIVE_THRESHOLD, policy)
        threshold_result = derive_threshold(
            ThresholdDerivation(
                policy=policy,
                client_errors=ctx.client_errors,
                n_min=cfg.threshold.n_min,
                q=cfg.threshold.q,
                tau_global=ctx.tau_global,
                threshold_cfg=cfg.threshold,
                seed=ctx.key.seed,
            )
        )
        logger.info(
            "threshold derivation complete",
            policy=policy,
            tau_global=threshold_result.tau_global,
            eligible=threshold_result.eligible_count,
            pending=threshold_result.pending_count,
        )

        print_step(SweepStep.EVALUATE, policy)
        eval_result = evaluate_policy_run(
            threshold_result.client_thresholds,
            ctx.score_provider.score_root,
            ctx.key.stage,
            ctx.key.seed,
            score_provider=ctx.score_provider,
        )

        print_step(SweepStep.WRITE_METRICS, policy)
        score_paths = layout.score_cell(ctx.key)
        prepared_manifest = request.prepared_dir / ArtifactFile.MANIFEST

        metrics = build_metrics_dict(
            MetricsBuildRequest(
                eval_result=eval_result,
                threshold_result=threshold_result,
                config_identity=hash_jsonable(request.cfg.model_dump()),
                split_manifest_identity=hash_file(prepared_manifest)
                if prepared_manifest.exists()
                else ProvenanceSentinel.MISSING_MANIFEST_HASH,
                model_identity=ctx.model_identity,
                score_artifact_identity=hash_file(score_paths.manifest_path),
            )
        )
        write_json_atomic(res_dir / ArtifactFile.METRICS, metrics)
        logger.info("results written", path=str(res_dir / ArtifactFile.METRICS))

        return metrics

    raise RuntimeError("unreachable: RunLifecycle always returns or raises")


def validate_sweep(
    cells: list[PolicyRunId],
) -> tuple[list[NarrativeText], dict[PolicyRunId, DatpConfig]]:
    errors: list[NarrativeText] = []
    configs: dict[PolicyRunId, DatpConfig] = {}
    for cell in cells:
        try:
            configs[cell] = run_config(
                stage=cell.cell.stage, policy=cell.policy, seed=cell.cell.seed
            )
        except ConfigError as exc:
            errors.append(f"{cell.label()}: {exc}")
    return errors, configs


def build_experiment_matrix() -> list[PolicyRunId]:
    return [
        PolicyRunId(
            cell=TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=seed),
            policy=policy,
        )
        for policy in sorted(CONTROLLED_POLICIES)
        for seed in BASE_CONFIG.experiment.seeds
    ]


def _init_worker(base_dir: Path) -> None:
    configure_logging(
        BASE_CONFIG.logging,
        base_dir / ArtifactDir.LOGS / ArtifactDir.WORKER_LOGS / str(os.getpid()),
    )


def _run_group_worker(
    key: TrainingCellId,
    group_cells: list[PolicyRunId],
    configs: dict[PolicyRunId, DatpConfig],
    base_dir: Path,
    data_root: Path,
    group_idx: Index,
    total_groups: SignedCount,
) -> SweepResult:
    result = SweepResult()
    _process_group(
        key, group_cells, configs, base_dir, result, group_idx, total_groups, data_root
    )
    return result


def run_sweep(
    *,
    base_dir: Path,
    data_root: Path | None = None,
    workers: WorkerCount = BASE_CONFIG.runtime.sweep_workers,
) -> SweepResult:
    t_start = time.monotonic()
    print_step(SweepStep.BUILD_MATRIX, detail="")
    cells = build_experiment_matrix()
    result = SweepResult(total=len(cells))
    print_sweep_banner(len(cells), str(base_dir))

    print_step(SweepStep.VALIDATE_MATRIX, detail="")
    errors, pre_composed_configs = validate_sweep(cells)

    if errors:
        for err in errors:
            logger.error("pre-validation failure", error=str(err))
        raise SystemExit(f"Sweep blocked: {len(errors)} config validation error(s)")

    groups: dict[TrainingCellId, list[PolicyRunId]] = defaultdict(list)
    for cell in cells:
        groups[cell.cell].append(cell)

    data_root = data_root if data_root is not None else base_dir
    ordered = sorted(groups.items(), key=lambda kv: (kv[0].stage, kv[0].seed))
    if workers == 1:
        for group_idx, (key, group_cells) in enumerate(ordered, start=1):
            _process_group(
                key,
                group_cells,
                pre_composed_configs,
                base_dir,
                result,
                group_idx,
                len(ordered),
                data_root,
            )
    else:
        with ProcessPoolExecutor(
            max_workers=min(workers, len(ordered)),
            mp_context=multiprocessing.get_context("spawn"),
            initializer=_init_worker,
            initargs=(base_dir,),
        ) as pool:
            futures = [
                pool.submit(
                    _run_group_worker,
                    key,
                    group_cells,
                    {cell: pre_composed_configs[cell] for cell in group_cells},
                    base_dir,
                    data_root,
                    group_idx,
                    len(ordered),
                )
                for group_idx, (key, group_cells) in enumerate(ordered, start=1)
            ]
            for future in futures:
                partial = future.result()
                result.completed += partial.completed
                result.skipped += partial.skipped
                result.failed += partial.failed
    total_elapsed = time.monotonic() - t_start
    print_sweep_summary(result, total_elapsed)
    return result


def _is_done(cell: PolicyRunId, base_dir: Path) -> bool:
    return results_exist(cell.policy, cell.stage, cell.seed, base_dir=base_dir)


def _account_skip(cell: PolicyRunId, result: SweepResult) -> None:
    logger.info("skipping completed cell", cell=cell.audit_id())
    result.skipped += 1
    print_policy_result(cell.policy, PolicyRunStatus.SKIPPED, 0.0)


def _process_group(
    key: TrainingCellId,
    group_cells: list[PolicyRunId],
    pre_composed_configs: dict[PolicyRunId, DatpConfig],
    base_dir: Path,
    result: SweepResult,
    group_idx: Index,
    total_groups: SignedCount,
    data_root: Path,
) -> None:
    print_group_header(key.stage, key.seed, len(group_cells), group_idx, total_groups)
    pending_cells = [c for c in group_cells if not _is_done(c, base_dir)]

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
        if _is_done(cell, base_dir):
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
    seed: RandomSeed,
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
            print_policy_result(cell.policy, PolicyRunStatus.FAILED, 0.0)
        for cell in group_cells:
            if cell not in pending_cells:
                _account_skip(cell, result)
        return False


def _run_shared_fl_group(
    group_cells: list[PolicyRunId],
    pre_composed_configs: dict[PolicyRunId, DatpConfig],
    base_dir: Path,
    data_root: Path,
) -> tuple[SignedCount, SignedCount]:
    first_cell = group_cells[0]
    stage, seed = first_cell.stage, first_cell.seed
    cfg = pre_composed_configs[first_cell]

    prepared_dir = processed_root(dataset_for_stage(stage), base_dir=data_root)

    for cell in group_cells:
        output_dir = (
            ArtifactLayout(base_dir=base_dir, stage=cell.stage)
            .policy_run(cell)
            .result_dir
        )
        write_resolved_config(pre_composed_configs[cell], output_dir)

    key = TrainingCellId(stage=stage, seed=seed)
    set_seeds(seed)

    try:
        ctx = build_shared_context(
            PipelineRequest(
                key=key,
                policy=ThresholdPolicy.GLOBAL_THRESHOLD,
                cfg=cfg,
                base_dir=base_dir,
                prepared_dir=prepared_dir,
            )
        )
    except Exception:
        logger.exception(
            "shared group setup failed",
            stage=key.stage,
            seed=key.seed,
            n_failed=len(group_cells),
        )
        for cell in group_cells:
            print_policy_result(cell.policy, PolicyRunStatus.FAILED, 0.0)
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
        )
        try:
            evaluate_policy(cell_request, ctx)
            print_policy_result(
                cell.policy, PolicyRunStatus.DONE, time.monotonic() - t0
            )
            completed += 1
        except Exception:
            logger.exception(
                "cell failed", policy=cell.policy, stage=key.stage, seed=key.seed
            )
            print_policy_result(
                cell.policy, PolicyRunStatus.FAILED, time.monotonic() - t0
            )
            failed += 1
    return completed, failed
