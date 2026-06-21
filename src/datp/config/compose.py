"""Hydra-backed config composition with Pydantic validation."""

from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

from pathlib import Path
from typing import Any, NoReturn

from hydra import compose as hydra_compose
from hydra import initialize_config_module
from hydra.core.global_hydra import GlobalHydra
from omegaconf import DictConfig, OmegaConf
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator
from pydantic_core import ErrorDetails

from datp.artifacts.names import ArtifactFile
from datp.config.models import DatpConfig
from datp.config.stages import ExperimentStage
from datp.core.enums import (
    CONTROLLED_POLICIES,
)
from datp.core.errors import fmt

_CONFIG_MODULE = "datp.conf"
_CONFIG_NAME = "config"


class ComposeError(Exception):
    """Raised when config composition encounters invalid parameters."""


class ComposeRequest(BaseModel):
    """External request to compose an experiment config."""

    model_config = ConfigDict(frozen=True)
    stage: ExperimentStage
    policy: ThresholdPolicy
    seed: int

    @model_validator(mode="before")
    @classmethod
    def preprocess(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Coerce to lowercase for consistent enum parsing.
            if "stage" in data and isinstance(data["stage"], str):
                data["stage"] = data["stage"].lower()
            if "policy" in data and isinstance(data["policy"], str):
                data["policy"] = data["policy"].lower()
        return data

    @model_validator(mode="after")
    def validate_scientific_constraints(self) -> "ComposeRequest":
        valid_policies = frozenset(CONTROLLED_POLICIES)
        if self.policy not in valid_policies:
            allowed = sorted(p.value for p in valid_policies)
            raise ValueError(
                fmt(
                    "config",
                    f"{self.policy.value} is not valid for stage {self.stage.value}",
                    f"one of {allowed}",
                    self.policy.value,
                )
            )
        return self


def _raise_enum_compose_error(
    err: ErrorDetails,
    stage_input: object,
    policy_input: object,
    exc: ValidationError,
) -> None:
    if "stage" in err["loc"]:
        valid_stages = sorted(s.value for s in ExperimentStage)
        raise ComposeError(
            fmt(
                "config",
                "Invalid stage",
                f"one of {valid_stages}",
                repr(stage_input),
            )
        ) from exc
    if "policy" in err["loc"]:
        valid_policies = sorted(p.value for p in ThresholdPolicy)
        raise ComposeError(
            fmt(
                "config",
                "Invalid policy",
                f"one of {valid_policies}",
                repr(policy_input),
            )
        ) from exc


def _raise_compose_error_from_validation(
    exc: ValidationError,
    stage_input: object,
    policy_input: object,
) -> NoReturn:
    """Inspect Pydantic ValidationError and raise the appropriate ComposeError."""
    for err in exc.errors():
        if err["type"] == "enum":
            _raise_enum_compose_error(err, stage_input, policy_input, exc)
        if err["type"] == "value_error":
            raise ComposeError(err["msg"]) from exc
    raise ComposeError(str(exc)) from exc


def _normalize_request(
    *,
    stage: ExperimentStage | str,
    policy: ThresholdPolicy | str,
    seed: int,
) -> ComposeRequest:
    try:
        return ComposeRequest.model_validate(
            {"stage": stage, "policy": policy, "seed": seed}
        )
    except ValidationError as exc:
        _raise_compose_error_from_validation(exc, stage, policy)


def _compose_hydra_config(*, overrides: list[str]) -> DictConfig:
    GlobalHydra.instance().clear()
    with initialize_config_module(config_module=_CONFIG_MODULE, version_base=None):
        return hydra_compose(
            config_name=_CONFIG_NAME,
            overrides=overrides,
            return_hydra_config=False,
        )


def _validate_resolved_config(cfg: DictConfig) -> DatpConfig:
    resolved = OmegaConf.to_container(cfg, resolve=True, enum_to_str=True)
    if not isinstance(resolved, dict):
        raise ComposeError(
            fmt(
                "config",
                "Resolved config must be a mapping",
                "dict",
                type(resolved).__name__,
            )
        )
    try:
        return DatpConfig.model_validate(resolved)
    except ValidationError as exc:
        raise ComposeError(str(exc)) from exc


def _build_overrides(
    *,
    stage: ExperimentStage,
    policy: ThresholdPolicy,
    seed: int,
) -> list[str]:
    overrides = [
        f"stage={stage}",
        f"policy={policy}",
        f"seed={seed}",
    ]
    return overrides


def _compose_and_validate(req: ComposeRequest) -> tuple[DictConfig, DatpConfig]:
    cfg = _compose_hydra_config(
        overrides=_build_overrides(
            stage=req.stage,
            policy=req.policy,
            seed=req.seed,
        )
    )
    return cfg, _validate_resolved_config(cfg)


def resolved_config_yaml(cfg: DatpConfig | DictConfig) -> str:
    """Render a resolved config model into canonical YAML text."""
    payload = cfg
    if isinstance(cfg, DatpConfig):
        payload = OmegaConf.create(cfg.model_dump(mode="json"))
    return OmegaConf.to_yaml(payload, resolve=True)


def write_resolved_config(
    cfg: DatpConfig | DictConfig,
    output_dir: Path,
) -> Path:
    """Persist ``resolved_config.yaml`` into ``output_dir``."""
    output_dir.mkdir(parents=True, exist_ok=True)
    dest = output_dir / ArtifactFile.RESOLVED_CONFIG
    dest.write_text(resolved_config_yaml(cfg), encoding="utf-8")
    return dest


def compose_config(
    *,
    stage: ExperimentStage | str,
    policy: ThresholdPolicy | str,
    seed: int,
) -> DatpConfig:
    """Build a validated runtime config from Hydra-composed defaults + overrides.

    Accepts ``ExperimentStage``/``ThresholdPolicy`` enum values or string
    representations (case-insensitive) at the public boundary. Strings are
    normalized to enums via :class:`ComposeRequest` before internal processing.
    """
    req = _normalize_request(stage=stage, policy=policy, seed=seed)
    _, cfg = _compose_and_validate(req)
    return cfg


BASE_CONFIG: DatpConfig = _validate_resolved_config(_compose_hydra_config(overrides=[]))


def compose_analysis_config() -> DatpConfig:
    """Return the base config for post-hoc analysis modules.

    Analysis functions operate over all verified cells and do not have a single
    stage or seed. This function returns scalar threshold/analysis parameters
    (q, n_min, cluster_random_state, cal_sweep_n_cal, …) from canonical
    defaults without attaching misleading experiment context.
    """
    return BASE_CONFIG
