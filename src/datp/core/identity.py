from __future__ import annotations

import enum
import math
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from datp.core.enums import (
    Baseline,
    PathToken,
    Regime,
)

if TYPE_CHECKING:
    from typing import TypeAlias

# ── Type aliases ───────────────────────────────────────────────────────────
# Shared training key: a TrainingCellId groups cells that share one FL encoder + score artifacts.
TrainingKey: "TypeAlias" = "TrainingCellId"


class AlphaLabel(enum.StrEnum):
    """Canonical alpha label for Dirichlet concentration regimes.

    ``IID`` represents α = ∞ (Dirichlet → uniform, no heterogeneity).
    ``PathToken.ALPHA_IID`` is the filesystem form: ``alpha_`` + this value.
    """

    IID = "iid"

    @property
    def display(self) -> str:
        """Uppercase display form: ``IID``."""
        return self.value.upper()

    @property
    def path_dir(self) -> str:
        """Filesystem directory segment: ``alpha_iid``."""
        return f"{PathToken.ALPHA_PREFIX}{self.value}"

    def __repr__(self) -> str:
        return f"AlphaLabel.{self.name}"


def alpha_label(alpha: float | None) -> str | None:
    if alpha is None:
        return None
    if math.isinf(alpha):
        return AlphaLabel.IID
    return f"{alpha:g}"


def alpha_from_label(label: str | None) -> float | None:
    """Convert serialized alpha label back to float. AlphaLabel.IID → math.inf; None → None."""
    if label is None:
        return None
    if label == AlphaLabel.IID:
        return math.inf
    return float(label)


def format_alpha_dir(alpha: float) -> str:
    label = alpha_label(alpha)
    if label == AlphaLabel.IID:
        return PathToken.ALPHA_IID
    return f"{PathToken.ALPHA_PREFIX}{label}"


def parse_alpha_dir(name: str) -> float | None:
    if not name.startswith(PathToken.ALPHA_PREFIX):
        return None
    if name == PathToken.ALPHA_IID:
        return math.inf
    return float(name.removeprefix(PathToken.ALPHA_PREFIX))


def seed_segment(seed: int) -> str:
    return f"{PathToken.SEED_PREFIX}{seed}"


def make_run_id(regime: Regime, seed: int, alpha: float | None = None) -> str:
    ts_ms = int(time.time() * 1000)
    parts = [regime.value, f"seed{seed}"]
    label = alpha_label(alpha)
    if label is not None:
        parts.append(f"alpha{label}")
    parts.append(str(ts_ms))
    return "_".join(parts)


@dataclass(frozen=True, slots=True)
class TrainingCellId:
    """Shared training identity for one FL encoder and score-artifact cell."""

    regime: Regime
    seed: int
    alpha: float | None

    def label(self) -> str:
        parts = [f"regime={self.regime}", f"seed={self.seed}"]
        lbl = alpha_label(self.alpha)
        if lbl is not None:
            parts.append(f"alpha={lbl}")
        return " ".join(parts)


@dataclass(frozen=True, slots=True)
class BaselineRunId:
    """Identity for one baseline evaluation run within a shared training cell."""

    cell: TrainingCellId
    baseline: Baseline

    @property
    def regime(self) -> Regime:
        return self.cell.regime

    @property
    def seed(self) -> int:
        return self.cell.seed

    @property
    def alpha(self) -> float | None:
        return self.cell.alpha

    def audit_id(self) -> str:
        suffix = f"_alpha{alpha_label(self.alpha)}" if self.alpha is not None else ""
        return f"{self.regime}_{self.baseline}_seed{self.seed}{suffix}"

    def shared_training_key(self) -> TrainingKey:
        return self.cell

    def label(self) -> str:
        parts = [
            f"regime={self.regime}",
            f"baseline={self.baseline}",
            f"seed={self.seed}",
        ]
        lbl = alpha_label(self.alpha)
        if lbl is not None:
            parts.append(f"alpha={lbl}")
        return " ".join(parts)

    def tracking_name(self) -> str:
        suffix = f"_alpha{alpha_label(self.alpha)}" if self.alpha is not None else ""
        return f"{self.regime.value}_{self.baseline.value}_seed{self.seed}{suffix}"
