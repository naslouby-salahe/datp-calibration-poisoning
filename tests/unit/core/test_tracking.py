"""Tests verifying MLflow tracking initialization, run context nesting, parameter, metric, and artifact logging."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from datp.core.tracking import (
    _MlflowModule,
    TrackingMetric,
    TrackingMetricKey,
    TrackingParam,
    TrackingParamKey,
    init_tracking,
    log_artifact,
    log_metrics,
    log_params,
    tracking_run,
)


class TestInitTracking:
    """Tests verifying init_tracking behavior under different MLflow availability scenarios."""

    def test_disables_when_mlflow_unavailable(self, tmp_path: Path) -> None:
        """Verify that tracking is disabled when mlflow package is not importable."""
        import datp.core.tracking as t

        t._TRACKING_ENABLED.set(True)
        t._import_mlflow.cache_clear()
        with patch("datp.core.tracking._import_mlflow", return_value=None):
            init_tracking(experiment_name="test", tracking_uri=tmp_path.as_uri())
        assert t._TRACKING_ENABLED.get() is False

    def test_enables_when_mlflow_available(self, tmp_path: Path) -> None:
        """Verify that tracking is enabled and initialized when mlflow is available."""
        mock = MagicMock(spec=_MlflowModule)
        import datp.core.tracking as t

        t._TRACKING_ENABLED.set(False)
        with patch("datp.core.tracking._import_mlflow", return_value=mock):
            init_tracking(experiment_name="test_exp", tracking_uri=tmp_path.as_uri())
        assert t._TRACKING_ENABLED.get() is True
        mock.set_tracking_uri.assert_called_once_with(tmp_path.as_uri())
        mock.set_experiment.assert_called_once_with("test_exp")


class TestTrackingRun:
    """Tests verifying mlflow nested/root run context creation."""

    def test_yields_none_when_tracking_disabled(self) -> None:
        """Confirm context manager is a no-op when tracking is disabled."""
        import datp.core.tracking as t

        t._TRACKING_ENABLED.set(False)
        with tracking_run(run_name="test", params=None):
            assert t._TRACKING_ENABLED.get() is False

    def test_yields_none_when_mlflow_missing(self) -> None:
        """Confirm context manager is a no-op when mlflow is not importable."""
        import datp.core.tracking as t

        t._TRACKING_ENABLED.set(True)
        with patch("datp.core.tracking._import_mlflow", return_value=None):
            with tracking_run(run_name="test", params=None):
                assert t._TRACKING_ENABLED.get() is True

    def test_starts_run_with_params(self) -> None:
        """Verify starting a run configures mlflow parameters."""
        mock_mlflow = MagicMock(spec=_MlflowModule)
        mock_run = MagicMock()
        mock_mlflow.start_run.return_value = mock_run
        mock_mlflow.active_run.return_value = None

        import datp.core.tracking as t

        t._TRACKING_ENABLED.set(True)
        with patch("datp.core.tracking._import_mlflow", return_value=mock_mlflow):
            with tracking_run(
                run_name="my_run",
                params=(TrackingParam(TrackingParamKey.SEED, 1),),
            ):
                assert mock_mlflow.start_run.called

        mock_mlflow.start_run.assert_called_once_with(run_name="my_run", nested=False)
        mock_mlflow.log_params.assert_called_once_with({"seed": "1"})

    def test_nests_when_active_run_exists(self) -> None:
        """Verify run context nesting when an active run already exists in mlflow."""
        mock_mlflow = MagicMock(spec=_MlflowModule)
        mock_run = MagicMock()
        mock_mlflow.start_run.return_value = mock_run
        mock_mlflow.active_run.return_value = MagicMock()

        import datp.core.tracking as t

        t._TRACKING_ENABLED.set(True)
        with patch("datp.core.tracking._import_mlflow", return_value=mock_mlflow):
            with tracking_run(run_name="nested_run", params=None):
                assert mock_mlflow.active_run.called

        mock_mlflow.start_run.assert_called_once_with(
            run_name="nested_run", nested=True
        )


class TestLogMetrics:
    """Tests verifying metric logging and filtering rules."""

    def test_noop_when_tracking_disabled(self) -> None:
        """Verify logging is a no-op when tracking is disabled."""
        import datp.core.tracking as t

        t._TRACKING_ENABLED.set(False)
        log_metrics(
            (TrackingMetric(TrackingMetricKey.SWEEP_TOTAL, 1.0),),
            step=None,
            prefix=None,
        )

    def test_noop_when_mlflow_missing(self) -> None:
        """Verify logging is a no-op when mlflow is not importable."""
        import datp.core.tracking as t

        t._TRACKING_ENABLED.set(True)
        with patch("datp.core.tracking._import_mlflow", return_value=None):
            log_metrics(
                (TrackingMetric(TrackingMetricKey.SWEEP_TOTAL, 1.0),),
                step=None,
                prefix=None,
            )

    def test_logs_numeric_metrics(self) -> None:
        """Verify correct forwarding of numeric metrics to mlflow."""
        mock_mlflow = MagicMock(spec=_MlflowModule)
        import datp.core.tracking as t

        t._TRACKING_ENABLED.set(True)
        with patch("datp.core.tracking._import_mlflow", return_value=mock_mlflow):
            log_metrics(
                (
                    TrackingMetric(TrackingMetricKey.SWEEP_TOTAL, 0.5),
                    TrackingMetric(TrackingMetricKey.SWEEP_COMPLETED, 1.0),
                ),
                step=10,
                prefix=None,
            )

        mock_mlflow.log_metrics.assert_called_once()
        call_args = mock_mlflow.log_metrics.call_args
        assert call_args.args[0] == {"sweep_total": 0.5, "sweep_completed": 1.0}
        assert call_args.kwargs["step"] == 10

    def test_adds_prefix_to_keys(self) -> None:
        """Verify prepending prefix strings to logged metric keys."""
        mock_mlflow = MagicMock(spec=_MlflowModule)
        import datp.core.tracking as t

        t._TRACKING_ENABLED.set(True)
        with patch("datp.core.tracking._import_mlflow", return_value=mock_mlflow):
            log_metrics(
                (TrackingMetric(TrackingMetricKey.SWEEP_TOTAL, 0.3),),
                step=None,
                prefix="train",
            )

        call_args = mock_mlflow.log_metrics.call_args
        assert call_args.args[0] == {"train.sweep_total": 0.3}

    def test_skips_nonfinite_values(self) -> None:
        """Ensure infinite and NaN metric values are filtered out."""
        mock_mlflow = MagicMock(spec=_MlflowModule)
        import datp.core.tracking as t

        t._TRACKING_ENABLED.set(True)
        with patch("datp.core.tracking._import_mlflow", return_value=mock_mlflow):
            log_metrics(
                (
                    TrackingMetric(TrackingMetricKey.SWEEP_TOTAL, 1.0),
                    TrackingMetric(TrackingMetricKey.SWEEP_FAILED, float("inf")),
                    TrackingMetric(TrackingMetricKey.SWEEP_SKIPPED, float("nan")),
                ),
                step=None,
                prefix=None,
            )

        call_args = mock_mlflow.log_metrics.call_args
        metrics = call_args.args[0]
        assert TrackingMetricKey.SWEEP_TOTAL.value in metrics
        assert TrackingMetricKey.SWEEP_FAILED.value not in metrics
        assert TrackingMetricKey.SWEEP_SKIPPED.value not in metrics

    def test_skips_non_numeric_values(self) -> None:
        """Ensure non-numeric metric values are filtered out."""
        mock_mlflow = MagicMock(spec=_MlflowModule)
        import datp.core.tracking as t

        t._TRACKING_ENABLED.set(True)
        with patch("datp.core.tracking._import_mlflow", return_value=mock_mlflow):
            log_metrics(
                (
                    TrackingMetric(TrackingMetricKey.SWEEP_TOTAL, 1.0),
                    TrackingMetric(
                        TrackingMetricKey.SWEEP_FAILED,
                        "string",  # type: ignore[arg-type]
                    ),
                ),
                step=None,
                prefix=None,
            )

        call_args = mock_mlflow.log_metrics.call_args
        metrics = call_args.args[0]
        assert TrackingMetricKey.SWEEP_TOTAL.value in metrics
        assert TrackingMetricKey.SWEEP_FAILED.value not in metrics

    def test_no_call_when_all_metrics_filtered(self) -> None:
        """Verify log_metrics is not called if all input metrics are filtered."""
        mock_mlflow = MagicMock(spec=_MlflowModule)
        import datp.core.tracking as t

        t._TRACKING_ENABLED.set(True)
        with patch("datp.core.tracking._import_mlflow", return_value=mock_mlflow):
            log_metrics(
                (TrackingMetric(TrackingMetricKey.SWEEP_FAILED, float("inf")),),
                step=None,
                prefix=None,
            )

        mock_mlflow.log_metrics.assert_not_called()


class TestLogParams:
    """Tests verifying parameter logging forwarding."""

    def test_noop_when_tracking_disabled(self) -> None:
        """Verify log_params is a no-op when tracking is disabled."""
        import datp.core.tracking as t

        t._TRACKING_ENABLED.set(False)
        log_params((TrackingParam(TrackingParamKey.SEED, 1),))

    def test_noop_when_mlflow_missing(self) -> None:
        """Verify log_params is a no-op when mlflow is not importable."""
        import datp.core.tracking as t

        t._TRACKING_ENABLED.set(True)
        with patch("datp.core.tracking._import_mlflow", return_value=None):
            log_params((TrackingParam(TrackingParamKey.SEED, 1),))

    def test_delegates_to_mlflow(self) -> None:
        """Verify parameter map is string-converted and logged to mlflow."""
        mock_mlflow = MagicMock(spec=_MlflowModule)
        import datp.core.tracking as t

        t._TRACKING_ENABLED.set(True)
        with patch("datp.core.tracking._import_mlflow", return_value=mock_mlflow):
            log_params(
                (
                    TrackingParam(TrackingParamKey.SEED, 1),
                    TrackingParam(TrackingParamKey.LABEL, None),
                )
            )

        mock_mlflow.log_params.assert_called_once_with({"seed": "1", "label": "none"})


class TestLogArtifact:
    """Tests verifying artifact logging forwarding."""

    def test_noop_when_tracking_disabled(self, tmp_path: Path) -> None:
        """Verify log_artifact is a no-op when tracking is disabled."""
        import datp.core.tracking as t

        t._TRACKING_ENABLED.set(False)
        log_artifact(tmp_path / "fake.txt", artifact_path=None)

    def test_noop_when_mlflow_missing(self, tmp_path: Path) -> None:
        """Verify log_artifact is a no-op when mlflow is not importable."""
        import datp.core.tracking as t

        t._TRACKING_ENABLED.set(True)
        with patch("datp.core.tracking._import_mlflow", return_value=None):
            log_artifact(tmp_path / "fake.txt", artifact_path=None)

    def test_delegates_to_mlflow_with_path_conversion(self, tmp_path: Path) -> None:
        """Verify log_artifact translates file Path object to string for mlflow."""
        mock_mlflow = MagicMock(spec=_MlflowModule)
        import datp.core.tracking as t

        t._TRACKING_ENABLED.set(True)
        model_path = tmp_path / "model.pt"
        with patch("datp.core.tracking._import_mlflow", return_value=mock_mlflow):
            log_artifact(model_path, artifact_path="models")

        mock_mlflow.log_artifact.assert_called_once_with(
            str(model_path), artifact_path="models"
        )
