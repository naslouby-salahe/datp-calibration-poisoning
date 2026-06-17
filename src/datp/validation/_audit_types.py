from __future__ import annotations

import dataclasses
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from datp.checkpointing.enums import ConvergenceStatus
    from datp.core.enums import (
        Baseline,
        Regime,
        ScoringStage,
    )
    from datp.core.types import ThresholdResult
    from datp.validation.invariants import InvariantHashes, InvariantKey
    from datp.validation.schemas import (
        CICIoTHomogeneityRecord,
        ClientMetricRecord,
        ClusterAssignmentRecord,
        ConvergenceAuditRecord,
        DatasetPartitionAudit,
        FPRCompanionRecord,
        MetricDenominatorAuditRecord,
        MetricRecomputationRecord,
        PerAttackMetricRecord,
        ReconstructionErrorSummaryRecord,
        RegimeCAlphaAuditRecord,
        RunManifestRecord,
        ThresholdRecord,
        WarningRecord,
        WorstClientRecord,
    )


@dataclasses.dataclass(frozen=True, slots=True)
class _CellPanel:
    cv_fpr: float | None = None
    cv_tpr: float | None = None
    macro_f1_mean: float | None = None
    macro_f1_p10: float | None = None
    auroc_mean: float | None = None
    pr_auc_mean: float | None = None
    mean_fpr: float | None = None
    std_fpr: float | None = None
    iqr_fpr: float | None = None
    worst_client_fpr: float | None = None
    worst_client_tpr: float | None = None
    worst_client_macro_f1: float | None = None
    worst_client_balanced_accuracy: float | None = None
    convergence_round: int | None = None
    tau_global: float | None = None
    coverage_ratio: str | None = None

    @classmethod
    def empty(cls) -> _CellPanel:
        """Explicit sentinel for a cell with no available data."""
        return cls()


@dataclasses.dataclass(slots=True)
class _AuditAccumulator:
    manifest_records: list[RunManifestRecord] = dataclasses.field(default_factory=list)
    client_records: list[ClientMetricRecord] = dataclasses.field(default_factory=list)
    attack_records: list[PerAttackMetricRecord] = dataclasses.field(
        default_factory=list
    )
    threshold_records: list[ThresholdRecord] = dataclasses.field(default_factory=list)
    recon_records: list[ReconstructionErrorSummaryRecord] = dataclasses.field(
        default_factory=list
    )
    denominator_records: list[MetricDenominatorAuditRecord] = dataclasses.field(
        default_factory=list
    )
    convergence_records: list[ConvergenceAuditRecord] = dataclasses.field(
        default_factory=list
    )
    cluster_records: list[ClusterAssignmentRecord] = dataclasses.field(
        default_factory=list
    )
    companion_records: list[FPRCompanionRecord] = dataclasses.field(
        default_factory=list
    )
    worst_client_records: list[WorstClientRecord] = dataclasses.field(
        default_factory=list
    )
    homogeneity_records: list[CICIoTHomogeneityRecord] = dataclasses.field(
        default_factory=list
    )
    regime_c_alpha_records: list[RegimeCAlphaAuditRecord] = dataclasses.field(
        default_factory=list
    )
    partition_audits: dict[str, DatasetPartitionAudit] = dataclasses.field(
        default_factory=dict
    )
    invariant_inputs: dict[InvariantKey, dict[Baseline, InvariantHashes]] = (
        dataclasses.field(default_factory=lambda: defaultdict(dict))
    )
    score_hashes_by_cell: dict[
        InvariantKey, dict[Baseline, dict[tuple[ScoringStage, str], str]]
    ] = dataclasses.field(default_factory=lambda: defaultdict(dict))
    recomputation_records: list[MetricRecomputationRecord] = dataclasses.field(
        default_factory=list
    )
    cell_panel: dict[tuple[Regime, int, str | None, Baseline], _CellPanel] = (
        dataclasses.field(default_factory=dict)
    )
    warnings: list[WarningRecord] = dataclasses.field(default_factory=list)
    missing_confusion_warned: set[str] = dataclasses.field(default_factory=set)


@dataclasses.dataclass(frozen=True, slots=True)
class _RunContext:
    """All loaded and validated data for a single metrics run."""

    regime: Regime
    baseline: Baseline
    seed: int
    alpha: float | None
    alpha_text: str | None
    run_id: str
    metrics: dict[str, Any]
    data_root: Path
    score_root: Path
    checkpoint: Path
    partition_path: Path
    partition_payload: dict[str, Any]
    metadata: dict[str, Any]
    feature_count: int | None
    normalized_clients: list[dict[str, Any]]
    client_count: int
    split_hash: str
    model_hash: str
    training_hash: str
    preprocessing_hash: str
    train_count: int | None
    calibration_count: int | None
    test_count: int | None
    eligible_count: int
    pending_count: int
    incomplete_ids: frozenset[str]
    eligible_client_ids: frozenset[str]
    pending_client_ids: frozenset[str]
    convergence_round: int | None
    convergence_value: float | None
    convergence_status: ConvergenceStatus
    curve_path: str | None
    invariant_key: InvariantKey


@dataclasses.dataclass(frozen=True, slots=True)
class _ScoreArrays:
    """Loaded score arrays from disk for a single run."""

    cal_errors: dict[str, np.ndarray]
    test_benign_scores: dict[str, np.ndarray]
    test_attack_scores: dict[str, np.ndarray]
    threshold_result: ThresholdResult | None


@dataclasses.dataclass(frozen=True, slots=True)
class _ClientMetricParams:
    """Bundle per-client metric inputs to keep argument count below threshold."""

    client_id: str
    row: dict[str, Any]
    n_benign: int
    n_attack: int
    tp: int
    fp: int
    tn: int
    fn: int
    auroc: float | None
    pr_auc: float | None
    eligible: bool
    calibration_pending: bool
    evaluation_incomplete: bool
    coverage_ratio: str
