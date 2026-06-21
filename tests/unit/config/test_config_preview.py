from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

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
from datp.config.stages import ExperimentStage
from datp.core.enums import CONTROLLED_POLICIES

_STAGE = ExperimentStage.NBAIOT_MAIN


class TestComposeRequest:
    """Direct ComposeRequest model tests — validate boundary contracts."""

    def test_valid_request(self) -> None:
        req = ComposeRequest.model_validate(
            {"stage": _STAGE, "policy": ThresholdPolicy.GLOBAL_THRESHOLD, "seed": 0}
        )
        assert req.stage is _STAGE
        assert req.policy is ThresholdPolicy.GLOBAL_THRESHOLD
        assert req.seed == 0

    def test_string_input_coerced(self) -> None:
        req = ComposeRequest.model_validate(
            {"stage": "nbaiot_main", "policy": "global_threshold", "seed": 0}
        )
        assert req.stage is _STAGE
        assert req.policy is ThresholdPolicy.GLOBAL_THRESHOLD

    def test_invalid_stage_raises(self) -> None:
        with pytest.raises(ValueError):
            ComposeRequest.model_validate(
                {"stage": "z", "policy": ThresholdPolicy.GLOBAL_THRESHOLD, "seed": 0}
            )

    def test_invalid_policy_raises(self) -> None:
        with pytest.raises(ValueError):
            ComposeRequest.model_validate(
                {"stage": _STAGE, "policy": "b9", "seed": 0}
            )

    def test_all_controlled_policies_pass(self) -> None:
        for policy in CONTROLLED_POLICIES:
            req = ComposeRequest.model_validate(
                {"stage": _STAGE, "policy": policy, "seed": 0}
            )
            assert req.policy is policy


class TestComposeConfig:
    def test_basic_composition(self) -> None:
        cfg = compose_config(stage=_STAGE, policy=ThresholdPolicy.GLOBAL_THRESHOLD, seed=0)
        assert cfg.stage is _STAGE
        assert cfg.policy is ThresholdPolicy.GLOBAL_THRESHOLD
        assert cfg.seed == 0
        assert cfg.model.input_dim == 115
        assert cfg.federation.convergence.rounds_initial == 40
        assert cfg.threshold.q == pytest.approx(0.95)

    def test_invalid_stage(self) -> None:
        with pytest.raises(ComposeError, match="(?i)invalid|stage"):
            compose_config(stage="z", policy=ThresholdPolicy.GLOBAL_THRESHOLD, seed=0)

    def test_invalid_policy(self) -> None:
        with pytest.raises(ComposeError, match="(?i)invalid|policy"):
            compose_config(stage=_STAGE, policy="b9", seed=0)

    def test_string_input_accepted(self) -> None:
        cfg = compose_config(stage="nbaiot_main", policy="global_threshold", seed=0)
        assert cfg.stage is _STAGE
        assert cfg.policy is ThresholdPolicy.GLOBAL_THRESHOLD

    def test_deep_copy_isolation(self) -> None:
        cfg1 = compose_config(stage=_STAGE, policy=ThresholdPolicy.GLOBAL_THRESHOLD, seed=0)
        cfg2 = compose_config(stage=_STAGE, policy=ThresholdPolicy.GLOBAL_THRESHOLD, seed=1)
        with pytest.raises(Exception):
            cfg1.model.input_dim = 999
        assert cfg2.model.input_dim == 115


class TestResolvedConfigYaml:
    def test_yaml_output_from_pydantic_config(self) -> None:
        cfg = compose_config(stage=_STAGE, policy=ThresholdPolicy.GLOBAL_THRESHOLD, seed=0)
        yaml_text = resolved_config_yaml(cfg)
        assert "stage: nbaiot_main" in yaml_text
        assert "policy: global_threshold" in yaml_text
        assert "seed: 0" in yaml_text

    def test_yaml_output_roundtrips(self) -> None:
        cfg = compose_config(stage=_STAGE, policy=ThresholdPolicy.LOCAL_THRESHOLD, seed=42)
        yaml_text = resolved_config_yaml(cfg)
        parsed = yaml.safe_load(yaml_text)
        assert parsed["stage"] == "nbaiot_main"
        assert parsed["policy"] == "local_threshold"
        assert parsed["seed"] == 42


class TestWriteResolvedConfig:
    def test_writes_file(self, tmp_path: Path) -> None:
        cfg = compose_config(stage=_STAGE, policy=ThresholdPolicy.GLOBAL_THRESHOLD, seed=0)
        dest = write_resolved_config(cfg, tmp_path)
        assert dest.exists()
        assert dest.name == "resolved_config.yaml"
        content = yaml.safe_load(dest.read_text())
        assert content["stage"] == "nbaiot_main"

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        cfg = compose_config(stage=_STAGE, policy=ThresholdPolicy.GLOBAL_THRESHOLD, seed=0)
        nested = tmp_path / "deep" / "nested"
        dest = write_resolved_config(cfg, nested)
        assert dest.parent == nested
        assert dest.exists()


class TestPreviewConfig:
    def test_writes_resolved_config(self, tmp_path: Path) -> None:
        dest = preview_config(
            stage=_STAGE,
            policy=ThresholdPolicy.GLOBAL_THRESHOLD,
            seed=0,
            output_dir=tmp_path,
        )
        assert dest.exists()
        assert dest.name == ArtifactFile.RESOLVED_CONFIG
        content = yaml.safe_load(dest.read_text())
        assert content["stage"] == "nbaiot_main"
        assert content["policy"] == "global_threshold"
        assert content["seed"] == 0

    def test_default_output_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        dest = preview_config(stage=_STAGE, policy=ThresholdPolicy.LOCAL_THRESHOLD, seed=42)
        assert "nbaiot_main" in str(dest)
        assert "local_threshold" in str(dest)
        assert "seed_42" in str(dest)
        assert dest.name == ArtifactFile.RESOLVED_CONFIG

    def test_validation_failure_propagates(self) -> None:
        with pytest.raises(ComposeError):
            compose_config(stage="z", policy=ThresholdPolicy.GLOBAL_THRESHOLD, seed=0)

    def test_yaml_is_valid(self, tmp_path: Path) -> None:
        dest = preview_config(
            stage=_STAGE, policy=ThresholdPolicy.CLUSTER_THRESHOLD, seed=7, output_dir=tmp_path
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
                "--stage=nbaiot_main",
                "--policy=global_threshold",
                "--seed=0",
                f"--output-dir={tmp_path}",
            ]
        )
        assert rc == 0
        assert (tmp_path / ArtifactFile.RESOLVED_CONFIG).exists()

    def test_preview_invalid_stage_exits_one(self, tmp_path: Path) -> None:
        rc = main(
            [
                "config",
                "preview",
                "--stage=z",
                "--policy=global_threshold",
                "--seed=0",
                f"--output-dir={tmp_path}",
            ]
        )
        assert rc != 0

    def test_no_command_exits_one(self) -> None:
        rc = main([])
        assert rc == 1
