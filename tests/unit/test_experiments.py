from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from datp.config import BASE_CONFIG, ExperimentStage
from datp.core import PolicyRunId, TrainingCellId
from datp.data import ManifestMetadata, Split, create_manifest, filename_for_split
from datp.enums import CONTROLLED_POLICIES, Activation, ArtifactFile, ThresholdPolicy
from datp.experiments import (
    PipelineRequest,
    PreparedDataRequest,
    SharedPipelineContext,
    SweepResult,
    SweepStep,
    _is_done,
    build_experiment_matrix,
    build_shared_context,
    ensure_prepared_data,
    ensure_trained_scores,
    evaluate_policy,
    run_sweep,
    validate_sweep,
)
from datp.thresholding import EligibilityResult
from tests.fixtures import valid_metrics_json

_STAGE = ExperimentStage.NBAIOT_MAIN


def _write_raw_file(raw_dir: Path) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_file = raw_dir / "raw.csv"
    raw_file.write_text("x\n1\n")
    return raw_file


def _write_processed_client(prepared_dir: Path) -> None:
    client_dir = prepared_dir / "client_0"
    client_dir.mkdir(parents=True, exist_ok=True)
    for split in Split:
        (client_dir / filename_for_split(split)).write_text("placeholder")
    (client_dir / ArtifactFile.SCALER).write_bytes(b"scaler")


def _write_manifest(prepared_dir: Path, raw_dir: Path, raw_file: Path) -> None:
    create_manifest(
        dataset="nbaiot",
        raw_files=[raw_file],
        raw_base_dir=raw_dir,
        metadata=ManifestMetadata.model_validate({"n_devices": 1, "n_features": 2}),
        manifest_path=prepared_dir / ArtifactFile.MANIFEST,
    )


def _patch_paths(monkeypatch, prepared_dir: Path, raw_dir: Path) -> None:
    import datp.experiments as mod

    monkeypatch.setattr(mod, "processed_root", lambda *a, **kw: prepared_dir)
    monkeypatch.setattr(mod, "raw_root", lambda *a, **kw: raw_dir)
    monkeypatch.setattr(
        mod,
        "load_scaler",
        lambda _: SimpleNamespace(
            n_features_in_=mod.dataset_spec("nbaiot").feature_count
        ),
    )
    monkeypatch.setattr(mod, "run_schema_audit", Mock())


