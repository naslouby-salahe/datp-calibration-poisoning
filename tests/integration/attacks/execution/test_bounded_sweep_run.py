"""End-to-end integration tests for the bounded-sweep poisoning run on nbaiot_main."""

from __future__ import annotations

import math

import pytest
import torch

from datp.artifacts.layout import ArtifactLayout
from datp.attacks.constants import N_MIN
from datp.attacks.execution.bounded_sweep_run import (
    run_nbaiot_main,
    write_nbaiot_main_manifest,
)
from datp.attacks.score_containers import build_score_collection
from datp.config.attack_config import CalibrationPoisoningConfig
from datp.config.compose import BASE_CONFIG
from datp.config.models import ConvergenceConfig, DatpConfig, FederationConfig
from datp.core.device import resolve_device
from datp.attacks.enums import PoisoningSourceStrategy, ReservoirDraw
from datp.core.enums import ScoringStage, ThresholdPolicy
from datp.core.identity import TrainingCellId
from datp.config.models import ExperimentStage
from datp.core.seeds import set_seeds
from datp.federated.protocols.fedavg import run_fl_training
from datp.federated.types import ClientData
from datp.scoring.loading import load_main_cal_errors
from datp.scoring.loading import load_parquets_from_dir

_N_FEATURES = 10
_N_TRAIN = 200
_N_CAL = 150
_N_TEST = 50
_N_CLIENTS = 4
_CONFIG = CalibrationPoisoningConfig.for_bounded_sweep()


def _make_client_data(seed: int) -> dict[str, ClientData]:
    """Build deterministic synthetic client data for a given seed."""
    device = resolve_device(require_cuda=False)
    rng = torch.Generator().manual_seed(seed)
    data = {}
    for i in range(_N_CLIENTS):
        data[f"client_{i}"] = ClientData(
            train=torch.randn(_N_TRAIN, _N_FEATURES, generator=rng).to(device),
            val=torch.randn(_N_CAL, _N_FEATURES, generator=rng).to(device),
            test_benign=torch.randn(_N_TEST, _N_FEATURES, generator=rng).to(device),
            test_attack=(torch.randn(_N_TEST, _N_FEATURES, generator=rng) + 5.0).to(
                device
            ),
        )
    return data


def _make_cfg() -> DatpConfig:
    """Build a minimal DatpConfig for nbaiot_main with 1-round convergence."""
    return BASE_CONFIG.model_copy(
        update={
            "stage": ExperimentStage.NBAIOT_MAIN,
            "model": BASE_CONFIG.model.model_copy(
                update={"input_dim": _N_FEATURES, "encoder_dims": [8, 4]}
            ),
            "dataset": BASE_CONFIG.dataset.model_copy(
                update={"feature_count": _N_FEATURES}
            ),
            "machine": BASE_CONFIG.machine.model_copy(update={"batch_size_train": 64}),
            "federation": FederationConfig(
                local_epochs=1,
                convergence=ConvergenceConfig(
                    rounds_initial=1,
                    rounds_max=1,
                    relative_threshold=0.001,
                    window=2,
                    round_timeout_s=300.0,
                ),
            ),
        }
    )


@pytest.fixture(scope="module")
def trained_base_dir(tmp_path_factory):
    """Train all seeds once and return the base directory shared by the sweep tests."""
    base_dir = tmp_path_factory.mktemp("trained")
    cfg = _make_cfg()
    for training_seed in _CONFIG.seeds.training:
        set_seeds(training_seed)
        run_fl_training(
            cfg=cfg,
            client_data=_make_client_data(training_seed),
            seed=training_seed,
            base_dir=base_dir,
        )
    return base_dir


@pytest.fixture(scope="module")
def sweep_manifest(trained_base_dir):
    """Run the bounded sweep once on the trained base directory."""
    return run_nbaiot_main(base_dir=trained_base_dir, config=_CONFIG)


