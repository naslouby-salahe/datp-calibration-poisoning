from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

import datp.reporting.build as package
from datp.artifacts import nbaiot_main_manifest_path, sensitivity_manifest_path
from datp.attacks.manifests import (
    ArtifactProvenance,
    BoundedSweepManifest,
    BoundedSweepResultRow,
    ClusterStabilityRow,
    DrawVariantRow,
    ProvenanceRecord,
    ScaleNormalizationRow,
    SensitivityManifest,
    TrustBoundaryRow,
)
from datp.config import BASE_CONFIG, ExperimentStage
from datp.core import (
    REPOSITORY_NAME,
    ClientThreshold,
    PolicyRunId,
    SeedPair,
    SeedRecord,
    TrainingCellId,
)
from datp.enums import (
    ArtifactDir,
    ClaimClassification,
    AttackerObjective,
    ClientStatus,
    DatasetID,
    EvidenceRole,
    FigureName,
    ManifestProvenanceSource,
    MetricName,
    PackageDir,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ReservoirDraw,
    RunKind,
    SeedScope,
    SidecarField,
    ThresholdPolicy,
)
from datp.evaluation import (
    BinaryMetrics,
    ClientEvaluationRecord,
    ConfusionCounts,
    DispersionMetrics,
    EvaluationResult,
)
from datp.reporting.build import (
    _REPRESENTATIVE_SEED_FIGURES,
    _eligible_intersection_fprs,
    _evaluation_from_payload,
    _validate_figure_sidecars,
)
from datp.reporting.figures import (
    MANDATORY_FOOTNOTE,
    NOT_CONFIRMATORY_WARNING,
    ResultTable,
    _build_table_row,
    format_mean_std,
    generate_table3,
)
from datp.reporting.poisoning import (
    _classify_claim,
    build_poisoning_summaries,
    build_sensitivity_summaries,
)
from datp.thresholding import SweepMetrics
from tests.fixtures import extended_row_fields


def _payload(
    *, cv_fpr: float = math.nan, pending: list[str] | None = None
) -> SweepMetrics:
    pending_ids = pending or []
    per_client = [
        {
            "client_id": "c1",
            MetricName.FPR.value: 0.0,
            MetricName.TPR.value: 1.0,
            MetricName.TNR.value: 1.0,
            MetricName.FNR.value: 0.0,
            MetricName.PRECISION.value: 1.0,
            MetricName.RECALL.value: 1.0,
            MetricName.BALANCED_ACCURACY.value: 1.0,
            MetricName.MACRO_F1.value: 1.0,
            "confusion_matrix": {
                "tp": 10,
                "fp": 0,
                "tn": 10,
                "fn": 0,
            },
            "n_benign": 10,
            "n_attack": 10,
            "calibration_pending": False,
            "evaluation_incomplete": False,
            "threshold_value": 0.5,
            "threshold_source": "global",
        },
        {
            "client_id": "c2",
            MetricName.FPR.value: 0.0,
            MetricName.TPR.value: 1.0,
            MetricName.TNR.value: 1.0,
            MetricName.FNR.value: 0.0,
            MetricName.PRECISION.value: 1.0,
            MetricName.RECALL.value: 1.0,
            MetricName.BALANCED_ACCURACY.value: 1.0,
            MetricName.MACRO_F1.value: 1.0,
            "confusion_matrix": {
                "tp": 10,
                "fp": 0,
                "tn": 10,
                "fn": 0,
            },
            "n_benign": 10,
            "n_attack": 10,
            "calibration_pending": "c2" in pending_ids,
            "evaluation_incomplete": False,
            "threshold_value": 0.5,
            "threshold_source": "tau_global_fallback"
            if "c2" in pending_ids
            else "global",
        },
    ]
    eligible = 2 - len(pending_ids)
    return SweepMetrics.model_validate(
        {
            "schema_version": "2",
            "metric_schema_version": "2",
            "threshold_schema_version": "1",
            "run_id": "a_global_threshold_seed0",
            "run_kind": RunKind.CORE_LADDER,
            "dataset": "nbaiot",
            "policy": "global_threshold",
            "stage": "nbaiot_main",
            "seed": 0,
            "threshold_scope": "eligible_client_arithmetic_mean",
            "threshold_strategy_name": "global_threshold",
            "tau_global": 0.5,
            "per_client": per_client,
            "eligible_ids": [
                row["client_id"]
                for row in per_client
                if row["client_id"] not in pending_ids
            ],
            "pending_ids": pending_ids,
            "eval_incomplete_ids": [],
            "eligible_count": eligible,
            "pending_count": len(pending_ids),
            "eval_incomplete_count": 0,
            "client_count": 2,
            "coverage_ratio": eligible / 2,
            "cv_fpr": cv_fpr,
            "mean_fpr": 0.0,
            "std_fpr": 0.0,
            "cv_tpr": 0.0,
            "iqr_fpr": 0.0,
            "iqr_tpr": 0.0,
            "worst_client_fpr": 0.0,
            "worst_client_id": "c1",
            "worst_ba": 1.0,
            "p10_macro_f1": 1.0,
            "aggregate_metrics": {
                MetricName.CV_FPR: cv_fpr,
                MetricName.P10_MACRO_F1: 1.0,
            },
            "provenance": {
                "config_identity": "test",
                "split_manifest_identity": "test",
                "model_identity": "test",
                "score_artifact_identity": "test",
                "metric_code_version": "test",
                "threshold_code_version": "test",
                "package_version": "test",
                "generated_at_utc": "2026-01-01T00:00:00+00:00",
            },
        }
    )


def test_reporting_loader_recomputes_and_rejects_bad_saved_cv_fpr() -> None:
    with pytest.raises(ValueError, match="Metric schema mismatch"):
        _evaluation_from_payload(_payload(cv_fpr=0.25), metric_tol=1e-9)


