from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from datp.core.tracking import (
    _MlflowModule,
    TrackingMetric,
    TrackingMetricKey,
    TrackingMetrics,
    TrackingParam,
    TrackingParamKey,
    TrackingParams,
    TrackingTag,
    TrackingTagKey,
    TrackingTags,
    init_tracking,
    log_artifact,
    log_metrics,
    log_params,
    tracking_run,
)


class TestInitTracking:
    def test_disables_when_mlflow_unavailable(self, tmp_path: Path) -> None:
        import datp.core.tracking as t

        t._TRACKING_ENABLED = True  # noqa: SLF001
        t._MLFLOW = None  # noqa: SLF001
        with patch("datp.core.tracking._import_mlflow", return_value=None):
            init_tracking(experiment_name="test", tracking_uri=tmp_path.as_uri())
        assert t._TRACKING_ENABLED is False  # noqa: SLF001

    def test_enables_when_mlflow_available(self, tmp_path: Path) -> None:
        mock = MagicMock(spec=_MlflowModule)
        import datp.core.tracking as t

        t._TRACKING_ENABLED = False  # noqa: SLF001
        with patch("datp.core.tracking._import_mlflow", return_value=mock):
            init_tracking(experiment_name="test_exp", tracking_uri=tmp_path.as_uri())
        assert t._TRACKING_ENABLED is True  # noqa: SLF001
        mock.set_tracking_uri.assert_called_once_with(tmp_path.as_uri())
        mock.set_experiment.assert_called_once_with("test_exp")


class TestTrackingRun:
    def test_yields_none_when_tracking_disabled(self) -> None:
        import datp.core.tracking as t

        t._TRACKING_ENABLED = False  # noqa: SLF001
        with tracking_run(run_name="test", params=None, tags=None):
            assert t._TRACKING_ENABLED is False

    def test_yields_none_when_mlflow_missing(self) -> None:
        import datp.core.tracking as t

        t._TRACKING_ENABLED = True  # noqa: SLF001
        with patch("datp.core.tracking._import_mlflow", return_value=None):
            with tracking_run(run_name="test", params=None, tags=None):
                assert t._TRACKING_ENABLED is True

    def test_starts_run_with_params_and_tags(self) -> None:
        mock_mlflow = MagicMock(spec=_MlflowModule)
        mock_run = MagicMock()
        mock_mlflow.start_run.return_value = mock_run
        mock_mlflow.active_run.return_value = None

        import datp.core.tracking as t

        t._TRACKING_ENABLED = True  # noqa: SLF001
        with patch("datp.core.tracking._import_mlflow", return_value=mock_mlflow):
            with tracking_run(
                run_name="my_run",
                params=TrackingParams((TrackingParam(TrackingParamKey.SEED, 1),)),
                tags=TrackingTags((TrackingTag(TrackingTagKey.PIPELINE, "eval"),)),
            ):
                assert mock_mlflow.start_run.called

        mock_mlflow.start_run.assert_called_once_with(run_name="my_run", nested=False)
        mock_mlflow.log_params.assert_called_once_with({"seed": "1"})
        mock_mlflow.set_tags.assert_called_once_with({"pipeline": "eval"})

    def test_nests_when_active_run_exists(self) -> None:
        mock_mlflow = MagicMock(spec=_MlflowModule)
        mock_run = MagicMock()
        mock_mlflow.start_run.return_value = mock_run
        mock_mlflow.active_run.return_value = MagicMock()  # already in a run

        import datp.core.tracking as t

        t._TRACKING_ENABLED = True  # noqa: SLF001
        with patch("datp.core.tracking._import_mlflow", return_value=mock_mlflow):
            with tracking_run(run_name="nested_run", params=None, tags=None):
                assert mock_mlflow.active_run.called

        mock_mlflow.start_run.assert_called_once_with(
            run_name="nested_run", nested=True
        )


