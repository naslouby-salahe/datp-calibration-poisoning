"""Unit tests for poisoning-results report generation."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from pydantic import ValidationError

from datp.artifacts.poison_layout import PoisonLayout
from datp.attacks.enums import (
    AttackerObjective,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
)
from datp.attacks.manifests.bounded_sweep_manifest import (
    BoundedSweepManifest,
    BoundedSweepResultRow,
)
from datp.attacks.manifests.run_manifest import ProvenanceRecord
from datp.core.enums import ThresholdPolicy
from datp.core.provenance import REPOSITORY_NAME
from datp.core.seeds import derive_seed_record
from datp.core.seeds import SeedPair
from datp.reporting.poisoning import build_poisoning_summaries

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
    seed_record = derive_seed_record(
        SeedPair(training_seed=training_seed, poisoning_seed=poisoning_seed),
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
        artifact_provenance={"source": "synthetic-test"},
        mu_flag_threshold_by_training_seed=dict.fromkeys(_TRAINING, 0.01),
        n_cells=len(rows),
        results=rows,
    )


def _write_manifest(base_dir: Path, manifest: BoundedSweepManifest) -> None:
    path = PoisonLayout(base_dir=base_dir).nbaiot_main_manifest()
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
    names = {path.name for path in result.paths}
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
