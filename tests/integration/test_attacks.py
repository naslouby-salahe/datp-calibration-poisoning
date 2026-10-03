from __future__ import annotations

import inspect
import math

import numpy as np
import pytest
from tests.integration.conftest import (
    N_CAL,
    N_CLIENTS,
    N_TEST,
    TINY_FRACTIONS,
    TINY_PAIR_COUNT,
    TINY_POLICY_COUNT,
    TINY_SEEDS,
    TRAINING_SEED,
)

from datp.artifacts import (
    ArtifactLayout,
    nbaiot_main_manifest_path,
    sensitivity_manifest_path,
)
from datp.attacks import sensitivity as sensitivity_run
from datp.attacks import sweep as sweep_module
from datp.attacks.injection import (
    ThresholdPairBase,
    assert_no_inplace_mutation,
    build_score_collection,
)
from datp.attacks.manifests import BoundedSweepManifest, SensitivityManifest
from datp.attacks.metrics import ClusterThresholdPair, compute_fleet_fpr
from datp.attacks.sweep import (
    InjectionSpec,
    inject_single_victim,
    load_seed_collections,
    run_nbaiot_main,
    write_nbaiot_main_manifest,
)
from datp.config import CLUSTER_K_NBAIOT, N_MIN, POISONING_SEEDS, ExperimentStage
from datp.core import SeedPair, TrainingCellId
from datp.enums import (
    AttackerObjective,
    PoisoningSourceStrategy,
    ReservoirDraw,
    ScoringStage,
    ThresholdPolicy,
)
from datp.scoring import load_main_cal_errors, load_parquets_from_dir
from datp.thresholding import ClientThresholdsCollection
from datp.types import ClientId
from tests_support.inference import (
    InferenceInput,
    PairedDeltas,
    SeedDelta,
    collect_paired_deltas,
    compute_inference,
)
from tests_support.smoke_harness import (
    cluster_count,
    collection_from_score_set,
    run_smoke_cell,
    victim_seed_deltas,
)
from tests_support.synthetic_scores import (
    StandardScoreSetRequest,
    make_standard_score_set,
)


@pytest.fixture(scope="module")
def sweep_manifest(scores_dir, tiny_runtime):
    """Run the tiny bounded sweep once on the synthetic score directory."""
    return run_nbaiot_main(base_dir=scores_dir, config=tiny_runtime)


@pytest.mark.integration
def test_run_nbaiot_main_sweep_end_to_end(sweep_manifest) -> None:
    """Full nbaiot_main sweep runs poisoning and writes a manifest with AUROC invariance."""
    manifest = sweep_manifest

    assert manifest.n_cells == len(TINY_SEEDS.training) * N_CLIENTS * TINY_POLICY_COUNT * TINY_PAIR_COUNT * len(
        TINY_FRACTIONS
    )
    assert len(manifest.results) == manifest.n_cells
    assert set(manifest.mu_flag_threshold_by_training_seed) == set(
        TINY_SEEDS.training
    )
    assert tuple(sorted(manifest.training_seeds)) == tuple(
        sorted(TINY_SEEDS.training)
    )
    assert tuple(sorted(manifest.poisoning_seeds)) == tuple(
        sorted(TINY_SEEDS.poisoning)
    )
    assert manifest.provenance.local_epochs == 1

    assert all(row.auroc_invariant for row in manifest.results)

    zero_fraction_rows = [
        r for r in manifest.results if math.isclose(r.fraction, 0.0, abs_tol=0.0)
    ]
    assert zero_fraction_rows
    assert all(r.delta_tau == pytest.approx(0.0) for r in zero_fraction_rows)

    for row in manifest.results:
        assert hasattr(row, "victim_tpr_clean")
        assert hasattr(row, "victim_delta_tpr")
        assert hasattr(row, "victim_ba_clean")
        assert hasattr(row, "victim_delta_ba")