def test_existing_processed_data_is_verified_and_reused(
    tmp_path: Path,
    monkeypatch,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_file = _write_raw_file(raw_dir)
    prepared_dir = tmp_path / "processed" / "nbaiot"
    _write_processed_client(prepared_dir)
    _write_manifest(prepared_dir, raw_dir, raw_file)
    _patch_paths(monkeypatch, prepared_dir, raw_dir)

    prepare_mock = Mock()
    monkeypatch.setattr("datp.experiments.prepare_nbaiot", prepare_mock)

    result = ensure_prepared_data(
        PreparedDataRequest(
            stage=_STAGE,
            seed=0,
            cfg=BASE_CONFIG,
            base_dir=tmp_path,
        )
    )

    assert result == prepared_dir
    prepare_mock.assert_not_called()


def test_missing_processed_data_runs_preparation_then_verifies(
    tmp_path: Path,
    monkeypatch,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_file = _write_raw_file(raw_dir)
    prepared_dir = tmp_path / "processed" / "nbaiot"
    _patch_paths(monkeypatch, prepared_dir, raw_dir)

    def prepare(*, raw_dir, output_dir, **kwargs) -> None:
        _write_processed_client(prepared_dir)
        _write_manifest(prepared_dir, raw_dir, raw_file)
        return {}

    prepare_mock = Mock(side_effect=prepare)
    monkeypatch.setattr("datp.experiments.prepare_nbaiot", prepare_mock)

    result = ensure_prepared_data(
        PreparedDataRequest(
            stage=_STAGE,
            seed=0,
            cfg=BASE_CONFIG,
            base_dir=tmp_path,
        )
    )

    assert result == prepared_dir
    prepare_mock.assert_called_once()


def _make_request(
    policy: ThresholdPolicy,
    tmp_path: Path,
    seed: int = 1,
) -> PipelineRequest:
    """Build a minimal PipelineRequest with a mock config for the given policy."""
    cfg = MagicMock()
    cfg.threshold.n_min = 100
    cfg.threshold.q = 95
    cfg.model.input_dim = 115
    cfg.model.encoder_dims = [64, 32]
    cfg.model.epochs = 5
    cfg.model.patience = 3
    cfg.model.lr = 1e-3
    cfg.model.activation = Activation.RELU
    cfg.model.use_bn = True
    cfg.machine.batch_size_train = 256
    cfg.logging.training_progress_interval = 10
    return PipelineRequest(
        key=TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=seed),
        policy=policy,
        cfg=cfg,
        base_dir=tmp_path,
        prepared_dir=tmp_path / "prepared",
    )


def _patch_context_inputs():
    return (
        patch(
            "datp.experiments.ensure_trained_scores",
            return_value=MagicMock(model_hash="model-hash"),
        ),
        patch(
            "datp.experiments.load_main_cal_errors",
            return_value={"c1": np.array([0.1, 0.2])},
        ),
        patch(
            "datp.experiments.identify_eligible",
            return_value=EligibilityResult(eligible_ids=("c1",), pending_ids=()),
        ),
        patch("datp.experiments.compute_client_thresholds", return_value={"c1": 0.15}),
        patch("datp.experiments.compute_tau_global", return_value=0.15),
        patch("datp.experiments.ScoreProvider"),
    )


class TestBuildSharedContext:
    """Context building from trained scores."""

    def test_build_context_returns_typed_context(self, tmp_path: Path) -> None:
        request = _make_request(ThresholdPolicy.GLOBAL_THRESHOLD, tmp_path)

        with ExitStack() as stack:
            mocks = [stack.enter_context(p) for p in _patch_context_inputs()]
            ctx = build_shared_context(request)

        mocks[0].assert_called_once()
        assert isinstance(ctx, SharedPipelineContext)
        assert ctx.key == request.key
        assert list(ctx.client_errors.keys()) == ["c1"]
        assert np.array_equal(ctx.client_errors["c1"], np.array([0.1, 0.2]))
        assert ctx.eligible == ("c1",)
        assert ctx.pending == ()
        assert ctx.client_taus == pytest.approx({"c1": 0.15})
        assert ctx.tau_global == pytest.approx(0.15)
        assert ctx.score_provider is mocks[-1].return_value
        assert ctx.model_identity == "model-hash"

    def test_reports_steps(self, tmp_path: Path) -> None:
        request = _make_request(ThresholdPolicy.GLOBAL_THRESHOLD, tmp_path)

        with ExitStack() as stack:
            for p in _patch_context_inputs():
                stack.enter_context(p)
            step = stack.enter_context(patch("datp.experiments.print_step"))
            build_shared_context(request)

        assert [c.args[0] for c in step.call_args_list] == [
            SweepStep.LOAD_CAL_SCORES,
            SweepStep.COMPUTE_ELIGIBILITY,
            SweepStep.COMPUTE_TAU_GLOBAL,
            SweepStep.INIT_SCORE_PROVIDER,
        ]


class TestEvaluatePolicy:
    """Policy evaluation against a shared context."""

    @staticmethod
    def _ctx(request: PipelineRequest) -> SharedPipelineContext:
        return SharedPipelineContext(
            key=request.key,
            client_errors={"c1": np.array([0.1, 0.2])},
            eligible=("c1",),
            pending=(),
            client_taus={"c1": 0.15},
            tau_global=0.15,
            score_provider=MagicMock(),
            model_identity="model-hash",
        )

    def test_run_returns_metrics_and_reports_steps(self, tmp_path: Path) -> None:
        request = _make_request(ThresholdPolicy.LOCAL_THRESHOLD, tmp_path)
        mock_metrics = MagicMock()

        with (
            patch(
                "datp.experiments.derive_threshold",
                return_value=MagicMock(
                    tau_global=0.15,
                    eligible_count=1,
                    pending_count=0,
                    client_thresholds={"c1": 0.15},
                ),
            ),
            patch("datp.experiments.evaluate_policy_run", return_value=MagicMock()),
            patch("datp.experiments.build_metrics_dict", return_value=mock_metrics),
            patch("datp.experiments.write_json_atomic"),
            patch("datp.experiments.RunLifecycle"),
            patch("datp.experiments.print_step") as step,
        ):
            result = evaluate_policy(request, self._ctx(request))

        assert result is mock_metrics
        assert [c.args[0] for c in step.call_args_list] == [
            SweepStep.DERIVE_THRESHOLD,
            SweepStep.EVALUATE,
            SweepStep.WRITE_METRICS,
        ]


class TestEnsureTrainedScores:
    """Train-or-reuse logic for the scored baseline artifacts."""

    @staticmethod
    def _request(tmp_path: Path, seed: int) -> PipelineRequest:
        (tmp_path / "prepared").mkdir(parents=True, exist_ok=True)
        return PipelineRequest(
            key=TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=seed),
            policy=ThresholdPolicy.GLOBAL_THRESHOLD,
            cfg=MagicMock(),
            base_dir=tmp_path,
            prepared_dir=tmp_path / "prepared",
        )

    def test_skips_training_when_scores_exist(self, tmp_path: Path) -> None:
        manifest = MagicMock(model_hash="model-hash")
        with (
            patch(
                "datp.experiments.validate_scoring_manifest",
                return_value=manifest,
            ),
            patch("datp.federated.run_fl_training") as run_fl,
        ):
            result = ensure_trained_scores(self._request(tmp_path, 5))

        run_fl.assert_not_called()
        assert result is manifest

    @pytest.mark.parametrize(
        "failure", [FileNotFoundError("missing"), ValueError("partial")]
    )
    def test_trains_when_scores_missing_or_incomplete(
        self, tmp_path: Path, failure: Exception
    ) -> None:
        manifest = MagicMock(model_hash="model-hash")
        with (
            patch(
                "datp.experiments.validate_scoring_manifest",
                side_effect=[failure, manifest],
            ),
            patch(
                "datp.federated.load_client_data",
                return_value={"c1": object()},
            ),
            patch("datp.federated.run_fl_training") as run_fl,
        ):
            result = ensure_trained_scores(self._request(tmp_path, 6))

        run_fl.assert_called_once()
        assert result is manifest


