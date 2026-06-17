from __future__ import annotations

from pathlib import Path

from datp.artifacts.io import write_csv as _write_csv
from datp.artifacts.io import write_json_atomic as _write_json
from datp.checkpointing.enums import ConvergenceStatus
from datp.config.models import DatpConfig
from datp.core.enums import (
    Baseline,
    Regime,
)
from datp.core.identity import alpha_label
from datp.core.provenance import (
    source_hash,
    utc_timestamp,
)
from datp.core.provenance import (
    git_commit as current_git_commit,
)
from datp.data.paths import prepared_root_for_regime
from datp.validation._audit_helpers import _safe_diff
from datp.validation._audit_types import _AuditAccumulator, _CellPanel
from datp.validation._client_pipeline import _process_run
from datp.validation._warnings import (
    check_b2_utility_tradeoff as _check_b2_utility_tradeoff,
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
    B4_CLUSTER_STABILITY_CSV,
    BASELINE_INVARIANTS_JSON,
    BLOCKED_RESUME_COMMAND,
    BLOCKED_RESUME_REGIME_A_COMMAND,
    CICIOT_HOMOGENEITY_AUDIT_CSV,
    CLUSTER_ASSIGNMENTS_CSV,
    CONVERGENCE_AUDIT_CSV,
    DATASET_PARTITION_AUDIT_JSON,
    DEFAULT_COVERAGE_RATIO,
    FPR_COMPANION_METRICS_CSV,
    METRIC_DENOMINATOR_AUDIT_CSV,
    METRIC_RECOMPUTATION_AUDIT_CSV,
    PER_ATTACK_METRICS_CSV,
    PER_CLIENT_METRICS_CSV,
    RECONSTRUCTION_ERROR_SUMMARY_CSV,
    REGIME_C_ALPHA_AUDIT_CSV,
    REGIME_C_SEVERITY_TREND_CSV,
    RUN_MANIFEST_CSV,
    SEED_DELTAS_CSV,
    THRESHOLD_VALUES_CSV,
    WARNINGS_MD,
    WORST_CLIENT_TRACKING_CSV,
)
from datp.validation.datasets import (
    build_regime_c_alpha_audit,
    compute_b4_cluster_stability,
    compute_regime_c_severity_trend,
)
from datp.validation.discovery import completed_metric_paths as _completed_metric_paths
from datp.validation.discovery import parse_metric_path as _parse_metric_path
from datp.validation.enums import (
    AuditSeverity,
    AuditStatus,
    WarningCode,
)
from datp.validation.invariants import build_invariant_results
from datp.validation.schemas import (
    B4ClusterStabilityRecord,
    BaselineInvariantResult,
    ClusterAssignmentRecord,
    RegimeCAlphaAuditRecord,
    RegimeCSeverityTrendRecord,
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
    Path("src/datp/thresholding/strategies/b1_global.py"),
    Path("src/datp/thresholding/strategies/b2_personalized.py"),
    Path("src/datp/thresholding/strategies/b3_family.py"),
    Path("src/datp/thresholding/strategies/b4_cluster.py"),
    Path("src/datp/thresholding/thresholds.py"),
)
_METRICS_SOURCE_FILES = (
    Path("src/datp/evaluation/metrics.py"),
    Path("src/datp/evaluation/confusion.py"),
)


