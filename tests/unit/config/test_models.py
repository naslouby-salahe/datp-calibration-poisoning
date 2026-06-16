"""Unit tests for individual Pydantic config models.

Covers construction, rejection, boundary, and cross-section validation
for every model in ``datp.config.models``.
"""

from __future__ import annotations

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
from datp.core.enums import Activation, Baseline


# ── SafetyBounds ──────────────────────────────────────────────────────────


class TestSafetyBounds:
    def test_valid_construction(self) -> None:
        sb = SafetyBounds(max_batch_size_train=512)
        assert sb.max_batch_size_train == 512

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            SafetyBounds(max_batch_size_train=512, bogus=1) # type: ignore[call-arg]

    def test_missing_required(self) -> None:
        with pytest.raises(ValidationError):
            SafetyBounds() # type: ignore[call-arg]


# ── ConvergenceConfig ─────────────────────────────────────────────────────


class TestConvergenceConfig:
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
            ConvergenceConfig( # type: ignore[call-arg]
                rounds_initial=40,
                rounds_max=150,
                relative_threshold=0.005,
                window=10,
                round_timeout_s=400.0,
                bogus=1, # type: ignore[call-arg]
            )

    def test_missing_required(self) -> None:
        with pytest.raises(ValidationError):
            ConvergenceConfig(rounds_initial=40) # type: ignore[call-arg]


# ── ModelConfig ───────────────────────────────────────────────────────────


class TestModelConfig:
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
            ModelConfig( # type: ignore[call-arg]
                input_dim=115,
                encoder_dims=[80, 40, 20],
                lr=0.001,
                epochs=200,
                patience=10,
                activation=Activation.RELU,
                use_bn=False,
                bogus=1, # type: ignore[call-arg]
            )

    def test_missing_required(self) -> None:
        with pytest.raises(ValidationError):
            ModelConfig(input_dim=115) # type: ignore[call-arg]


# ── DatasetConfig ─────────────────────────────────────────────────────────


class TestDatasetConfig:
    def test_valid_construction(self) -> None:
        d = DatasetConfig(
            feature_count=115,
            n_min=100,
            cap=50000,
            b0_val_fraction=0.1,
            regime_c_train_fraction=0.7,
            regime_c_cal_fraction=0.15,
            attack_reserve_fraction=0.2,
            nbaiot_balanced_test=False,
        )
        assert d.feature_count == 115
        assert d.n_min == 100

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            DatasetConfig( # type: ignore[call-arg]
                feature_count=115,
                n_min=100,
                cap=50000,
                b0_val_fraction=0.1,
                regime_c_train_fraction=0.7,
                regime_c_cal_fraction=0.15,
                attack_reserve_fraction=0.2,
                nbaiot_balanced_test=False,
                bogus=1, # type: ignore[call-arg]
            )


# ── MachineConfig ─────────────────────────────────────────────────────────


class TestMachineConfig:
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
            MachineConfig( # type: ignore[call-arg]
                batch_size_train=256,
                scoring_batch_size=4096,
                require_cuda=True,
                ray_num_gpus_per_client=0.5,
                per_client_ram_gb=1.5,
                reserve_ram_gb=3.5,
                ray_object_store_mb=256,
                cache_maxsize=16,
                safety_bounds=SafetyBounds(max_batch_size_train=512),
                bogus=1, # type: ignore[call-arg]
            )


# ── FederationConfig ──────────────────────────────────────────────────────


class TestFederationConfig:
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
            FederationConfig( # type: ignore[call-arg]
                convergence=ConvergenceConfig(
                    rounds_initial=40,
                    rounds_max=150,
                    relative_threshold=0.005,
                    window=10,
                    round_timeout_s=400.0,
                ),
                local_epochs=5,
                bogus=1, # type: ignore[call-arg]
            )


# ── ThresholdConfig ───────────────────────────────────────────────────────