def test_reporting_loader_rejects_denominator_mismatch() -> None:
    payload = _payload()
    first = payload.per_client[0].model_copy(update={"n_benign": 11})
    payload = payload.model_copy(
        update={"per_client": (first, *payload.per_client[1:])}
    )
    with pytest.raises(ValueError, match="Benign denominator mismatch"):
        _evaluation_from_payload(payload, metric_tol=1e-9)


def test_reporting_loader_rejects_missing_eligible_ids() -> None:
    payload = _payload()
    raw = payload.model_dump(mode="json")
    raw.pop("eligible_ids")
    with pytest.raises(ValidationError):
        SweepMetrics.model_validate(raw)


def test_eligible_intersection_rejects_mismatched_sets() -> None:
    left = _evaluation_from_payload(_payload(pending=[]), metric_tol=1e-9)
    right_payload = _payload(pending=["c2"]).model_copy(
        update={
            "policy": ThresholdPolicy.LOCAL_THRESHOLD,
            "std_fpr": math.nan,
            "iqr_fpr": math.nan,
            "cv_tpr": math.nan,
            "iqr_tpr": math.nan,
        }
    )
    right = _evaluation_from_payload(right_payload, metric_tol=1e-9)

    with pytest.raises(ValueError, match="Eligible-client set mismatch"):
        _eligible_intersection_fprs(left, right)


def _write_sidecar(figures_dir: Path, fig_name: str, data: dict) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)
    (figures_dir / f"{fig_name}_data.json").write_text(json.dumps(data))


def _valid_sidecar(fig_name: str) -> dict:
    return {
        "figure": fig_name,
        "title": f"{fig_name} — representative seed, descriptive only",
        "evidence_role": EvidenceRole.DESCRIPTIVE.value,
        "seed_scope": SeedScope.REPRESENTATIVE_SEED.value,
        SidecarField.NOT_CONFIRMATORY_WARNING.value: NOT_CONFIRMATORY_WARNING,
        "seeds": [0],
    }


def test_valid_sidecars_pass(tmp_path: Path) -> None:
    figures_dir = tmp_path / "figures"
    for fig in _REPRESENTATIVE_SEED_FIGURES:
        _write_sidecar(figures_dir, fig, _valid_sidecar(fig))
    errors = _validate_figure_sidecars(figures_dir)
    assert errors == []


def test_missing_sidecar_fails(tmp_path: Path) -> None:
    figures_dir = tmp_path / "figures"
    figures_dir.mkdir(parents=True)
    one_fig = min(_REPRESENTATIVE_SEED_FIGURES)
    _write_sidecar(figures_dir, one_fig, _valid_sidecar(one_fig))
    errors = _validate_figure_sidecars(figures_dir)
    assert any("Missing figure sidecar" in e for e in errors)


def test_wrong_seed_scope_fails(tmp_path: Path) -> None:
    figures_dir = tmp_path / "figures"
    for fig in _REPRESENTATIVE_SEED_FIGURES:
        sidecar = _valid_sidecar(fig)
        sidecar["seed_scope"] = SeedScope.ALL_SEEDS.value
        _write_sidecar(figures_dir, fig, sidecar)
    errors = _validate_figure_sidecars(figures_dir)
    assert any("seed_scope" in e for e in errors)


def test_wrong_evidence_role_fails(tmp_path: Path) -> None:
    figures_dir = tmp_path / "figures"
    for fig in _REPRESENTATIVE_SEED_FIGURES:
        sidecar = _valid_sidecar(fig)
        sidecar["evidence_role"] = "confirmatory"
        _write_sidecar(figures_dir, fig, sidecar)
    errors = _validate_figure_sidecars(figures_dir)
    assert any("evidence_role" in e for e in errors)


def test_missing_not_confirmatory_warning_fails(tmp_path: Path) -> None:
    figures_dir = tmp_path / "figures"
    for fig in _REPRESENTATIVE_SEED_FIGURES:
        sidecar = _valid_sidecar(fig)
        del sidecar[SidecarField.NOT_CONFIRMATORY_WARNING.value]
        _write_sidecar(figures_dir, fig, sidecar)
    errors = _validate_figure_sidecars(figures_dir)
    assert any(SidecarField.NOT_CONFIRMATORY_WARNING.value in e for e in errors)


def test_title_without_representative_seed_fails(tmp_path: Path) -> None:
    figures_dir = tmp_path / "figures"
    for fig in _REPRESENTATIVE_SEED_FIGURES:
        sidecar = _valid_sidecar(fig)
        sidecar["title"] = "Plain title without the required wording"
        _write_sidecar(figures_dir, fig, sidecar)
    errors = _validate_figure_sidecars(figures_dir)
    assert any("title" in e or "representative seed" in e.lower() for e in errors)


def test_representative_seed_figures_uses_canonical_names() -> None:

    canonical = {FigureName.FIGURE_1.value, FigureName.FIGURE_2.value}
    assert _REPRESENTATIVE_SEED_FIGURES == canonical


