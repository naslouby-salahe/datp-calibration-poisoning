"""Unit tests for poisoning-results report generation."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from pydantic import ValidationError

from datp.artifacts.layout import nbaiot_main_manifest_path
from datp.attacks.enums import (
    AttackerObjective,
    ManifestProvenanceSource,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
)
from datp.attacks.manifests.bounded_sweep_manifest import (
    ArtifactProvenance,
    BoundedSweepManifest,
    BoundedSweepResultRow,
)
from datp.attacks.manifests.run_manifest import ProvenanceRecord
from datp.core.enums import ThresholdPolicy
from datp.core.provenance import REPOSITORY_NAME
from datp.core.seeds import SeedPair, SeedRecord
from datp.reporting.poisoning import build_poisoning_summaries
from tests.fixtures.sweep_rows import extended_row_fields

_VICTIMS = tuple(f"c{i}" for i in range(9))
_TRAINING = tuple(range(10))
_POISONING = tuple(range(100, 110))
_ANALYSIS = tuple(range(300, 310))


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


def test_build_poisoning_summaries_writes_required_outputs(tmp_path: Path) -> None:
    _write_manifest(tmp_path, _manifest(_synthetic_rows()))
    result = build_poisoning_summaries(tmp_path)
    names = {path.name for path in result}
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


def test_lowering_directional_excess_is_sign_aware(tmp_path: Path) -> None:
    _write_manifest(tmp_path, _manifest(_synthetic_rows()))
    build_poisoning_summaries(tmp_path)
    data = json.loads(
        (tmp_path / "analysis" / "directional_excess_over_random.json").read_text()
    )
    lowering = next(
        row
        for row in data
        if row["objective"] == AttackerObjective.THRESHOLD_LOWER.value
        and row["policy"] == ThresholdPolicy.LOCAL_THRESHOLD.value
    )
    assert lowering["median_directional_excess"] == pytest.approx(1.00)
    assert lowering["gate2_pass"] is True


def test_claim_gate_outputs_full_vulnerability_for_supported_condition(
    tmp_path: Path,
) -> None:
    _write_manifest(tmp_path, _manifest(_synthetic_rows()))
    build_poisoning_summaries(tmp_path)
    data = json.loads((tmp_path / "analysis" / "claim_gate_decisions.json").read_text())
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
    with pytest.raises(ValidationError, match="0..9"):
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


def _build_and_load(tmp_path: Path, stem: str) -> list[dict]:
    _write_manifest(tmp_path, _manifest(_synthetic_rows()))
    build_poisoning_summaries(tmp_path)
    return json.loads((tmp_path / "analysis" / f"{stem}.json").read_text())


def test_new_summaries_and_definitions_are_written(tmp_path: Path) -> None:
    _write_manifest(tmp_path, _manifest(_synthetic_rows()))
    names = {p.name for p in build_poisoning_summaries(tmp_path)}
    assert {
        "downstream_extended.json",
        "client_level_effects.json",
        "cluster_stability_summary.json",
        "duplicate_and_bound_summary.json",
        "gate_sensitivity.json",
        "metric_definitions.json",
    }.issubset(names)
    definitions = json.loads(
        (tmp_path / "analysis" / "metric_definitions.json").read_text()
    )
    assert "p10_macro_f1" in definitions
    assert "worst_ba" in definitions


def test_gate2_records_are_objective_matched_and_carry_distributions(
    tmp_path: Path,
) -> None:
    data = _build_and_load(tmp_path, "directional_excess_over_random")
    assert data
    for row in data:
        assert row["control_objective"] == row["objective"]
        assert row["control_source"] == PoisoningSourceStrategy.RANDOM_BENIGN.value
        assert len(row["per_seed_directional_excess"]) == 10
        assert row["permutation_p"] == pytest.approx(2 / 1024)
        assert row["mean_directional_excess"] == pytest.approx(1.0)


def test_downstream_records_carry_seed_values_and_intervals(tmp_path: Path) -> None:
    data = _build_and_load(tmp_path, "downstream_extended")
    row = next(
        r
        for r in data
        if r["summary_metric"] == "victim_delta_tpr"
        and r["policy"] == ThresholdPolicy.LOCAL_THRESHOLD.value
    )
    assert len(row["per_seed_values"]) == 10
    assert row["bootstrap_ci_lower"] <= row["mean_effect"] <= row["bootstrap_ci_upper"]
    assert 0.0 <= row["permutation_p"] <= 1.0


def test_fixed_cluster_metrics_only_for_cluster_policy(tmp_path: Path) -> None:
    data = _build_and_load(tmp_path, "downstream_extended")
    fixed = [r for r in data if r["summary_metric"].startswith("fixed_cluster_")]
    assert fixed
    assert {r["policy"] for r in fixed} == {ThresholdPolicy.CLUSTER_THRESHOLD.value}


def test_nonvictim_and_absolute_burden_metrics_present(tmp_path: Path) -> None:
    data = _build_and_load(tmp_path, "downstream_extended")
    metrics = {r["summary_metric"] for r in data}
    assert {
        "nonvictim_mean_delta_tpr",
        "nonvictim_delta_fn_total",
        "nonvictim_delta_fp_total",
        "victim_delta_fn",
        "victim_delta_fp",
        "victim_delta_fpr",
    }.issubset(metrics)


def test_client_level_effects_one_record_per_victim(tmp_path: Path) -> None:
    data = _build_and_load(tmp_path, "client_level_effects")
    group = [
        r
        for r in data
        if r["policy"] == ThresholdPolicy.LOCAL_THRESHOLD.value
        and r["source"] == PoisoningSourceStrategy.HIGH_SCORE_BENIGN.value
    ]
    assert {r["victim_id"] for r in group} == set(_VICTIMS)
    assert all(r["n_seeds"] == 10 for r in group)


def test_cluster_stability_summary_compares_fixed_and_recomputed(
    tmp_path: Path,
) -> None:
    data = _build_and_load(tmp_path, "cluster_stability_summary")
    assert {r["policy"] for r in data} == {ThresholdPolicy.CLUSTER_THRESHOLD.value}
    row = data[0]
    assert row["recomputed_victim_delta_tau"] is not None
    assert row["fixed_victim_delta_tau"] == pytest.approx(0.05)
    assert row["reassignment_rate"] == 0.0
    assert row["modal_sizes_clean"] == [4, 3, 2]


def test_gate_sensitivity_default_cell_matches_protocol(tmp_path: Path) -> None:
    data = _build_and_load(tmp_path, "gate_sensitivity")
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
        == (8, 5, 0.1, 0.01)
    )
    assert default["n_changed_vs_default"] == 0
    assert default["n_full_vulnerability"] == default["n_groups"]


def test_materiality_factor_changes_significance_and_claim_class() -> None:
    from datp.reporting.poisoning import (
        DEFAULT_GATE,
        GateParams,
        _claim_gate_decisions,
    )
    from datp.attacks.enums import ClaimClassification

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


def test_duplicate_summary_reports_rates(tmp_path: Path) -> None:
    data = _build_and_load(tmp_path, "duplicate_and_bound_summary")
    assert all(r["mean_duplicate_rate_poisoned"] == pytest.approx(0.05) for r in data)
    assert all(r["mean_n_replaced"] == pytest.approx(10.0) for r in data)
