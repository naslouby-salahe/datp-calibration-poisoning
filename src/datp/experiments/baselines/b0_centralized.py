"""B0 — Centralized reference comparator; violates FL by pooling all data. Not part of the controlled B1–B4 ladder and never described as a guaranteed upper bound."""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl
import torch

from datp.artifacts.io import write_metrics_atomic
from datp.artifacts.names import ArtifactFile
from datp.core.device import resolve_device
from datp.core.enums import (
    BASELINE_THRESHOLD_SOURCE,
    THRESHOLD_AGGREGATION_BY_BASELINE,
    Activation,
    B0NormalizationMode,
    Baseline,
    NormalizationScope,
    Regime,
    RunKind,
)
from datp.core.errors import fmt
from datp.core.logging import get_logger
from datp.core.metric_enums import ConfusionKey, MetricName
from datp.core.provenance import (
    MISSING_MANIFEST_HASH,
    NOT_APPLICABLE_B0_DIRECT_EVAL,
    git_commit,
    hash_file,
    hash_jsonable,
    source_hash,
    utc_timestamp,
)
from datp.core.seeds import set_seeds
from datp.core.tracking import log_artifact, log_metrics, tracking_run
from datp.core.types import (
    B0Result,
    ClientEvalResult,
    ClientThreshold,
    MetricsProvenance,
)
from datp.data.regimes.catalog import dataset_for_regime
from datp.data.scaling import apply_scaler, fit_scaler
from datp.data.splits import Split
from datp.evaluation.metrics import (
    ClientEvaluationRecord,
    build_evaluation_result,
    compute_client_record,
)
from datp.evaluation.ranking import compute_binary_ranking_metrics
from datp.federated.data_loading import (
    df_to_tensor,
    discover_client_dirs,
    load_client_artifact,
    release_freed_heap,
)
from datp.modeling.autoencoder import Autoencoder
from datp.modeling.centralized_training import train_ae
from datp.scoring.generation import compute_reconstruction_errors
from datp.thresholding.metrics_serialization import (
    METRIC_SCHEMA_VERSION,
    METRICS_SCHEMA_VERSION,
    THRESHOLD_SCHEMA_VERSION,
)
from datp.thresholding.thresholds import percentile_threshold

logger = get_logger(__name__)

_NORMALIZATION_SCOPE: dict[B0NormalizationMode, NormalizationScope] = {
    B0NormalizationMode.POOLED_ZSCORE: NormalizationScope.POOLED_ZSCORE,
    B0NormalizationMode.PER_CLIENT_PREPARED: NormalizationScope.PER_CLIENT_ZSCORE,
}


@dataclass(frozen=True, slots=True)
class B0ConfigIdentity:
    """Training config fingerprint for B0 provenance — only the parameters that
    materially change training behavior."""

    input_dim: int
    hidden_dims: list[int]
    n_min: int
    q: float
    epochs: int
    lr: float
    batch_size: int


@dataclass(frozen=True, slots=True)
class B0RunRequest:
    prepared_dir: Path
    output_dir: Path
    seed: int
    input_dim: int
    hidden_dims: list[int]
    n_min: int
    q: float
    epochs: int
    patience: int
    lr: float
    batch_size: int
    val_fraction: float
    activation: Activation
    use_bn: bool
    training_progress_interval: int
    regime: Regime


def _validate_b0_regime(regime: Regime) -> None:
    if regime not in (Regime.A, Regime.B):
        raise ValueError(
            fmt(
                "baselines.b0",
                "B0 is not supported for this regime",
                "regime a or b",
                repr(regime),
            )
        )