def _touch(path: Path, text: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


@pytest.fixture
def outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    base_dir = tmp_path / "outputs"
    table = _touch(base_dir / ArtifactDir.TABLES / "table3_nbaiot.csv")
    figure = _touch(base_dir / ArtifactDir.FIGURES / "figure_1.pdf")
    analysis = _touch(base_dir / ArtifactDir.ANALYSIS / "bootstrap_cis.csv")
    sensitivity = _touch(base_dir / ArtifactDir.ANALYSIS / "draw_variant_summary.csv")
    _touch(nbaiot_main_manifest_path(base_dir), "{}")
    _touch(sensitivity_manifest_path(base_dir), "{}")
    _touch(base_dir / ArtifactDir.FIGURES / "stray_figure1_seed1.png")

    monkeypatch.setattr(package, "build_all", lambda *_args: (table, figure))
    monkeypatch.setattr(
        package, "build_poisoning_summaries", lambda *_args: (analysis,)
    )
    monkeypatch.setattr(package, "build_poisoning_figures", lambda *_args: ())
    monkeypatch.setattr(
        package, "build_sensitivity_summaries", lambda *_args: (sensitivity,)
    )
    return base_dir


def _build(outputs: Path, results_dir: Path) -> tuple[Path, ...]:
    return package.build_report_package(
        base_dir=outputs, results_dir=results_dir, cfg=BASE_CONFIG
    )


def test_package_groups_every_report_output(outputs: Path, tmp_path: Path) -> None:
    results_dir = tmp_path / "results"

    paths = _build(outputs, results_dir)

    assert {path.relative_to(results_dir).as_posix() for path in paths} == {
        f"{PackageDir.CONFIG}/resolved_config.yaml",
        f"{PackageDir.MANIFESTS}/nbaiot_main_manifest.json",
        f"{PackageDir.MANIFESTS}/sensitivity_manifest.json",
        "tables/table3_nbaiot.csv",
        "figures/figure_1.pdf",
        "analysis/bootstrap_cis.csv",
        "analysis/draw_variant_summary.csv",
    }
    assert all(path.is_file() for path in paths)


def test_package_omits_files_the_report_did_not_generate(
    outputs: Path, tmp_path: Path
) -> None:
    results_dir = tmp_path / "results"

    _build(outputs, results_dir)

    assert not (results_dir / "figures" / "stray_figure1_seed1.png").exists()


def test_package_is_rebuilt_from_scratch(outputs: Path, tmp_path: Path) -> None:
    results_dir = tmp_path / "results"
    stale = _touch(results_dir / "figures" / "obsolete.pdf")

    _build(outputs, results_dir)

    assert not stale.exists()


def test_package_never_clears_the_run_outputs(outputs: Path) -> None:
    with pytest.raises(ValueError, match="Refusing to clear"):
        _build(outputs, outputs.parent)

    assert (outputs / ArtifactDir.TABLES / "table3_nbaiot.csv").exists()


_VICTIMS = tuple(f"c{i}" for i in range(9))


_TRAINING = tuple(range(20))


_POISONING = tuple(range(100, 120))


_ANALYSIS = tuple(range(300, 320))


def _fpr_fields(objective: AttackerObjective) -> dict[str, float]:
    poisoned = 0.20 if objective == AttackerObjective.THRESHOLD_LOWER else 0.10
    return {
        "cv_fpr_clean": 0.10,
        "cv_fpr_poisoned": poisoned,
        "delta_cv_fpr": poisoned - 0.10,
        "mean_fpr_clean": 0.10,
        "mean_fpr_poisoned": poisoned,
        "delta_mean_fpr": poisoned - 0.10,
        "iqr_fpr_clean": 0.01,
        "iqr_fpr_poisoned": 0.03 if poisoned > 0.10 else 0.01,
        "delta_iqr_fpr": 0.02 if poisoned > 0.10 else 0.0,
        "max_min_fpr_clean": 0.02,
        "max_min_fpr_poisoned": 0.05 if poisoned > 0.10 else 0.02,
        "delta_max_min_fpr": 0.03 if poisoned > 0.10 else 0.0,
        "worst_client_fpr_clean": 0.20,
        "worst_client_fpr_poisoned": 0.35 if poisoned > 0.10 else 0.20,
        "delta_worst_client_fpr": 0.15 if poisoned > 0.10 else 0.0,
    }


def _victim_harm_fields(objective: AttackerObjective) -> dict[str, float]:
    poisoned = 0.80 if objective == AttackerObjective.THRESHOLD_RAISE else 0.90
    return {
        "victim_tpr_clean": 0.90,
        "victim_tpr_poisoned": poisoned,
        "victim_delta_tpr": poisoned - 0.90,
        "victim_ba_clean": 0.85,
        "victim_ba_poisoned": 0.75 if poisoned < 0.90 else 0.85,
        "victim_delta_ba": -0.10 if poisoned < 0.90 else 0.0,
        "victim_macro_f1_clean": 0.80,
        "victim_macro_f1_poisoned": 0.70 if poisoned < 0.90 else 0.80,
        "victim_delta_macro_f1": -0.10 if poisoned < 0.90 else 0.0,
    }


def _cluster_fields(policy: ThresholdPolicy, delta_tau: float) -> dict[str, float]:
    fields = (
        "cluster_delta_tau_agg",
        "cluster_delta_tau_churn",
        "cluster_delta_tau_frozen_scaler",
        "cluster_delta_tau_normalization_gap",
        "cluster_victim_effect",
        "cluster_non_victim_effect",
    )
    if policy != ThresholdPolicy.CLUSTER_THRESHOLD:
        return dict.fromkeys(fields, math.nan)
    return {
        "cluster_delta_tau_agg": 0.10,
        "cluster_delta_tau_churn": 0.05,
        "cluster_delta_tau_frozen_scaler": 0.12,
        "cluster_delta_tau_normalization_gap": 0.03,
        "cluster_victim_effect": delta_tau,
        "cluster_non_victim_effect": 0.02,
    }


def _row(
    *,
    source: PoisoningSourceStrategy,
    objective: AttackerObjective,
    training_seed: int,
    poisoning_seed: int,
    victim_id: str,
    delta_tau: float,
    fraction: float = 0.10,
    policy: ThresholdPolicy = ThresholdPolicy.LOCAL_THRESHOLD,
) -> BoundedSweepResultRow:
    seed_record = SeedRecord(
        pair=SeedPair(training_seed=training_seed, poisoning_seed=poisoning_seed),
        client_idx=int(victim_id[1:]),
        scope_idx=0,
    )
    return BoundedSweepResultRow(
        policy=policy,
        source=source,
        objective=objective,
        fraction=fraction,
        target_scope=PoisoningTargetScope.SINGLE_CLIENT,
        victim_id=victim_id,
        training_seed=training_seed,
        poisoning_seed=poisoning_seed,
        seed_record=seed_record,
        delta_tau=delta_tau,
        delta_tau_rel=delta_tau,
        is_victim_significant=not math.isclose(delta_tau, 0.0),
        **_fpr_fields(objective),
        coverage_ratio=1.0,
        n_eligible=9,
        mu_flag_triggered=False,
        auroc_invariant=True,
        blast_fraction=0.0,
        n_blast_significant=0,
        n_spillover=2 if policy == ThresholdPolicy.CLUSTER_THRESHOLD else 0,
        n_non_victims=8,
        **_victim_harm_fields(objective),
        **_cluster_fields(policy, delta_tau),
        **extended_row_fields(policy),
    )


def _manifest(rows: tuple[BoundedSweepResultRow, ...]) -> BoundedSweepManifest:
    return BoundedSweepManifest(
        generated_at_utc="2026-06-23T00:00:00+00:00",
        provenance=ProvenanceRecord(
            local_epochs=1,
            repository=REPOSITORY_NAME,
            code_commit="test-commit",
        ),
        policies=(ThresholdPolicy.LOCAL_THRESHOLD, ThresholdPolicy.CLUSTER_THRESHOLD),
        sources=(
            PoisoningSourceStrategy.RANDOM_BENIGN,
            PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            PoisoningSourceStrategy.LOW_SCORE_BENIGN,
        ),
        source_objective_pairs=(
            "random_benign+threshold_raise",
            "random_benign+threshold_lower",
            "high_score_benign+threshold_raise",
            "low_score_benign+threshold_lower",
        ),
        fractions=(0.10,),
        training_seeds=_TRAINING,
        poisoning_seeds=_POISONING,
        analysis_seeds=_ANALYSIS,
        config_hash="config-hash",
        artifact_provenance=ArtifactProvenance(
            source=ManifestProvenanceSource.NBAIOT_MAIN_SWEEP
        ),
        mu_flag_threshold_by_training_seed=dict.fromkeys(_TRAINING, 0.01),
        n_cells=len(rows),
        results=rows,
    )


def _write_manifest(base_dir: Path, manifest: BoundedSweepManifest) -> None:
    path = nbaiot_main_manifest_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest.model_dump_json(indent=2))


