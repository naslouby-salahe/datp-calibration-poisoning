from __future__ import annotations

from pathlib import Path

import pytest

from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactDir
from datp.core.enums import (
    Baseline,
    Regime,
)
from datp.core.identity import BaselineRunId, TrainingCellId

_OUTPUTS = Path(ArtifactDir.OUTPUTS)


def _run(regime: Regime, baseline: Baseline, seed: int, alpha: float | None = None):
    return BaselineRunId(
        cell=TrainingCellId(regime=regime, seed=seed, alpha=alpha),
        baseline=baseline,
    )


def _score_cell(regime: Regime, seed: int, alpha: float | None = None):
    return TrainingCellId(regime=regime, seed=seed, alpha=alpha)


@pytest.mark.integration
def test_canonical_path() -> None:
    layout_a = ArtifactLayout(base_dir=_OUTPUTS, regime=Regime.A)
    layout_c = ArtifactLayout(base_dir=_OUTPUTS, regime=Regime.C)

    rp = layout_a.baseline_run(_run(Regime.A, Baseline.B1, 0)).result_dir
    parts = rp.parts
    assert "b1" in parts, f"result_dir should contain baseline 'b1': {rp}"
    assert parts[-2] == "b1"  # baseline segment
    assert parts[-3] == "a"  # regime segment
    assert parts[-1].startswith("seed_")

    rp_alpha = layout_c.baseline_run(_run(Regime.C, Baseline.B2, 1, 0.5)).result_dir
    parts_a = rp_alpha.parts
    assert "b2" in parts_a
    assert "alpha_0.5" in parts_a

    sp = layout_a.score_cell(_score_cell(Regime.A, 0)).score_dir
    assert "b1" not in sp.parts and "b2" not in sp.parts

    cp = layout_a.checkpoint_dir(TrainingCellId(regime=Regime.A, seed=0, alpha=None))
    assert "b1" not in cp.parts and "b2" not in cp.parts

    rp_check = layout_a.baseline_run(_run(Regime.A, Baseline.B1, 42)).result_dir
    expected_suffix = "results/a/b1/seed_42"
    assert str(rp_check).endswith(expected_suffix), (
        f"Expected path ending with '{expected_suffix}', got '{rp_check}'"
    )

    sp_check = layout_a.score_cell(_score_cell(Regime.A, 42)).score_dir
    expected_score_suffix = "scores/a/seed_42"
    assert str(sp_check).endswith(expected_score_suffix), (
        f"Expected path ending with '{expected_score_suffix}', got '{sp_check}'"
    )

    cp_check = layout_a.checkpoint_dir(
        TrainingCellId(regime=Regime.A, seed=42, alpha=None)
    )
    expected_ckpt_suffix = "checkpoints/a/seed_42"
    assert str(cp_check).endswith(expected_ckpt_suffix), (
        f"Expected path ending with '{expected_ckpt_suffix}', got '{cp_check}'"
    )
