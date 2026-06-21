from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

import enum
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from datp.artifacts.io import write_csv as _write_csv
from datp.artifacts.io import write_json_atomic as _write_json
from datp.checkpointing.enums import ConvergenceStatus
from datp.config.models import DatpConfig
from datp.config.stages import ExperimentStage
from datp.core.provenance import (
    source_hash,
    utc_timestamp,
)
from datp.core.provenance import (
    git_commit as current_git_commit,
)
from datp.validation._audit_helpers import _safe_diff
from datp.validation._audit_types import _AuditAccumulator, _CellPanel
from datp.validation._client_pipeline import _process_run
from datp.validation._warnings import (
    check_local_threshold_utility_tradeoff as _check_local_threshold_utility_tradeoff,
)
from datp.validation._warnings import (
    emit_ciciot_homogeneity_warnings as _emit_ciciot_homogeneity_warnings,
)
from datp.validation._warnings import (
    emit_flat_cv_tpr_warnings as _emit_flat_cv_tpr_warnings,
)
from datp.validation._warnings import (
    emit_worst_client_stability_warnings as _emit_worst_client_stability_warnings,
)
from datp.validation.constants import (
    _AUDIT_RESULTS_COMMAND,
    AUDIT_SCHEMA_VERSION,
    AUDIT_SUMMARY_MD,
    POLICY_INVARIANTS_JSON,
    BLOCKED_RESUME_COMMAND,
    CICIOT_HOMOGENEITY_AUDIT_CSV,
    CLUSTER_ASSIGNMENTS_CSV,
    CLUSTER_STABILITY_CSV,
    CONVERGENCE_AUDIT_CSV,
    DATASET_PARTITION_AUDIT_JSON,
    DEFAULT_COVERAGE_RATIO,
    FPR_COMPANION_METRICS_CSV,
    METRIC_DENOMINATOR_AUDIT_CSV,
    METRIC_RECOMPUTATION_AUDIT_CSV,
    PER_ATTACK_METRICS_CSV,
    PER_CLIENT_METRICS_CSV,
    RECONSTRUCTION_ERROR_SUMMARY_CSV,
    RUN_MANIFEST_CSV,
    SEED_DELTAS_CSV,
    THRESHOLD_VALUES_CSV,
    WARNINGS_MD,
    WORST_CLIENT_TRACKING_CSV,
)
from datp.validation.datasets import (
    ClusterAssignments,
    compute_cluster_stability,
)
from datp.validation.discovery import completed_metric_paths as _completed_metric_paths
from datp.validation.enums import (
    AuditSeverity,
    AuditStatus,
    WarningCode,
)
from datp.validation.invariants import build_invariant_results
from datp.validation.schemas import (
    ClusterStabilityRecord,
    PolicyInvariantResult,
    ClusterAssignmentRecord,
    RunManifestRecord,
    SeedDeltaRecord,
    WarningRecord,
)

# Source files whose content is hashed into per-cell provenance records.
# These must track the real current module locations so provenance hashes
# reflect actual code, not a constant "MISSING" sentinel.
_SCORING_SOURCE_FILES = (
    Path("src/datp/scoring/generation.py"),
    Path("src/datp/scoring/schema.py"),
    Path("src/datp/scoring/cal_loading.py"),
)
_THRESHOLD_SOURCE_FILES = (
    Path("src/datp/thresholding/strategies/global_threshold.py"),
    Path("src/datp/thresholding/strategies/local_threshold.py"),
    Path("src/datp/thresholding/strategies/cluster_threshold.py"),
    Path("src/datp/thresholding/thresholds.py"),
)
_METRICS_SOURCE_FILES = (
    Path("src/datp/evaluation/metrics.py"),
    Path("src/datp/evaluation/confusion.py"),
)