def _build_seed_deltas(
    cell_panel: dict[tuple[Regime, int, str | None, Baseline], _CellPanel],
    warnings: list[WarningRecord],
) -> list[SeedDeltaRecord]:
    # Side effect: emits B2_UTILITY_TRADEOFF warnings.
    out: list[SeedDeltaRecord] = []
    for regime, seed, alpha_text in sorted({(r, s, a) for r, s, a, _ in cell_panel}):
        b1_key = (regime, seed, alpha_text, Baseline.B1)
        b2_key = (regime, seed, alpha_text, Baseline.B2)
        b4_key = (regime, seed, alpha_text, Baseline.B4)
        b1 = cell_panel[b1_key] if b1_key in cell_panel else _CellPanel.empty()
        b2 = cell_panel[b2_key] if b2_key in cell_panel else _CellPanel.empty()
        b4 = cell_panel[b4_key] if b4_key in cell_panel else _CellPanel.empty()
        out.append(
            SeedDeltaRecord(
                regime=regime,
                alpha=alpha_text,
                seed=seed,
                b1_cv_fpr=b1.cv_fpr,
                b2_cv_fpr=b2.cv_fpr,
                b4_cv_fpr=b4.cv_fpr,
                b1_cv_tpr=b1.cv_tpr,
                b2_cv_tpr=b2.cv_tpr,
                b4_cv_tpr=b4.cv_tpr,
                b1_macro_f1_mean=b1.macro_f1_mean,
                b2_macro_f1_mean=b2.macro_f1_mean,
                b4_macro_f1_mean=b4.macro_f1_mean,
                b1_macro_f1_p10=b1.macro_f1_p10,
                b2_macro_f1_p10=b2.macro_f1_p10,
                b4_macro_f1_p10=b4.macro_f1_p10,
                b1_auroc_mean=b1.auroc_mean,
                b2_auroc_mean=b2.auroc_mean,
                b4_auroc_mean=b4.auroc_mean,
                b1_pr_auc_mean=b1.pr_auc_mean,
                b2_pr_auc_mean=b2.pr_auc_mean,
                b4_pr_auc_mean=b4.pr_auc_mean,
                b1_mean_fpr=b1.mean_fpr,
                b2_mean_fpr=b2.mean_fpr,
                b4_mean_fpr=b4.mean_fpr,
                b1_std_fpr=b1.std_fpr,
                b2_std_fpr=b2.std_fpr,
                b4_std_fpr=b4.std_fpr,
                b1_iqr_fpr=b1.iqr_fpr,
                b2_iqr_fpr=b2.iqr_fpr,
                b4_iqr_fpr=b4.iqr_fpr,
                b1_worst_client_fpr=b1.worst_client_fpr,
                b2_worst_client_fpr=b2.worst_client_fpr,
                b4_worst_client_fpr=b4.worst_client_fpr,
                b1_worst_client_tpr=b1.worst_client_tpr,
                b2_worst_client_tpr=b2.worst_client_tpr,
                b4_worst_client_tpr=b4.worst_client_tpr,
                b1_worst_client_macro_f1=b1.worst_client_macro_f1,
                b2_worst_client_macro_f1=b2.worst_client_macro_f1,
                b4_worst_client_macro_f1=b4.worst_client_macro_f1,
                b1_worst_client_balanced_accuracy=b1.worst_client_balanced_accuracy,
                b2_worst_client_balanced_accuracy=b2.worst_client_balanced_accuracy,
                b4_worst_client_balanced_accuracy=b4.worst_client_balanced_accuracy,
                delta_cv_fpr_b1_minus_b2=_safe_diff(b1.cv_fpr, b2.cv_fpr),
                delta_cv_fpr_b1_minus_b4=_safe_diff(b1.cv_fpr, b4.cv_fpr),
                delta_cv_tpr_b1_minus_b2=_safe_diff(b1.cv_tpr, b2.cv_tpr),
                delta_cv_tpr_b1_minus_b4=_safe_diff(b1.cv_tpr, b4.cv_tpr),
                delta_macro_f1_b1_minus_b2=_safe_diff(
                    b1.macro_f1_mean, b2.macro_f1_mean
                ),
                delta_macro_f1_b1_minus_b4=_safe_diff(
                    b1.macro_f1_mean, b4.macro_f1_mean
                ),
                delta_pr_auc_b1_minus_b2=_safe_diff(b1.pr_auc_mean, b2.pr_auc_mean),
                delta_pr_auc_b1_minus_b4=_safe_diff(b1.pr_auc_mean, b4.pr_auc_mean),
                delta_auroc_b1_minus_b2=_safe_diff(b1.auroc_mean, b2.auroc_mean),
                delta_auroc_b1_minus_b4=_safe_diff(b1.auroc_mean, b4.auroc_mean),
                b1_convergence_round=b1.convergence_round,
                b2_convergence_round=b2.convergence_round,
                b4_convergence_round=b4.convergence_round,
                b1_tau_global=b1.tau_global,
                b2_tau_global=b2.tau_global,
                b4_tau_global=b4.tau_global,
                coverage_ratio=str(
                    b1.coverage_ratio
                    or b2.coverage_ratio
                    or b4.coverage_ratio
                    or DEFAULT_COVERAGE_RATIO
                ),
                status=AuditStatus.PASS
                if (b1.cv_fpr is not None and b2.cv_fpr is not None)
                else AuditStatus.BLOCKED_PENDING_RUN,
            )
        )

        _check_b2_utility_tradeoff(regime, seed, alpha_text, b1, b2, warnings)
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
        row.regime == Regime.A and row.status == AuditStatus.PASS for row in seed_deltas
    ):
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.BLOCKED_PENDING_RUN,
                code=WarningCode.PRIMARY_DELTA_INCOMPLETE,
                message="Regime A B1-vs-B2 seed delta table is incomplete.",
                exact_command=BLOCKED_RESUME_COMMAND,
            )
        )
    if not acc.cluster_records:
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.BLOCKED_PENDING_RUN,
                code=WarningCode.B4_CLUSTER_DIAGNOSTICS_INCOMPLETE,
                message="No B4 cluster assignment diagnostics were generated from completed artifacts.",
                exact_command=BLOCKED_RESUME_COMMAND,
            )
        )
    if not any(row.baseline == Baseline.B0 for row in acc.manifest_records):
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.BLOCKED_PENDING_RUN,
                code=WarningCode.B0_NORMALIZATION_DIAGNOSTIC_BLOCKED,
                message="Centralized pooled-normalization vs per-device-normalization diagnostic cannot run because B0 artifacts are missing.",
                exact_command=BLOCKED_RESUME_REGIME_A_COMMAND,
            )
        )
    acc.warnings.append(
        WarningRecord(
            severity=AuditSeverity.BLOCKED_PENDING_RUN,
            code=WarningCode.FIXED_OPERATING_POINT_METRICS_PENDING,
            message="FPR at fixed TPR and TPR at fixed FPR require persisted score arrays and operating-point configuration for every completed baseline cell.",
            exact_command=_AUDIT_RESULTS_COMMAND,
        )
    )