def _synthetic_rows() -> tuple[BoundedSweepResultRow, ...]:
    rows: list[BoundedSweepResultRow] = []
    for policy in (ThresholdPolicy.LOCAL_THRESHOLD, ThresholdPolicy.CLUSTER_THRESHOLD):
        for training_seed, poisoning_seed in zip(_TRAINING, _POISONING, strict=True):
            for victim_id in _VICTIMS:
                rows.extend(
                    (
                        _row(
                            policy=policy,
                            source=PoisoningSourceStrategy.RANDOM_BENIGN,
                            objective=AttackerObjective.THRESHOLD_RAISE,
                            training_seed=training_seed,
                            poisoning_seed=poisoning_seed,
                            victim_id=victim_id,
                            delta_tau=0.0,
                        ),
                        _row(
                            policy=policy,
                            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
                            objective=AttackerObjective.THRESHOLD_RAISE,
                            training_seed=training_seed,
                            poisoning_seed=poisoning_seed,
                            victim_id=victim_id,
                            delta_tau=1.00,
                        ),
                        _row(
                            policy=policy,
                            source=PoisoningSourceStrategy.RANDOM_BENIGN,
                            objective=AttackerObjective.THRESHOLD_LOWER,
                            training_seed=training_seed,
                            poisoning_seed=poisoning_seed,
                            victim_id=victim_id,
                            delta_tau=0.0,
                        ),
                        _row(
                            policy=policy,
                            source=PoisoningSourceStrategy.LOW_SCORE_BENIGN,
                            objective=AttackerObjective.THRESHOLD_LOWER,
                            training_seed=training_seed,
                            poisoning_seed=poisoning_seed,
                            victim_id=victim_id,
                            delta_tau=-1.00,
                        ),
                    )
                )
    return tuple(rows)


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, set[str]]:
    base = tmp_path_factory.mktemp("poisoning")
    _write_manifest(base, _manifest(_synthetic_rows()))
    names = {p.name for p in build_poisoning_summaries(base)}
    return base, names


def _load(built: tuple[Path, set[str]], stem: str) -> list[dict]:
    return json.loads((built[0] / "analysis" / f"{stem}.json").read_text())


def test_build_poisoning_summaries_writes_required_outputs(built) -> None:
    names = built[1]
    assert {
        "threshold_shift_summary.csv",
        "threshold_shift_summary.json",
        "directional_excess_over_random.csv",
        "directional_excess_over_random.json",
        "random_control_instability.csv",
        "random_control_instability.json",
        "leave_one_victim_out_sensitivity.csv",
        "leave_one_victim_out_sensitivity.json",
        "downstream_harm_raising.csv",
        "downstream_harm_raising.json",
        "downstream_harm_lowering.csv",
        "downstream_harm_lowering.json",
        "cluster_diagnostics_summary.csv",
        "cluster_diagnostics_summary.json",
        "claim_gate_decisions.csv",
        "claim_gate_decisions.json",
        "manifest_summary.json",
    }.issubset(names)


def test_lowering_directional_excess_is_sign_aware(built) -> None:
    data = _load(built, "directional_excess_over_random")
    lowering = next(
        row
        for row in data
        if row["objective"] == AttackerObjective.THRESHOLD_LOWER.value
        and row["policy"] == ThresholdPolicy.LOCAL_THRESHOLD.value
    )
    assert lowering["median_directional_excess"] == pytest.approx(1.00)
    assert lowering["gate2_pass"] is True


def test_claim_gate_outputs_full_vulnerability_for_supported_condition(built) -> None:
    data = _load(built, "claim_gate_decisions")
    assert {row["claim_class"] for row in data} == {"full_vulnerability"}