class AuditOutputName(enum.StrEnum):
    POLICY_INVARIANTS = "policy_invariants"
    RUN_MANIFEST = "run_manifest"
    SEED_DELTAS = "seed_deltas"
    PER_CLIENT_METRICS = "per_client_metrics"
    PER_ATTACK_METRICS = "per_attack_metrics"
    THRESHOLD_VALUES = "threshold_values"
    RECONSTRUCTION_ERROR_SUMMARY = "reconstruction_error_summary"
    CLUSTER_ASSIGNMENTS = "cluster_assignments"
    DATASET_PARTITION_AUDIT = "dataset_partition_audit"
    CONVERGENCE_AUDIT = "convergence_audit"
    METRIC_DENOMINATOR_AUDIT = "metric_denominator_audit"
    METRIC_RECOMPUTATION_AUDIT = "metric_recomputation_audit"
    FPR_COMPANION_METRICS = "fpr_companion_metrics"
    WORST_CLIENT_TRACKING = "worst_client_tracking"
    CLUSTER_STABILITY = "cluster_stability"
    WARNINGS = "warnings"
    AUDIT_SUMMARY = "audit_summary"


@dataclass(frozen=True, slots=True)
class AuditOutputPath:
    name: AuditOutputName
    path: Path


@dataclass(frozen=True, slots=True)
class AuditOutputPaths:
    paths: tuple[AuditOutputPath, ...]

    def __contains__(self, name: object) -> bool:
        return any(item.name == name or item.name.value == name for item in self.paths)

    def items(self) -> tuple[tuple[str, Path], ...]:
        return tuple((item.name.value, item.path) for item in self.paths)

    def path_for(self, name: AuditOutputName) -> Path:
        for item in self.paths:
            if item.name == name:
                return item.path
        raise KeyError(name)


@dataclass(frozen=True, slots=True)
class DatasetPartitionAuditPayload:
    schema_version: str
    partitions: tuple[object, ...]


@dataclass(frozen=True, slots=True)
class _PoliciesPanel:
    global_panel: _CellPanel
    local_panel: _CellPanel
    cluster_panel: _CellPanel


def _per_policy_fields(panels: _PoliciesPanel) -> dict[str, object]:
    g, loc, c = panels.global_panel, panels.local_panel, panels.cluster_panel
    return {
        "global_cv_fpr": g.cv_fpr,
        "local_cv_fpr": loc.cv_fpr,
        "cluster_cv_fpr": c.cv_fpr,
        "global_cv_tpr": g.cv_tpr,
        "local_cv_tpr": loc.cv_tpr,
        "cluster_cv_tpr": c.cv_tpr,
        "global_macro_f1_mean": g.macro_f1_mean,
        "local_macro_f1_mean": loc.macro_f1_mean,
        "cluster_macro_f1_mean": c.macro_f1_mean,
        "global_macro_f1_p10": g.macro_f1_p10,
        "local_macro_f1_p10": loc.macro_f1_p10,
        "cluster_macro_f1_p10": c.macro_f1_p10,
        "global_auroc_mean": g.auroc_mean,
        "local_auroc_mean": loc.auroc_mean,
        "cluster_auroc_mean": c.auroc_mean,
        "global_pr_auc_mean": g.pr_auc_mean,
        "local_pr_auc_mean": loc.pr_auc_mean,
        "cluster_pr_auc_mean": c.pr_auc_mean,
        "global_mean_fpr": g.mean_fpr,
        "local_mean_fpr": loc.mean_fpr,
        "cluster_mean_fpr": c.mean_fpr,
        "global_std_fpr": g.std_fpr,
        "local_std_fpr": loc.std_fpr,
        "cluster_std_fpr": c.std_fpr,
        "global_iqr_fpr": g.iqr_fpr,
        "local_iqr_fpr": loc.iqr_fpr,
        "cluster_iqr_fpr": c.iqr_fpr,
        "global_worst_client_fpr": g.worst_client_fpr,
        "local_worst_client_fpr": loc.worst_client_fpr,
        "cluster_worst_client_fpr": c.worst_client_fpr,
        "global_worst_client_tpr": g.worst_client_tpr,
        "local_worst_client_tpr": loc.worst_client_tpr,
        "cluster_worst_client_tpr": c.worst_client_tpr,
        "global_worst_client_macro_f1": g.worst_client_macro_f1,
        "local_worst_client_macro_f1": loc.worst_client_macro_f1,
        "cluster_worst_client_macro_f1": c.worst_client_macro_f1,
        "global_worst_client_balanced_accuracy": g.worst_client_balanced_accuracy,
        "local_worst_client_balanced_accuracy": loc.worst_client_balanced_accuracy,
        "cluster_worst_client_balanced_accuracy": c.worst_client_balanced_accuracy,
        "global_convergence_round": g.convergence_round,
        "local_convergence_round": loc.convergence_round,
        "cluster_convergence_round": c.convergence_round,
        "global_tau_global": g.tau_global,
        "local_tau_global": loc.tau_global,
        "cluster_tau_global": c.tau_global,
    }