@pytest.mark.integration
def test_sweep_rows_carry_non_victim_and_absolute_burden(sweep_manifest) -> None:
    """Non-victim downstream effects and absolute counts are populated and consistent."""
    for row in sweep_manifest.results:
        assert row.victim_fp_poisoned >= 0
        assert row.victim_fn_poisoned >= 0
        assert row.victim_n_test_benign > 0
        assert row.victim_delta_fpr == pytest.approx(
            row.victim_fpr_poisoned - row.victim_fpr_clean
        )
        assert math.isfinite(row.nonvictim_mean_delta_tpr)
        assert math.isfinite(row.nonvictim_mean_delta_fpr)
    zero = [r for r in sweep_manifest.results if r.fraction == 0.0]
    assert all(r.nonvictim_delta_fp_total == 0 for r in zero)
    assert all(r.nonvictim_delta_fn_total == 0 for r in zero)
    assert all(r.n_replaced == 0 for r in zero)


@pytest.mark.integration
def test_global_policy_shifts_shared_threshold(sweep_manifest) -> None:
    """Under GLOBAL_THRESHOLD a targeted raise moves the shared threshold upward."""
    rows = [
        r
        for r in sweep_manifest.results
        if r.policy == ThresholdPolicy.GLOBAL_THRESHOLD
        and r.fraction == 0.4
        and r.source == PoisoningSourceStrategy.HIGH_SCORE_BENIGN
    ]
    assert rows
    assert any(r.delta_tau > 0.0 for r in rows)


@pytest.mark.integration
def test_cluster_rows_have_transition_and_fixed_assignment_fields(
    sweep_manifest,
) -> None:
    """Cluster rows carry sizes, reassignments, and frozen-assignment effects; others are empty."""
    cluster = [
        r
        for r in sweep_manifest.results
        if r.policy == ThresholdPolicy.CLUSTER_THRESHOLD
    ]
    other = [
        r
        for r in sweep_manifest.results
        if r.policy != ThresholdPolicy.CLUSTER_THRESHOLD
    ]
    assert all(r.cluster_sizes_clean and sum(r.cluster_sizes_clean) == N_CLIENTS for r in cluster)
    assert all(math.isfinite(r.fixed_cluster_victim_delta_tau) for r in cluster)
    assert all(r.cluster_n_reassigned >= 0 for r in cluster)
    assert all(not r.cluster_sizes_clean for r in other)
    assert all(math.isnan(r.fixed_cluster_victim_delta_tau) for r in other)
    zero = [r for r in cluster if r.fraction == 0.0]
    assert all(r.cluster_n_reassigned == 0 for r in zero)
    assert all(
        r.fixed_cluster_victim_delta_tau == pytest.approx(0.0, abs=1e-12) for r in zero
    )


@pytest.mark.integration
def test_duplicate_rates_and_bound_utilization(sweep_manifest) -> None:
    """Poisoned buffers never have fewer duplicates than clean ones; utilization stays bounded."""
    for row in sweep_manifest.results:
        assert row.cal_duplicate_rate_poisoned >= row.cal_duplicate_rate_clean - 1e-12
        if math.isfinite(row.delta_tau_bound_utilization):
            assert row.delta_tau_bound_utilization <= 1.0 + 1e-9


@pytest.fixture(scope="module")
def sensitivity_manifest(scores_dir, tiny_runtime):
    """Run the tiny sensitivity analyses once on the synthetic score directory."""
    return sensitivity_run.run_sensitivity(scores_dir, tiny_runtime)