def test_five_seed_manifest_is_rejected() -> None:
    rows = tuple(
        _row(
            source=PoisoningSourceStrategy.RANDOM_BENIGN,
            objective=AttackerObjective.THRESHOLD_RAISE,
            training_seed=seed,
            poisoning_seed=seed + 100,
            victim_id="c0",
            delta_tau=0.0,
        )
        for seed in range(5)
    )
    with pytest.raises(ValidationError, match="0..19"):
        payload = _manifest(rows).model_dump()
        payload.update(
            {
                "training_seeds": tuple(range(5)),
                "poisoning_seeds": tuple(range(100, 105)),
                "analysis_seeds": tuple(range(300, 305)),
                "mu_flag_threshold_by_training_seed": dict.fromkeys(range(5), 0.01),
            }
        )
        BoundedSweepManifest.model_validate(payload)


def test_new_summaries_and_definitions_are_written(built) -> None:
    names = built[1]
    assert {
        "downstream_extended.json",
        "client_level_effects.json",
        "cluster_stability_summary.json",
        "duplicate_and_bound_summary.json",
        "gate_sensitivity.json",
        "metric_definitions.json",
    }.issubset(names)
    definitions = _load(built, "metric_definitions")
    assert "p10_macro_f1" in definitions
    assert "worst_ba" in definitions


def test_gate2_records_are_objective_matched_and_carry_distributions(built) -> None:
    data = _load(built, "directional_excess_over_random")
    assert data
    for row in data:
        assert row["control_objective"] == row["objective"]
        assert row["control_source"] == PoisoningSourceStrategy.RANDOM_BENIGN.value
        assert len(row["per_seed_directional_excess"]) == 20
        assert row["permutation_p"] == pytest.approx(2 / (2**20))
        assert row["mean_directional_excess"] == pytest.approx(1.0)


def test_downstream_records_carry_seed_values_and_intervals(built) -> None:
    data = _load(built, "downstream_extended")
    row = next(
        r
        for r in data
        if r["summary_metric"] == "victim_delta_tpr"
        and r["policy"] == ThresholdPolicy.LOCAL_THRESHOLD.value
    )
    assert len(row["per_seed_values"]) == 20
    assert row["bootstrap_ci_lower"] <= row["mean_effect"] <= row["bootstrap_ci_upper"]
    assert 0.0 <= row["permutation_p"] <= 1.0


def test_fixed_cluster_metrics_only_for_cluster_policy(built) -> None:
    data = _load(built, "downstream_extended")
    fixed = [r for r in data if r["summary_metric"].startswith("fixed_cluster_")]
    assert fixed
    assert {r["policy"] for r in fixed} == {ThresholdPolicy.CLUSTER_THRESHOLD.value}


def test_nonvictim_and_absolute_burden_metrics_present(built) -> None:
    data = _load(built, "downstream_extended")
    metrics = {r["summary_metric"] for r in data}
    assert {
        "nonvictim_mean_delta_tpr",
        "nonvictim_delta_fn_total",
        "nonvictim_delta_fp_total",
        "victim_delta_fn",
        "victim_delta_fp",
        "victim_delta_fpr",
    }.issubset(metrics)


def test_client_level_effects_one_record_per_victim(built) -> None:
    data = _load(built, "client_level_effects")
    group = [
        r
        for r in data
        if r["policy"] == ThresholdPolicy.LOCAL_THRESHOLD.value
        and r["source"] == PoisoningSourceStrategy.HIGH_SCORE_BENIGN.value
    ]
    assert {r["victim_id"] for r in group} == set(_VICTIMS)
    assert all(r["n_seeds"] == 20 for r in group)


def test_cluster_stability_summary_compares_fixed_and_recomputed(built) -> None:
    data = _load(built, "cluster_stability_summary")
    assert {r["policy"] for r in data} == {ThresholdPolicy.CLUSTER_THRESHOLD.value}
    row = data[0]
    assert row["recomputed_victim_delta_tau"] is not None
    assert row["fixed_victim_delta_tau"] == pytest.approx(0.05)
    assert row["reassignment_rate"] == 0.0
    assert row["modal_sizes_clean"] == [4, 3, 2]


def test_gate_sensitivity_default_cell_matches_protocol(built) -> None:
    data = _load(built, "gate_sensitivity")
    assert len(data) == 5 * 5 * 3 * 3
    default = next(
        r
        for r in data
        if (
            r["sign_consistency"],
            r["victim_majority"],
            r["materiality_factor"],
            r["iqr_floor_factor"],
        )
        == (16, 5, 0.1, 0.01)
    )
    assert default["n_changed_vs_default"] == 0
    assert default["n_full_vulnerability"] == default["n_groups"]


def test_materiality_factor_changes_significance_and_claim_class() -> None:
    from datp.enums import ClaimClassification
    from datp.reporting.poisoning import DEFAULT_GATE, GateParams, _claim_gate_decisions

    manifest = _manifest(_synthetic_rows())
    strict = GateParams(
        sign_consistency=DEFAULT_GATE.sign_consistency,
        victim_majority=DEFAULT_GATE.victim_majority,
        materiality_factor=100.0,
        iqr_floor_factor=DEFAULT_GATE.iqr_floor_factor,
    )
    default_classes = {d.claim_class for d in _claim_gate_decisions(manifest)}
    strict_classes = {d.claim_class for d in _claim_gate_decisions(manifest, strict)}
    assert default_classes == {ClaimClassification.FULL_VULNERABILITY}
    assert ClaimClassification.FULL_VULNERABILITY not in strict_classes


def test_duplicate_summary_reports_rates(built) -> None:
    data = _load(built, "duplicate_and_bound_summary")
    assert all(r["mean_duplicate_rate_poisoned"] == pytest.approx(0.05) for r in data)
    assert all(r["mean_n_replaced"] == pytest.approx(10.0) for r in data)


_BASE = {
    "victim_id": "c0",
    "source": PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
    "objective": AttackerObjective.THRESHOLD_RAISE,
    "fraction": 0.4,
}