def _delta_fields(panels: _PoliciesPanel) -> dict[str, object]:
    g, loc, c = panels.global_panel, panels.local_panel, panels.cluster_panel
    return {
        "delta_cv_fpr_global_minus_local": _safe_diff(g.cv_fpr, loc.cv_fpr),
        "delta_cv_fpr_global_minus_cluster": _safe_diff(g.cv_fpr, c.cv_fpr),
        "delta_cv_tpr_global_minus_local": _safe_diff(g.cv_tpr, loc.cv_tpr),
        "delta_cv_tpr_global_minus_cluster": _safe_diff(g.cv_tpr, c.cv_tpr),
        "delta_macro_f1_global_minus_local": _safe_diff(
            g.macro_f1_mean, loc.macro_f1_mean
        ),
        "delta_macro_f1_global_minus_cluster": _safe_diff(
            g.macro_f1_mean, c.macro_f1_mean
        ),
        "delta_pr_auc_global_minus_local": _safe_diff(g.pr_auc_mean, loc.pr_auc_mean),
        "delta_pr_auc_global_minus_cluster": _safe_diff(g.pr_auc_mean, c.pr_auc_mean),
        "delta_auroc_global_minus_local": _safe_diff(g.auroc_mean, loc.auroc_mean),
        "delta_auroc_global_minus_cluster": _safe_diff(g.auroc_mean, c.auroc_mean),
    }


def _build_seed_delta_record(
    stage: ExperimentStage,
    seed: int,
    panels: _PoliciesPanel,
) -> SeedDeltaRecord:
    g, loc, c = panels.global_panel, panels.local_panel, panels.cluster_panel
    coverage = str(
        g.coverage_ratio
        or loc.coverage_ratio
        or c.coverage_ratio
        or DEFAULT_COVERAGE_RATIO
    )
    status = (
        AuditStatus.PASS
        if (g.cv_fpr is not None and loc.cv_fpr is not None)
        else AuditStatus.BLOCKED_PENDING_RUN
    )
    return SeedDeltaRecord.model_validate(
        {"stage": stage, "seed": seed, "coverage_ratio": coverage, "status": status}
        | _per_policy_fields(panels)
        | _delta_fields(panels)
    )


def _build_seed_deltas(
    cell_panel: Mapping[tuple[ExperimentStage, int, ThresholdPolicy], _CellPanel],
    warnings: list[WarningRecord],
) -> list[SeedDeltaRecord]:
    # Side effect: emits LOCAL_UTILITY_TRADEOFF warnings.
    out: list[SeedDeltaRecord] = []
    for stage, seed in sorted({(s, sd) for s, sd, _ in cell_panel}):
        global_panel = cell_panel.get(
            (stage, seed, ThresholdPolicy.GLOBAL_THRESHOLD), _CellPanel.empty()
        )
        local_panel = cell_panel.get(
            (stage, seed, ThresholdPolicy.LOCAL_THRESHOLD), _CellPanel.empty()
        )
        cluster_panel = cell_panel.get(
            (stage, seed, ThresholdPolicy.CLUSTER_THRESHOLD), _CellPanel.empty()
        )
        out.append(
            _build_seed_delta_record(
                stage,
                seed,
                _PoliciesPanel(
                    global_panel=global_panel,
                    local_panel=local_panel,
                    cluster_panel=cluster_panel,
                ),
            )
        )
        _check_local_threshold_utility_tradeoff(
            (stage, seed), global_panel, local_panel, warnings
        )
    return out


