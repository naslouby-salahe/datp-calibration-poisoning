"""B1/B2/B3/B4 all derive thresholds from the same shared score artifacts produced by one FL training run per (regime, seed, alpha)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from datp.artifacts.io import write_metrics_atomic
from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.lifecycle import RunLifecycle
from datp.artifacts.names import ArtifactFile
from datp.core.enums import Baseline
from datp.core.errors import fmt
from datp.core.identity import BaselineRunId
from datp.core.logging import get_logger
from datp.core.provenance import MISSING_MANIFEST_HASH, hash_file, hash_jsonable
from datp.core.tracking import (
    TrackingMetric,
    TrackingMetricKey,
    TrackingMetrics,
    log_metrics,
)
from datp.evaluation.metrics import evaluate_baseline
from datp.experiments.enums import SweepStep
from datp.experiments.models import PipelineRequest, SharedPipelineContext
from datp.experiments.stages.train_encoder import ensure_fl_checkpoint
from datp.scoring.cal_loading import load_main_cal_errors
from datp.scoring.loading import ScoreProvider
from datp.thresholding.eligibility import (
    compute_client_thresholds,
    compute_tau_global,
    identify_eligible,
)
from datp.thresholding.metrics_serialization import SweepMetrics, build_metrics_dict
from datp.thresholding.thresholds import _DeriveInput, derive_threshold

logger = get_logger(__name__)


class SharedTrainingExecutor:
    def __init__(
        self,
        *,
        step_fn: Callable[[SweepStep, str], None] | None,
        checkpoint_status_fn: Callable[[bool, Path], None] | None,
    ) -> None:
        self._step_fn = step_fn
        self._checkpoint_status_fn = checkpoint_status_fn

    def _step(self, step: SweepStep, detail: str = "") -> None:
        if self._step_fn is not None:
            self._step_fn(step, detail)

    def build_context(self, request: PipelineRequest) -> SharedPipelineContext:
        """Train once then load all shared per-group artifacts; caller must set seeds before calling."""
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
            key.regime,
            key.seed,
            key.alpha,
            request.base_dir,
            request.checkpoint_round,
        )

        self._step(SweepStep.COMPUTE_ELIGIBILITY)
        eligible, pending = identify_eligible(client_errors, n_min=cfg.threshold.n_min)

        self._step(SweepStep.COMPUTE_TAU_GLOBAL)
        client_taus = compute_client_thresholds(
            client_errors, eligible, q=cfg.threshold.q
        )
        tau_global = compute_tau_global(client_taus)

        self._step(SweepStep.INIT_SCORE_PROVIDER)
        layout = ArtifactLayout(base_dir=request.base_dir, regime=key.regime)
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
    def __init__(self, *, step_fn: Callable[[SweepStep, str], None] | None) -> None:
        self._step_fn = step_fn

    def _step(self, step: SweepStep, detail: str = "") -> None:
        if self._step_fn is not None:
            self._step_fn(step, detail)

    def run(
        self,
        request: PipelineRequest,
        ctx: SharedPipelineContext,
    ) -> SweepMetrics:
        baseline = request.baseline
        cfg = request.cfg
        layout = ArtifactLayout(base_dir=request.base_dir, regime=ctx.key.regime)
        run = BaselineRunId(cell=ctx.key, baseline=baseline)
        run_paths = (
            layout.baseline_run_for_round(run, ctx.checkpoint_round)
            if ctx.checkpoint_round is not None
            else layout.baseline_run(run)
        )
        res_dir = run_paths.result_dir

        with RunLifecycle(res_dir, baseline=baseline, seed=ctx.key.seed):
            self._step(SweepStep.DERIVE_THRESHOLD, baseline)
            threshold_result = derive_threshold(
                _DeriveInput(
                    baseline=baseline,
                    client_errors=ctx.client_errors,
                    n_min=cfg.threshold.n_min,
                    q=cfg.threshold.q,
                    tau_global=ctx.tau_global,
                    regime=ctx.key.regime,
                    threshold_cfg=cfg.threshold,
                    seed=ctx.key.seed,
                    alpha=ctx.key.alpha,
                )
            )
            logger.info(
                "threshold derivation complete",
                baseline=baseline,
                tau_global=threshold_result.tau_global,
                eligible=threshold_result.eligible_count,
                pending=threshold_result.pending_count,
            )

            self._step(SweepStep.EVALUATE, baseline)
            eval_result = evaluate_baseline(
                threshold_result.client_thresholds,
                ctx.score_provider.score_root,
                ctx.key.regime,
                ctx.key.seed,
                ctx.key.alpha,
                score_provider=ctx.score_provider,
            )

            self._step(SweepStep.WRITE_METRICS, baseline)
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
            score_manifest = score_paths.manifest_path
            prepared_manifest = request.prepared_dir / ArtifactFile.MANIFEST
            metrics = build_metrics_dict(
                eval_result,
                threshold_result,
                config_identity=hash_jsonable(request.cfg.model_dump()),
                split_manifest_identity=hash_file(prepared_manifest)
                if prepared_manifest.exists()
                else MISSING_MANIFEST_HASH,
                model_checkpoint_identity=hash_file(ckpt_file),
                score_artifact_identity=hash_file(score_manifest),
                checkpoint_round=ctx.checkpoint_round,
            )
            write_metrics_atomic(res_dir, metrics)
            logger.info("results written", path=str(res_dir / ArtifactFile.METRICS))

            log_metrics(
                TrackingMetrics(
                    (
                        TrackingMetric.for_baseline(
                            baseline,
                            TrackingMetricKey.ELIGIBLE,
                            threshold_result.eligible_count,
                        ),
                        TrackingMetric.for_baseline(
                            baseline,
                            TrackingMetricKey.PENDING,
                            threshold_result.pending_count,
                        ),
                        TrackingMetric.for_baseline(
                            baseline,
                            TrackingMetricKey.TAU_GLOBAL,
                            threshold_result.tau_global,
                        ),
                    )
                ),
                step=None,
                prefix=None,
            )

            return metrics

        raise RuntimeError(  # pragma: no cover — unreachable; RunLifecycle.__exit__ never suppresses
            fmt(
                "pipeline.executor",
                "unreachable: RunLifecycle always returns or raises",
                "",
                "",
            )
        )


class IsolatedBaselineExecutor:
    def __init__(self, *, step_fn: Callable[[SweepStep, str], None] | None) -> None:
        self._step_fn = step_fn

    def _step(self, step: SweepStep, detail: str = "") -> None:
        if self._step_fn is not None:
            self._step_fn(step, detail)

    def run(self, request: PipelineRequest) -> None:
        from datp.core.enums import ISOLATED_BASELINES
        from datp.experiments.baselines.b0_centralized import B0RunRequest, run_b0

        baseline = request.baseline
        key = request.key
        cfg = request.cfg

        if baseline not in ISOLATED_BASELINES:
            raise ValueError(
                fmt(
                    "pipeline.executor",
                    "Not an isolated baseline",
                    str(sorted(ISOLATED_BASELINES)),
                    baseline,
                )
            )

        out_dir = (
            ArtifactLayout(base_dir=request.base_dir, regime=key.regime)
            .baseline_run(BaselineRunId(cell=key, baseline=baseline))
            .result_dir
        )

        if baseline == Baseline.B0:
            self._step(SweepStep.RUN_B0, key.label())
            run_b0(
                B0RunRequest(
                    prepared_dir=request.prepared_dir,
                    output_dir=out_dir,
                    seed=key.seed,
                    input_dim=cfg.model.input_dim,
                    hidden_dims=cfg.model.encoder_dims,
                    n_min=cfg.threshold.n_min,
                    q=cfg.threshold.q,
                    epochs=cfg.model.epochs,
                    patience=cfg.model.patience,
                    lr=cfg.model.lr,
                    batch_size=cfg.machine.batch_size_train,
                    activation=cfg.model.activation,
                    use_bn=cfg.model.use_bn,
                    training_progress_interval=cfg.logging.training_progress_interval,
                    val_fraction=cfg.dataset.b0_val_fraction,
                    regime=key.regime,
                )
            )