class TestThresholdConfig:
    def test_valid_construction(self) -> None:
        t = ThresholdConfig(
            n_min=100,
            q=0.95,
            b4_regime_a_mode="fixed",
            b4_k_regime_a=3,
            b4_k_candidates=[2, 3, 4, 5],
            b4_n_init=10,
            b4_random_state=42,
        )
        assert t.q == 0.95
        assert t.b4_regime_a_mode == "fixed"

    def test_invalid_b4_mode_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ThresholdConfig(
                n_min=100,
                q=0.95,
                b4_regime_a_mode="invalid_mode", # type: ignore[arg-type]
                b4_k_regime_a=3,
                b4_k_candidates=[2, 3, 4, 5],
                b4_n_init=10,
                b4_random_state=42,
            )

    def test_silhouette_mode_accepted(self) -> None:
        t = ThresholdConfig(
            n_min=100,
            q=0.95,
            b4_regime_a_mode="silhouette",
            b4_k_regime_a=3,
            b4_k_candidates=[2, 3, 4, 5],
            b4_n_init=10,
            b4_random_state=42,
        )
        assert t.b4_regime_a_mode == "silhouette"

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            ThresholdConfig( # type: ignore[call-arg]
                n_min=100,
                q=0.95,
                b4_regime_a_mode="fixed",
                b4_k_regime_a=3,
                b4_k_candidates=[2, 3, 4, 5],
                b4_n_init=10,
                b4_random_state=42,
                bogus=1, # type: ignore[call-arg]
            )


# ── ExperimentConfig ──────────────────────────────────────────────────────


class TestExperimentConfig:
    def test_valid_construction(self) -> None:
        e = ExperimentConfig(
            seeds=[0, 1, 2],
            regime_c_alphas=[0.1, 0.5, 1.0],
            regime_c_n_clients=20,
            absorption_strong_retention=0.75,
            absorption_partial=0.25,
        )
        assert e.seeds == [0, 1, 2]
        assert e.absorption_strong_retention == 0.75

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            ExperimentConfig( # type: ignore[call-arg]
                seeds=[0, 1, 2],
                regime_c_alphas=[0.1, 0.5, 1.0],
                regime_c_n_clients=20,
                absorption_strong_retention=0.75,
                absorption_partial=0.25,
                bogus=1, # type: ignore[call-arg]
            )


# ── StatisticsConfig ──────────────────────────────────────────────────────


class TestStatisticsConfig:
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
            StatisticsConfig( # type: ignore[call-arg]
                n_bootstrap=10000,
                ci_level=0.95,
                bootstrap_seed=42,
                significance_alpha=0.05,
                dispersion_threshold=0.10,
                bogus=1, # type: ignore[call-arg]
            )


# ── QualityGateConfig ─────────────────────────────────────────────────────


class TestQualityGateConfig:
    def test_valid_construction(self) -> None:
        qg = QualityGateConfig(
            b0_sanity_min=0.90,
            b3_dispersion_threshold=0.25,
            ciciot_homogeneity_threshold=0.05,
            js_divergence_n_bins=32,
        )
        assert qg.b0_sanity_min == 0.90

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            QualityGateConfig( # type: ignore[call-arg]
                b0_sanity_min=0.90,
                b3_dispersion_threshold=0.25,
                ciciot_homogeneity_threshold=0.05,
                js_divergence_n_bins=32,
                bogus=1, # type: ignore[call-arg]
            )


# ── StyleConfig ───────────────────────────────────────────────────────────


class TestStyleConfig:
    def test_valid_construction(self) -> None:
        s = StyleConfig(
            dpi=300,
            font_size=9,
            figsize_single_col=(3.5, 2.5),
            figsize_double_col=(7.16, 3.0),
            baseline_colors={
                Baseline.B0: "#808080",
                Baseline.B1: "#1f77b4",
                Baseline.B2: "#ff7f0e",
                Baseline.B3: "#2ca02c",
                Baseline.B4: "#d62728",
            },
            baseline_labels={
                Baseline.B0: "B0 (Centralised)",
                Baseline.B1: "B1 (Client-Averaged)",
                Baseline.B2: "B2 (Per-Client)",
                Baseline.B3: "B3 (Family-Mean)",
                Baseline.B4: "B4 (Cluster-Mean)",
            },
        )
        assert s.dpi == 300
        assert s.baseline_colors[Baseline.B1] == "#1f77b4"

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            StyleConfig( # type: ignore[call-arg]
                dpi=300,
                font_size=9,
                figsize_single_col=(3.5, 2.5),
                figsize_double_col=(7.16, 3.0),
                baseline_colors={Baseline.B1: "#1f77b4"},
                baseline_labels={Baseline.B1: "B1"},
                bogus=1, # type: ignore[call-arg]
            )