def _emit_structural_warnings(
    acc: _AuditAccumulator, seed_deltas: list[SeedDeltaRecord]
) -> None:
    if any(
        row.convergence_status == ConvergenceStatus.BLOCKED_PENDING_RUN
        for row in acc.convergence_records
    ):
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.BLOCKED_PENDING_RUN,
                code=WarningCode.MISSING_CONVERGENCE_CURVES,
                message="Existing checkpoints do not include convergence curves or FedAvg-weighted benign validation loss per round.",
                exact_command=BLOCKED_RESUME_COMMAND,
            )
        )
    if not any(
        row.stage == ExperimentStage.NBAIOT_MAIN and row.status == AuditStatus.PASS
        for row in seed_deltas
    ):
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.BLOCKED_PENDING_RUN,
                code=WarningCode.PRIMARY_DELTA_INCOMPLETE,
                message="NBAIOT_MAIN GLOBAL_THRESHOLD-vs-LOCAL_THRESHOLD seed delta table is incomplete.",
                exact_command=BLOCKED_RESUME_COMMAND,
            )
        )
    if not acc.cluster_records:
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.BLOCKED_PENDING_RUN,
                code=WarningCode.CLUSTER_DIAGNOSTICS_INCOMPLETE,
                message="No cluster assignment diagnostics were generated from completed artifacts.",
                exact_command=BLOCKED_RESUME_COMMAND,
            )
        )
    acc.warnings.append(
        WarningRecord(
            severity=AuditSeverity.BLOCKED_PENDING_RUN,
            code=WarningCode.FIXED_OPERATING_POINT_METRICS_PENDING,
            message="FPR at fixed TPR and TPR at fixed FPR require persisted score arrays and operating-point configuration for every completed clean run cell.",
            exact_command=_AUDIT_RESULTS_COMMAND,
        )
    )


def _cluster_stability_from_cluster_records(
    cluster_records: list[ClusterAssignmentRecord],
) -> list[ClusterStabilityRecord]:
    keyed_assignments = tuple(
        (
            rec.stage,
            rec.seed,
            rec.client_id,
            _cluster_id_to_int(rec.cluster_id),
        )
        for rec in cluster_records
    )
    stability: list[ClusterStabilityRecord] = []
    stage_keys = sorted({row[0] for row in keyed_assignments})
    for stage in stage_keys:
        seed_keys = sorted({row[1] for row in keyed_assignments if row[0] == stage})
        assignments = tuple(
            ClusterAssignments(
                seed=seed,
                assignments=tuple(
                    sorted(
                        (row[2], row[3])
                        for row in keyed_assignments
                        if row[0] == stage and row[1] == seed
                    )
                ),
            )
            for seed in seed_keys
        )
        stability.extend(compute_cluster_stability(assignments, stage))
    return stability


def _cluster_id_to_int(cluster_id: str) -> int:
    try:
        return int(cluster_id.split("_")[-1]) if "_" in cluster_id else int(cluster_id)
    except (ValueError, IndexError):
        return hash(cluster_id)


def _compute_source_hashes() -> tuple[str, str, str]:
    scoring_hash = source_hash(list(_SCORING_SOURCE_FILES))
    threshold_hash = source_hash(list(_THRESHOLD_SOURCE_FILES))
    metrics_hash = source_hash(list(_METRICS_SOURCE_FILES))
    return scoring_hash, threshold_hash, metrics_hash


def _process_all_runs(
    metric_paths: list[Path],
    base_dir: Path,
    acc: _AuditAccumulator,
    *,
    git_commit: str,
    timestamp: str,
    scoring_hash: str,
    threshold_hash: str,
    metrics_hash: str,
    cfg: DatpConfig,
    data_root: Path | None,
) -> None:
    for metrics_path in metric_paths:
        _process_run(
            metrics_path,
            base_dir,
            acc,
            git_commit=git_commit,
            timestamp=timestamp,
            scoring_hash=scoring_hash,
            threshold_hash=threshold_hash,
            metrics_hash=metrics_hash,
            cfg=cfg,
            data_root=data_root,
        )


