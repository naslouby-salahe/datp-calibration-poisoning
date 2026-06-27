"""Unit tests for Pydantic configuration model construction and defaults."""

from __future__ import annotations
from datp.core.enums import ThresholdPolicy

import pytest
from pydantic import ValidationError

from datp.config.models import (
    ConvergenceConfig,
    DatasetConfig,
    DatpConfig,
    ExperimentConfig,
    FederationConfig,
    LoggingConfig,
    MachineConfig,
    ModelConfig,
    QualityGateConfig,
    ReportingConfig,
    RuntimeConfig,
    SafetyBounds,
    StatisticsConfig,
    StyleConfig,
    ThresholdConfig,
    TrackingConfig,
)
from datp.core.enums import Activation


class TestSafetyBounds:
    """Numeric safety bounds on config fields."""

    def test_valid_construction(self) -> None:
        sb = SafetyBounds(max_batch_size_train=512)
        assert sb.max_batch_size_train == 512

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            SafetyBounds.model_validate({"max_batch_size_train": 512, "bogus": 1})

    def test_missing_required(self) -> None:
        with pytest.raises(ValidationError):
            SafetyBounds.model_validate({})


class TestConvergenceConfig:
    """ConvergenceConfig field defaults and constraints."""

    def test_valid_construction(self) -> None:
        c = ConvergenceConfig(
            rounds_initial=40,
            rounds_max=150,
            relative_threshold=0.005,
            window=10,
            round_timeout_s=400.0,
        )
        assert c.rounds_initial == 40
        assert c.rounds_max == 150

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            ConvergenceConfig.model_validate(
                {
                    "rounds_initial": 40,
                    "rounds_max": 150,
                    "relative_threshold": 0.005,
                    "window": 10,
                    "round_timeout_s": 400.0,
                    "bogus": 1,
                }
            )

    def test_missing_required(self) -> None:
        with pytest.raises(ValidationError):
            ConvergenceConfig.model_validate({"rounds_initial": 40})


class TestModelConfig:
    """ModelConfig field defaults and validation."""

    def test_valid_construction(self) -> None:
        m = ModelConfig(
            input_dim=115,
            encoder_dims=[80, 40, 20],
            lr=0.001,
            epochs=200,
            patience=10,
            activation=Activation.RELU,
            use_bn=False,
        )
        assert m.input_dim == 115
        assert m.activation == Activation.RELU

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            ModelConfig.model_validate(
                {
                    "input_dim": 115,
                    "encoder_dims": [80, 40, 20],
                    "lr": 0.001,
                    "epochs": 200,
                    "patience": 10,
                    "activation": Activation.RELU,
                    "use_bn": False,
                    "bogus": 1,
                }
            )

    def test_missing_required(self) -> None:
        with pytest.raises(ValidationError):
            ModelConfig.model_validate({"input_dim": 115})


class TestDatasetConfig:
    """DatasetConfig field defaults and validation."""

    def test_valid_construction(self) -> None:
        d = DatasetConfig(
            feature_count=115,
            n_min=100,
            cap=50000,
            attack_reserve_fraction=0.2,
            nbaiot_balanced_test=False,
        )
        assert d.feature_count == 115
        assert d.n_min == 100

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            DatasetConfig.model_validate(
                {
                    "feature_count": 115,
                    "n_min": 100,
                    "cap": 50000,
                    "attack_reserve_fraction": 0.2,
                    "nbaiot_balanced_test": False,
                    "bogus": 1,
                }
            )


class TestMachineConfig:
    """MachineConfig field defaults and constraints."""

    def test_valid_construction(self) -> None:
        m = MachineConfig(
            batch_size_train=256,
            scoring_batch_size=4096,
            require_cuda=True,
            ray_num_gpus_per_client=0.5,
            per_client_ram_gb=1.5,
            reserve_ram_gb=3.5,
            max_concurrent_override=4,
            ray_object_store_mb=256,
            cache_maxsize=16,
            safety_bounds=SafetyBounds(max_batch_size_train=512),
        )
        assert m.batch_size_train == 256

    def test_batch_size_train_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            MachineConfig(
                batch_size_train=0,
                scoring_batch_size=4096,
                require_cuda=True,
                ray_num_gpus_per_client=0.5,
                per_client_ram_gb=1.5,
                reserve_ram_gb=3.5,
                ray_object_store_mb=256,
                cache_maxsize=16,
                safety_bounds=SafetyBounds(max_batch_size_train=512),
            )

    def test_max_concurrent_override_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            MachineConfig(
                batch_size_train=256,
                scoring_batch_size=4096,
                require_cuda=True,
                ray_num_gpus_per_client=0.5,
                per_client_ram_gb=1.5,
                reserve_ram_gb=3.5,
                max_concurrent_override=0,
                ray_object_store_mb=256,
                cache_maxsize=16,
                safety_bounds=SafetyBounds(max_batch_size_train=512),
            )

    def test_max_concurrent_override_can_be_none(self) -> None:
        m = MachineConfig(
            batch_size_train=256,
            scoring_batch_size=4096,
            require_cuda=True,
            ray_num_gpus_per_client=0.5,
            per_client_ram_gb=1.5,
            reserve_ram_gb=3.5,
            max_concurrent_override=None,
            ray_object_store_mb=256,
            cache_maxsize=16,
            safety_bounds=SafetyBounds(max_batch_size_train=512),
        )
        assert m.max_concurrent_override is None

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            MachineConfig.model_validate(
                {
                    "batch_size_train": 256,
                    "scoring_batch_size": 4096,
                    "require_cuda": True,
                    "ray_num_gpus_per_client": 0.5,
                    "per_client_ram_gb": 1.5,
                    "reserve_ram_gb": 3.5,
                    "ray_object_store_mb": 256,
                    "cache_maxsize": 16,
                    "safety_bounds": SafetyBounds(max_batch_size_train=512),
                    "bogus": 1,
                }
            )


