"""Shared-training and threshold-evaluation executors for policy-run pipelines."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from datp.artifacts.io import write_metrics_atomic
from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.lifecycle import RunLifecycle
from datp.artifacts.names import ArtifactFile
from datp.core.identity import PolicyRunId
from datp.core.logging import get_logger
from datp.core.provenance import MISSING_MANIFEST_HASH, hash_file, hash_jsonable
from datp.core.tracking import (
    TrackingMetric,
    TrackingMetricKey,
    TrackingMetrics,
    log_metrics,
)
from datp.evaluation.metrics import evaluate_policy_run
from datp.experiments.models import PipelineRequest, SharedPipelineContext, SweepStep
from datp.experiments.stages.train_encoder import ensure_fl_checkpoint
from datp.scoring.loading import ScoreProvider, load_main_cal_errors
from datp.thresholding.eligibility import (
    compute_client_thresholds,
    compute_tau_global,
    identify_eligible,
)
from datp.thresholding.metrics_serialization import (
    MetricsBuildRequest,
    SweepMetrics,
    build_metrics_dict,
)
from datp.thresholding.thresholds import _DeriveInput, derive_threshold

logger = get_logger(__name__)


class SharedTrainingExecutor:
    """Executor for shared FL training steps: checkpoint, cal scores, eligibility, and context."""

    def __init__(
        self,
        *,
        step_fn: Callable[[SweepStep, str], None] | None,
        checkpoint_status_fn: Callable[[bool, Path], None] | None,
    ) -> None:
        """Initialize with optional step and checkpoint-status callbacks."""
        self._step_fn = step_fn
        self._checkpoint_status_fn = checkpoint_status_fn

    def _step(self, step: SweepStep, detail: str = "") -> None:
        """Invoke the step callback if provided."""
        if self._step_fn is not None:
            self._step_fn(step, detail)

    def build_context(self, request: PipelineRequest) -> SharedPipelineContext:
        """Build shared pipeline context by running FL checkpoint, calibration scores, and eligibility."""
        key = request.key
        cfg = request.cfg

        ensure_fl_checkpoint(
            request,
            step_fn=self._step_fn,
            checkpoint_status_fn=self._checkpoint_status_fn,
            lock_timeout=cfg.runtime.lock_timeout_seconds,
        )

        self._step(SweepStep.LOAD_CAL_SCORES)
        client_errors = load_main_cal_errors(
            key.stage, key.seed, request.base_dir, request.checkpoint_round
        )

        self._step(SweepStep.COMPUTE_ELIGIBILITY)
        eligible, pending = identify_eligible(client_errors, n_min=cfg.threshold.n_min)

        self._step(SweepStep.COMPUTE_TAU_GLOBAL)
        client_taus = compute_client_thresholds(
            client_errors, eligible, q=cfg.threshold.q
        )
        tau_global = compute_tau_global(client_taus)

        self._step(SweepStep.INIT_SCORE_PROVIDER)
        layout = ArtifactLayout(base_dir=request.base_dir, stage=key.stage)
        score_cell = (
            layout.score_cell_for_round(key, request.checkpoint_round)
            if request.checkpoint_round is not None
            else layout.score_cell(key)
        )
        score_provider = ScoreProvider(score_cell.score_dir)

        return SharedPipelineContext(
            key=key,
            client_errors=client_errors,
            eligible=eligible,
            pending=pending,
            client_taus=client_taus,
            tau_global=tau_global,
            score_provider=score_provider,
            checkpoint_round=request.checkpoint_round,
        )


class ThresholdEvaluationExecutor:
    """Executor for threshold derivation and policy-run evaluation within a shared context."""

    def __init__(self, *, step_fn: Callable[[SweepStep, str], None] | None) -> None:
        """Initialize with an optional step-tracking callback."""
        self._step_fn = step_fn

    def _step(self, step: SweepStep, detail: str = "") -> None:
        """Invoke the step callback if provided."""
        if self._step_fn is not None:
            self._step_fn(step, detail)

    def run(self, request: PipelineRequest, ctx: SharedPipelineContext) -> SweepMetrics:
        """Derive thresholds, evaluate the policy run, write metrics, and log tracking data."""
        policy = request.policy
        cfg = request.cfg
        layout = ArtifactLayout(base_dir=request.base_dir, stage=ctx.key.stage)
        run = PolicyRunId(cell=ctx.key, policy=policy)

        run_paths = (
            layout.policy_run_for_round(run, ctx.checkpoint_round)
            if ctx.checkpoint_round is not None
            else layout.policy_run(run)
        )
        res_dir = run_paths.result_dir

        with RunLifecycle(res_dir, policy=policy, seed=ctx.key.seed):
            self._step(SweepStep.DERIVE_THRESHOLD, policy)
            threshold_result = derive_threshold(
                _DeriveInput(
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

            self._step(SweepStep.EVALUATE, policy)
            eval_result = evaluate_policy_run(
                threshold_result.client_thresholds,
                ctx.score_provider.score_root,
                ctx.key.stage,
                ctx.key.seed,
                score_provider=ctx.score_provider,
            )

            self._step(SweepStep.WRITE_METRICS, policy)
            score_paths = (
                layout.score_cell_for_round(ctx.key, ctx.checkpoint_round)
                if ctx.checkpoint_round is not None
                else layout.score_cell(ctx.key)
            )
            ckpt_dir = (
                layout.checkpoint_dir_for_round(ctx.key, ctx.checkpoint_round)
                if ctx.checkpoint_round is not None
                else layout.checkpoint_dir(ctx.key)
            )

            ckpt_file = ckpt_dir / ArtifactFile.MODEL_CHECKPOINT
            prepared_manifest = request.prepared_dir / ArtifactFile.MANIFEST

            metrics = build_metrics_dict(
                MetricsBuildRequest(
                    eval_result=eval_result,
                    threshold_result=threshold_result,
                    config_identity=hash_jsonable(request.cfg.model_dump()),
                    split_manifest_identity=hash_file(prepared_manifest)
                    if prepared_manifest.exists()
                    else MISSING_MANIFEST_HASH,
                    model_checkpoint_identity=hash_file(ckpt_file),
                    score_artifact_identity=hash_file(score_paths.manifest_path),
                    checkpoint_round=ctx.checkpoint_round,
                )
            )
            write_metrics_atomic(res_dir, metrics)
            logger.info("results written", path=str(res_dir / ArtifactFile.METRICS))

            log_metrics(
                TrackingMetrics(
                    (
                        TrackingMetric.for_policy(
                            policy,
                            TrackingMetricKey.ELIGIBLE,
                            threshold_result.eligible_count,
                        ),
                        TrackingMetric.for_policy(
                            policy,
                            TrackingMetricKey.PENDING,
                            threshold_result.pending_count,
                        ),
                        TrackingMetric.for_policy(
                            policy,
                            TrackingMetricKey.TAU_GLOBAL,
                            threshold_result.tau_global,
                        ),
                    )
                ),
                step=None,
                prefix=None,
            )
            return metrics

        raise RuntimeError(
            "[pipeline.executor] unreachable: RunLifecycle always returns or raises. Expected: . Got: ."
        )