def _write_audit_artifacts(
    audit_dir: Path,
    acc: _AuditAccumulator,
    seed_deltas: list[SeedDeltaRecord],
    cluster_stability_records: list[ClusterStabilityRecord],
    invariant_results: list[PolicyInvariantResult],
) -> None:
    _write_csv(audit_dir / RUN_MANIFEST_CSV, acc.manifest_records)
    _write_csv(audit_dir / FPR_COMPANION_METRICS_CSV, acc.companion_records)
    _write_csv(audit_dir / WORST_CLIENT_TRACKING_CSV, acc.worst_client_records)
    _write_csv(audit_dir / CICIOT_HOMOGENEITY_AUDIT_CSV, acc.homogeneity_records)
    _write_csv(audit_dir / CLUSTER_STABILITY_CSV, cluster_stability_records)
    _write_csv(audit_dir / SEED_DELTAS_CSV, seed_deltas)
    _write_csv(audit_dir / PER_CLIENT_METRICS_CSV, acc.client_records)
    _write_csv(audit_dir / PER_ATTACK_METRICS_CSV, acc.attack_records)
    _write_csv(audit_dir / THRESHOLD_VALUES_CSV, acc.threshold_records)
    _write_csv(audit_dir / RECONSTRUCTION_ERROR_SUMMARY_CSV, acc.recon_records)
    _write_csv(audit_dir / CLUSTER_ASSIGNMENTS_CSV, acc.cluster_records)
    _write_csv(audit_dir / CONVERGENCE_AUDIT_CSV, acc.convergence_records)
    _write_csv(audit_dir / METRIC_DENOMINATOR_AUDIT_CSV, acc.denominator_records)
    _write_csv(audit_dir / METRIC_RECOMPUTATION_AUDIT_CSV, acc.recomputation_records)
    _write_json(
        audit_dir / POLICY_INVARIANTS_JSON,
        invariant_results,
    )
    _write_json(
        audit_dir / DATASET_PARTITION_AUDIT_JSON,
        DatasetPartitionAuditPayload(
            schema_version=AUDIT_SCHEMA_VERSION,
            partitions=tuple(acc.partition_audits.values()),
        ),
    )
    _write_warnings(audit_dir / WARNINGS_MD, acc.warnings)
    _write_summary(
        audit_dir / AUDIT_SUMMARY_MD,
        acc.manifest_records,
        invariant_results,
        acc.warnings,
    )


def _audit_output_paths(audit_dir: Path) -> AuditOutputPaths:
    return AuditOutputPaths(
        paths=(
            AuditOutputPath(
                AuditOutputName.POLICY_INVARIANTS,
                audit_dir / POLICY_INVARIANTS_JSON,
            ),
            AuditOutputPath(AuditOutputName.RUN_MANIFEST, audit_dir / RUN_MANIFEST_CSV),
            AuditOutputPath(AuditOutputName.SEED_DELTAS, audit_dir / SEED_DELTAS_CSV),
            AuditOutputPath(
                AuditOutputName.PER_CLIENT_METRICS, audit_dir / PER_CLIENT_METRICS_CSV
            ),
            AuditOutputPath(
                AuditOutputName.PER_ATTACK_METRICS, audit_dir / PER_ATTACK_METRICS_CSV
            ),
            AuditOutputPath(
                AuditOutputName.THRESHOLD_VALUES, audit_dir / THRESHOLD_VALUES_CSV
            ),
            AuditOutputPath(
                AuditOutputName.RECONSTRUCTION_ERROR_SUMMARY,
                audit_dir / RECONSTRUCTION_ERROR_SUMMARY_CSV,
            ),
            AuditOutputPath(
                AuditOutputName.CLUSTER_ASSIGNMENTS, audit_dir / CLUSTER_ASSIGNMENTS_CSV
            ),
            AuditOutputPath(
                AuditOutputName.DATASET_PARTITION_AUDIT,
                audit_dir / DATASET_PARTITION_AUDIT_JSON,
            ),
            AuditOutputPath(
                AuditOutputName.CONVERGENCE_AUDIT, audit_dir / CONVERGENCE_AUDIT_CSV
            ),
            AuditOutputPath(
                AuditOutputName.METRIC_DENOMINATOR_AUDIT,
                audit_dir / METRIC_DENOMINATOR_AUDIT_CSV,
            ),
            AuditOutputPath(
                AuditOutputName.METRIC_RECOMPUTATION_AUDIT,
                audit_dir / METRIC_RECOMPUTATION_AUDIT_CSV,
            ),
            AuditOutputPath(
                AuditOutputName.FPR_COMPANION_METRICS,
                audit_dir / FPR_COMPANION_METRICS_CSV,
            ),
            AuditOutputPath(
                AuditOutputName.WORST_CLIENT_TRACKING,
                audit_dir / WORST_CLIENT_TRACKING_CSV,
            ),
            AuditOutputPath(
                AuditOutputName.CLUSTER_STABILITY,
                audit_dir / CLUSTER_STABILITY_CSV,
            ),
            AuditOutputPath(AuditOutputName.WARNINGS, audit_dir / WARNINGS_MD),
            AuditOutputPath(
                AuditOutputName.AUDIT_SUMMARY, audit_dir / AUDIT_SUMMARY_MD
            ),
        )
    )