def _compute_regime_c_cv_fpr(
    rec: RegimeCAlphaAuditRecord,
    cell_panel: dict[tuple[Regime, int, str | None, Baseline], _CellPanel],
) -> tuple[float | None, float | None, float | None]:
    """Look up B1, B2, B4 CV(FPR) values from cell_panel for a Regime C record."""
    from datp.core.identity import AlphaLabel

    alpha_text: str | None = (
        rec.alpha if rec.alpha not in (AlphaLabel.IID, "inf") else None
    )
    if rec.alpha in (AlphaLabel.IID, "inf"):
        alpha_text = AlphaLabel.IID

    def _cv(key: tuple[Regime, int, str | None, Baseline]) -> float | None:
        panel = cell_panel.get(key)
        return panel.cv_fpr if panel is not None else None

    return (
        _cv((Regime.C, rec.seed, alpha_text, Baseline.B1)),
        _cv((Regime.C, rec.seed, alpha_text, Baseline.B2)),
        _cv((Regime.C, rec.seed, alpha_text, Baseline.B4)),
    )


def _enrich_regime_c_records_with_cv(
    records: list[RegimeCAlphaAuditRecord],
    cell_panel: dict[tuple[Regime, int, str | None, Baseline], _CellPanel],
) -> list[RegimeCAlphaAuditRecord]:
    enriched: list[RegimeCAlphaAuditRecord] = []
    for rec in records:
        b1_cv, b2_cv, b4_cv = _compute_regime_c_cv_fpr(rec, cell_panel)
        enriched.append(
            rec.model_copy(
                update={
                    "b1_cv_fpr": b1_cv,
                    "b2_cv_fpr": b2_cv,
                    "b4_cv_fpr": b4_cv,
                    "delta_b1_b2": _safe_diff(b1_cv, b2_cv),
                    "delta_b1_b4": _safe_diff(b1_cv, b4_cv),
                    "eligible_only_cv_fpr": b1_cv,
                }
            )
        )
    return enriched