class TestNoProductionAssert:
    """Executor source contains no production-only assert statements."""

    def test_no_assert_in_executor_source(self) -> None:
        import inspect

        import datp.experiments as mod

        source = inspect.getsource(mod)

        non_comment = "\n".join(
            line for line in source.splitlines() if not line.strip().startswith("#")
        )
        assert "assert " not in non_comment, (
            "Production assert found in pipeline/executor.py"
        )


class TestPipelineRequest:
    """PipelineRequest field accessibility and immutability."""

    def _make_cfg(self) -> MagicMock:
        """Build a mock config with threshold n_min=100 and q=95."""
        cfg = MagicMock()
        cfg.threshold.n_min = 100
        cfg.threshold.q = 95
        return cfg

    def test_fields_accessible(self, tmp_path: Path) -> None:
        key = TrainingCellId(stage=_STAGE, seed=3)
        cfg = self._make_cfg()
        req = PipelineRequest(
            key=key,
            policy=ThresholdPolicy.GLOBAL_THRESHOLD,
            cfg=cfg,
            base_dir=tmp_path,
            prepared_dir=tmp_path / "prepared",
        )
        assert req.key is key
        assert req.policy == ThresholdPolicy.GLOBAL_THRESHOLD
        assert req.cfg is cfg
        assert req.base_dir == tmp_path
        assert req.prepared_dir == tmp_path / "prepared"

    def test_key_carried_through(self, tmp_path: Path) -> None:
        key = TrainingCellId(stage=_STAGE, seed=9)
        cfg = self._make_cfg()
        req = PipelineRequest(
            key=key,
            policy=ThresholdPolicy.LOCAL_THRESHOLD,
            cfg=cfg,
            base_dir=tmp_path,
            prepared_dir=tmp_path,
        )
        assert req.key.stage == _STAGE
        assert req.key.seed == 9

    def test_immutable(self, tmp_path: Path) -> None:
        key = TrainingCellId(stage=_STAGE, seed=1)
        req = PipelineRequest(
            key=key,
            policy=ThresholdPolicy.GLOBAL_THRESHOLD,
            cfg=self._make_cfg(),
            base_dir=tmp_path,
            prepared_dir=tmp_path,
        )
        with pytest.raises((AttributeError, TypeError)):
            setattr(req, "policy", ThresholdPolicy.LOCAL_THRESHOLD)


