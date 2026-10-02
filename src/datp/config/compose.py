from __future__ import annotations

from datp.types import (
    JsonValue,
    NarrativeText,
    RandomSeed,
)


from pathlib import Path
from enum import StrEnum

import datp.conf as hydra_config_package
from hydra import compose as hydra_compose
from hydra import initialize_config_module
from hydra.core.global_hydra import GlobalHydra
from omegaconf import DictConfig, OmegaConf
from pydantic import ValidationError, model_validator

from datp.artifacts.names import ArtifactFile
from datp.config.models import DatpConfig, ExperimentStage, StrictModel
from datp.core.enums import CONTROLLED_POLICIES, ThresholdPolicy

_CONFIG_MODULE = hydra_config_package.__name__
_CONFIG_NAME = "config"


class ComposeRequestField(StrEnum):

    STAGE = "stage"
    POLICY = "policy"
    SEED = "seed"


class ComposeError(Exception):
    pass


class ComposeRequest(StrictModel):

    stage: ExperimentStage
    policy: ThresholdPolicy
    seed: RandomSeed

    @model_validator(mode="before")
    @classmethod
    def preprocess(cls, data: JsonValue) -> JsonValue:
        if isinstance(data, dict):
            return {
                k: v.lower()
                if isinstance(v, str)
                and k in (ComposeRequestField.STAGE, ComposeRequestField.POLICY)
                else v
                for k, v in data.items()
            }
        return data

    @model_validator(mode="after")
    def validate_scientific_constraints(self) -> "ComposeRequest":
        if self.policy not in frozenset(CONTROLLED_POLICIES):
            allowed = sorted(p for p in CONTROLLED_POLICIES)
            raise ValueError(
                f"{self.policy} invalid for {self.stage}. Expected: {allowed}."
            )
        return self


def _compose_hydra_config(*, overrides: list[NarrativeText]) -> DictConfig:
    GlobalHydra.instance().clear()
    with initialize_config_module(config_module=_CONFIG_MODULE, version_base=None):
        return hydra_compose(
            config_name=_CONFIG_NAME, overrides=overrides, return_hydra_config=False
        )


def _validate_resolved_config(cfg: DictConfig) -> DatpConfig:
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
    *, stage: ExperimentStage, policy: ThresholdPolicy, seed: RandomSeed
) -> DatpConfig:
    try:
        req = ComposeRequest.model_validate(
            {
                ComposeRequestField.STAGE: stage,
                ComposeRequestField.POLICY: policy,
                ComposeRequestField.SEED: seed,
            }
        )
    except ValidationError as exc:
        err_msg = exc.errors()[0].get("msg", str(exc))
        raise ComposeError(f"[config] Validation Error: {err_msg}") from exc

    overrides = [
        f"stage={req.stage}",
        f"policy={req.policy}",
        f"seed={req.seed}",
    ]
    cfg = _compose_hydra_config(overrides=overrides)
    return _validate_resolved_config(cfg)


def resolved_config_yaml(cfg: DatpConfig | DictConfig) -> NarrativeText:
    payload = (
        OmegaConf.create(cfg.model_dump(mode="json"))
        if isinstance(cfg, DatpConfig)
        else cfg
    )
    return OmegaConf.to_yaml(payload, resolve=True)


def write_resolved_config(cfg: DatpConfig | DictConfig, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    dest = output_dir / ArtifactFile.RESOLVED_CONFIG
    dest.write_text(resolved_config_yaml(cfg))
    return dest


BASE_CONFIG: DatpConfig = _validate_resolved_config(_compose_hydra_config(overrides=[]))


def compose_analysis_config() -> DatpConfig:
    return BASE_CONFIG