class TestFederationConfig:
    """FederationConfig field defaults and relationships."""

    def test_valid_construction(self) -> None:
        f = FederationConfig(
            convergence=ConvergenceConfig(
                rounds_initial=40,
                rounds_max=150,
                relative_threshold=0.005,
                window=10,
                round_timeout_s=400.0,
            ),
            local_epochs=5,
        )
        assert f.local_epochs == 5

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            FederationConfig.model_validate(
                {
                    "convergence": ConvergenceConfig(
                        rounds_initial=40,
                        rounds_max=150,
                        relative_threshold=0.005,
                        window=10,
                        round_timeout_s=400.0,
                    ),
                    "local_epochs": 5,
                    "bogus": 1,
                }
            )


class TestThresholdConfig:
    """ThresholdConfig field defaults and validation."""

    def test_valid_construction(self) -> None:
        t = ThresholdConfig(
            n_min=100,
            q=95,
            cluster_k_nbaiot=3,
            cluster_n_init=10,
            cluster_max_iter=300,
            cluster_random_state=42,
        )
        assert t.q == pytest.approx(95)
        assert t.cluster_k_nbaiot == 3

    def test_q_must_be_locked_to_95(self) -> None:
        with pytest.raises(ValidationError, match="Input should be"):
            ThresholdConfig.model_validate(
                {
                    "n_min": 100,
                    "q": 0.95,
                    "cluster_k_nbaiot": 3,
                    "cluster_n_init": 10,
                    "cluster_max_iter": 300,
                    "cluster_random_state": 42,
                }
            )

    def test_cluster_k_must_be_locked_to_three(self) -> None:
        with pytest.raises(ValidationError, match="Input should be 3"):
            ThresholdConfig.model_validate(
                {
                    "n_min": 100,
                    "q": 95,
                    "cluster_k_nbaiot": 4,
                    "cluster_n_init": 10,
                    "cluster_max_iter": 300,
                    "cluster_random_state": 42,
                }
            )

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            ThresholdConfig.model_validate(
                {
                    "n_min": 100,
                    "q": 95,
                    "cluster_k_nbaiot": 3,
                    "cluster_n_init": 10,
                    "cluster_max_iter": 300,
                    "cluster_random_state": 42,
                    "bogus": 1,
                }
            )


class TestExperimentConfig:
    """ExperimentConfig field defaults."""

    def test_valid_construction(self) -> None:
        e = ExperimentConfig(seeds=[0, 1, 2])
        assert e.seeds == [0, 1, 2]

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            ExperimentConfig.model_validate(
                {
                    "seeds": [0, 1, 2],
                    "bogus": 1,
                }
            )


class TestStatisticsConfig:
    """StatisticsConfig field defaults."""

    def test_valid_construction(self) -> None:
        s = StatisticsConfig(
            n_bootstrap=10000,
            ci_level=0.95,
            bootstrap_seed=42,
            significance_alpha=0.05,
            dispersion_threshold=0.10,
        )
        assert s.n_bootstrap == 10000

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            StatisticsConfig.model_validate(
                {
                    "n_bootstrap": 10000,
                    "ci_level": 0.95,
                    "bootstrap_seed": 42,
                    "significance_alpha": 0.05,
                    "dispersion_threshold": 0.10,
                    "bogus": 1,
                }
            )


class TestQualityGateConfig:
    """QualityGateConfig field defaults."""

    def test_valid_construction(self) -> None:
        qg = QualityGateConfig(
            js_divergence_n_bins=32,
        )
        assert qg.js_divergence_n_bins == 32

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            QualityGateConfig.model_validate(
                {
                    "js_divergence_n_bins": 32,
                    "bogus": 1,
                }
            )


