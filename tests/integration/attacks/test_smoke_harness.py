"""Smoke-test calibration-channel poisoning invariants on synthetic score sets."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from datp.attacks.constants import CLUSTER_K_NBAIOT
from datp.artifacts.poison_names import CALIBRATION_POISONING_OUTPUT_ROOT
from datp.attacks.constants import POISONING_SEEDS
from datp.core.provenance import REPOSITORY_NAME
from datp.attacks.threshold_recomputation.cluster_threshold_recompute import (
    ClusterThresholdPair,
)
from datp.attacks.execution.cell_runner import (
    InjectionSpec,
    inject_single_victim,
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
from datp.attacks.threshold_recomputation.threshold_recompute import ThresholdPair
from datp.attacks.enums import (
    AttackerObjective,
    CalibrationInjectionRule,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
)
from datp.core.enums import ThresholdPolicy
from datp.core.seeds import SeedPair
from datp.config.models import ExperimentStage
from datp.testsupport.smoke_harness import (
    cluster_count,
    collection_from_score_set,
    run_smoke_cell,
    victim_seed_deltas,
)
from datp.testsupport.synthetic_scores import (
    StandardScoreSetRequest,
    make_standard_score_set,
)
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
    """Build a synthetic score collection with 9 eligible and 1 pending client."""
    return collection_from_score_set(
        make_standard_score_set(StandardScoreSetRequest(n_eligible=9, n_pending=1))
    )


@pytest.mark.parametrize("policy", _ALL_POLICIES)
def test_invariant_1_f0_reproduces_clean_zero_delta(collection, policy):
    """Zero-fraction poisoning leaves calibration scores and thresholds unchanged."""
    cell = run_smoke_cell(
        collection,
        victim_id=_VICTIM,
        policy=policy,
        source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        fraction=0.0,
    )

    np.testing.assert_array_equal(
        cell.outcome.poisoned_cal_set.for_client(_VICTIM).cal,
        collection.clients[_VICTIM].cal,
    )

    for entry in cell.poisoned_metrics.delta_tau.values():
        assert entry.delta_tau == pytest.approx(0.0)
    assert cell.outcome.injection.n_replaced == 0


def test_invariant_2_cardinality_preserved(collection):
    """Fixed-budget replacement keeps victim calibration size unchanged."""
    n_before = collection.clients[_VICTIM].n_cal
    outcome = inject_single_victim(
        collection,
        victim_id=_VICTIM,
        spec=InjectionSpec(
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            fraction=_HIGH_FRACTION,
            seed_pair=SeedPair(training_seed=0, poisoning_seed=100),
            objective=None,
        ),
    )
    assert outcome.injection.n_total == n_before
    assert outcome.poisoned_cal_set.for_client(_VICTIM).cal.shape[0] == n_before
    assert outcome.injection.n_replaced == max(1, round(_HIGH_FRACTION * n_before))

    rebuilt: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for cid, c in collection.clients.items():
        cal = (
            outcome.poisoned_cal_set.for_client(cid).cal
            if cid in outcome.poisoned_cal_set.client_ids
            else c.cal
        )
        rebuilt[cid] = (cal, c.test_benign, c.test_attack)
    poisoned_collection = build_score_collection(rebuilt)
    assert poisoned_collection.eligible_ids == collection.eligible_ids


def test_invariant_3_no_inplace_mutation(collection):
    """Injection produces a new array; the original calibration is never mutated in place."""
    victim_clean = collection.clients[_VICTIM].cal
    snapshot = victim_clean.copy()
    cell = run_smoke_cell(
        collection,
        victim_id=_VICTIM,
        policy=ThresholdPolicy.LOCAL_THRESHOLD,
        source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        fraction=_HIGH_FRACTION,
    )

    assert_no_inplace_mutation(snapshot, collection.clients[_VICTIM].cal)

    assert cell.outcome.poisoned_cal_set.for_client(_VICTIM).cal is not victim_clean
    assert not np.array_equal(
        cell.outcome.poisoned_cal_set.for_client(_VICTIM).cal, snapshot
    )


def test_invariant_4_high_raises_low_lowers_local_threshold(collection):
    """HIGH_SCORE_BENIGN raises and LOW_SCORE_BENIGN lowers the local threshold."""
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


def test_invariant_5_pending_excluded_and_gets_tau_global(collection):
    """Calibration-pending clients are excluded from poisoning and threshold recomputation."""
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

        assert pending not in collection.eligible_ids
        assert pending not in pair.thresholds_pois
        assert pending not in pair.thresholds_clean

        assert pending not in cell.poisoned_metrics.delta_tau
        fleet = cell.poisoned_metrics.fleet_fpr
        assert fleet.n_eligible == len(collection.eligible_ids)
        assert fleet.n_total == len(collection.clients)


def test_invariant_6_determinism(collection):
    """Identical injection specs and seeds produce identical poisoned outputs."""
    out_a = inject_single_victim(
        collection,
        victim_id=_VICTIM,
        spec=InjectionSpec(
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            fraction=_HIGH_FRACTION,
            seed_pair=SeedPair(training_seed=0, poisoning_seed=100),
            objective=None,
        ),
    )
    out_b = inject_single_victim(
        collection,
        victim_id=_VICTIM,
        spec=InjectionSpec(
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            fraction=_HIGH_FRACTION,
            seed_pair=SeedPair(training_seed=0, poisoning_seed=100),
            objective=None,
        ),
    )
    np.testing.assert_array_equal(
        out_a.poisoned_cal_set.for_client(_VICTIM).cal,
        out_b.poisoned_cal_set.for_client(_VICTIM).cal,
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


def test_invariant_7_cluster_threshold_decomposition_identity(collection):
    """Cluster threshold delta decomposes into aggregation and churn components."""
    cell = run_smoke_cell(
        collection,
        victim_id=_VICTIM,
        policy=ThresholdPolicy.CLUSTER_THRESHOLD,
        source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        fraction=_HIGH_FRACTION,
    )
    pair = cell.poisoned_pair
    assert isinstance(pair, ClusterThresholdPair)
    assert pair.decomposition
    for entry in pair.decomposition.values():
        assert math.isfinite(entry.delta_tau_total)
        assert math.isfinite(entry.delta_tau_agg)
        assert math.isfinite(entry.delta_tau_churn)
        assert entry.delta_tau_total == pytest.approx(
            entry.delta_tau_agg + entry.delta_tau_churn, abs=1e-9
        )


def test_invariant_8_two_layer_bootstrap_on_seed_aggregates(collection):
    """Bootstrap inference across poisoning seeds produces valid seed aggregates and confidence intervals."""
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
            direction=AttackerObjective.THRESHOLD_RAISE,
        )
    )
    assert len(result.seed_aggregates) == len(POISONING_SEEDS) == 10
    assert result.bootstrap_ci.n_seeds == 10
    assert len(eligible) * len(POISONING_SEEDS) == 90
    assert result.n_feasible_victims == len(eligible)

    assert result.sign_test.n_total == 10


def test_invariant_9_manifest_round_trip(collection, tmp_path):
    """Built manifest survives emit-then-load round-trip with all fields intact."""
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
            repository=REPOSITORY_NAME,
        )
    )
    run_dir = tmp_path / "cell"
    emit_manifest(manifest, run_dir)
    loaded = load_manifest(run_dir)

    assert loaded.reservoir_mode == RESERVOIR_MODE
    assert loaded.mu_flag_threshold == pytest.approx(cell.mu_flag_threshold)
    assert loaded.injection_rule == CalibrationInjectionRule.REPLACE_FIXED_BUDGET
    assert loaded.provenance.local_epochs == 1

    assert loaded.seed_record.entropy == (0, 100, 0, 0)
    assert loaded.seed_record.training_seed == 0
    assert loaded.seed_record.poisoning_seed == 100
    assert loaded.seed_record.client_idx == 0
    assert loaded.seed_record.scope_idx == 0


def test_invariant_9_manifest_requires_locked_mu_flag(tmp_path):
    """Emitting a manifest without a locked mu-flag threshold raises an error."""
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
            repository=REPOSITORY_NAME,
        )
    )
    with pytest.raises(ManifestEmissionError):
        emit_manifest(manifest, tmp_path / "cell")


def test_invariant_10_auroc_invariant(collection):
    """AUROC is unchanged by calibration-only poisoning for every client."""
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


def test_invariant_11_cv_fpr_reported_with_coverage(collection):
    """Fleet FPR reports coverage ratio matching eligible-to-total client proportion."""
    cell = run_smoke_cell(
        collection,
        victim_id=_VICTIM,
        policy=ThresholdPolicy.LOCAL_THRESHOLD,
        source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        fraction=_HIGH_FRACTION,
    )
    fleet = cell.poisoned_metrics.fleet_fpr

    expected_coverage = len(collection.eligible_ids) / len(collection.clients)
    assert fleet.coverage_ratio == pytest.approx(expected_coverage)
    assert 0.0 < fleet.coverage_ratio <= 1.0


def test_invariant_11_cv_fpr_no_epsilon_returns_nan_when_mean_zero():
    """CV of FPR is NaN when mean FPR is zero (division by zero is expected)."""
    rng = np.random.default_rng(0)
    clients: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for i in range(4):
        cal = np.maximum(rng.normal(0.05, 0.02, size=200), 0.0)
        test_benign = np.zeros(50, dtype=np.float64)
        test_attack = np.full(50, 0.9, dtype=np.float64)
        clients[f"eligible_{i}"] = (cal, test_benign, test_attack)
    coll = build_score_collection(clients)

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
    assert math.isnan(fleet.cv_fpr)


def test_global_shift_less_than_local_shift(collection):
    """Global threshold shift magnitude is strictly less than local threshold shift."""
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

    assert global_shift < local_shift


def test_cluster_threshold_k_fixed_at_three(collection):
    """Cluster count is fixed at 3 both before and after poisoning."""
    clean_cal = collection.cal_dict()
    assert cluster_count(clean_cal) == CLUSTER_K_NBAIOT == 3

    outcome = inject_single_victim(
        collection,
        victim_id=_VICTIM,
        spec=InjectionSpec(
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            fraction=_HIGH_FRACTION,
            seed_pair=SeedPair(training_seed=0, poisoning_seed=100),
            objective=None,
        ),
    )
    poisoned_cal = dict(clean_cal)
    poisoned_cal[_VICTIM] = outcome.poisoned_cal_set.for_client(_VICTIM).cal
    assert cluster_count(poisoned_cal) == CLUSTER_K_NBAIOT == 3


def test_outputs_in_temp_only(collection, tmp_path, monkeypatch):
    """Manifest emission writes only under the run directory, never to the global output root."""
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
            repository=REPOSITORY_NAME,
        )
    )
    run_dir = tmp_path / "run"
    emit_manifest(manifest, run_dir)

    assert (run_dir / "run_manifest.json").exists()

    assert not (tmp_path / CALIBRATION_POISONING_OUTPUT_ROOT).exists()
    assert not Path(CALIBRATION_POISONING_OUTPUT_ROOT).exists()


def test_lowering_increases_fpr_dispersion(collection):
    """Lowering the victim threshold increases at least one FPR dispersion metric."""
    cell = run_smoke_cell(
        collection,
        victim_id=_VICTIM,
        policy=ThresholdPolicy.LOCAL_THRESHOLD,
        source=PoisoningSourceStrategy.LOW_SCORE_BENIGN,
        fraction=_HIGH_FRACTION,
    )

    victim_delta = cell.poisoned_metrics.delta_tau[_VICTIM].delta_tau
    assert victim_delta < 0.0, (
        f"LOW_SCORE_BENIGN must lower the victim threshold; got Δτ={victim_delta:.4f}"
    )

    clean_fpr = cell.clean_metrics.fleet_fpr
    pois_fpr = cell.poisoned_metrics.fleet_fpr

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
