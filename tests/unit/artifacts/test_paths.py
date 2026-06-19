from __future__ import annotations

import re
import time
from pathlib import Path

from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactDir
from datp.core.enums import (
    Baseline,
    Regime,
    ScoringStage,
)
from datp.core.identity import (
    BaselineRunId,
    TrainingCellId,
    make_run_id,
)

_OUTPUTS = Path(ArtifactDir.OUTPUTS)


def _run(regime: Regime, baseline: Baseline, seed: int, alpha: float | None = None):
    return BaselineRunId(
        cell=TrainingCellId(regime=regime, seed=seed, alpha=alpha),
        baseline=baseline,
    )


def _cell(regime: Regime, seed: int, alpha: float | None = None):
    return TrainingCellId(regime=regime, seed=seed, alpha=alpha)


def _score_cell(regime: Regime, seed: int, alpha: float | None = None):
    return _cell(regime, seed, alpha)


class TestMakeRunId:
    """Tests marked with ``collision_proof`` for gate-file -k matching."""

    def test_collision_proof_different_timestamps(self) -> None:
        id1 = make_run_id(Regime.A, seed=0)
        time.sleep(0.002)
        id2 = make_run_id(Regime.A, seed=0)
        assert id1 != id2

    def test_collision_proof_format_without_alpha(self) -> None:
        rid = make_run_id(Regime.A, seed=42)
        assert rid.startswith("a_seed42_")
        ts_part = rid.split("_")[-1]
        assert ts_part.isdigit()
        assert len(ts_part) >= 13 # ms since epoch

    def test_collision_proof_format_with_alpha(self) -> None:
        rid = make_run_id(Regime.C, seed=7, alpha=0.5)
        assert "c_seed7_alpha0.5_" in rid
        ts_part = rid.rsplit("_", 1)[-1]
        assert ts_part.isdigit()

    def test_collision_proof_no_flat_file_pattern(self) -> None:
        rid = make_run_id(Regime.A, seed=0)
        assert not re.match(r"^regime_[a-c]_b\d_seed\d+\.json$", rid)


class TestCanonicalResultPath:
    """Tests marked with ``canonical_result_path`` for gate-file -k matching."""

    def test_canonical_result_path_without_alpha(self) -> None:
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, regime=Regime.A)
            .baseline_run(_run(Regime.A, Baseline.B1, 0))
            .result_dir
        )
        assert p == Path("outputs/results/a/b1/seed_0")

    def test_canonical_result_path_with_alpha(self) -> None:
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, regime=Regime.C)
            .baseline_run(_run(Regime.C, Baseline.B2, 3, 0.1))
            .result_dir
        )
        assert p == Path("outputs/results/c/b2/seed_3/alpha_0.1")

    def test_canonical_result_path_custom_base(self, tmp_path: Path) -> None:
        p = (
            ArtifactLayout(base_dir=tmp_path / "out", regime=Regime.B)
            .baseline_run(_run(Regime.B, Baseline.B4, 1))
            .result_dir
        )
        assert p == tmp_path / "out/results/b/b4/seed_1"

    def test_canonical_result_path_includes_baseline(self) -> None:
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, regime=Regime.A)
            .baseline_run(_run(Regime.A, Baseline.B3, 5))
            .result_dir
        )
        assert "b3" in p.parts

    def test_log_path_without_alpha(self) -> None:
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, regime=Regime.A)
            .baseline_run(_run(Regime.A, Baseline.B1, 0))
            .log_dir
        )
        assert p == Path("outputs/logs/a/b1/seed_0")

    def test_log_path_with_alpha(self) -> None:
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, regime=Regime.C)
            .baseline_run(_run(Regime.C, Baseline.B2, 3, 0.5))
            .log_dir
        )
        assert p == Path("outputs/logs/c/b2/seed_3/alpha_0.5")

    def test_log_path_includes_baseline(self) -> None:
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, regime=Regime.B)
            .baseline_run(_run(Regime.B, Baseline.B4, 1))
            .log_dir
        )
        assert "b4" in p.parts


class TestCheckpointPath:
    def test_checkpoint_path_without_alpha(self) -> None:
        p = ArtifactLayout(base_dir=_OUTPUTS, regime=Regime.A).checkpoint_dir(
            _cell(Regime.A, 0)
        )
        assert p == Path("outputs/checkpoints/a/seed_0")

    def test_checkpoint_path_with_alpha(self) -> None:
        p = ArtifactLayout(base_dir=_OUTPUTS, regime=Regime.C).checkpoint_dir(
            _cell(Regime.C, 2, 0.3)
        )
        assert p == Path("outputs/checkpoints/c/seed_2/alpha_0.3")

    def test_checkpoint_path_has_no_baseline_segment(self) -> None:
        p = ArtifactLayout(base_dir=_OUTPUTS, regime=Regime.A).checkpoint_dir(
            _cell(Regime.A, 0)
        )
        for part in p.parts:
            assert not re.match(r"^b\d$", part), (
                f"checkpoint path must not contain baseline segment, got {part}"
            )


class TestScorePath:
    def test_score_path_base(self) -> None:
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, regime=Regime.A)
            .score_cell(_score_cell(Regime.A, 0))
            .score_dir
        )
        assert p == Path("outputs/scores/a/seed_0")

    def test_score_path_with_stage(self) -> None:
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, regime=Regime.A)
            .score_cell(_score_cell(Regime.A, 0))
            .score_dir
            / ScoringStage.CAL.value
        )
        assert p == Path("outputs/scores/a/seed_0/cal")



    def test_score_path_with_alpha(self) -> None:
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, regime=Regime.C)
            .score_cell(_score_cell(Regime.C, 1, 0.5))
            .score_dir
            / ScoringStage.TEST_BENIGN.value
        )
        assert p == Path("outputs/scores/c/seed_1/alpha_0.5/test_benign")