class TestStyleConfig:
    """StyleConfig field defaults."""

    def test_valid_construction(self) -> None:
        s = StyleConfig(
            dpi=300,
            font_size=9,
            figsize_single_col=(3.5, 2.5),
            figsize_double_col=(7.16, 3.0),
            policy_colors={
                ThresholdPolicy.GLOBAL_THRESHOLD: "#1f77b4",
                ThresholdPolicy.LOCAL_THRESHOLD: "#ff7f0e",
                ThresholdPolicy.CLUSTER_THRESHOLD: "#d62728",
            },
            policy_labels={
                ThresholdPolicy.GLOBAL_THRESHOLD: "GLOBAL_THRESHOLD",
                ThresholdPolicy.LOCAL_THRESHOLD: "LOCAL_THRESHOLD",
                ThresholdPolicy.CLUSTER_THRESHOLD: "CLUSTER_THRESHOLD",
            },
        )
        assert s.dpi == 300
        assert s.policy_colors[ThresholdPolicy.GLOBAL_THRESHOLD] == "#1f77b4"

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            StyleConfig.model_validate(
                {
                    "dpi": 300,
                    "font_size": 9,
                    "figsize_single_col": (3.5, 2.5),
                    "figsize_double_col": (7.16, 3.0),
                    "policy_colors": {ThresholdPolicy.GLOBAL_THRESHOLD: "#1f77b4"},
                    "policy_labels": {
                        ThresholdPolicy.GLOBAL_THRESHOLD: "GLOBAL_THRESHOLD"
                    },
                    "bogus": 1,
                }
            )


class TestLoggingConfig:
    """LoggingConfig field defaults."""

    def test_valid_construction(self) -> None:
        lc = LoggingConfig(
            level="INFO",
            json_format=False,
            max_bytes=10485760,
            backup_count=5,
            training_progress_interval=10,
        )
        assert lc.level == "INFO"

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            LoggingConfig.model_validate(
                {
                    "level": "INFO",
                    "json_format": False,
                    "max_bytes": 10485760,
                    "backup_count": 5,
                    "training_progress_interval": 10,
                    "bogus": 1,
                }
            )


class TestRuntimeConfig:
    """RuntimeConfig field defaults."""

    def test_valid_construction(self) -> None:
        r = RuntimeConfig(
            lock_timeout_seconds=3600.0,
            ray_memory_threshold=0.90,
        )
        assert abs(r.lock_timeout_seconds - 3600.0) < 1e-9

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            RuntimeConfig.model_validate(
                {
                    "lock_timeout_seconds": 3600.0,
                    "ray_memory_threshold": 0.90,
                    "bogus": 1,
                }
            )


class TestTrackingConfig:
    """TrackingConfig field defaults."""

    def test_valid_construction(self) -> None:
        t = TrackingConfig(
            experiment_name="datp",
            tracking_uri="sqlite:///mlruns.db",
        )
        assert t.experiment_name == "datp"

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            TrackingConfig.model_validate(
                {
                    "experiment_name": "datp",
                    "tracking_uri": "sqlite:///mlruns.db",
                    "bogus": 1,
                }
            )


class TestReportingConfig:
    """ReportingConfig field defaults."""

    def test_valid_construction(self) -> None:
        r = ReportingConfig(
            figure2_max_points=5000,
            figure2_rng_seed=42,
            metric_tol=1e-9,
            style=StyleConfig(
                dpi=300,
                font_size=9,
                figsize_single_col=(3.5, 2.5),
                figsize_double_col=(7.16, 3.0),
                policy_colors={ThresholdPolicy.GLOBAL_THRESHOLD: "#1f77b4"},
                policy_labels={ThresholdPolicy.GLOBAL_THRESHOLD: "GLOBAL_THRESHOLD"},
            ),
        )
        assert r.figure2_max_points == 5000

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            ReportingConfig.model_validate(
                {
                    "figure2_max_points": 5000,
                    "figure2_rng_seed": 42,
                    "metric_tol": 1e-9,
                    "style": StyleConfig(
                        dpi=300,
                        font_size=9,
                        figsize_single_col=(3.5, 2.5),
                        figsize_double_col=(7.16, 3.0),
                        policy_colors={ThresholdPolicy.GLOBAL_THRESHOLD: "#1f77b4"},
                        policy_labels={
                            ThresholdPolicy.GLOBAL_THRESHOLD: "GLOBAL_THRESHOLD"
                        },
                    ),
                    "bogus": 1,
                }
            )


class TestDatpConfig:
    """DatpConfig composition and top-level validation."""

    def test_optional_runtime_fields_default_to_none(self) -> None:

        from datp.config.compose import BASE_CONFIG

        assert BASE_CONFIG.stage is None
        assert BASE_CONFIG.policy is None
        assert BASE_CONFIG.seed is None

    def test_frozen_config_is_immutable(self) -> None:
        from datp.config.compose import BASE_CONFIG

        with pytest.raises((TypeError, ValueError, ValidationError)):
            BASE_CONFIG.model.input_dim = 999

    def test_canonical_config_disables_batchnorm(self) -> None:

        from datp.config.compose import BASE_CONFIG

        assert BASE_CONFIG.model.use_bn is False

    def test_missing_required_section_fails(self) -> None:
        with pytest.raises(ValidationError):
            DatpConfig.model_validate(
                {
                    "model": ModelConfig(
                        input_dim=115,
                        encoder_dims=[80, 40, 20],
                        lr=0.001,
                        epochs=200,
                        patience=10,
                        activation=Activation.RELU,
                        use_bn=False,
                    ),
                }
            )
