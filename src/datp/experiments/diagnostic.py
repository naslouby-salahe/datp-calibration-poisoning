from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from datp.artifacts.io import write_json_atomic, write_metrics_atomic
from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.lifecycle import RunLifecycle
from datp.artifacts.names import ArtifactFile
from datp.checkpointing.enums import CheckpointProtocolMode
from datp.config.compose import compose_config, write_resolved_config
from datp.config.models import DatpConfig
from datp.core.enums import (
    Baseline,
    Regime,
)
from datp.core.identity import TrainingCellId
from datp.core.logging import get_logger
from datp.core.seeds import set_seeds
from datp.evaluation.metrics import EvaluationResult, evaluate_baseline
from datp.experiments.console import print_summary, step_context
from datp.experiments.enums import (
    ContingencyDecision,
    DiagnosticStep,
)
from datp.experiments.executor import SharedTrainingExecutor
from datp.experiments.models import ContingencyRecord, PipelineRequest
from datp.thresholding.metrics_serialization import SweepMetrics, build_metrics_dict
from datp.thresholding.thresholds import derive_threshold

logger = get_logger(__name__)

# ── canonical identity strings for inline diagnostic metrics provenance ───


@dataclass(frozen=True, slots=True)
class DiagnosticInlineIdentity:
    config: str = "DIAGNOSTIC_INLINE_CONFIG"
    split_manifest: str = "DIAGNOSTIC_INLINE_MANIFEST"
    model_checkpoint: str = "DIAGNOSTIC_INLINE_CHECKPOINT"
    score_artifact: str = "DIAGNOSTIC_INLINE_SCORES"


DIAGNOSTIC_INLINE = DiagnosticInlineIdentity()

# ── typed result containers ───────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class DiagnosticMetrics:
    regime: Regime
    seed: int
    alpha: float | None
    b1: SweepMetrics
    b2: SweepMetrics
    delta_cv_fpr: float
    diagnostic_tag: str


@dataclass(frozen=True, slots=True)
class DiagnosticExtras:
    contingency: ContingencyDecision | None = None


# ── type aliases ──────────────────────────────────────────────────────────

PrepareFn = Callable[[], None]
ExtrasFn = Callable[
    [Path, DatpConfig, EvaluationResult, EvaluationResult], DiagnosticExtras
]


@dataclass(frozen=True, slots=True)
class DiagnosticRequest:
    regime: Regime
    seed: int
    output_dir: Path
    run_dir: Path
    prepared_dir: Path
    prepare_fn: PrepareFn
    diagnostic_tag: str
    alpha: float | None
    skip_prepare: bool
    extras_fn: ExtrasFn | None
    phase3_dir: Path | None


def run_diagnostic(request: DiagnosticRequest) -> None:
    """Execute the B1/B2 diagnostic pipeline for one (regime, seed, alpha) cell."""
    t0 = time.monotonic()

    with step_context(DiagnosticStep.COMPOSE_CONFIG):
        cfg = compose_config(
            regime=request.regime,
            baseline=Baseline.B1,
            seed=request.seed,
            alpha=request.alpha,
        )
        if cfg.checkpoint_protocol is not None:
            cfg = cfg.model_copy(
                update={
                    "checkpoint_protocol": cfg.checkpoint_protocol.model_copy(
                        update={"mode": CheckpointProtocolMode.DISABLED}
                    )
                }
            )

    write_resolved_config(cfg, request.run_dir)

    with step_context(DiagnosticStep.PREPARE_DATA):
        manifest_file = request.prepared_dir / ArtifactFile.MANIFEST
        if manifest_file.exists():
            logger.info(
                "prepared data found, skipping preparation",
                prepared_dir=str(request.prepared_dir),
            )
        elif request.skip_prepare:
            logger.warning(
                "--skip-prepare set but manifest missing; running preparation",
                prepared_dir=str(request.prepared_dir),
            )
            request.prepare_fn()
        else:
            request.prepare_fn()

    b1_eval, b2_eval, diagnostics = _run_b1_b2_evaluation(
        cfg=cfg,
        prepared_dir=request.prepared_dir,
        output_dir=request.output_dir,
        regime=request.regime,
        seed=request.seed,
        alpha=request.alpha,
        diagnostic_tag=request.diagnostic_tag,
    )

    extras = DiagnosticExtras()
    with (
        step_context(DiagnosticStep.WRITE_METRICS),
        RunLifecycle(request.run_dir, seed=request.seed),
    ):
        write_metrics_atomic(request.run_dir, diagnostics)
        logger.info("metrics written", path=str(request.run_dir / ArtifactFile.METRICS))
        if request.extras_fn is not None:
            extras = request.extras_fn(request.run_dir, cfg, b1_eval, b2_eval)

    coverage = (
        len(b1_eval.eligible_ids),
        len(b1_eval.eligible_ids) + len(b1_eval.pending_ids),
    )
    with step_context(DiagnosticStep.SUMMARY):
        print_summary(
            request.regime,
            request.seed,
            b1_eval.cv_fpr,
            b2_eval.cv_fpr,
            coverage,
            str(request.run_dir),
            time.monotonic() - t0,
            alpha=request.alpha,
            contingency=extras.contingency,
        )