def _manifest_sensitivity_summaries() -> SensitivityManifest:
    cluster = tuple(
        ClusterStabilityRow(
            **_BASE,
            training_seed=0,
            k=3,
            n_init=10,
            random_state=rs,
            victim_delta_tau=0.1 * (rs + 1),
            fixed_victim_delta_tau=0.05,
            victim_size_clean=2,
            victim_size_poisoned=1 if rs == 0 else 2,
            n_reassigned=3 if rs == 0 else 0,
            silhouette_clean=0.4,
            silhouette_poisoned=0.3,
            sizes_clean=(4, 3, 2),
            sizes_poisoned=(4, 4, 1),
        )
        for rs in range(2)
    )
    scale = (
        ScaleNormalizationRow(
            **_BASE,
            training_seed=0,
            tau_local_cv_clean=0.5,
            tau_local_max_min_ratio_clean=3.0,
            score_scale_cv_clean=0.6,
            raw_global_victim_delta_tau=0.2,
            normalized_global_victim_delta_tau=0.1,
            raw_global_victim_delta_fpr=0.02,
            normalized_global_victim_delta_fpr=0.01,
            raw_global_cv_fpr_clean=1.0,
            normalized_global_cv_fpr_clean=0.5,
            raw_global_cv_fpr_poisoned=1.2,
            normalized_global_cv_fpr_poisoned=0.6,
        ),
    )
    variants = (
        DrawVariantRow(
            **_BASE,
            training_seed=0,
            policy=ThresholdPolicy.LOCAL_THRESHOLD,
            draw=ReservoirDraw.WITHOUT_REPLACEMENT,
            requested_n_replaced=40,
            effective_n_replaced=10,
            pool_size=10,
            delta_tau_with_replacement=0.4,
            delta_tau_variant=0.1,
            duplicate_rate_with_replacement=0.3,
            duplicate_rate_variant=0.0,
        ),
        DrawVariantRow(
            **_BASE,
            training_seed=0,
            policy=ThresholdPolicy.LOCAL_THRESHOLD,
            draw=ReservoirDraw.INTERPOLATED_TAIL,
            requested_n_replaced=40,
            effective_n_replaced=40,
            pool_size=10,
            delta_tau_with_replacement=0.4,
            delta_tau_variant=0.3,
            duplicate_rate_with_replacement=0.3,
            duplicate_rate_variant=0.0,
        ),
    )
    trust = (
        TrustBoundaryRow(
            **_BASE,
            training_seed=0,
            policy=ThresholdPolicy.LOCAL_THRESHOLD,
            delta_tau_undefended=0.4,
            delta_tau_trim_primary=0.1,
            delta_tau_trim_appendix=0.0,
            residual_vs_clean_trim_primary=0.3,
            residual_vs_clean_trim_appendix=0.2,
            overwrite_reference_shift=0.8,
            buffer_to_overwrite_ratio=0.5,
        ),
    )
    return SensitivityManifest(
        generated_at_utc="2026-07-01T00:00:00+00:00",
        provenance=ProvenanceRecord(
            local_epochs=1, repository=REPOSITORY_NAME, code_commit="test-commit"
        ),
        config_hash="hash",
        cluster_stability=cluster,
        scale_normalization=scale,
        draw_variants=variants,
        trust_boundary=trust,
    )


def _write(base_dir: Path) -> None:
    path = sensitivity_manifest_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_manifest_sensitivity_summaries().model_dump_json())


def _load_sensitivity_summaries(base_dir: Path, stem: str) -> list[dict]:
    return json.loads((base_dir / "analysis" / f"{stem}.json").read_text())


def test_missing_manifest_is_reported(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="sensitivity manifest"):
        build_sensitivity_summaries(tmp_path)


def test_cluster_sensitivity_summary(tmp_path: Path) -> None:
    _write(tmp_path)
    build_sensitivity_summaries(tmp_path)
    row = _load_sensitivity_summaries(tmp_path, "cluster_stability_sensitivity")[0]
    assert row["k"] == 3
    assert row["victim_singleton_poisoned_rate"] == pytest.approx(0.5)
    assert row["reassignment_rate"] == pytest.approx(0.5)
    assert row["mean_init_sd_victim_delta_tau"] == pytest.approx(0.0707106781, rel=1e-6)


def test_scale_normalization_summary(tmp_path: Path) -> None:
    _write(tmp_path)
    build_sensitivity_summaries(tmp_path)
    row = _load_sensitivity_summaries(tmp_path, "scale_normalization_summary")[0]
    assert row["raw_global_victim_delta_tau"] == pytest.approx(0.2)
    assert row["normalized_global_victim_delta_tau"] == pytest.approx(0.1)
    assert row["mean_tau_local_max_min_ratio_clean"] == pytest.approx(3.0)


def test_draw_variant_summary(tmp_path: Path) -> None:
    _write(tmp_path)
    build_sensitivity_summaries(tmp_path)
    rows = {
        r["draw"]: r
        for r in _load_sensitivity_summaries(tmp_path, "draw_variant_summary")
    }
    distinct = rows[ReservoirDraw.WITHOUT_REPLACEMENT.value]
    assert distinct["full_budget_feasible_rate"] == 0.0
    assert distinct["mean_duplicate_rate_variant"] == 0.0
    assert distinct["variant_to_baseline_ratio"] == pytest.approx(0.25)
    assert distinct["synthesized_values"] is False
    interpolated = rows[ReservoirDraw.INTERPOLATED_TAIL.value]
    assert interpolated["synthesized_values"] is True
    assert interpolated["full_budget_feasible_rate"] == 1.0


