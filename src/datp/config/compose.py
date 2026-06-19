"""Hydra-backed config composition with Pydantic validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, NoReturn

from hydra import compose as hydra_compose
from hydra import initialize_config_module
from hydra.core.global_hydra import GlobalHydra
from omegaconf import DictConfig, OmegaConf
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from datp.artifacts.names import ArtifactFile
from datp.config.models import DatpConfig
from datp.core.enums import (
    REGIME_BASELINES,
    Baseline,
    Regime,
)
from datp.core.errors import fmt

_CONFIG_MODULE = "datp.conf"
_CONFIG_NAME = "config"


class ComposeError(Exception):
    """Raised when config composition encounters invalid parameters."""


class ComposeRequest(BaseModel):
    """External request to compose an experiment config."""

    model_config = ConfigDict(frozen=True)
    regime: Regime
    baseline: Baseline
    seed: int
    alpha: float | None = None

    @model_validator(mode="before")
    @classmethod
    def preprocess(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Coerce to lowercase for consistent enum parsing.
            if "regime" in data and isinstance(data["regime"], str):
                data["regime"] = data["regime"].lower()
            if "baseline" in data and isinstance(data["baseline"], str):
                data["baseline"] = data["baseline"].lower()
        return data

    @model_validator(mode="after")
    def validate_scientific_constraints(self) -> "ComposeRequest":
        if self.regime == Regime.C and self.alpha is None:
            raise ValueError(
                fmt("config", "alpha is required for regime c", "a float", "None")
            )
        valid_baselines = REGIME_BASELINES.get(self.regime, frozenset())
        if self.baseline not in valid_baselines:
            allowed = sorted(b.value for b in valid_baselines)
            raise ValueError(
                fmt(
                    "config",
                    f"{self.baseline.value} is not valid for regime {self.regime.value}",
                    f"one of {allowed}",
                    self.baseline.value,
                )
            )
        return self


def _raise_enum_compose_error(
    err: Any,
    regime_input: "Regime | str",
    baseline_input: "Baseline | str",
    exc: "ValidationError",
) -> None:
    if "regime" in err["loc"]:
        valid_regimes = sorted(r.value for r in Regime)
        raise ComposeError(
            fmt(
                "config",
                "Invalid regime",
                f"one of {valid_regimes}",
                repr(regime_input),
            )
        ) from exc
    if "baseline" in err["loc"]:
        valid_baselines = sorted(b.value for b in Baseline)
        raise ComposeError(
            fmt(
                "config",
                "Invalid baseline",
                f"one of {valid_baselines}",
                repr(baseline_input),
            )
        ) from exc


def _raise_compose_error_from_validation(
    exc: "ValidationError",
    regime_input: "Regime | str",
    baseline_input: "Baseline | str",
) -> "NoReturn":
    """Inspect Pydantic ValidationError and raise the appropriate ComposeError."""
    for err in exc.errors():
        if err["type"] == "enum":
            _raise_enum_compose_error(err, regime_input, baseline_input, exc)
        if err["type"] == "value_error":
            raise ComposeError(err["msg"]) from exc
    raise ComposeError(str(exc)) from exc


def _normalize_request(
    *,
    regime: Regime | str,
    baseline: Baseline | str,
    seed: int,
    alpha: float | None,
) -> ComposeRequest:
    try:
        return ComposeRequest.model_validate(
            {"regime": regime, "baseline": baseline, "seed": seed, "alpha": alpha}
        )
    except ValidationError as exc:
        _raise_compose_error_from_validation(exc, regime, baseline)


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
        return DatpConfig.model_validate(resolved, context={"hydra_config": True})
    except ValidationError as exc:
        raise ComposeError(str(exc)) from exc


def _build_overrides(
    *,
    regime: Regime,
    baseline: Baseline,
    seed: int,
    alpha: float | None,
) -> list[str]:
    overrides = [
        f"regime={regime}",
        f"baseline={baseline}",
        f"seed={seed}",
    ]
    if alpha is not None:
        overrides.append(f"alpha={alpha}")
    return overrides


def _compose_and_validate(
    *,
    regime: Regime | str,
    baseline: Baseline | str,
    seed: int,
    alpha: float | None,
) -> tuple[DictConfig, DatpConfig]:
    req = _normalize_request(
        regime=regime,
        baseline=baseline,
        seed=seed,
        alpha=alpha,
    )
    cfg = _compose_hydra_config(
        overrides=_build_overrides(
            regime=req.regime,
            baseline=req.baseline,
            seed=req.seed,
            alpha=req.alpha,
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
    regime: Regime | str,
    baseline: Baseline | str,
    seed: int,
    alpha: float | None = None,
) -> DatpConfig:
    """Build a validated runtime config from Hydra-composed defaults + overrides.

    Accepts ``Regime``/``Baseline`` enum values or string representations
    (case-insensitive) at the boundary. Strings are normalized to enums
    internally via :class:`ComposeRequest`.
    """
    _, cfg = _compose_and_validate(
        regime=regime,
        baseline=baseline,
        seed=seed,
        alpha=alpha,
    )
    return cfg


BASE_CONFIG: DatpConfig = _validate_resolved_config(_compose_hydra_config(overrides=[]))


def compose_analysis_config() -> DatpConfig:
    """Return the base config for post-hoc analysis modules.

    Analysis functions operate over all verified cells and do not have a single
    regime, baseline, or seed. This function returns scalar threshold/analysis
    parameters (q, n_min, b4_random_state, cal_sweep_n_cal, …) from canonical
    defaults without attaching misleading experiment context.
    """
    return BASE_CONFIG