class TestSharedPipelineContext:
    """SharedPipelineContext fields and pending-client tracking."""

    def _make_key(self) -> TrainingCellId:
        return TrainingCellId(stage=_STAGE, seed=1)

    def test_fields_accessible(self, tmp_path: Path) -> None:
        from datp.scoring import ScoreProvider

        key = self._make_key()
        errors = {"c0": np.array([0.1, 0.2]), "c1": np.array([0.3])}
        taus = {"c0": 0.15, "c1": 0.28}
        provider = ScoreProvider(tmp_path)

        ctx = SharedPipelineContext(
            key=key,
            client_errors=errors,
            eligible=["c0", "c1"],
            pending=[],
            client_taus=taus,
            tau_global=0.20,
            score_provider=provider,
            model_identity="model-hash",
        )

        assert ctx.key is key
        assert ctx.eligible == ["c0", "c1"]
        assert ctx.pending == []
        assert ctx.tau_global == pytest.approx(0.20)
        assert set(ctx.client_taus) == {"c0", "c1"}
        assert ctx.score_provider is provider

    def test_pending_clients_tracked(self, tmp_path: Path) -> None:
        from datp.scoring import ScoreProvider

        key = self._make_key()
        ctx = SharedPipelineContext(
            key=key,
            client_errors={"c0": np.array([0.1])},
            eligible=[],
            pending=["c0"],
            client_taus={},
            tau_global=0.0,
            score_provider=ScoreProvider(tmp_path),
            model_identity="model-hash",
        )
        assert "c0" in ctx.pending
        assert ctx.eligible == []

    def test_mutable(self, tmp_path: Path) -> None:
        from datp.scoring import ScoreProvider

        key = self._make_key()
        ctx = SharedPipelineContext(
            key=key,
            client_errors={},
            eligible=[],
            pending=[],
            client_taus={},
            tau_global=0.0,
            score_provider=ScoreProvider(tmp_path),
            model_identity="model-hash",
        )
        ctx.tau_global = 0.99
        assert ctx.tau_global == pytest.approx(0.99)

    def test_no_eager_score_arrays(self, tmp_path: Path) -> None:
        from datp.scoring import ScoreProvider

        ctx = SharedPipelineContext(
            key=self._make_key(),
            client_errors={},
            eligible=[],
            pending=[],
            client_taus={},
            tau_global=0.0,
            score_provider=ScoreProvider(tmp_path),
            model_identity="model-hash",
        )
        assert not hasattr(ctx, "test_scores"), "test_scores must be removed"


class TestSweepStep:
    """SweepStep initialization and defaults."""

    def test_init_score_provider_step_value(self) -> None:
        assert SweepStep.INIT_SCORE_PROVIDER == "init_score_provider"


_TOTAL_CELLS = 30


class TestBuildExperimentMatrix:
    """Experiment matrix construction from sweep config."""

    def test_total_count(self):
        cells = build_experiment_matrix()
        assert len(cells) == _TOTAL_CELLS

    def test_all_nbaiot_main_stage(self):
        cells = build_experiment_matrix()
        assert all(c.stage == _STAGE for c in cells)

    def test_only_controlled_policies(self):
        cells = build_experiment_matrix()
        assert {c.policy for c in cells} == set(CONTROLLED_POLICIES)

    def test_cells_are_policy_run_id_instances(self):
        cells = build_experiment_matrix()
        assert all(isinstance(c, PolicyRunId) for c in cells)

    def test_each_policy_has_ten_seeds(self):
        cells = build_experiment_matrix()
        for policy in CONTROLLED_POLICIES:
            policy_cells = [c for c in cells if c.policy == policy]
            assert len(policy_cells) == 10


class TestValidateSweep:
    """Sweep validation checks."""

    def test_all_valid(self):
        cells = build_experiment_matrix()
        errors, configs = validate_sweep(cells)
        assert errors == []
        assert len(configs) == len(cells)

    def test_configs_keyed_by_policy_run_id(self):
        cells = build_experiment_matrix()
        _, configs = validate_sweep(cells)
        for cell in cells:
            assert cell in configs
            assert configs[cell] is not None

    def test_empty_cells_returns_empty(self):
        errors, configs = validate_sweep([])
        assert errors == []
        assert configs == {}


class TestSweepResult:
    """SweepResult field defaults and structure."""

    def test_defaults(self):
        r = SweepResult()
        assert r.total == 0
        assert r.completed == 0
        assert r.skipped == 0
        assert r.failed == 0

    def test_explicit_total(self):
        r = SweepResult(total=42)
        assert r.total == 42
        assert r.completed == 0


