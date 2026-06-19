from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from datp.app.cli import main
from datp.app.cli.config import preview_config
from datp.artifacts.names import ArtifactFile
from datp.config.compose import (
    ComposeError,
    ComposeRequest,
    compose_config,
    resolved_config_yaml,
    write_resolved_config,
)
from datp.core.enums import REGIME_BASELINES, Baseline, Regime


class TestComposeRequest:
    """Direct ComposeRequest model tests — validate boundary contracts."""

    def test_valid_request(self) -> None:
        req = ComposeRequest.model_validate(
            {"regime": Regime.A, "baseline": Baseline.B1, "seed": 0}
        )
        assert req.regime is Regime.A
        assert req.baseline is Baseline.B1
        assert req.seed == 0
        assert req.alpha is None

    def test_valid_with_alpha(self) -> None:
        req = ComposeRequest.model_validate(
            {"regime": Regime.C, "baseline": Baseline.B1, "seed": 0, "alpha": 0.5}
        )
        assert req.alpha == pytest.approx(0.5)

    def test_alpha_required_for_regime_c(self) -> None:
        with pytest.raises(ValueError, match="alpha is required for regime c"):
            ComposeRequest.model_validate(
                {"regime": Regime.C, "baseline": Baseline.B1, "seed": 0}
            )

    def test_baseline_not_in_regime_baselines(self) -> None:
        with pytest.raises(ValueError, match="b3 is not valid for regime b"):
            ComposeRequest.model_validate(
                {"regime": Regime.B, "baseline": Baseline.B3, "seed": 0}
            )

    def test_b0_not_in_regime_c(self) -> None:
        with pytest.raises(ValueError, match="b0 is not valid for regime c"):
            ComposeRequest.model_validate(
                {"regime": Regime.C, "baseline": Baseline.B0, "seed": 0, "alpha": 0.1}
            )

    def test_string_input_coerced(self) -> None:
        req = ComposeRequest.model_validate(
            {"regime": "a", "baseline": "b1", "seed": 0}
        )
        assert req.regime is Regime.A
        assert req.baseline is Baseline.B1

    def test_case_insensitive_string_input(self) -> None:
        req = ComposeRequest.model_validate(
            {"regime": "A", "baseline": "B1", "seed": 0}
        )
        assert req.regime is Regime.A
        assert req.baseline is Baseline.B1

    def test_invalid_regime_enum_raises(self) -> None:
        with pytest.raises(ValueError):
            ComposeRequest.model_validate(
                {"regime": "z", "baseline": Baseline.B1, "seed": 0}
            )

    def test_invalid_baseline_enum_raises(self) -> None:
        with pytest.raises(ValueError):
            ComposeRequest.model_validate(
                {"regime": Regime.A, "baseline": "b9", "seed": 0}
            )

    def test_all_regime_baselines_combinations_pass(self) -> None:
        for regime, baselines in REGIME_BASELINES.items():
            for baseline in baselines:
                alpha = 0.5 if regime == Regime.C else None
                req = ComposeRequest.model_validate(
                    {
                        "regime": regime,
                        "baseline": baseline,
                        "seed": 0,
                        "alpha": alpha,
                    }
                )
                assert req.regime is regime
                assert req.baseline is baseline


class TestComposeConfig:
    def test_basic_composition(self) -> None:
        cfg = compose_config(regime=Regime.A, baseline=Baseline.B1, seed=0)
        assert cfg.regime is Regime.A
        assert cfg.baseline is Baseline.B1
        assert cfg.seed == 0
        assert cfg.model.input_dim == 115
        assert cfg.federation.convergence.rounds_initial == 40
        assert cfg.threshold.q == pytest.approx(0.95)

    def test_regime_c_requires_alpha(self) -> None:
        with pytest.raises(ComposeError, match="alpha is required for regime c"):
            compose_config(regime=Regime.C, baseline=Baseline.B1, seed=0)

    def test_regime_c_with_alpha(self) -> None:
        cfg = compose_config(regime=Regime.C, baseline=Baseline.B1, seed=0, alpha=0.5)
        assert cfg.alpha == pytest.approx(0.5)

    def test_b3_not_valid_for_regime_b(self) -> None:
        with pytest.raises(ComposeError, match="b3 is not valid for regime b"):
            compose_config(regime=Regime.B, baseline=Baseline.B3, seed=0)

    def test_b0_not_valid_for_regime_c(self) -> None:
        with pytest.raises(ComposeError, match="b0 is not valid for regime c"):
            compose_config(regime=Regime.C, baseline=Baseline.B0, seed=0, alpha=0.1)

    def test_invalid_regime(self) -> None:
        with pytest.raises(ComposeError, match="Invalid regime"):
            compose_config(regime="z", baseline=Baseline.B1, seed=0)

    def test_invalid_baseline(self) -> None:
        with pytest.raises(ComposeError, match="Invalid baseline"):
            compose_config(regime=Regime.A, baseline="b9", seed=0)

    def test_string_input_accepted(self) -> None:
        """String regime/baseline inputs are accepted at the compose_config boundary."""
        cfg = compose_config(regime="a", baseline="b1", seed=0)
        assert cfg.regime is Regime.A
        assert cfg.baseline is Baseline.B1

    def test_case_insensitive_strings(self) -> None:
        cfg = compose_config(regime="A", baseline="B1", seed=0)
        assert cfg.regime is Regime.A
        assert cfg.baseline is Baseline.B1

    def test_alpha_absent_when_not_regime_c(self) -> None:
        cfg = compose_config(regime=Regime.A, baseline=Baseline.B1, seed=0)
        assert cfg.alpha is None

    def test_deep_copy_isolation(self) -> None:
        cfg1 = compose_config(regime=Regime.A, baseline=Baseline.B1, seed=0)
        cfg2 = compose_config(regime=Regime.A, baseline=Baseline.B1, seed=1)
        with pytest.raises(Exception):
            cfg1.model.input_dim = 999
        assert cfg2.model.input_dim == 115