@pytest.mark.integration
def test_sensitivity_run_end_to_end(sensitivity_manifest) -> None:
    """Sensitivity analyses produce cluster, scale, and distinct-draw rows."""
    manifest = sensitivity_manifest

    n_tasks = len(TINY_SEEDS.training) * N_CLIENTS * 2
    assert len(manifest.scale_normalization) == n_tasks
    assert len(manifest.cluster_stability) == n_tasks * 2
    assert len(manifest.draw_variants) == n_tasks * 3 * 3
    assert len(manifest.trust_boundary) == n_tasks * 3
    for row in manifest.draw_variants:
        assert 0.0 <= row.duplicate_rate_variant <= 1.0
        assert row.effective_n_replaced <= row.requested_n_replaced
        if row.draw == ReservoirDraw.INTERPOLATED_TAIL:
            assert row.effective_n_replaced == row.requested_n_replaced
        if row.draw == ReservoirDraw.WITHOUT_REPLACEMENT:
            assert row.effective_n_replaced == min(
                row.requested_n_replaced, row.pool_size
            )
    for row in manifest.trust_boundary:
        assert math.isfinite(row.delta_tau_undefended)
        assert math.isfinite(row.delta_tau_trim_primary)
        assert math.isfinite(row.residual_vs_clean_trim_appendix)
    for row in manifest.scale_normalization:
        assert math.isfinite(row.raw_global_victim_delta_tau)
        assert math.isfinite(row.normalized_global_victim_delta_tau)


@pytest.mark.integration
def test_sensitivity_manifest_is_written(
    tmp_path, monkeypatch, sensitivity_manifest
) -> None:
    """The sensitivity manifest is written to the poisoning layout and validates on reload."""
    monkeypatch.setattr(
        sensitivity_run, "run_sensitivity", lambda *_a, **_k: sensitivity_manifest
    )
    path = sensitivity_run.write_sensitivity_manifest(tmp_path)
    assert path == sensitivity_manifest_path(tmp_path)
    assert SensitivityManifest.model_validate_json(path.read_text()) == sensitivity_manifest


@pytest.mark.integration
def test_score_collection_matches_synthetic_clients(scores_dir) -> None:
    """Loaded calibration and test scores match the written client IDs and shapes."""
    cal_errors = load_main_cal_errors(
        ExperimentStage.NBAIOT_MAIN, TRAINING_SEED, scores_dir
    )
    score_dir = (
        ArtifactLayout(base_dir=scores_dir, stage=ExperimentStage.NBAIOT_MAIN)
        .score_cell(TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=TRAINING_SEED))
        .score_dir
    )
    test_benign = load_parquets_from_dir(
        score_dir / ScoringStage.TEST_BENIGN, allow_empty=False
    )
    test_attack = load_parquets_from_dir(
        score_dir / ScoringStage.TEST_ATTACK, allow_empty=False
    )
    collection = build_score_collection(
        {
            cid: (cal, test_benign[cid], test_attack[cid])
            for cid, cal in cal_errors.items()
        },
        n_min=N_MIN,
    )

    client_ids = tuple(f"client_{i}" for i in range(N_CLIENTS))
    assert sorted(collection.clients) == list(client_ids)
    assert collection.eligibility.eligible_ids == client_ids
    assert collection.eligibility.pending_ids == ()
    for cid in client_ids:
        client = collection.clients[cid]
        assert client.cal.shape[0] == N_CAL
        assert client.test_benign.shape[0] == N_TEST
        assert client.test_attack.shape[0] == N_TEST


