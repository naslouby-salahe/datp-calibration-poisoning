from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import torch

from datp.config import (
    BASE_CONFIG,
    ConvergenceConfig,
    DatpConfig,
    ExperimentStage,
    FederationConfig,
)
from datp.core import ClientThreshold
from datp.data import ClientData
from datp.enums import (
    POLICY_THRESHOLD_SOURCE,
    Activation,
    ClientStatus,
    MetricName,
    PayloadKey,
    RunKind,
    ThresholdPolicy,
)
from datp.evaluation import (
    BinaryMetrics,
    ClientEvaluationRecord,
    ConfusionCounts,
    EvaluationResult,
    build_evaluation_result,
)
from datp.modeling import Autoencoder
from datp.scoring import ScoringColumn, load_parquets_from_dir


def make_cuda_validation_model() -> Autoencoder:
    """Build a small Autoencoder model for CUDA validation tests."""
    return Autoencoder(
        input_dim=10,
        hidden_dims=[8, 4],
        activation=Activation.RELU,
        use_bn=False,
    )


N_FEATURES = 10


N_TRAIN = 200


N_VAL = 50


N_TEST = 50


SEED = 42


def make_client_data(n_clients: int, seed: int = SEED) -> dict[str, ClientData]:
    """Generate mock client datasets with train, val, test_benign, and test_attack splits."""
    device = torch.device("cpu")
    rng = torch.Generator().manual_seed(seed)
    data = {}
    for i in range(n_clients):
        data[f"client_{i}"] = ClientData(
            train=torch.randn(N_TRAIN, N_FEATURES, generator=rng).to(device),
            val=torch.randn(N_VAL, N_FEATURES, generator=rng).to(device),
            test_benign=torch.randn(N_TEST, N_FEATURES, generator=rng).to(device),
            test_attack=(torch.randn(N_TEST, N_FEATURES, generator=rng) + 5.0).to(
                device
            ),
        )
    return data


def make_fl_cfg(
    stage: ExperimentStage = ExperimentStage.NBAIOT_MAIN,
    n_features: int = N_FEATURES,
    rounds: int = 2,
    encoder_dims: list[int] | None = None,
) -> DatpConfig:
    """Build a federated learning configuration instance with customized parameters."""
    return BASE_CONFIG.model_copy(
        update={
            "stage": stage,
            "model": BASE_CONFIG.model.model_copy(
                update={
                    "input_dim": n_features,
                    "encoder_dims": encoder_dims or [8, 4],
                }
            ),
            "dataset": BASE_CONFIG.dataset.model_copy(
                update={"feature_count": n_features}
            ),
            "machine": BASE_CONFIG.machine.model_copy(update={"batch_size_train": 64}),
            "federation": FederationConfig(
                local_epochs=1,
                convergence=ConvergenceConfig(
                    rounds_initial=1,
                    rounds_max=rounds,
                    relative_threshold=0.001,
                    window=2,
                    round_timeout_s=300.0,
                ),
            ),
        }
    )


N_BENIGN = 300


N_ATTACK = 50


DEVICES = ["TestDev_A", "TestDev_B"]


def make_synthetic_raw(base: Path) -> Path:
    """Write synthetic CSV traffic logs mimicking N-BAIOT benign and attack data."""
    raw = base / "raw"
    rng = np.random.default_rng(42)
    cols = [f"feat_{i}" for i in range(N_FEATURES)]

    for device_id in DEVICES:
        dev_dir = raw / device_id
        dev_dir.mkdir(parents=True)
        pd.DataFrame(
            rng.standard_normal((N_BENIGN, N_FEATURES)),
            columns=pd.Index(cols),
        ).to_csv(
            dev_dir / "benign_traffic.csv",
            index=False,
        )
        attack_dir = dev_dir / "gafgyt_attacks"
        attack_dir.mkdir()
        pd.DataFrame(
            rng.standard_normal((N_ATTACK, N_FEATURES)),
            columns=pd.Index(cols),
        ).to_csv(
            attack_dir / "combo.csv",
            index=False,
        )
    return raw