class TestLogMetrics:
    def test_noop_when_tracking_disabled(self) -> None:
        import datp.core.tracking as t

        t._TRACKING_ENABLED = False  # noqa: SLF001
        log_metrics(
            TrackingMetrics((TrackingMetric(TrackingMetricKey.TAU, 1.0),)),
            step=None,
            prefix=None,
        )

    def test_noop_when_mlflow_missing(self) -> None:
        import datp.core.tracking as t

        t._TRACKING_ENABLED = True  # noqa: SLF001
        with patch("datp.core.tracking._import_mlflow", return_value=None):
            log_metrics(
                TrackingMetrics((TrackingMetric(TrackingMetricKey.TAU, 1.0),)),
                step=None,
                prefix=None,
            )

    def test_logs_numeric_metrics(self) -> None:
        mock_mlflow = MagicMock(spec=_MlflowModule)
        import datp.core.tracking as t

        t._TRACKING_ENABLED = True  # noqa: SLF001
        with patch("datp.core.tracking._import_mlflow", return_value=mock_mlflow):
            log_metrics(
                TrackingMetrics(
                    (
                        TrackingMetric(TrackingMetricKey.TRAIN_LOSS, 0.5),
                        TrackingMetric(TrackingMetricKey.VAL_LOSS, 1.0),
                    )
                ),
                step=10,
                prefix=None,
            )

        mock_mlflow.log_metrics.assert_called_once()
        call_args = mock_mlflow.log_metrics.call_args
        assert call_args.args[0] == {"train_loss": 0.5, "val_loss": 1.0}
        assert call_args.kwargs["step"] == 10

    def test_adds_prefix_to_keys(self) -> None:
        mock_mlflow = MagicMock(spec=_MlflowModule)
        import datp.core.tracking as t

        t._TRACKING_ENABLED = True  # noqa: SLF001
        with patch("datp.core.tracking._import_mlflow", return_value=mock_mlflow):
            log_metrics(
                TrackingMetrics((TrackingMetric(TrackingMetricKey.TRAIN_LOSS, 0.3),)),
                step=None,
                prefix="train",
            )

        call_args = mock_mlflow.log_metrics.call_args
        assert call_args.args[0] == {"train.train_loss": 0.3}

    def test_skips_nonfinite_values(self) -> None:
        mock_mlflow = MagicMock(spec=_MlflowModule)
        import datp.core.tracking as t

        t._TRACKING_ENABLED = True  # noqa: SLF001
        with patch("datp.core.tracking._import_mlflow", return_value=mock_mlflow):
            log_metrics(
                TrackingMetrics(
                    (
                        TrackingMetric(TrackingMetricKey.TAU, 1.0),
                        TrackingMetric(TrackingMetricKey.N_CLIENTS, float("inf")),
                        TrackingMetric(TrackingMetricKey.EPOCHS_RUN, float("nan")),
                    )
                ),
                step=None,
                prefix=None,
            )

        call_args = mock_mlflow.log_metrics.call_args
        metrics = call_args.args[0]
        assert TrackingMetricKey.TAU.value in metrics
        assert TrackingMetricKey.N_CLIENTS.value not in metrics
        assert TrackingMetricKey.EPOCHS_RUN.value not in metrics

    def test_skips_non_numeric_values(self) -> None:
        mock_mlflow = MagicMock(spec=_MlflowModule)
        import datp.core.tracking as t

        t._TRACKING_ENABLED = True  # noqa: SLF001
        with patch("datp.core.tracking._import_mlflow", return_value=mock_mlflow):
            log_metrics(
                TrackingMetrics(
                    (
                        TrackingMetric(TrackingMetricKey.TAU, 1.0),
                        TrackingMetric(
                            TrackingMetricKey.N_CLIENTS,
                            "string",  # type: ignore[arg-type]
                        ),
                    )
                ),
                step=None,
                prefix=None,
            )

        call_args = mock_mlflow.log_metrics.call_args
        metrics = call_args.args[0]
        assert TrackingMetricKey.TAU.value in metrics
        assert TrackingMetricKey.N_CLIENTS.value not in metrics

    def test_no_call_when_all_metrics_filtered(self) -> None:
        mock_mlflow = MagicMock(spec=_MlflowModule)
        import datp.core.tracking as t

        t._TRACKING_ENABLED = True  # noqa: SLF001
        with patch("datp.core.tracking._import_mlflow", return_value=mock_mlflow):
            log_metrics(
                TrackingMetrics(
                    (TrackingMetric(TrackingMetricKey.N_CLIENTS, float("inf")),)
                ),
                step=None,
                prefix=None,
            )

        mock_mlflow.log_metrics.assert_not_called()


class TestLogParams:
    def test_noop_when_tracking_disabled(self) -> None:
        import datp.core.tracking as t

        t._TRACKING_ENABLED = False  # noqa: SLF001
        log_params(TrackingParams((TrackingParam(TrackingParamKey.SEED, 1),)))

    def test_noop_when_mlflow_missing(self) -> None:
        import datp.core.tracking as t

        t._TRACKING_ENABLED = True  # noqa: SLF001
        with patch("datp.core.tracking._import_mlflow", return_value=None):
            log_params(TrackingParams((TrackingParam(TrackingParamKey.SEED, 1),)))

    def test_delegates_to_mlflow(self) -> None:
        mock_mlflow = MagicMock(spec=_MlflowModule)
        import datp.core.tracking as t

        t._TRACKING_ENABLED = True  # noqa: SLF001
        with patch("datp.core.tracking._import_mlflow", return_value=mock_mlflow):
            log_params(
                TrackingParams(
                    (
                        TrackingParam(TrackingParamKey.SEED, 1),
                        TrackingParam(TrackingParamKey.ALPHA, None),
                    )
                )
            )

        mock_mlflow.log_params.assert_called_once_with(
            {"seed": "1", "alpha": "none"}
        )


class TestLogArtifact:
    def test_noop_when_tracking_disabled(self, tmp_path: Path) -> None:
        import datp.core.tracking as t

        t._TRACKING_ENABLED = False  # noqa: SLF001
        log_artifact(str(tmp_path / "fake.txt"), artifact_path=None)  # should not raise

    def test_noop_when_mlflow_missing(self, tmp_path: Path) -> None:
        import datp.core.tracking as t

        t._TRACKING_ENABLED = True  # noqa: SLF001
        with patch("datp.core.tracking._import_mlflow", return_value=None):
            log_artifact(str(tmp_path / "fake.txt"), artifact_path=None)

    def test_delegates_to_mlflow_with_path_conversion(self, tmp_path: Path) -> None:
        mock_mlflow = MagicMock(spec=_MlflowModule)
        import datp.core.tracking as t

        t._TRACKING_ENABLED = True  # noqa: SLF001
        model_path = tmp_path / "model.pt"
        with patch("datp.core.tracking._import_mlflow", return_value=mock_mlflow):
            log_artifact(model_path, artifact_path="models")

        mock_mlflow.log_artifact.assert_called_once_with(
            str(model_path), artifact_path="models"
        )