def _run_b1_b2_evaluation(
    *,
    cfg: DatpConfig,
    prepared_dir: Path,
    output_dir: Path,
    regime: Regime,
    seed: int,
    alpha: float | None,
    diagnostic_tag: str,
) -> tuple[EvaluationResult, EvaluationResult, DiagnosticMetrics]:
    key = TrainingCellId(regime=regime, seed=seed, alpha=alpha)
    request = PipelineRequest(
        key=key,
        baseline=Baseline.B1,
        cfg=cfg,
        base_dir=output_dir,
        prepared_dir=prepared_dir,
        checkpoint_round=None,
    )

    with step_context(DiagnosticStep.SET_SEEDS):
        set_seeds(seed)

    with step_context(DiagnosticStep.FL_TRAINING):
        ctx = SharedTrainingExecutor(
            step_fn=None, checkpoint_status_fn=None
        ).build_context(request)

    n_min = cfg.threshold.n_min
    q = cfg.threshold.q

    with step_context(DiagnosticStep.DERIVE_THRESHOLDS):
        b1_result = derive_threshold(
            Baseline.B1,
            ctx.client_errors,
            n_min,
            q,
            ctx.tau_global,
            regime,
            threshold_cfg=cfg.threshold,
            seed=seed,
            alpha=alpha,
        )
        tau_global = b1_result.tau_global
        b2_result = derive_threshold(
            Baseline.B2,
            ctx.client_errors,
            n_min,
            q,
            tau_global,
            regime,
            threshold_cfg=cfg.threshold,
            seed=seed,
            alpha=alpha,
        )

    with step_context(DiagnosticStep.EVALUATE):
        score_root = ArtifactLayout(
            base_dir=output_dir, regime=regime
        ).score_cell(key).score_dir
        b1_eval = evaluate_baseline(
            b1_result.client_thresholds,
            score_root,
            regime,
            seed,
            alpha,
            score_provider=ctx.score_provider,
        )
        b2_eval = evaluate_baseline(
            b2_result.client_thresholds,
            score_root,
            regime,
            seed,
            alpha,
            score_provider=ctx.score_provider,
        )

    inline = DIAGNOSTIC_INLINE
    return b1_eval, b2_eval, DiagnosticMetrics(
        regime=regime,
        seed=seed,
        alpha=alpha,
        b1=build_metrics_dict(
            b1_eval,
            b1_result,
            config_identity=inline.config,
            split_manifest_identity=inline.split_manifest,
            model_checkpoint_identity=inline.model_checkpoint,
            score_artifact_identity=inline.score_artifact,
            checkpoint_round=None,
        ),
        b2=build_metrics_dict(
            b2_eval,
            b2_result,
            config_identity=inline.config,
            split_manifest_identity=inline.split_manifest,
            model_checkpoint_identity=inline.model_checkpoint,
            score_artifact_identity=inline.score_artifact,
            checkpoint_round=None,
        ),
        delta_cv_fpr=b1_eval.cv_fpr - b2_eval.cv_fpr,
        diagnostic_tag=diagnostic_tag,
    )


def make_regime_a_extras(phase3_dir: Path | None) -> ExtrasFn:
    def _extras(
        run_dir: Path,
        cfg: DatpConfig,
        b1_eval: EvaluationResult,
        b2_eval: EvaluationResult,
    ) -> DiagnosticExtras:
        with step_context(DiagnosticStep.CONTINGENCY_DECISION):
            contingency = _make_contingency_decision(
                b1_eval,
                b2_eval,
                dispersion_threshold=cfg.statistics.dispersion_threshold,
            )
            write_json_atomic(
                run_dir / "contingency_decision.json",
                contingency.model_dump(mode="json"),
            )
            if phase3_dir is not None:
                phase3_dir.mkdir(parents=True, exist_ok=True)
                write_json_atomic(
                    phase3_dir / "contingency_decision.json",
                    contingency.model_dump(mode="json"),
                )
            logger.info(
                "contingency decision made",
                decision=contingency.decision.value,
                cv_fpr_b1=contingency.cv_fpr_b1,
            )
        return DiagnosticExtras(contingency=contingency.decision)

    return _extras


def _make_contingency_decision(
    b1_eval: EvaluationResult,
    b2_eval: EvaluationResult,
    *,
    dispersion_threshold: float,
) -> ContingencyRecord:
    """Preliminary Regime A check; GO means B1 dispersion justifies full-matrix compute."""
    cv_b1 = b1_eval.cv_fpr
    cv_b2 = b2_eval.cv_fpr

    decision = (
        ContingencyDecision.GO
        if cv_b1 > dispersion_threshold
        else ContingencyDecision.CONTINGENCY
    )

    return ContingencyRecord(
        decision=decision,
        cv_fpr_b1=cv_b1,
        cv_fpr_b2=cv_b2,
        delta_cv_fpr=cv_b1 - cv_b2,
        dispersion_threshold=dispersion_threshold,
        rationale=(
            f"Preliminary diagnostic check: CV(FPR)_B1 = {cv_b1:.4f} and "
            f"CV(FPR)_B2 = {cv_b2:.4f} indicate a measurable threshold-scope effect. "
            "The final primary endpoint is the Regime A B1-vs-B2 per-seed bootstrap CI on CV(FPR)."
        ),
    )