def test_trust_boundary_summary(tmp_path: Path) -> None:
    _write(tmp_path)
    build_sensitivity_summaries(tmp_path)
    row = _load_sensitivity_summaries(tmp_path, "trust_boundary_summary")[0]
    assert row["mean_delta_tau_undefended"] == pytest.approx(0.4)
    assert row["trim_primary_reduction"] == pytest.approx(0.75)
    assert row["mean_buffer_to_overwrite_ratio"] == pytest.approx(0.5)


RNG = np.random.default_rng(99)


_DEVICE_IDS = [f"dev_{i}" for i in range(6)]


_ELIGIBLE_IDS = _DEVICE_IDS[:5]


_PENDING_IDS = _DEVICE_IDS[5:]


def _make_client_record(
    client_id: str, policy: ThresholdPolicy
) -> ClientEvaluationRecord:
    fpr = float(RNG.uniform(0.01, 0.15))
    tpr = float(RNG.uniform(0.85, 0.99))
    tnr = 1.0 - fpr
    fnr = 1.0 - tpr
    return ClientEvaluationRecord(
        client_id=client_id,
        metrics=BinaryMetrics(
            fpr=fpr,
            tpr=tpr,
            tnr=tnr,
            fnr=fnr,
            precision=90 / (90 + 5),
            recall=90 / (90 + 10),
            balanced_accuracy=float(RNG.uniform(0.80, 0.98)),
            macro_f1=float(RNG.uniform(0.75, 0.95)),
        ),
        confusion=ConfusionCounts(tp=90, fp=5, tn=95, fn=10),
        n_benign=100,
        n_attack=100,
        threshold=ClientThreshold(
            client_id=client_id,
            threshold=0.1,
            status=(
                ClientStatus.CALIBRATION_PENDING
                if client_id in _PENDING_IDS
                else ClientStatus.ELIGIBLE
            ),
            strategy=policy,
        ),
        evaluation_incomplete=False,
    )


def _make_eval_result(policy: ThresholdPolicy, seed: int) -> EvaluationResult:
    clients = tuple(_make_client_record(d, policy) for d in _DEVICE_IDS)
    eligible_fprs = [c.metrics.fpr for c in clients if c.client_id in _ELIGIBLE_IDS]
    eligible_tprs = [c.metrics.tpr for c in clients if c.client_id in _ELIGIBLE_IDS]
    from datp.statistics import cv

    _cv_fpr = cv(np.array(eligible_fprs), ddof=0)
    cv_fpr = float(_cv_fpr) if not math.isnan(_cv_fpr) else 0.0
    _cv_tpr = cv(np.array(eligible_tprs), ddof=0)
    cv_tpr = float(_cv_tpr) if not math.isnan(_cv_tpr) else 0.0
    mean_fpr = float(np.mean(eligible_fprs))
    std_fpr = float(np.std(eligible_fprs, ddof=1))
    fpr_arr = np.array(eligible_fprs)
    tpr_arr = np.array(eligible_tprs)
    iqr_fpr = (
        float(np.percentile(fpr_arr, 75) - np.percentile(fpr_arr, 25))
        if len(fpr_arr) >= 2
        else float("nan")
    )
    iqr_tpr = (
        float(np.percentile(tpr_arr, 75) - np.percentile(tpr_arr, 25))
        if len(tpr_arr) >= 2
        else float("nan")
    )
    ba_list = [
        c.metrics.balanced_accuracy for c in clients if c.client_id in _ELIGIBLE_IDS
    ]
    f1_list = [c.metrics.macro_f1 for c in clients if c.client_id in _ELIGIBLE_IDS]
    worst_fpr = float(max(eligible_fprs)) if eligible_fprs else float("nan")
    worst_id: str | None = next(
        (
            c.client_id
            for c in clients
            if c.client_id in _ELIGIBLE_IDS
            and math.isclose(c.metrics.fpr, worst_fpr, abs_tol=1e-12)
        ),
        None,
    )
    cell = TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=seed)
    run = PolicyRunId(cell=cell, policy=policy)
    return EvaluationResult(
        run=run,
        dataset=DatasetID.NBAIOT,
        clients=clients,
        eligible_ids=tuple(_ELIGIBLE_IDS),
        pending_ids=tuple(_PENDING_IDS),
        incomplete_ids=(),
        coverage_ratio=len(_ELIGIBLE_IDS) / len(_DEVICE_IDS),
        dispersion=DispersionMetrics(
            cv_fpr=cv_fpr,
            mean_fpr=mean_fpr,
            std_fpr=std_fpr,
            cv_tpr=cv_tpr,
            iqr_fpr=iqr_fpr,
            iqr_tpr=iqr_tpr,
            max_min_fpr_gap=worst_fpr - float(min(eligible_fprs))
            if len(eligible_fprs) >= 2
            else 0.0,
            worst_client_fpr=worst_fpr,
            worst_client_id=worst_id,
            eligible_count=len(eligible_fprs),
            client_count=len(clients),
            worst_ba=float(min(ba_list)) if ba_list else float("nan"),
            p10_macro_f1=float(np.percentile(f1_list, 10)) if f1_list else float("nan"),
        ),
    )


_STYLE = BASE_CONFIG.reporting.style


def _synthetic_results() -> dict[ThresholdPolicy, list[EvaluationResult]]:
    data: dict[ThresholdPolicy, list[EvaluationResult]] = {}
    for bl in (
        ThresholdPolicy.GLOBAL_THRESHOLD,
        ThresholdPolicy.LOCAL_THRESHOLD,
        ThresholdPolicy.CLUSTER_THRESHOLD,
    ):
        data[bl] = [_make_eval_result(bl, seed) for seed in range(2)]
    return data


def _synthetic_results_single_seed() -> dict[ThresholdPolicy, list[EvaluationResult]]:
    return {
        ThresholdPolicy.GLOBAL_THRESHOLD: [
            _make_eval_result(ThresholdPolicy.GLOBAL_THRESHOLD, 0)
        ]
    }