class TestResolvedConfigYaml:
    def test_yaml_output_from_pydantic_config(self) -> None:
        cfg = compose_config(regime=Regime.A, baseline=Baseline.B1, seed=0)
        yaml_text = resolved_config_yaml(cfg)
        assert "regime: a" in yaml_text
        assert "baseline: b1" in yaml_text
        assert "seed: 0" in yaml_text

    def test_yaml_output_roundtrips(self) -> None:
        cfg = compose_config(regime=Regime.B, baseline=Baseline.B2, seed=42)
        yaml_text = resolved_config_yaml(cfg)
        parsed = yaml.safe_load(yaml_text)
        assert parsed["regime"] == "b"
        assert parsed["baseline"] == "b2"
        assert parsed["seed"] == 42


class TestWriteResolvedConfig:
    def test_writes_file(self, tmp_path: Path) -> None:
        cfg = compose_config(regime=Regime.A, baseline=Baseline.B1, seed=0)
        dest = write_resolved_config(cfg, tmp_path)
        assert dest.exists()
        assert dest.name == "resolved_config.yaml"
        content = yaml.safe_load(dest.read_text())
        assert content["regime"] == "a"

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        cfg = compose_config(regime=Regime.A, baseline=Baseline.B1, seed=0)
        nested = tmp_path / "deep" / "nested"
        dest = write_resolved_config(cfg, nested)
        assert dest.parent == nested
        assert dest.exists()

    def test_regime_c_includes_alpha(self, tmp_path: Path) -> None:
        cfg = compose_config(regime=Regime.C, baseline=Baseline.B1, seed=0, alpha=0.5)
        dest = write_resolved_config(cfg, tmp_path)
        content = yaml.safe_load(dest.read_text())
        assert content["alpha"] == pytest.approx(0.5)


class TestPreviewConfig:
    def test_writes_resolved_config(self, tmp_path: Path) -> None:
        dest = preview_config(
            regime=Regime.A,
            baseline=Baseline.B1,
            seed=0,
            output_dir=tmp_path,
        )
        assert dest.exists()
        assert dest.name == ArtifactFile.RESOLVED_CONFIG
        content = yaml.safe_load(dest.read_text())
        assert content["regime"] == "a"
        assert content["baseline"] == "b1"
        assert content["seed"] == 0

    def test_default_output_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        dest = preview_config(regime=Regime.B, baseline=Baseline.B2, seed=42)
        assert dest.parent == Path("outputs/results/b/b2/seed_42")
        assert dest.name == ArtifactFile.RESOLVED_CONFIG

    def test_regime_c_output_path_includes_alpha(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        dest = preview_config(regime=Regime.C, baseline=Baseline.B1, seed=0, alpha=0.5)
        assert dest.name == ArtifactFile.RESOLVED_CONFIG
        assert str(dest).endswith(f"seed_0/alpha_0.5/{ArtifactFile.RESOLVED_CONFIG}")

    def test_validation_failure_propagates(self) -> None:
        with pytest.raises(ComposeError, match="Invalid regime"):
            compose_config(regime="z", baseline=Baseline.B1, seed=0)

    def test_yaml_is_valid(self, tmp_path: Path) -> None:
        dest = preview_config(
            regime=Regime.A, baseline=Baseline.B4, seed=7, output_dir=tmp_path
        )
        content = yaml.safe_load(dest.read_text())
        assert isinstance(content, dict)
        assert content["federation"]["convergence"]["rounds_max"] == 150


class TestCLI:
    def test_preview_exits_zero(self, tmp_path: Path) -> None:
        rc = main(
            [
                "config",
                "preview",
                "--regime=a",
                "--baseline=b1",
                "--seed=0",
                f"--output-dir={tmp_path}",
            ]
        )
        assert rc == 0
        assert (tmp_path / ArtifactFile.RESOLVED_CONFIG).exists()

    def test_preview_invalid_regime_exits_one(self, tmp_path: Path) -> None:
        rc = main(
            [
                "config",
                "preview",
                "--regime=z",
                "--baseline=b1",
                "--seed=0",
                f"--output-dir={tmp_path}",
            ]
        )
        assert rc != 0

    def test_no_command_exits_one(self) -> None:
        rc = main([])
        assert rc == 1

    def test_training_not_invoked(self, tmp_path: Path) -> None:
        rc = main(
            [
                "config",
                "preview",
                "--regime=a",
                "--baseline=b1",
                "--seed=0",
                f"--output-dir={tmp_path}",
            ]
        )
        assert rc == 0
        content = yaml.safe_load((tmp_path / ArtifactFile.RESOLVED_CONFIG).read_text())
        assert "regime" in content
        assert not (tmp_path / "metrics.json").exists()
