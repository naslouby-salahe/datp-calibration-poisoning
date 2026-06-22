"""synthetic smoke validation — end-to-end protocol invariants (Phase D).

CPU-only, deterministic, no real data. Asserts the union of the smoke invariants
from the tickets and the protocol-of-record
``docs/DATP_CP_Roadmap.md`` §10 line 142. Each invariant is a behavior assertion
over the real pipeline wired by ``datp.testsupport.smoke_harness``.

Invariant map (see the decision log 2026-06-16 reconciliation entry):
  Prompt 1 f=0 reproduces clean exactly, zero Δτ
  Prompt 2 cardinality preserved after injection
  Prompt 3 clean arrays never mutated in place
  Prompt 4 HIGH raises / LOW lowers thresholds (direction)
  Prompt 5 Calibration-Pending excluded from victims/CV(FPR), gets tau_global
  Prompt 6 determinism (same seeds -> identical outputs)
  Prompt 7 CLUSTER_THRESHOLD Δτ_total = Δτ_agg + Δτ_churn
  Prompt 8 two-layer stats: bootstrap on 5 seed aggregates, not 45
  Prompt 9 manifest round-trips (child seeds, locks, reservoir mode, mu_flag)
  Prompt 10 AUROC invariant (test scores unchanged)
  Prompt 11 CV(FPR) reported with coverage, no ε
  Roadmap RANDOM_BENIGN -> near-null
  Roadmap GLOBAL_THRESHOLD victim shift < LOCAL_THRESHOLD victim shift (same single-client attack)
  Roadmap CLUSTER_THRESHOLD K stays fixed at 3 under clean AND poisoned cal
  Roadmap outputs in temp only
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from datp.artifacts.poison_names import (
    CLUSTER_K_NBAIOT,
    CALIBRATION_POISONING_OUTPUT_ROOT,
)
from datp.attacks.constants import POISONING_SEEDS
from datp.attacks.threshold_recomputation.cluster_threshold_recompute import ClusterThresholdPair
from datp.attacks.execution.cell_runner import (
    InjectionSpec,
    inject_single_victim,
    pending_threshold,
)
from datp.attacks.planning.guardrails import assert_no_inplace_mutation
from datp.attacks.metrics.inference import (
    InferenceInput,
    PairedDeltas,
    SeedDelta,
    collect_paired_deltas,
    compute_inference,
)
from datp.attacks.metrics.metric_engine import compute_fleet_fpr
from datp.attacks.manifests.run_logger import (
    ManifestBuildRequest,
    ManifestEmissionError,
    build_manifest,
    emit_manifest,
    load_manifest,
)
from datp.attacks.manifests.run_manifest import RESERVOIR_MODE
from datp.attacks.score_containers import build_score_collection
from datp.attacks.reservoirs.source_strategies import near_null_criterion
from datp.attacks.threshold_recomputation.threshold_recompute import ThresholdPair
from datp.attacks.enums import (
    AttackerObjective,
    CalibrationInjectionRule,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ThresholdPolicy,
)
from datp.core.seeds import SeedPair
from datp.config.stages import ExperimentStage
from datp.testsupport.smoke_harness import (
    cluster_count,
    collection_from_score_set,
    run_smoke_cell,
    victim_seed_deltas,
)
from datp.testsupport.synthetic_scores import make_standard_score_set
from datp.thresholding.eligibility import ClientThresholdsCollection

pytestmark = pytest.mark.integration

_VICTIM = "eligible_0"
_HIGH_FRACTION = 0.40
_ALL_POLICIES = (
    ThresholdPolicy.GLOBAL_THRESHOLD,
    ThresholdPolicy.LOCAL_THRESHOLD,
    ThresholdPolicy.CLUSTER_THRESHOLD,
)


@pytest.fixture
def collection():
    """Standard 9-eligible + 1-pending synthetic collection (deterministic)."""
    return collection_from_score_set(make_standard_score_set(n_eligible=9, n_pending=1))


# ---------------------------------------------------------------------------
# Invariant 1 — f=0 reproduces clean exactly with zero Δτ
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("policy", _ALL_POLICIES)
def test_invariant_1_f0_reproduces_clean_zero_delta(collection, policy):
    cell = run_smoke_cell(
        collection,
        victim_id=_VICTIM,
        policy=policy,
        source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        fraction=0.0,
    )
    # Poisoned cal is an exact copy of clean cal for the victim.
    np.testing.assert_array_equal(
        cell.outcome.poisoned_cal[_VICTIM], collection.clients[_VICTIM].cal
    )
    # Every per-victim Δτ is exactly zero.
    for entry in cell.poisoned_metrics.delta_tau.values():
        assert entry.delta_tau == pytest.approx(0.0)
    assert cell.outcome.injection.n_replaced == 0


# ---------------------------------------------------------------------------
# Invariant 2 — cardinality preserved after injection
# ---------------------------------------------------------------------------


def test_invariant_2_cardinality_preserved(collection):
    n_before = collection.clients[_VICTIM].n_cal
    outcome = inject_single_victim(
        collection,
        victim_id=_VICTIM,
        spec=InjectionSpec(
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            fraction=_HIGH_FRACTION,
            seed_pair=SeedPair(training_seed=0, poisoning_seed=100),
        ),
    )
    assert outcome.injection.n_total == n_before
    assert outcome.poisoned_cal[_VICTIM].shape[0] == n_before
    assert outcome.injection.n_replaced == max(1, round(_HIGH_FRACTION * n_before))
    # Eligibility partition is invariant under replacement.
    rebuilt: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for cid, c in collection.clients.items():
        cal = outcome.poisoned_cal[cid] if cid in outcome.poisoned_cal else c.cal
        rebuilt[cid] = (cal, c.test_benign, c.test_attack)
    poisoned_collection = build_score_collection(rebuilt)
    assert poisoned_collection.eligible_ids == collection.eligible_ids


# ---------------------------------------------------------------------------
# Invariant 3 — clean arrays never mutated in place
# ---------------------------------------------------------------------------


def test_invariant_3_no_inplace_mutation(collection):
    victim_clean = collection.clients[_VICTIM].cal
    snapshot = victim_clean.copy()
    cell = run_smoke_cell(
        collection,
        victim_id=_VICTIM,
        policy=ThresholdPolicy.LOCAL_THRESHOLD,
        source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        fraction=_HIGH_FRACTION,
    )
    # The victim's clean array object is unchanged after the full pipeline.
    assert_no_inplace_mutation(snapshot, collection.clients[_VICTIM].cal)
    # The poisoned array is a distinct object that actually differs.
    assert cell.outcome.poisoned_cal[_VICTIM] is not victim_clean
    assert not np.array_equal(cell.outcome.poisoned_cal[_VICTIM], snapshot)


# ---------------------------------------------------------------------------
# Invariant 4 — HIGH raises, LOW lowers (direction)
# ---------------------------------------------------------------------------


def test_invariant_4_high_raises_low_lowers_local_threshold(collection):
    high = run_smoke_cell(
        collection,
        victim_id=_VICTIM,
        policy=ThresholdPolicy.LOCAL_THRESHOLD,
        source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        fraction=_HIGH_FRACTION,
    )
    low = run_smoke_cell(
        collection,
        victim_id=_VICTIM,
        policy=ThresholdPolicy.LOCAL_THRESHOLD,
        source=PoisoningSourceStrategy.LOW_SCORE_BENIGN,
        fraction=_HIGH_FRACTION,
    )
    assert high.poisoned_metrics.delta_tau[_VICTIM].delta_tau > 0.0
    assert low.poisoned_metrics.delta_tau[_VICTIM].delta_tau < 0.0


# ---------------------------------------------------------------------------
# Invariant 5 — Calibration-Pending excluded; receives tau_global
# ---------------------------------------------------------------------------


def test_invariant_5_pending_excluded_and_gets_tau_global(collection):
    pending_ids = collection.pending_ids
    assert pending_ids, "fixture must include a Calibration-Pending client"
    pending = pending_ids[0]

    for policy in _ALL_POLICIES:
        cell = run_smoke_cell(
            collection,
            victim_id=_VICTIM,
            policy=policy,
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            fraction=_HIGH_FRACTION,
        )
        pair = cell.poisoned_pair
        # Pending client is not an eligible victim / not in per-client thresholds.
        assert pending not in collection.eligible_ids
        assert pending not in pair.thresholds_pois
        assert pending not in pair.thresholds_clean
        # Pending excluded from per-victim Δτ and from CV(FPR) eligibility count.
        assert pending not in cell.poisoned_metrics.delta_tau
        fleet = cell.poisoned_metrics.fleet_fpr
        assert fleet.n_eligible == len(collection.eligible_ids)
        assert fleet.n_total == len(collection.clients)
        # Pending client's fallback threshold is the global threshold.
        assert pending_threshold(pair) == pair.tau_global_pois


# ---------------------------------------------------------------------------
# Invariant 6 — determinism (same seeds -> identical outputs)
# ---------------------------------------------------------------------------


def test_invariant_6_determinism(collection):
    out_a = inject_single_victim(
        collection,
        victim_id=_VICTIM,
        spec=InjectionSpec(
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            fraction=_HIGH_FRACTION,
            seed_pair=SeedPair(training_seed=0, poisoning_seed=100),
        ),
    )
    out_b = inject_single_victim(
        collection,
        victim_id=_VICTIM,
        spec=InjectionSpec(
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            fraction=_HIGH_FRACTION,
            seed_pair=SeedPair(training_seed=0, poisoning_seed=100),
        ),
    )
    np.testing.assert_array_equal(
        out_a.poisoned_cal[_VICTIM], out_b.poisoned_cal[_VICTIM]
    )
    np.testing.assert_array_equal(
        out_a.injection.positions_replaced, out_b.injection.positions_replaced
    )

    cell_a = run_smoke_cell(
        collection,
        victim_id=_VICTIM,
        policy=ThresholdPolicy.LOCAL_THRESHOLD,
        source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        fraction=_HIGH_FRACTION,
    )
    cell_b = run_smoke_cell(
        collection,
        victim_id=_VICTIM,
        policy=ThresholdPolicy.LOCAL_THRESHOLD,
        source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        fraction=_HIGH_FRACTION,
    )
    assert cell_a.poisoned_metrics.delta_tau[_VICTIM].delta_tau == pytest.approx(
        cell_b.poisoned_metrics.delta_tau[_VICTIM].delta_tau
    )
    cv_fpr_a = cell_a.poisoned_metrics.fleet_fpr.cv_fpr
    cv_fpr_b = cell_b.poisoned_metrics.fleet_fpr.cv_fpr
    assert cv_fpr_a == pytest.approx(cv_fpr_b) or (
        math.isnan(cv_fpr_a) and math.isnan(cv_fpr_b)
    )


# ---------------------------------------------------------------------------
# Invariant 7 — CLUSTER_THRESHOLD decomposition identity Δτ_total = Δτ_agg + Δτ_churn
# ---------------------------------------------------------------------------


def test_invariant_7_cluster_threshold_decomposition_identity(collection):
    cell = run_smoke_cell(
        collection,
        victim_id=_VICTIM,
        policy=ThresholdPolicy.CLUSTER_THRESHOLD,
        source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        fraction=_HIGH_FRACTION,
    )
    pair = cell.poisoned_pair
    assert isinstance(pair, ClusterThresholdPair)
    assert pair.decomposition  # client-indexed, non-empty
    for entry in pair.decomposition.values():
        assert math.isfinite(entry.delta_tau_total)
        assert math.isfinite(entry.delta_tau_agg)
        assert math.isfinite(entry.delta_tau_churn)
        assert entry.delta_tau_total == pytest.approx(
            entry.delta_tau_agg + entry.delta_tau_churn, abs=1e-9
        )


# ---------------------------------------------------------------------------
# Invariant 8 — two-layer stats: bootstrap on 5 seed aggregates, not 45
# ---------------------------------------------------------------------------


def test_invariant_8_two_layer_bootstrap_on_seed_aggregates(collection):
    eligible = collection.eligible_ids
    deltas: dict[str, dict[int, SeedDelta]] = {}
    for victim in eligible:
        seed_deltas = victim_seed_deltas(
            collection,
            victim_id=victim,
            policy=ThresholdPolicy.LOCAL_THRESHOLD,
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            fraction=_HIGH_FRACTION,
            poisoning_seeds=POISONING_SEEDS,
        )
        deltas[victim] = collect_paired_deltas(
            victim_id=victim, seed_deltas=seed_deltas
        )
    paired = PairedDeltas(deltas=deltas)

    result = compute_inference(
        InferenceInput(
            paired=paired,
            poisoning_seeds=POISONING_SEEDS,
            direction="raise",
        )
    )
    # Layer 2: exactly 5 seed-level aggregates (one per poisoning seed).
    assert len(result.seed_aggregates) == len(POISONING_SEEDS) == 5
    # Bootstrap CI is computed on the 5 aggregates — NOT on 9*5 = 45 raw deltas.
    assert result.bootstrap_ci.n_seeds == 5
    assert len(eligible) * len(POISONING_SEEDS) == 45
    assert result.n_feasible_victims == len(eligible)
    # Supporting sign test also operates on the 5 aggregates.
    assert result.sign_test.n_total == 5


# ---------------------------------------------------------------------------
# Invariant 9 — manifest round-trips with all locks
# ---------------------------------------------------------------------------


def test_invariant_9_manifest_round_trip(collection, tmp_path):
    cell = run_smoke_cell(
        collection,
        victim_id=_VICTIM,
        policy=ThresholdPolicy.LOCAL_THRESHOLD,
        source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        fraction=_HIGH_FRACTION,
    )
    manifest = build_manifest(
        ManifestBuildRequest(
            dataset="synthetic",
            stage=ExperimentStage.SYNTHETIC_SMOKE,
            policy=ThresholdPolicy.LOCAL_THRESHOLD,
            objective=AttackerObjective.THRESHOLD_RAISE,
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            fraction=_HIGH_FRACTION,
            target_scope=PoisoningTargetScope.SINGLE_CLIENT,
            training_seed=0,
            poisoning_seed=100,
            client_idx=0,
            scope_idx=0,
            mu_flag_threshold=cell.mu_flag_threshold,
            repository="datp-calibration-poisoning",
        )
    )
    run_dir = tmp_path / "cell"
    emit_manifest(manifest, run_dir)
    loaded = load_manifest(run_dir)

    assert loaded.reservoir_mode == RESERVOIR_MODE
    assert loaded.mu_flag_threshold == pytest.approx(cell.mu_flag_threshold)
    assert loaded.injection_rule == CalibrationInjectionRule.REPLACE_FIXED_BUDGET
    assert loaded.provenance.local_epochs == 1  # E=1 lock
    # All child seeds round-trip via the recorded SeedSequence entropy.
    assert loaded.seed_record.entropy == (0, 100, 0, 0)
    assert loaded.seed_record.training_seed == 0
    assert loaded.seed_record.poisoning_seed == 100
    assert loaded.seed_record.client_idx == 0
    assert loaded.seed_record.scope_idx == 0


def test_invariant_9_manifest_requires_locked_mu_flag(tmp_path):
    manifest = build_manifest(
        ManifestBuildRequest(
            dataset="synthetic",
            stage=ExperimentStage.SYNTHETIC_SMOKE,
            policy=ThresholdPolicy.LOCAL_THRESHOLD,
            objective=AttackerObjective.THRESHOLD_RAISE,
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            fraction=_HIGH_FRACTION,
            target_scope=PoisoningTargetScope.SINGLE_CLIENT,
            training_seed=0,
            poisoning_seed=100,
            client_idx=0,
            scope_idx=0,
            mu_flag_threshold=None,
            repository="datp-calibration-poisoning",
        )
    )
    with pytest.raises(ManifestEmissionError):
        emit_manifest(manifest, tmp_path / "cell")


# ---------------------------------------------------------------------------
# Invariant 10 — AUROC invariant (test scores never modified)
# ---------------------------------------------------------------------------


def test_invariant_10_auroc_invariant(collection):
    cell = run_smoke_cell(
        collection,
        victim_id=_VICTIM,
        policy=ThresholdPolicy.LOCAL_THRESHOLD,
        source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        fraction=_HIGH_FRACTION,
    )
    clean = cell.clean_metrics.auroc_records
    poisoned = cell.poisoned_metrics.auroc_records
    assert clean.keys() == poisoned.keys()
    for cid in clean:
        assert clean[cid].auroc is not None
        assert poisoned[cid].auroc is not None
        assert clean[cid].auroc == pytest.approx(poisoned[cid].auroc)


# ---------------------------------------------------------------------------
# Invariant 11 — CV(FPR) reported with coverage; no ε in denominator
# ---------------------------------------------------------------------------


def test_invariant_11_cv_fpr_reported_with_coverage(collection):
    cell = run_smoke_cell(
        collection,
        victim_id=_VICTIM,
        policy=ThresholdPolicy.LOCAL_THRESHOLD,
        source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        fraction=_HIGH_FRACTION,
    )
    fleet = cell.poisoned_metrics.fleet_fpr
    # Coverage is always reported alongside CV(FPR).
    expected_coverage = len(collection.eligible_ids) / len(collection.clients)
    assert fleet.coverage_ratio == pytest.approx(expected_coverage)
    assert 0.0 < fleet.coverage_ratio <= 1.0


def test_invariant_11_cv_fpr_no_epsilon_returns_nan_when_mean_zero():
    """When every eligible FPR is 0, CV(FPR)=σ/µ has µ=0 -> nan (no ε stabilizer)."""
    # Build a collection whose benign test scores are all below any threshold.
    rng = np.random.default_rng(0)
    clients: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for i in range(4):
        cal = np.maximum(rng.normal(0.05, 0.02, size=200), 0.0)
        test_benign = np.zeros(50, dtype=np.float64)  # FPR will be exactly 0
        test_attack = np.full(50, 0.9, dtype=np.float64)
        clients[f"eligible_{i}"] = (cal, test_benign, test_attack)
    coll = build_score_collection(clients)

    # Uniform thresholds well above the (zero) benign scores.
    pair = ThresholdPair(
        policy=ThresholdPolicy.LOCAL_THRESHOLD,
        tau_global_clean=0.5,
        tau_global_pois=0.5,
        thresholds_clean=ClientThresholdsCollection.from_mapping(
            dict.fromkeys(coll.eligible_ids, 0.5),
            ThresholdPolicy.LOCAL_THRESHOLD,
        ),
        thresholds_pois=ClientThresholdsCollection.from_mapping(
            dict.fromkeys(coll.eligible_ids, 0.5),
            ThresholdPolicy.LOCAL_THRESHOLD,
        ),
    )
    fleet = compute_fleet_fpr(coll, pair, mu_flag_threshold=None)
    assert fleet.mean_fpr == pytest.approx(0.0)
    assert math.isnan(fleet.cv_fpr)  # NOT a finite ε-stabilized value, NOT 0


# ---------------------------------------------------------------------------
# Roadmap invariant — RANDOM_BENIGN is a near-null negative control
# ---------------------------------------------------------------------------


def test_roadmap_random_benign_near_null(collection):
    cell = run_smoke_cell(
        collection,
        victim_id=_VICTIM,
        policy=ThresholdPolicy.LOCAL_THRESHOLD,
        source=PoisoningSourceStrategy.RANDOM_BENIGN,
        fraction=_HIGH_FRACTION,
    )
    entry = cell.poisoned_metrics.delta_tau[_VICTIM]
    # Resampling from the full benign pool preserves the distribution: |Δτ| should
    # stay within the per-client materiality stage (0.1 * IQR).
    assert near_null_criterion(
        delta_tau=entry.delta_tau,
        delta_tau_null_threshold=entry.delta_tau_scale,
    )
    assert not entry.is_significant


# ---------------------------------------------------------------------------
# Roadmap invariant — GLOBAL_THRESHOLD victim shift < LOCAL_THRESHOLD victim shift (same attack)
# ---------------------------------------------------------------------------


def test_roadmap_global_shift_less_than_local_shift(collection):
    global_cell = run_smoke_cell(
        collection,
        victim_id=_VICTIM,
        policy=ThresholdPolicy.GLOBAL_THRESHOLD,
        source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        fraction=_HIGH_FRACTION,
    )
    local_cell = run_smoke_cell(
        collection,
        victim_id=_VICTIM,
        policy=ThresholdPolicy.LOCAL_THRESHOLD,
        source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        fraction=_HIGH_FRACTION,
    )
    global_shift = abs(global_cell.poisoned_metrics.delta_tau[_VICTIM].delta_tau)
    local_shift = abs(local_cell.poisoned_metrics.delta_tau[_VICTIM].delta_tau)
    # GLOBAL_THRESHOLD averages the victim's shift over all eligible clients -> diluted.
    assert global_shift < local_shift


# ---------------------------------------------------------------------------
# Roadmap invariant — CLUSTER_THRESHOLD K stays fixed at 3 under clean AND poisoned cal
# ---------------------------------------------------------------------------


def test_roadmap_cluster_threshold_k_fixed_at_three(collection):
    clean_cal = collection.cal_dict()
    assert cluster_count(clean_cal) == CLUSTER_K_NBAIOT == 3

    outcome = inject_single_victim(
        collection,
        victim_id=_VICTIM,
        spec=InjectionSpec(
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            fraction=_HIGH_FRACTION,
            seed_pair=SeedPair(training_seed=0, poisoning_seed=100),
        ),
    )
    poisoned_cal = dict(clean_cal)
    poisoned_cal[_VICTIM] = outcome.poisoned_cal[_VICTIM]
    assert cluster_count(poisoned_cal) == CLUSTER_K_NBAIOT == 3


# ---------------------------------------------------------------------------
# Roadmap invariant — outputs written to temp only
# ---------------------------------------------------------------------------


def test_roadmap_outputs_in_temp_only(collection, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cell = run_smoke_cell(
        collection,
        victim_id=_VICTIM,
        policy=ThresholdPolicy.LOCAL_THRESHOLD,
        source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        fraction=_HIGH_FRACTION,
    )
    manifest = build_manifest(
        ManifestBuildRequest(
            dataset="synthetic",
            stage=ExperimentStage.SYNTHETIC_SMOKE,
            policy=ThresholdPolicy.LOCAL_THRESHOLD,
            objective=AttackerObjective.THRESHOLD_RAISE,
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            fraction=_HIGH_FRACTION,
            target_scope=PoisoningTargetScope.SINGLE_CLIENT,
            training_seed=0,
            poisoning_seed=100,
            client_idx=0,
            scope_idx=0,
            mu_flag_threshold=cell.mu_flag_threshold,
            repository="datp-calibration-poisoning",
        )
    )
    run_dir = tmp_path / "run"
    emit_manifest(manifest, run_dir)

    assert (run_dir / "run_manifest.json").exists()
    # The real output root must never be created by a synthetic smoke run.
    assert not (tmp_path / CALIBRATION_POISONING_OUTPUT_ROOT).exists()
    assert not Path(CALIBRATION_POISONING_OUTPUT_ROOT).exists()


# ---------------------------------------------------------------------------
# Roadmap invariant 8 — THRESHOLD_LOWER connects to positive FPR-dispersion movement
# ---------------------------------------------------------------------------


def test_roadmap_invariant_8_lowering_increases_fpr_dispersion(collection):
    """Roadmap §13.8: LOW_SCORE_BENIGN under LOCAL_THRESHOLD must increase FPR dispersion.

    Under LOCAL_THRESHOLD, only the victim's threshold changes. A lower victim
    threshold means more benign test samples exceed it, increasing the victim's FPR
    while non-victims are unaffected — so max-min FPR gap and worst-client FPR
    must increase relative to the clean baseline.
    """
    cell = run_smoke_cell(
        collection,
        victim_id=_VICTIM,
        policy=ThresholdPolicy.LOCAL_THRESHOLD,
        source=PoisoningSourceStrategy.LOW_SCORE_BENIGN,
        fraction=_HIGH_FRACTION,
    )
    # Prerequisite: victim threshold must have dropped (invariant 4 establishes this).
    victim_delta = cell.poisoned_metrics.delta_tau[_VICTIM].delta_tau
    assert victim_delta < 0.0, (
        f"LOW_SCORE_BENIGN must lower the victim threshold; got Δτ={victim_delta:.4f}"
    )

    clean_fpr = cell.clean_metrics.fleet_fpr
    pois_fpr = cell.poisoned_metrics.fleet_fpr

    # At least one FPR-dispersion metric must increase (roadmap §10.2, §13.8).
    dispersion_increased = (
        (
            not math.isnan(pois_fpr.max_min_fpr_gap)
            and not math.isnan(clean_fpr.max_min_fpr_gap)
            and pois_fpr.max_min_fpr_gap > clean_fpr.max_min_fpr_gap
        )
        or (
            not math.isnan(pois_fpr.iqr_fpr)
            and not math.isnan(clean_fpr.iqr_fpr)
            and pois_fpr.iqr_fpr > clean_fpr.iqr_fpr
        )
        or (
            not math.isnan(pois_fpr.worst_client_fpr)
            and not math.isnan(clean_fpr.worst_client_fpr)
            and pois_fpr.worst_client_fpr > clean_fpr.worst_client_fpr
        )
    )
    assert dispersion_increased, (
        f"THRESHOLD_LOWER must increase FPR dispersion under LOCAL_THRESHOLD. "
        f"victim Δτ={victim_delta:.4f}, "
        f"clean(max_min={clean_fpr.max_min_fpr_gap:.4f}, iqr={clean_fpr.iqr_fpr:.4f}, "
        f"worst={clean_fpr.worst_client_fpr:.4f}), "
        f"poisoned(max_min={pois_fpr.max_min_fpr_gap:.4f}, iqr={pois_fpr.iqr_fpr:.4f}, "
        f"worst={pois_fpr.worst_client_fpr:.4f})"
    )