def run_results_audit(
    base_dir: Path, audit_dir: Path, cfg: DatpConfig, data_root: Path | None = None
) -> AuditOutputPaths:
    base_dir = Path(base_dir)
    audit_dir = Path(audit_dir)
    audit_dir.mkdir(parents=True, exist_ok=True)

    git_commit = current_git_commit()
    timestamp = utc_timestamp()
    scoring_hash, threshold_hash, metrics_hash = _compute_source_hashes()

    acc = _AuditAccumulator()
    metric_paths = _completed_metric_paths(base_dir)
    if not metric_paths:
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.BLOCKED_PENDING_RUN,
                code=WarningCode.NO_COMPLETED_RESULTS,
                message="No completed metrics.json artifacts were found.",
                exact_command=BLOCKED_RESUME_COMMAND,
            )
        )

    _process_all_runs(
        metric_paths,
        base_dir,
        acc,
        git_commit=git_commit,
        timestamp=timestamp,
        scoring_hash=scoring_hash,
        threshold_hash=threshold_hash,
        metrics_hash=metrics_hash,
        cfg=cfg,
        data_root=data_root,
    )

    cluster_stability_records = _cluster_stability_from_cluster_records(
        acc.cluster_records
    )
    invariant_results = build_invariant_results(
        acc.invariant_inputs, acc.score_hashes_by_cell
    )
    seed_deltas = _build_seed_deltas(acc.cell_panel, acc.warnings)

    _emit_structural_warnings(acc, seed_deltas)
    _emit_worst_client_stability_warnings(acc.worst_client_records, acc.warnings)
    _emit_flat_cv_tpr_warnings(acc.cell_panel, acc.warnings)
    _emit_ciciot_homogeneity_warnings(
        acc.homogeneity_records,
        acc.warnings,
        homogeneity_threshold=cfg.quality_gates.ciciot_homogeneity_threshold,
    )

    _write_audit_artifacts(
        audit_dir,
        acc,
        seed_deltas,
        cluster_stability_records,
        invariant_results,
    )
    return _audit_output_paths(audit_dir)


def _write_warnings(path: Path, warnings: list[WarningRecord]) -> None:
    lines = ["# DATP Results Audit Warnings", ""]
    if not warnings:
        lines.append("No warnings.")
    for warning in warnings:
        lines.append(f"- **{warning.severity} `{warning.code}`**: {warning.message}")
        if warning.exact_command:
            lines.append(f" Command: `{warning.exact_command}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_summary(
    path: Path,
    manifest_records: list[RunManifestRecord],
    invariant_results: list[PolicyInvariantResult],
    warnings: list[WarningRecord],
) -> None:
    pass_count = sum(row.status == AuditStatus.PASS for row in invariant_results)
    blocked_count = sum(
        row.status == AuditStatus.BLOCKED_PENDING_RUN for row in invariant_results
    )
    fail_count = sum(row.status == AuditStatus.FAIL for row in invariant_results)
    lines = [
        "# DATP Results Audit Summary",
        "",
        f"- Completed runs audited: {len(manifest_records)}",
        f"- Controlled-policy invariant PASS cells: {pass_count}",
        f"- Controlled-policy invariant BLOCKED_PENDING_RUN cells: {blocked_count}",
        f"- Controlled-policy invariant FAIL cells: {fail_count}",
        f"- Warning records: {len(warnings)}",
        "",
        "Controlled threshold policies share the trained encoder and scores. Threshold attribution claims are valid only after the invariant passes for the same (stage, seed) cell.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