def valid_metrics_dict(
    policy: str = "global_threshold", stage: str = "nbaiot_main", seed: int = 0
) -> dict:
    """Build a dictionary representing a valid payload conforming to schema requirements."""
    client = {
        PayloadKey.CLIENT_ID: "c1",
        "fpr": 0.0,
        "tpr": 1.0,
        "tnr": 1.0,
        "fnr": 0.0,
        "precision": 1.0,
        "recall": 1.0,
        "balanced_accuracy": 1.0,
        "macro_f1": 1.0,
        PayloadKey.CONFUSION_MATRIX: {"tp": 10, "fp": 0, "tn": 10, "fn": 0},
        PayloadKey.N_BENIGN: 10,
        PayloadKey.N_ATTACK: 10,
        PayloadKey.CALIBRATION_PENDING: False,
        PayloadKey.EVALUATION_INCOMPLETE: False,
        PayloadKey.THRESHOLD_VALUE: 0.5,
        PayloadKey.THRESHOLD_SOURCE: POLICY_THRESHOLD_SOURCE[
            ThresholdPolicy(policy)
        ].value,
    }
    return {
        PayloadKey.SCHEMA_VERSION: "2",
        PayloadKey.METRIC_SCHEMA_VERSION: "2",
        PayloadKey.THRESHOLD_SCHEMA_VERSION: "1",
        PayloadKey.RUN_ID: f"{stage}_{policy}_seed{seed}",
        PayloadKey.RUN_KIND: RunKind.CORE_LADDER.value,
        PayloadKey.DATASET: "nbaiot",
        PayloadKey.POLICY: policy,
        PayloadKey.STAGE: stage,
        PayloadKey.SEED: seed,
        PayloadKey.THRESHOLD_SCOPE: "eligible_client_arithmetic_mean",
        PayloadKey.THRESHOLD_STRATEGY_NAME: policy,
        "tau_global": 0.5,
        PayloadKey.PER_CLIENT: [client],
        PayloadKey.ELIGIBLE_IDS: ["c1"],
        PayloadKey.PENDING_IDS: [],
        PayloadKey.EVAL_INCOMPLETE_IDS: [],
        PayloadKey.ELIGIBLE_COUNT: 1,
        PayloadKey.PENDING_COUNT: 0,
        PayloadKey.EVAL_INCOMPLETE_COUNT: 0,
        PayloadKey.CLIENT_COUNT: 1,
        PayloadKey.COVERAGE_RATIO: 1.0,
        "cv_fpr": 0.0,
        "mean_fpr": 0.0,
        "std_fpr": 0.0,
        "cv_tpr": 0.0,
        "iqr_fpr": 0.0,
        "iqr_tpr": 0.0,
        "worst_client_fpr": 0.0,
        "worst_client_id": "c1",
        "worst_ba": 1.0,
        "p10_macro_f1": 1.0,
        PayloadKey.AGGREGATE_METRICS: {
            MetricName.CV_FPR.value: 0.0,
            MetricName.P10_MACRO_F1.value: 1.0,
        },
        PayloadKey.PROVENANCE: {
            PayloadKey.CONFIG_IDENTITY: "abc123",
            PayloadKey.SPLIT_MANIFEST_IDENTITY: "def456",
            PayloadKey.MODEL_IDENTITY: "ghi789",
            PayloadKey.SCORE_ARTIFACT_IDENTITY: "jkl012",
            PayloadKey.METRIC_CODE_VERSION: "v1",
            PayloadKey.THRESHOLD_CODE_VERSION: "v1",
            PayloadKey.PACKAGE_VERSION: "v1",
            PayloadKey.GENERATED_AT_UTC: "2026-01-01T00:00:00+00:00",
        },
    }


def valid_metrics_json(
    policy: str = "global_threshold", stage: str = "nbaiot_main", seed: int = 0
) -> str:
    """Build a JSON string representing a valid payload conforming to schema requirements."""
    return json.dumps(valid_metrics_dict(policy, stage, seed))


def assert_loads_client_score_parquets(score_dir: Path) -> None:
    """Verify that score arrays are correctly loaded from client-specific Parquet files."""
    _write_score_artifact(score_dir / "client_a.parquet", [0.1, 0.2])
    _write_score_artifact(score_dir / "client_b.parquet", [0.3, 0.4, 0.5])
    result = load_parquets_from_dir(score_dir)
    assert set(result.keys()) == {"client_a", "client_b"}
    np.testing.assert_allclose(result["client_a"], [0.1, 0.2])
    np.testing.assert_allclose(result["client_b"], [0.3, 0.4, 0.5])