# ── LoggingConfig ─────────────────────────────────────────────────────────


class TestLoggingConfig:
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
            LoggingConfig( # type: ignore[call-arg]
                level="INFO",
                json_format=False,
                max_bytes=10485760,
                backup_count=5,
                training_progress_interval=10,
                bogus=1, # type: ignore[call-arg]
            )


# ── RuntimeConfig ─────────────────────────────────────────────────────────


class TestRuntimeConfig:
    def test_valid_construction(self) -> None:
        r = RuntimeConfig(
            lock_timeout_seconds=3600.0,
            ray_memory_threshold=0.90,
        )
        assert r.lock_timeout_seconds == 3600.0

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            RuntimeConfig( # type: ignore[call-arg]
                lock_timeout_seconds=3600.0,
                ray_memory_threshold=0.90,
                bogus=1, # type: ignore[call-arg]
            )


# ── TrackingConfig ────────────────────────────────────────────────────────


class TestTrackingConfig:
    def test_valid_construction(self) -> None:
        t = TrackingConfig(
            experiment_name="datp",
            tracking_uri="sqlite:///mlruns.db",
        )
        assert t.experiment_name == "datp"

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            TrackingConfig( # type: ignore[call-arg]
                experiment_name="datp",
                tracking_uri="sqlite:///mlruns.db",
                bogus=1, # type: ignore[call-arg]
            )


# ── ReportingConfig ───────────────────────────────────────────────────────


class TestReportingConfig:
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
                baseline_colors={Baseline.B1: "#1f77b4"},
                baseline_labels={Baseline.B1: "B1"},
            ),
        )
        assert r.figure2_max_points == 5000

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            ReportingConfig( # type: ignore[call-arg]
                figure2_max_points=5000,
                figure2_rng_seed=42,
                metric_tol=1e-9,
                style=StyleConfig(
                    dpi=300,
                    font_size=9,
                    figsize_single_col=(3.5, 2.5),
                    figsize_double_col=(7.16, 3.0),
                    baseline_colors={Baseline.B1: "#1f77b4"},
                    baseline_labels={Baseline.B1: "B1"},
                ),
                bogus=1, # type: ignore[call-arg]
            )


# ── DatpConfig ────────────────────────────────────────────────────────────


class TestDatpConfig:
    """Top-level config model with cross-section validators."""

    def test_optional_runtime_fields_default_to_none(self) -> None:
        """regime, baseline, seed, alpha are optional override slots."""
        from datp.config.compose import BASE_CONFIG

        assert BASE_CONFIG.regime is None
        assert BASE_CONFIG.baseline is None
        assert BASE_CONFIG.seed is None
        assert BASE_CONFIG.alpha is None

    def test_frozen_config_is_immutable(self) -> None:
        from datp.config.compose import BASE_CONFIG

        # frozen=True means __setattr__ raises on mutation attempt.
        with pytest.raises((TypeError, ValueError, ValidationError)):
            BASE_CONFIG.model.input_dim = 999 # type: ignore[misc]

    def test_missing_required_section_fails(self) -> None:
        with pytest.raises(ValidationError):
            DatpConfig( # type: ignore[call-arg]
                model=ModelConfig(
                    input_dim=115,
                    encoder_dims=[80, 40, 20],
                    lr=0.001,
                    epochs=200,
                    patience=10,
                    activation=Activation.RELU,
                    use_bn=False,
                ),
            )