@pytest.mark.integration
def test_missing_cell_raises(tmp_path, tiny_runtime) -> None:
    """Loading scores for a training seed without artifacts raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_main_cal_errors(ExperimentStage.NBAIOT_MAIN, 999, tmp_path)
    with pytest.raises(FileNotFoundError):
        load_seed_collections(tmp_path, tiny_runtime)


@pytest.mark.integration
def test_write_nbaiot_main_manifest_writes_canonical_path(
    tmp_path, monkeypatch, sweep_manifest
) -> None:
    """Manifest is written to the canonical layout path and validates on reload."""
    monkeypatch.setattr(sweep_module, "run_nbaiot_main", lambda *_a, **_k: sweep_manifest)

    out_path = write_nbaiot_main_manifest(tmp_path)

    assert out_path == nbaiot_main_manifest_path(tmp_path)
    assert out_path.name == "nbaiot_main_manifest.json"
    assert BoundedSweepManifest.model_validate_json(out_path.read_text()) == sweep_manifest


def test_run_nbaiot_main_sweep_config_is_required() -> None:
    """run_nbaiot_main requires a config argument (not optional)."""
    config_param = inspect.signature(run_nbaiot_main).parameters["config"]
    assert config_param.default is inspect.Parameter.empty


pytestmark = pytest.mark.integration


_VICTIM = ClientId("eligible_0")


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
        cell.outcome.poisoned_cal_set[_VICTIM].cal,
        collection.clients[_VICTIM].cal,
    )

    for entry in cell.poisoned_metrics.delta_tau.values():
        assert entry.delta_tau == pytest.approx(0.0)
    assert cell.outcome.injection.n_replaced == 0


def test_invariant_2_cardinality_preserved(collection):
    """Fixed-budget replacement keeps victim calibration size unchanged."""
    n_before = collection.clients[_VICTIM].cal.size
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
    assert outcome.poisoned_cal_set[_VICTIM].cal.shape[0] == n_before
    assert outcome.injection.n_replaced == max(1, round(_HIGH_FRACTION * n_before))

    rebuilt: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for cid, c in collection.clients.items():
        cal = (
            outcome.poisoned_cal_set[cid].cal
            if cid in outcome.poisoned_cal_set
            else c.cal
        )
        rebuilt[cid] = (cal, c.test_benign, c.test_attack)
    poisoned_collection = build_score_collection(rebuilt)
    assert poisoned_collection.eligibility.eligible_ids == collection.eligibility.eligible_ids


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

    assert cell.outcome.poisoned_cal_set[_VICTIM].cal is not victim_clean
    assert not np.array_equal(
        cell.outcome.poisoned_cal_set[_VICTIM].cal, snapshot
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
    pending_ids = collection.eligibility.pending_ids
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

        assert pending not in collection.eligibility.eligible_ids
        assert pending not in pair.thresholds_pois
        assert pending not in pair.thresholds_clean

        assert pending not in cell.poisoned_metrics.delta_tau
        fleet = cell.poisoned_metrics.fleet_fpr
        assert fleet.n_eligible == len(collection.eligibility.eligible_ids)
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
        out_a.poisoned_cal_set[_VICTIM].cal,
        out_b.poisoned_cal_set[_VICTIM].cal,
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
    eligible = collection.eligibility.eligible_ids
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
    result = compute_inference(
        InferenceInput(
            paired=PairedDeltas(deltas=deltas),
            poisoning_seeds=POISONING_SEEDS,
            direction=AttackerObjective.THRESHOLD_RAISE,
        )
    )
    assert len(result.seed_aggregates) == len(POISONING_SEEDS) == 10
    assert result.bootstrap_ci.n_seeds == 10
    assert len(eligible) * len(POISONING_SEEDS) == 90
    assert result.n_feasible_victims == len(eligible)

    assert result.sign_test.n_total == 10


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

    expected_coverage = len(collection.eligibility.eligible_ids) / len(collection.clients)
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

    pair = ThresholdPairBase(
        policy=ThresholdPolicy.LOCAL_THRESHOLD,
        tau_global_clean=0.5,
        tau_global_pois=0.5,
        thresholds_clean=ClientThresholdsCollection.from_mapping(
            dict.fromkeys(coll.eligibility.eligible_ids, 0.5),
            ThresholdPolicy.LOCAL_THRESHOLD,
        ),
        thresholds_pois=ClientThresholdsCollection.from_mapping(
            dict.fromkeys(coll.eligibility.eligible_ids, 0.5),
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
    clean_cal = {
        client.client_id: client.errors
        for client in collection.calibration_errors.clients
    }
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
    poisoned_cal[_VICTIM] = outcome.poisoned_cal_set[_VICTIM].cal
    assert cluster_count(poisoned_cal) == CLUSTER_K_NBAIOT == 3


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