def test_generate_table3_creates_files(tmp_path: Path) -> None:
    tex_path = generate_table3(_synthetic_results(), tmp_path, style=_STYLE)
    assert tex_path.exists()
    assert tex_path.suffix == ".tex"
    csv_path = tmp_path / "table3_nbaiot.csv"
    assert csv_path.exists()


def test_table3_contains_footnote(tmp_path: Path) -> None:
    tex_path = generate_table3(_synthetic_results(), tmp_path, style=_STYLE)
    content = tex_path.read_text()
    assert MANDATORY_FOOTNOTE in content


def test_table3_contains_coverage_ratio(tmp_path: Path) -> None:
    tex_path = generate_table3(_synthetic_results(), tmp_path, style=_STYLE)
    content = tex_path.read_text()
    assert "0.83" in content


def test_table_labels_p10_macro_f1_precisely(tmp_path: Path) -> None:
    tex_path = generate_table3(_synthetic_results(), tmp_path, style=_STYLE)
    content = tex_path.read_text()
    assert "P10 client Macro-F1" in content
    assert "& Worst BA & Macro-F1 &" not in content


def test_build_table_row_multi_seed() -> None:
    results = [_make_eval_result(ThresholdPolicy.GLOBAL_THRESHOLD, s) for s in range(3)]
    row = _build_table_row(ThresholdPolicy.GLOBAL_THRESHOLD, results)
    assert row.policy == ThresholdPolicy.GLOBAL_THRESHOLD
    assert row.eligible_count == 5
    assert row.pending_count == 1
    assert row.coverage_ratio == pytest.approx(5 / 6)
    assert row.cv_fpr_std > 0


def test_build_table_row_single_seed() -> None:
    results = [_make_eval_result(ThresholdPolicy.LOCAL_THRESHOLD, 0)]
    row = _build_table_row(ThresholdPolicy.LOCAL_THRESHOLD, results)
    assert row.policy == ThresholdPolicy.LOCAL_THRESHOLD
    assert row.cv_fpr_std == pytest.approx(0.0)
    assert row.cv_tpr_std == pytest.approx(0.0)


def test_build_table_row_eligible_count_mismatch_raises() -> None:
    r1 = _make_eval_result(ThresholdPolicy.GLOBAL_THRESHOLD, 0)
    r2 = _make_eval_result(ThresholdPolicy.GLOBAL_THRESHOLD, 1)
    object.__setattr__(r2, "eligible_ids", ("dev_0", "dev_1"))
    with pytest.raises(ValueError, match="Coverage count mismatch"):
        _build_table_row(ThresholdPolicy.GLOBAL_THRESHOLD, [r1, r2])


def test_result_table_to_csv(tmp_path: Path) -> None:
    results = [_make_eval_result(ThresholdPolicy.GLOBAL_THRESHOLD, 0)]
    row = _build_table_row(ThresholdPolicy.GLOBAL_THRESHOLD, results)
    table = ResultTable(title="Test", style=_STYLE, rows=[row])
    csv_path = table.to_csv(tmp_path / "test.csv")
    assert csv_path.exists()

    with csv_path.open("r") as f:
        reader = list(csv.reader(f))
    assert reader[0][0] == "ThresholdPolicy"
    assert MANDATORY_FOOTNOTE in reader[-1][0]


def test_build_table_row_nonfinite_coverage_raises() -> None:
    r1 = _make_eval_result(ThresholdPolicy.GLOBAL_THRESHOLD, 0)
    object.__setattr__(r1, "coverage_ratio", float("nan"))
    with pytest.raises(ValueError, match="Coverage ratio missing"):
        _build_table_row(ThresholdPolicy.GLOBAL_THRESHOLD, [r1])


def test_format_mean_std_normal() -> None:
    result = format_mean_std(0.123, 0.045, bold=False)
    assert "\\textbf" not in result
    assert "0.123" in result
    assert "±" in result
    assert "0.045" in result


def test_format_mean_std_bold() -> None:
    result = format_mean_std(0.123, 0.045, bold=True)
    assert "\\textbf" in result


def test_format_mean_std_nan_returns_dash() -> None:
    assert format_mean_std(float("nan"), 0.045, bold=False) == "---"
    assert format_mean_std(float("nan"), 0.045, bold=True) == "---"


def test_format_mean_std_zero_std() -> None:
    result = format_mean_std(0.5, 0.0, bold=False)
    assert "0.500" in result
    assert "0.000" in result


def test_analysis_csv_uses_unix_line_endings(tmp_path: Path) -> None:
    """Verify generated csv files end lines with LF so git never rewrites them."""
    from datp.enums import AnalysisReportStem
    from datp.reporting.poisoning import _write_records

    _, csv_path = _write_records(
        tmp_path,
        AnalysisReportStem.THRESHOLD_SHIFT_SUMMARY,
        [{"a": 1, "b": 2}, {"a": 3, "b": 4}],
    )

    assert b"\r" not in csv_path.read_bytes()


class TestClaimClassification:
    """The control-instability flag only demotes a claim when the control confounds it."""

    def test_unstable_control_demotes_to_instability(self) -> None:
        assert (
            _classify_claim(True, True, True, True)
            is ClaimClassification.CALIBRATION_INSTABILITY
        )

    def test_missing_excess_over_control_demotes_to_instability(self) -> None:
        assert (
            _classify_claim(False, True, False, True)
            is ClaimClassification.CALIBRATION_INSTABILITY
        )

    def test_all_gates_pass_is_full_vulnerability(self) -> None:
        assert (
            _classify_claim(False, True, True, True)
            is ClaimClassification.FULL_VULNERABILITY
        )

    def test_threshold_shift_without_downstream_harm_is_mechanism_only(self) -> None:
        assert (
            _classify_claim(False, True, True, False)
            is ClaimClassification.MECHANISM_ONLY
        )

    def test_no_threshold_shift_is_null(self) -> None:
        assert (
            _classify_claim(False, False, True, True)
            is ClaimClassification.NULL_OR_CONDITIONAL
        )