class TestIsDone:
    """Completion tracking for policy runs."""

    def _run(self) -> PolicyRunId:
        return PolicyRunId(
            cell=TrainingCellId(stage=_STAGE, seed=0),
            policy=ThresholdPolicy.GLOBAL_THRESHOLD,
        )

    def test_missing_metrics_are_not_done(self, tmp_path: Path):
        assert _is_done(self._run(), tmp_path) is False

    def test_valid_metrics_are_done(self, tmp_path: Path):
        from datp.artifacts import ArtifactLayout

        run = self._run()
        result_dir = (
            ArtifactLayout(base_dir=tmp_path, stage=_STAGE).policy_run(run).result_dir
        )
        result_dir.mkdir(parents=True, exist_ok=True)
        (result_dir / "metrics.json").write_text(
            valid_metrics_json("global_threshold", "nbaiot_main", 0)
        )

        assert _is_done(run, tmp_path) is True


class _InlinePool:
    """Process-pool stand-in that runs submitted work in-process."""

    instances: list["_InlinePool"] = []

    def __init__(self, max_workers, mp_context, initializer, initargs) -> None:
        self.max_workers = max_workers
        self.mp_context = mp_context
        initializer(*initargs)
        _InlinePool.instances.append(self)

    def __enter__(self) -> "_InlinePool":
        return self

    def __exit__(self, *exc_info) -> None:
        return None

    def submit(self, fn, *args):
        from concurrent.futures import Future

        future = Future()
        future.set_result(fn(*args))
        return future


class TestParallelSweep:
    """The multi-worker path submits one seed group per task and merges the counts."""

    def test_groups_run_in_the_pool_and_counts_are_merged(self, tmp_path: Path):
        from unittest.mock import patch

        groups: list[int] = []

        def fake_process_group(key, cells, _configs, _base, result, idx, total, _root):
            groups.append(idx)
            result.completed += len(cells)
            result.skipped += 1

        _InlinePool.instances.clear()
        with (
            patch("datp.experiments.ProcessPoolExecutor", _InlinePool),
            patch("datp.experiments._process_group", fake_process_group),
            patch("datp.experiments.configure_logging") as configure,
        ):
            result = run_sweep(base_dir=tmp_path, workers=3)

        (pool,) = _InlinePool.instances
        assert pool.max_workers == 3
        assert pool.mp_context.get_start_method() == "spawn"
        assert groups == list(range(1, 11))
        assert result.completed == _TOTAL_CELLS
        assert result.skipped == 10
        assert result.failed == 0
        log_dir = configure.call_args.args[1]
        assert log_dir.parent == tmp_path / "logs" / "workers"

    def test_pool_never_exceeds_the_number_of_seed_groups(self, tmp_path: Path):
        from unittest.mock import patch

        _InlinePool.instances.clear()
        with (
            patch("datp.experiments.ProcessPoolExecutor", _InlinePool),
            patch("datp.experiments._process_group"),
            patch("datp.experiments.configure_logging"),
        ):
            run_sweep(base_dir=tmp_path, workers=64)

        assert _InlinePool.instances[0].max_workers == 10


class TestRunSweep:
    """End-to-end sweep execution."""

    def test_reports_matrix_total(self, tmp_path: Path):
        from unittest.mock import patch

        with patch("datp.experiments._process_group"):
            result = run_sweep(base_dir=tmp_path, workers=1)

        assert isinstance(result, SweepResult)
        assert result.total == _TOTAL_CELLS
        assert result.completed == 0
        assert result.failed == 0

    def test_skips_completed_runs(self, tmp_path: Path):
        import json
        from unittest.mock import patch

        from datp.artifacts import ArtifactLayout
        from tests.fixtures import valid_metrics_dict

        run = PolicyRunId(
            cell=TrainingCellId(stage=_STAGE, seed=0),
            policy=ThresholdPolicy.GLOBAL_THRESHOLD,
        )
        metrics_path = (
            ArtifactLayout(base_dir=tmp_path, stage=_STAGE).policy_run(run).metrics_path
        )
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_path.write_text(
            json.dumps(valid_metrics_dict("global_threshold", "nbaiot_main", 0))
        )

        _fail = RuntimeError("no data — mocked for unit test")
        with (
            patch("datp.experiments.logger"),
            patch("datp.experiments.ensure_prepared_data"),
            patch("datp.experiments.build_shared_context", side_effect=_fail),
        ):
            result = run_sweep(base_dir=tmp_path, workers=1)

        assert result.skipped >= 1
        assert result.failed == result.total - result.skipped

    def test_data_root_passed_through(self, tmp_path: Path):
        from unittest.mock import patch

        with patch("datp.experiments._process_group") as process_group:
            run_sweep(base_dir=tmp_path, data_root=tmp_path / "data", workers=1)

        assert process_group.call_args.args[-1] == tmp_path / "data"