def _run_b0_impl(
    request: B0RunRequest,
    *,
    normalization_mode: B0NormalizationMode,
) -> B0Result:
    prepared_dir = request.prepared_dir
    output_dir = request.output_dir
    seed = request.seed
    input_dim = request.input_dim
    hidden_dims = request.hidden_dims
    n_min = request.n_min
    q = request.q
    epochs = request.epochs
    patience = request.patience
    lr = request.lr
    batch_size = request.batch_size
    val_fraction = request.val_fraction
    activation = request.activation
    use_bn = request.use_bn
    training_progress_interval = request.training_progress_interval
    regime = request.regime

    _validate_b0_regime(regime)
    norm_scope = _NORMALIZATION_SCOPE[normalization_mode]
    run_name = (
        f"{Baseline.B0.value}_{normalization_mode.value}_{regime.value}_seed{seed}"
    )
    with tracking_run(
        run_name=run_name,
        params={
            "baseline": str(Baseline.B0),
            "regime": str(regime),
            "seed": str(seed),
            "epochs": str(epochs),
            "patience": str(patience),
            "learning_rate": str(lr),
            "batch_size": str(batch_size),
            "q": str(q),
            "n_min": str(n_min),
            "normalization_mode": normalization_mode.value,
        },
        tags={
            "baseline": str(Baseline.B0),
            "pipeline": RunKind.CENTRALIZED_REFERENCE.value,
        },
    ):
        set_seeds(seed)

        device = resolve_device(require_cuda=True)
        client_dirs = discover_client_dirs(prepared_dir)
        logger.info(
            "found clients",
            baseline=Baseline.B0,
            n_clients=len(client_dirs),
            path=str(prepared_dir),
        )

        train_frames: list[pl.DataFrame] = []
        cal_frames: list[pl.DataFrame] = []
        client_cal_counts: dict[str, int] = {}

        for cd in client_dirs:
            client_id = cd.name
            train_frames.append(load_client_artifact(cd, Split.TRAIN))
            cal_df = load_client_artifact(cd, Split.CAL)
            client_cal_counts[client_id] = len(cal_df)
            cal_frames.append(cal_df)

        pooled_train = pl.concat(train_frames, how="vertical")
        pooled_cal = pl.concat(cal_frames, how="vertical")

        if pooled_train.shape[1] != input_dim:
            raise ValueError(
                fmt(
                    "baselines.b0",
                    "input_dim mismatch",
                    f"{input_dim} columns",
                    f"{pooled_train.shape[1]} columns",
                )
            )

        global_scaler = None
        if normalization_mode == B0NormalizationMode.POOLED_ZSCORE:
            logger.warning(
                "POOLED_ZSCORE applies a second z-score scaler on top of already "
                "per-client-scaled prepared data; metrics are not comparable to "
                "PER_CLIENT_PREPARED baseline runs"
            )
            global_scaler = fit_scaler(pooled_train)
            pooled_train = apply_scaler(pooled_train, global_scaler)
            pooled_cal = apply_scaler(pooled_cal, global_scaler)

        n_total = len(pooled_train)
        n_val = max(1, int(n_total * val_fraction))
        indices = np.random.default_rng(seed).permutation(n_total)
        val_idx, train_idx = indices[:n_val], indices[n_val:]

        pooled_train_np = pooled_train.to_numpy()
        train_tensor = df_to_tensor(pooled_train_np[train_idx], device)
        val_tensor = df_to_tensor(pooled_train_np[val_idx], device)
        del pooled_train_np, pooled_train, train_frames
        release_freed_heap()

        model = Autoencoder(
            input_dim=input_dim,
            hidden_dims=hidden_dims,
            activation=activation,
            use_bn=use_bn,
        )
        model, epochs_run = train_ae(
            model,
            train_tensor,
            val_tensor,
            epochs=epochs,
            patience=patience,
            lr=lr,
            batch_size=batch_size,
            device=device,
            tracking_namespace=f"{Baseline.B0}.train",
            training_progress_interval=training_progress_interval,
        )

        cal_tensor = df_to_tensor(pooled_cal, device)
        cal_errors = compute_reconstruction_errors(model, cal_tensor)
        n_cal_errors = len(cal_errors)
        tau_b0 = percentile_threshold(cal_errors, q=q)
        del cal_tensor, cal_errors, pooled_cal, cal_frames
        release_freed_heap()
        logger.info(
            "b0 threshold computed",
            baseline=Baseline.B0,
            tau_b0=tau_b0,
            q=q,
            n_cal=n_cal_errors,
        )

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        ckpt_path = output_dir / ArtifactFile.MODEL_B0_CHECKPOINT
        tmp_path = ckpt_path.with_suffix(".pt.tmp")
        torch.save(model.state_dict(), tmp_path)
        tmp_path.rename(ckpt_path)
        b0_ckpt_hash = hash_file(ckpt_path)
        logger.info("b0 checkpoint saved", path=str(ckpt_path), hash=b0_ckpt_hash)

        cal_pending_clients = [
            cid for cid, cal_count in client_cal_counts.items() if cal_count < n_min
        ]
        pending_set = set(cal_pending_clients)
        threshold_source = BASELINE_THRESHOLD_SOURCE[Baseline.B0]

        per_client: dict[str, ClientEvalResult] = {}
        full_client_records: dict[str, ClientEvaluationRecord] = {}
        all_test_errors: list[np.ndarray] = []

        for client_dir in client_dirs:
            client_id = client_dir.name
            tb = load_client_artifact(client_dir, Split.TEST_BENIGN)
            ta = load_client_artifact(client_dir, Split.TEST_ATTACK)
            if global_scaler is not None:
                tb = apply_scaler(tb, global_scaler)
                ta = apply_scaler(ta, global_scaler)

            errors_benign = compute_reconstruction_errors(
                model, df_to_tensor(tb, device)
            )
            errors_attack = compute_reconstruction_errors(
                model, df_to_tensor(ta, device)
            )

            ct = ClientThreshold(
                client_id=client_id,
                threshold=tau_b0,
                calibration_pending=client_id in pending_set,
                strategy=Baseline.B0,
            )
            rec = compute_client_record(client_id, errors_benign, errors_attack, ct)
            full_client_records[client_id] = rec

            per_client[client_id] = ClientEvalResult(
                fpr=rec.metrics.fpr,
                tpr=rec.metrics.tpr,
                balanced_accuracy=rec.metrics.balanced_accuracy,
                macro_f1=rec.metrics.macro_f1,
                n_benign=rec.n_benign,
                n_attack=rec.n_attack,
                confusion_matrix={
                    ConfusionKey.TP.value: rec.confusion.tp,
                    ConfusionKey.FP.value: rec.confusion.fp,
                    ConfusionKey.TN.value: rec.confusion.tn,
                    ConfusionKey.FN.value: rec.confusion.fn,
                },
                benign_count=rec.n_benign,
                attack_count=rec.n_attack,
                calibration_pending=client_id in pending_set,
                evaluation_incomplete=rec.n_attack == 0,
                threshold_value=tau_b0,
                threshold_source=threshold_source,
            )

            all_test_errors.extend([errors_benign, errors_attack])
            del tb, ta, errors_benign, errors_attack
            release_freed_heap()

        benign_arrays = all_test_errors[0::2]
        attack_arrays = all_test_errors[1::2]
        pooled_benign = (
            np.concatenate(benign_arrays)
            if benign_arrays
            else np.empty(0, dtype=np.float64)
        )
        pooled_attack = (
            np.concatenate(attack_arrays)
            if attack_arrays
            else np.empty(0, dtype=np.float64)
        )
        ranking = compute_binary_ranking_metrics(pooled_benign, pooled_attack)
        auroc = ranking.auroc
        pr_auc = ranking.pr_auc
        logger.info(
            "b0 pooled auroc",
            baseline=Baseline.B0,
            auroc=auroc,
            normalization_mode=normalization_mode.value,
        )

        canonical_eval = build_evaluation_result(
            baseline=Baseline.B0,
            regime=regime,
            seed=seed,
            alpha=None,
            clients=tuple(full_client_records.values()),
            eligible_ids=tuple(cid for cid in per_client if cid not in pending_set),
            pending_ids=tuple(cal_pending_clients),
            incomplete_ids=tuple(
                cid for cid, metrics in per_client.items() if metrics.n_attack == 0
            ),
        )

        result = B0Result(
            schema_version=METRICS_SCHEMA_VERSION,
            metric_schema_version=METRIC_SCHEMA_VERSION,
            threshold_schema_version=THRESHOLD_SCHEMA_VERSION,
            run_id=f"{regime.value}_{Baseline.B0.value}_seed{seed}",
            run_kind=RunKind.CENTRALIZED_REFERENCE,
            baseline=Baseline.B0,
            regime=regime,
            seed=seed,
            dataset=dataset_for_regime(regime),
            tau_b0=tau_b0,
            tau_global=tau_b0,
            threshold_scope=THRESHOLD_AGGREGATION_BY_BASELINE[Baseline.B0],
            threshold_strategy_name=Baseline.B0.value,
            q=q,
            n_min=n_min,
            eligible_ids=canonical_eval.eligible_ids,
            pending_ids=canonical_eval.pending_ids,
            eval_incomplete_ids=canonical_eval.eval_incomplete_ids,
            eligible_count=canonical_eval.eligible_count,
            pending_count=len(cal_pending_clients),
            eval_incomplete_count=len(canonical_eval.eval_incomplete_ids),
            client_count=canonical_eval.client_count,
            coverage_ratio=canonical_eval.coverage_ratio,
            cv_fpr=canonical_eval.cv_fpr,
            mean_fpr=canonical_eval.mean_fpr,
            std_fpr=canonical_eval.std_fpr,
            cv_tpr=canonical_eval.cv_tpr,
            iqr_fpr=canonical_eval.iqr_fpr,
            iqr_tpr=canonical_eval.iqr_tpr,
            max_min_fpr_gap=canonical_eval.max_min_fpr_gap,
            worst_client_fpr=canonical_eval.worst_client_fpr,
            worst_client_id=canonical_eval.worst_client_id,
            worst_ba=canonical_eval.worst_ba,
            p10_macro_f1=canonical_eval.p10_macro_f1,
            auroc=auroc,
            pr_auc=pr_auc,
            aggregate_metrics={
                MetricName.CV_FPR: canonical_eval.cv_fpr,
                MetricName.MEAN_FPR: canonical_eval.mean_fpr,
                MetricName.STD_FPR: canonical_eval.std_fpr,
                MetricName.CV_TPR: canonical_eval.cv_tpr,
                MetricName.IQR_FPR: canonical_eval.iqr_fpr,
                MetricName.IQR_TPR: canonical_eval.iqr_tpr,
                MetricName.MAX_MIN_FPR_GAP: canonical_eval.max_min_fpr_gap,
                MetricName.WORST_CLIENT_FPR: canonical_eval.worst_client_fpr,
                MetricName.WORST_CLIENT_ID: canonical_eval.worst_client_id,
                MetricName.WORST_BA: canonical_eval.worst_ba,
                MetricName.P10_MACRO_F1: canonical_eval.p10_macro_f1,
            },
            provenance=MetricsProvenance(
                config_identity=hash_jsonable(
                    dataclasses.asdict(
                        B0ConfigIdentity(
                            input_dim=input_dim,
                            hidden_dims=hidden_dims,
                            n_min=n_min,
                            q=q,
                            epochs=epochs,
                            lr=lr,
                            batch_size=batch_size,
                        )
                    )
                ),
                split_manifest_identity=hash_file(prepared_dir / ArtifactFile.MANIFEST)
                if (prepared_dir / ArtifactFile.MANIFEST).exists()
                else MISSING_MANIFEST_HASH,
                model_checkpoint_identity=b0_ckpt_hash,
                score_artifact_identity=NOT_APPLICABLE_B0_DIRECT_EVAL,
                metric_code_version=source_hash([Path(__file__)]),
                threshold_code_version=git_commit(),
                package_version=git_commit(),
                generated_at_utc=utc_timestamp(),
            ),
            threshold_mode=THRESHOLD_AGGREGATION_BY_BASELINE[Baseline.B0],
            n_clients=len(client_dirs),
            calibration_pending_clients=tuple(cal_pending_clients),
            per_client=per_client,
            normalization_scope=norm_scope,
            normalization_mode=normalization_mode,
        )
        metrics_path = write_metrics_atomic(output_dir, result)
        logger.info(
            "b0 results written",
            baseline=Baseline.B0,
            path=str(metrics_path),
            epochs_run=epochs_run,
        )

        log_metrics(
            {
                "tau": tau_b0,
                MetricName.AUROC.value: math.nan if auroc is None else auroc,
                MetricName.PR_AUC.value: math.nan if pr_auc is None else pr_auc,
                "n_clients": float(len(client_dirs)),
                "epochs_run": float(epochs_run),
                "calibration_pending_count": float(len(cal_pending_clients)),
            },
            step=None,
            prefix=Baseline.B0,
        )
        log_artifact(metrics_path, artifact_path="results")

        return result


def run_b0(request: B0RunRequest) -> B0Result:
    return _run_b0_impl(
        request,
        normalization_mode=B0NormalizationMode.PER_CLIENT_PREPARED,
    )


def run_b0_pooled_norm(request: B0RunRequest) -> B0Result:
    return _run_b0_impl(
        request,
        normalization_mode=B0NormalizationMode.POOLED_ZSCORE,
    )