@pytest.mark.integration
def test_run_nbaiot_main_sweep_end_to_end(sweep_manifest) -> None:
    """Full nbaiot_main sweep runs poisoning and writes a manifest with AUROC invariance."""
    manifest = sweep_manifest

    assert manifest.n_cells == len(_CONFIG.seeds.training) * _N_CLIENTS * 3 * 4 * 4
    assert len(manifest.results) == manifest.n_cells
    assert set(manifest.mu_flag_threshold_by_training_seed) == set(
        _CONFIG.seeds.training
    )
    assert tuple(sorted(manifest.training_seeds)) == tuple(
        sorted(_CONFIG.seeds.training)
    )
    assert tuple(sorted(manifest.poisoning_seeds)) == tuple(
        sorted(_CONFIG.seeds.poisoning)
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
    assert all(r.cluster_sizes_clean and sum(r.cluster_sizes_clean) == _N_CLIENTS for r in cluster)
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


@pytest.mark.integration
def test_sensitivity_run_end_to_end(trained_base_dir, monkeypatch) -> None:
    """Sensitivity analyses produce cluster, scale, and distinct-draw rows."""
    from datp.attacks.execution import sensitivity_run

    monkeypatch.setattr(sensitivity_run, "CLUSTER_SENSITIVITY_K_GRID", (2, 3))
    monkeypatch.setattr(sensitivity_run, "CLUSTER_SENSITIVITY_RANDOM_STATES", (0, 1))
    monkeypatch.setattr(sensitivity_run, "CLUSTER_SENSITIVITY_N_INIT_GRID", (1,))
    manifest = sensitivity_run.run_sensitivity(trained_base_dir, _CONFIG)

    n_tasks = len(_CONFIG.seeds.training) * _N_CLIENTS * 4 * 3
    assert len(manifest.scale_normalization) == n_tasks
    assert len(manifest.cluster_stability) == n_tasks * 2 * 2
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
def test_sensitivity_manifest_is_written(trained_base_dir, monkeypatch) -> None:
    """The sensitivity manifest is written to the poisoning layout and validates on reload."""
    from datp.artifacts.poison_layout import PoisonLayout
    from datp.attacks.execution import sensitivity_run
    from datp.attacks.manifests.sensitivity_manifest import SensitivityManifest

    monkeypatch.setattr(sensitivity_run, "CLUSTER_SENSITIVITY_K_GRID", (2,))
    monkeypatch.setattr(sensitivity_run, "CLUSTER_SENSITIVITY_RANDOM_STATES", (0,))
    monkeypatch.setattr(sensitivity_run, "CLUSTER_SENSITIVITY_N_INIT_GRID", (1,))
    path = sensitivity_run.write_sensitivity_manifest(trained_base_dir)
    assert path == PoisonLayout(base_dir=trained_base_dir).sensitivity_manifest()
    SensitivityManifest.model_validate_json(path.read_text())


_SEED = 42


@pytest.mark.integration
def test_score_collection_matches_trained_clients(tmp_path) -> None:
    """Loaded calibration and test scores match the trained client IDs and shapes."""
    set_seeds(_SEED)
    cfg = _make_cfg()
    client_data = _make_client_data(_SEED)
    client_ids = sorted(client_data.keys())

    run_fl_training(cfg=cfg, client_data=client_data, seed=_SEED, base_dir=tmp_path)

    cal_errors = load_main_cal_errors(
        ExperimentStage.NBAIOT_MAIN, _SEED, tmp_path, None
    )
    layout = ArtifactLayout(base_dir=tmp_path, stage=ExperimentStage.NBAIOT_MAIN)
    score_dir = layout.score_cell(
        TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=_SEED)
    ).score_dir
    test_benign = load_parquets_from_dir(
        score_dir / ScoringStage.TEST_BENIGN.value, allow_empty=False
    )
    test_attack = load_parquets_from_dir(
        score_dir / ScoringStage.TEST_ATTACK.value, allow_empty=False
    )
    collection = build_score_collection(
        {
            cid: (cal, test_benign[cid], test_attack[cid])
            for cid, cal in cal_errors.items()
        },
        n_min=N_MIN,
    )

    assert sorted(collection.clients.keys()) == client_ids
    assert collection.eligible_ids == tuple(client_ids)
    assert collection.pending_ids == ()
    for cid in client_ids:
        client = collection.clients[cid]
        assert client.cal.shape[0] == _N_CAL
        assert client.test_benign.shape[0] == _N_TEST
        assert client.test_attack.shape[0] == _N_TEST


@pytest.mark.integration
def test_missing_cell_raises(tmp_path) -> None:
    """Loading calibration errors for a nonexistent training seed raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_main_cal_errors(ExperimentStage.NBAIOT_MAIN, 999, tmp_path, None)


@pytest.mark.integration
def test_write_nbaiot_main_manifest_writes_canonical_path(tmp_path) -> None:
    """Manifest is written to the canonical layout path under the base directory."""
    cfg = _make_cfg()
    for training_seed in _CONFIG.seeds.training:
        set_seeds(training_seed)
        client_data = _make_client_data(training_seed)
        run_fl_training(
            cfg=cfg,
            client_data=client_data,
            seed=training_seed,
            base_dir=tmp_path,
        )

    out_path = write_nbaiot_main_manifest(tmp_path)

    assert out_path.name == "nbaiot_main_manifest.json"
    assert out_path.exists()


def test_run_nbaiot_main_sweep_config_is_required() -> None:
    """run_nbaiot_main requires a config argument (not optional)."""

    import inspect

    sig = inspect.signature(run_nbaiot_main)
    config_param = sig.parameters["config"]
    assert config_param.default is inspect.Parameter.empty, (
        "run_nbaiot_main must not have a default config — "
        "callers must construct and pass CalibrationPoisoningConfig explicitly"
    )
