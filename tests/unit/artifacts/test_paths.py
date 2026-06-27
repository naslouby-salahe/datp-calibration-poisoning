"""Tests verifying path layouts, result/checkpoint directory paths, and run ID formatting."""

from __future__ import annotations

import re
import time
from pathlib import Path

from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactDir
from datp.config.models import ExperimentStage
from datp.core.enums import ScoringStage, ThresholdPolicy
from datp.core.identity import (
    PolicyRunId,
    TrainingCellId,
    make_run_id,
)

_OUTPUTS = Path(ArtifactDir.OUTPUTS)
_STAGE = ExperimentStage.NBAIOT_MAIN


def _run(stage: ExperimentStage, policy: ThresholdPolicy, seed: int) -> PolicyRunId:
    """Helper to build PolicyRunId instances."""
    return PolicyRunId(
        cell=TrainingCellId(stage=stage, seed=seed),
        policy=policy,
    )


def _cell(stage: ExperimentStage, seed: int) -> TrainingCellId:
    """Helper to build TrainingCellId instances."""
    return TrainingCellId(stage=stage, seed=seed)


class TestMakeRunId:
    """Tests verifying make_run_id collision guarantees and formats."""

    def test_collision_proof_different_timestamps(self) -> None:
        """Verify that calling make_run_id with a delay produces different IDs."""
        id1 = make_run_id(_STAGE, seed=0)
        time.sleep(0.002)
        id2 = make_run_id(_STAGE, seed=0)
        assert id1 != id2

    def test_collision_proof_format(self) -> None:
        """Verify that generated run IDs start with stage/seed and end in a timestamp."""
        rid = make_run_id(_STAGE, seed=42)
        assert rid.startswith("nbaiot_main_seed42_")
        ts_part = rid.rsplit("_", 1)[-1]
        assert ts_part.isdigit()
        assert len(ts_part) >= 13


class TestCanonicalResultPath:
    """Tests verifying the results and logging layouts across policies."""

    def test_canonical_result_path_global_threshold(self) -> None:
        """Verify canonical result path for global threshold policy matches layout."""
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, stage=_STAGE)
            .policy_run(_run(_STAGE, ThresholdPolicy.GLOBAL_THRESHOLD, 0))
            .result_dir
        )
        assert p == Path("outputs/results/nbaiot_main/global_threshold/seed_0")

    def test_canonical_result_path_local_threshold(self) -> None:
        """Verify canonical result path for local threshold policy matches layout."""
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, stage=_STAGE)
            .policy_run(_run(_STAGE, ThresholdPolicy.LOCAL_THRESHOLD, 3))
            .result_dir
        )
        assert p == Path("outputs/results/nbaiot_main/local_threshold/seed_3")

    def test_canonical_result_path_custom_base(self, tmp_path: Path) -> None:
        """Verify that layouts respect custom base directory override paths."""
        p = (
            ArtifactLayout(base_dir=tmp_path / "out", stage=_STAGE)
            .policy_run(_run(_STAGE, ThresholdPolicy.CLUSTER_THRESHOLD, 1))
            .result_dir
        )
        assert p == tmp_path / "out/results/nbaiot_main/cluster_threshold/seed_1"

    def test_canonical_result_path_includes_cluster_threshold(self) -> None:
        """Verify that cluster threshold result paths include the policy name."""
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, stage=_STAGE)
            .policy_run(_run(_STAGE, ThresholdPolicy.CLUSTER_THRESHOLD, 5))
            .result_dir
        )
        assert "cluster_threshold" in p.parts

    def test_log_path(self) -> None:
        """Verify canonical log directory path matches the expected layout."""
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, stage=_STAGE)
            .policy_run(_run(_STAGE, ThresholdPolicy.GLOBAL_THRESHOLD, 0))
            .log_dir
        )
        assert p == Path("outputs/logs/nbaiot_main/global_threshold/seed_0")

    def test_log_path_includes_cluster_threshold(self) -> None:
        """Verify log directory paths for cluster threshold include the policy name."""
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, stage=_STAGE)
            .policy_run(_run(_STAGE, ThresholdPolicy.CLUSTER_THRESHOLD, 1))
            .log_dir
        )
        assert "cluster_threshold" in p.parts


class TestCheckpointPath:
    """Tests verifying checkpoint output directory layouts."""

    def test_checkpoint_path(self) -> None:
        """Verify canonical checkpoint directory matches the expected layout."""
        p = ArtifactLayout(base_dir=_OUTPUTS, stage=_STAGE).checkpoint_dir(
            _cell(_STAGE, 0)
        )
        assert p == Path("outputs/checkpoints/nbaiot_main/seed_0")

    def test_checkpoint_path_has_no_policy_segment(self) -> None:
        """Verify that checkpoint directories contain no policy names since they are shared."""
        p = ArtifactLayout(base_dir=_OUTPUTS, stage=_STAGE).checkpoint_dir(
            _cell(_STAGE, 0)
        )
        for part in p.parts:
            assert not re.match(
                r"^(global_threshold|local_threshold|cluster_threshold)$", part
            ), f"checkpoint path must not contain policy segment, got {part}"


class TestScorePath:
    """Tests verifying scores output directory layouts."""

    def test_score_path_base(self) -> None:
        """Verify the base score directory layout path matches expectations."""
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, stage=_STAGE)
            .score_cell(_cell(_STAGE, 0))
            .score_dir
        )
        assert p == Path("outputs/scores/nbaiot_main/seed_0")

    def test_score_path_with_stage(self) -> None:
        """Verify scoring stage subdirectory paths match layout definitions."""
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, stage=_STAGE)
            .score_cell(_cell(_STAGE, 0))
            .score_dir
            / ScoringStage.CAL.value
        )
        assert p == Path("outputs/scores/nbaiot_main/seed_0/cal")