def extended_row_fields(policy: ThresholdPolicy) -> dict[str, Any]:
    """Return values for every row field added after the original bounded-sweep schema."""
    is_cluster = policy == ThresholdPolicy.CLUSTER_THRESHOLD
    nan = math.nan
    return {
        "victim_fpr_clean": 0.01,
        "victim_fpr_poisoned": 0.01,
        "victim_delta_fpr": 0.0,
        "victim_fp_clean": 10,
        "victim_fp_poisoned": 10,
        "victim_fn_clean": 5,
        "victim_fn_poisoned": 5,
        "victim_n_test_benign": 1000,
        "victim_n_test_attack": 100,
        "nonvictim_mean_tpr_clean": 0.9,
        "nonvictim_mean_tpr_poisoned": 0.9,
        "nonvictim_mean_delta_tpr": 0.0,
        "nonvictim_worst_delta_tpr": 0.0,
        "nonvictim_mean_fpr_clean": 0.01,
        "nonvictim_mean_fpr_poisoned": 0.01,
        "nonvictim_mean_delta_fpr": 0.0,
        "nonvictim_worst_delta_fpr": 0.0,
        "nonvictim_mean_delta_ba": 0.0,
        "nonvictim_mean_delta_macro_f1": 0.0,
        "nonvictim_delta_fp_total": 0,
        "nonvictim_delta_fn_total": 0,
        "victim_delta_tau_scale_base": 0.02,
        "iqr_median_clean": 0.02,
        "delta_tau_bound_utilization": 0.1,
        "n_replaced": 10,
        "cal_duplicate_rate_clean": 0.0,
        "cal_duplicate_rate_poisoned": 0.05,
        "cluster_sizes_clean": (4, 3, 2) if is_cluster else (),
        "cluster_sizes_poisoned": (4, 3, 2) if is_cluster else (),
        "cluster_victim_size_clean": 2 if is_cluster else nan,
        "cluster_victim_size_poisoned": 2 if is_cluster else nan,
        "cluster_n_reassigned": 0 if is_cluster else nan,
        "cluster_silhouette_clean": 0.4 if is_cluster else nan,
        "cluster_silhouette_poisoned": 0.4 if is_cluster else nan,
        "fixed_cluster_victim_delta_tau": 0.05 if is_cluster else nan,
        "fixed_cluster_victim_delta_tpr": 0.0 if is_cluster else nan,
        "fixed_cluster_victim_delta_fpr": 0.0 if is_cluster else nan,
        "fixed_cluster_delta_cv_fpr": 0.0 if is_cluster else nan,
        "fixed_cluster_delta_mean_fpr": 0.0 if is_cluster else nan,
        "fixed_cluster_nonvictim_mean_delta_tpr": 0.0 if is_cluster else nan,
        "fixed_cluster_nonvictim_mean_delta_fpr": 0.0 if is_cluster else nan,
    }


def _write_score_artifact(path: Path, values: list[float]) -> None:
    """Write score values as a single-column Parquet table artifact."""

    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.table(
        {ScoringColumn.RECONSTRUCTION_ERROR: pa.array(values, type=pa.float32())}
    )
    pq.write_table(table, path)


@dataclass(frozen=True, slots=True)
class _EvalSpec:
    policy: ThresholdPolicy = ThresholdPolicy.GLOBAL_THRESHOLD
    stage: ExperimentStage = ExperimentStage.NBAIOT_MAIN
    seed: int = 42
    eval_incomplete_ids: tuple[str, ...] = ()


def _make_eval_result(
    per_client: list[ClientEvaluationRecord],
    eligible_ids: list[str],
    pending_ids: list[str],
    spec: _EvalSpec = _EvalSpec(),
) -> EvaluationResult:
    return build_evaluation_result(
        policy=spec.policy,
        stage=spec.stage,
        seed=spec.seed,
        clients=tuple(per_client),
        eligible_ids=tuple(eligible_ids),
        pending_ids=tuple(pending_ids),
        incomplete_ids=spec.eval_incomplete_ids,
    )


def _make_client_record(
    client_id: str,
    fpr: float,
    tpr: float,
    *,
    n_benign: int = 100,
    n_attack: int = 100,
) -> ClientEvaluationRecord:
    tnr = 1.0 - fpr
    fnr = 1.0 - tpr
    ba = (tpr + tnr) / 2.0
    tp = int(tpr * n_attack)
    fp = int(fpr * n_benign)
    tn = int(tnr * n_benign)
    fn = int(fnr * n_attack)
    prec = tp / (tp + fp) if (tp + fp) > 0 else math.nan
    rec = tp / (tp + fn) if (tp + fn) > 0 else math.nan
    if n_benign > 0 and n_attack > 0:
        prec0 = tn / (tn + fn) if (tn + fn) > 0 else 0.0
        rec0 = tnr
        f1_0 = 2 * prec0 * rec0 / (prec0 + rec0) if (prec0 + rec0) > 0 else 0.0
        prec1 = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec1 = tpr
        f1_1 = 2 * prec1 * rec1 / (prec1 + rec1) if (prec1 + rec1) > 0 else 0.0
        macro_f1 = (f1_0 + f1_1) / 2.0
    else:
        macro_f1 = math.nan
    return ClientEvaluationRecord(
        client_id=client_id,
        metrics=BinaryMetrics(
            fpr=fpr,
            tpr=tpr,
            tnr=tnr,
            fnr=fnr,
            balanced_accuracy=ba,
            precision=prec,
            recall=rec,
            macro_f1=macro_f1,
        ),
        confusion=ConfusionCounts(tp=tp, fp=fp, tn=tn, fn=fn),
        n_benign=n_benign,
        n_attack=n_attack,
        threshold=ClientThreshold(
            client_id=client_id,
            threshold=0.5,
            status=ClientStatus.ELIGIBLE,
            strategy=ThresholdPolicy.GLOBAL_THRESHOLD,
        ),
        evaluation_incomplete=(n_attack == 0),
    )
