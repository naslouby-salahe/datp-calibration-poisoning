"""Hydra configuration composition, validation, and serialization for stage/policy/seed triplets."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hydra import compose as hydra_compose
from hydra import initialize_config_module
from hydra.core.global_hydra import GlobalHydra
from omegaconf import DictConfig, OmegaConf
from pydantic import ValidationError, model_validator

from datp.artifacts.names import ArtifactFile
from datp.config.models import DatpConfig, ExperimentStage, StrictModel
from datp.core.enums import CONTROLLED_POLICIES, ThresholdPolicy

_CONFIG_MODULE = "datp.conf"
_CONFIG_NAME = "config"


class ComposeError(Exception):
    """Error raised when config composition fails."""


class ComposeRequest(StrictModel):
    """Validated request to compose a DatpConfig for a stage/policy/seed triplet."""

    stage: ExperimentStage
    policy: ThresholdPolicy
    seed: int

    @model_validator(mode="before")
    @classmethod
    def preprocess(cls, data: Any) -> Any:
        """Lowercase stage and policy string values before validation."""
        if isinstance(data, dict):
            return {
                k: v.lower() if isinstance(v, str) and k in ("stage", "policy") else v
                for k, v in data.items()
            }
        return data

    @model_validator(mode="after")
    def validate_scientific_constraints(self) -> "ComposeRequest":
        """Validate that the policy is in the controlled set for the stage."""
        if self.policy not in frozenset(CONTROLLED_POLICIES):
            allowed = sorted(p.value for p in CONTROLLED_POLICIES)
            raise ValueError(
                f"{self.policy.value} invalid for {self.stage.value}. Expected: {allowed}."
            )
        return self


def _compose_hydra_config(*, overrides: list[str]) -> DictConfig:
    """Compose a Hydra DictConfig with the given overrides."""
    GlobalHydra.instance().clear()
    with initialize_config_module(config_module=_CONFIG_MODULE, version_base=None):
        return hydra_compose(
            config_name=_CONFIG_NAME, overrides=overrides, return_hydra_config=False
        )


def _validate_resolved_config(cfg: DictConfig) -> DatpConfig:
    """Resolve a Hydra DictConfig and validate against the DatpConfig model."""
    resolved = OmegaConf.to_container(cfg, resolve=True, enum_to_str=True)
    if not isinstance(resolved, dict):
        raise ComposeError(
            f"[config] Config must be a mapping. Got: {type(resolved).__name__}."
        )
    try:
        return DatpConfig.model_validate(resolved)
    except ValidationError as exc:
        raise ComposeError(str(exc)) from exc


def compose_config(
    *, stage: ExperimentStage | str, policy: ThresholdPolicy | str, seed: int
) -> DatpConfig:
    """Compose and validate a full DatpConfig for a stage/policy/seed triplet."""
    try:
        req = ComposeRequest.model_validate(
            {"stage": stage, "policy": policy, "seed": seed}
        )
    except ValidationError as exc:
        err_msg = exc.errors()[0].get("msg", str(exc))
        raise ComposeError(f"[config] Validation Error: {err_msg}") from exc

    overrides = [
        f"stage={req.stage.value}",
        f"policy={req.policy.value}",
        f"seed={req.seed}",
    ]
    cfg = _compose_hydra_config(overrides=overrides)
    return _validate_resolved_config(cfg)


def resolved_config_yaml(cfg: DatpConfig | DictConfig) -> str:
    """Serialize a resolved config to a YAML string."""
    payload = (
        OmegaConf.create(cfg.model_dump(mode="json"))
        if isinstance(cfg, DatpConfig)
        else cfg
    )
    return OmegaConf.to_yaml(payload, resolve=True)


def write_resolved_config(cfg: DatpConfig | DictConfig, output_dir: Path) -> Path:
    """Write the resolved config as YAML to the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    dest = output_dir / ArtifactFile.RESOLVED_CONFIG
    dest.write_text(resolved_config_yaml(cfg))
    return dest


BASE_CONFIG: DatpConfig = _validate_resolved_config(_compose_hydra_config(overrides=[]))


def compose_analysis_config() -> DatpConfig:
    """Return the base config for analysis purposes."""
    return BASE_CONFIG