def _b4_stability_from_cluster_records(
    cluster_records: list[ClusterAssignmentRecord],
) -> list[B4ClusterStabilityRecord]:
    from collections import defaultdict as _dd

    by_regime_alpha: dict[tuple[Regime, str | None], dict[int, dict[str, int]]] = _dd(
        lambda: _dd(dict)
    )
    for rec in cluster_records:
        try:
            cluster_int = (
                int(rec.cluster_id.split("_")[-1])
                if "_" in rec.cluster_id
                else int(rec.cluster_id)
            )
        except (ValueError, IndexError):
            cluster_int = hash(rec.cluster_id)
        by_regime_alpha[(rec.regime, rec.alpha)][rec.seed][rec.client_id] = cluster_int

    stability: list[B4ClusterStabilityRecord] = []
    for (regime, alpha), by_seed in by_regime_alpha.items():
        stability.extend(compute_b4_cluster_stability(dict(by_seed), regime, alpha))
    return stability


def run_results_audit(
    base_dir: Path, audit_dir: Path, cfg: DatpConfig, data_root: Path | None = None
) -> dict[str, Path]:
    base_dir = Path(base_dir)
    audit_dir = Path(audit_dir)
    audit_dir.mkdir(parents=True, exist_ok=True)

    git_commit = current_git_commit()
    timestamp = utc_timestamp()
    scoring_hash = source_hash(list(_SCORING_SOURCE_FILES))
    threshold_hash = source_hash(list(_THRESHOLD_SOURCE_FILES))
    metrics_hash = source_hash(list(_METRICS_SOURCE_FILES))

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

    _seen_regime_c: set[tuple[str, int]] = set()
    for metrics_path in metric_paths:
        run_id_obj = _parse_metric_path(base_dir, metrics_path)
        regime = run_id_obj.regime
        seed = run_id_obj.seed
        alpha = run_id_obj.alpha
        if regime != Regime.C or alpha is None or (str(alpha), seed) in _seen_regime_c:
            continue
        _seen_regime_c.add((str(alpha), seed))
        _data_root_c = data_root if data_root is not None else base_dir
        prepared = prepared_root_for_regime(
            Regime.C, base_dir=_data_root_c, alpha=alpha, seed=seed
        )
        record = build_regime_c_alpha_audit(prepared, alpha, seed)
        if record is not None:
            acc.regime_c_alpha_records.append(record)
        else:
            acc.warnings.append(
                WarningRecord(
                    severity=AuditSeverity.BLOCKED_PENDING_RUN,
                    code=WarningCode.REGIME_C_ALPHA_AUDIT_MISSING,
                    message=(
                        f"Regime C alpha={alpha_label(alpha)} seed={seed} prepared manifest is "
                        "missing; JS divergence and device-mixture proportions cannot be audited."
                    ),
                    exact_command=BLOCKED_RESUME_COMMAND,
                )
            )

    acc.regime_c_alpha_records = _enrich_regime_c_records_with_cv(
        acc.regime_c_alpha_records, acc.cell_panel
    )

    severity_trend_records: list[RegimeCSeverityTrendRecord] = (
        compute_regime_c_severity_trend(
            acc.regime_c_alpha_records,
            significance_alpha=float(cfg.statistics.significance_alpha),
        )
    )

    b4_stability_records: list[B4ClusterStabilityRecord] = (
        _b4_stability_from_cluster_records(acc.cluster_records)
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

    _write_csv(audit_dir / RUN_MANIFEST_CSV, acc.manifest_records)
    _write_csv(audit_dir / FPR_COMPANION_METRICS_CSV, acc.companion_records)
    _write_csv(audit_dir / WORST_CLIENT_TRACKING_CSV, acc.worst_client_records)
    _write_csv(audit_dir / CICIOT_HOMOGENEITY_AUDIT_CSV, acc.homogeneity_records)
    _write_csv(audit_dir / REGIME_C_ALPHA_AUDIT_CSV, acc.regime_c_alpha_records)
    _write_csv(audit_dir / REGIME_C_SEVERITY_TREND_CSV, severity_trend_records)
    _write_csv(audit_dir / B4_CLUSTER_STABILITY_CSV, b4_stability_records)
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
        audit_dir / BASELINE_INVARIANTS_JSON,
        [row.model_dump(mode="json") for row in invariant_results],
    )
    _write_json(
        audit_dir / DATASET_PARTITION_AUDIT_JSON,
        {
            "schema_version": AUDIT_SCHEMA_VERSION,
            "partitions": [
                row.model_dump(mode="json") for row in acc.partition_audits.values()
            ],
        },
    )
    _write_warnings(audit_dir / WARNINGS_MD, acc.warnings)
    _write_summary(
        audit_dir / AUDIT_SUMMARY_MD,
        acc.manifest_records,
        invariant_results,
        acc.warnings,
    )

    return {
        "baseline_invariants": audit_dir / BASELINE_INVARIANTS_JSON,
        "run_manifest": audit_dir / RUN_MANIFEST_CSV,
        "seed_deltas": audit_dir / SEED_DELTAS_CSV,
        "per_client_metrics": audit_dir / PER_CLIENT_METRICS_CSV,
        "per_attack_metrics": audit_dir / PER_ATTACK_METRICS_CSV,
        "threshold_values": audit_dir / THRESHOLD_VALUES_CSV,
        "reconstruction_error_summary": audit_dir / RECONSTRUCTION_ERROR_SUMMARY_CSV,
        "cluster_assignments": audit_dir / CLUSTER_ASSIGNMENTS_CSV,
        "dataset_partition_audit": audit_dir / DATASET_PARTITION_AUDIT_JSON,
        "convergence_audit": audit_dir / CONVERGENCE_AUDIT_CSV,
        "metric_denominator_audit": audit_dir / METRIC_DENOMINATOR_AUDIT_CSV,
        "metric_recomputation_audit": audit_dir / METRIC_RECOMPUTATION_AUDIT_CSV,
        "fpr_companion_metrics": audit_dir / FPR_COMPANION_METRICS_CSV,
        "worst_client_tracking": audit_dir / WORST_CLIENT_TRACKING_CSV,
        "regime_c_alpha_audit": audit_dir / REGIME_C_ALPHA_AUDIT_CSV,
        "regime_c_severity_trend": audit_dir / REGIME_C_SEVERITY_TREND_CSV,
        "b4_cluster_stability": audit_dir / B4_CLUSTER_STABILITY_CSV,
        "warnings": audit_dir / WARNINGS_MD,
        "audit_summary": audit_dir / AUDIT_SUMMARY_MD,
    }


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
    invariant_results: list[BaselineInvariantResult],
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
        f"- B1-B4 invariant PASS cells: {pass_count}",
        f"- B1-B4 invariant BLOCKED_PENDING_RUN cells: {blocked_count}",
        f"- B1-B4 invariant FAIL cells: {fail_count}",
        f"- Warning records: {len(warnings)}",
        "",
        "B0 is a centralized reference comparator; B1–B4 share the trained encoder and scores. Threshold attribution claims are valid only after the B1–B4 invariant passes for the same (regime, seed, alpha) cell.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
