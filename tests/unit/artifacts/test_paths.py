from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

import re
import time
from pathlib import Path

from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactDir
from datp.config.stages import ExperimentStage
from datp.core.enums import ScoringStage
from datp.core.identity import (
    PolicyRunId,
    TrainingCellId,
    make_run_id,
)

_OUTPUTS = Path(ArtifactDir.OUTPUTS)
_STAGE = ExperimentStage.NBAIOT_MAIN


def _run(stage: ExperimentStage, policy: ThresholdPolicy, seed: int) -> PolicyRunId:
    return PolicyRunId(
        cell=TrainingCellId(stage=stage, seed=seed),
        policy=policy,
    )


def _cell(stage: ExperimentStage, seed: int) -> TrainingCellId:
    return TrainingCellId(stage=stage, seed=seed)


class TestMakeRunId:
    """Tests marked with ``collision_proof`` for gate-file -k matching."""

    def test_collision_proof_different_timestamps(self) -> None:
        id1 = make_run_id(_STAGE, seed=0)
        time.sleep(0.002)
        id2 = make_run_id(_STAGE, seed=0)
        assert id1 != id2

    def test_collision_proof_format(self) -> None:
        rid = make_run_id(_STAGE, seed=42)
        assert rid.startswith("nbaiot_main_seed42_")
        ts_part = rid.rsplit("_", 1)[-1]
        assert ts_part.isdigit()
        assert len(ts_part) >= 13


class TestCanonicalResultPath:
    """Tests marked with ``canonical_result_path`` for gate-file -k matching."""

    def test_canonical_result_path_global(self) -> None:
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, stage=_STAGE)
            .policy_run(_run(_STAGE, ThresholdPolicy.GLOBAL_THRESHOLD, 0))
            .result_dir
        )
        assert p == Path("outputs/results/nbaiot_main/global_threshold/seed_0")

    def test_canonical_result_path_local(self) -> None:
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, stage=_STAGE)
            .policy_run(_run(_STAGE, ThresholdPolicy.LOCAL_THRESHOLD, 3))
            .result_dir
        )
        assert p == Path("outputs/results/nbaiot_main/local_threshold/seed_3")

    def test_canonical_result_path_custom_base(self, tmp_path: Path) -> None:
        p = (
            ArtifactLayout(base_dir=tmp_path / "out", stage=_STAGE)
            .policy_run(_run(_STAGE, ThresholdPolicy.CLUSTER_THRESHOLD, 1))
            .result_dir
        )
        assert p == tmp_path / "out/results/nbaiot_main/cluster_threshold/seed_1"

    def test_canonical_result_path_includes_cluster_threshold(self) -> None:
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, stage=_STAGE)
            .policy_run(_run(_STAGE, ThresholdPolicy.CLUSTER_THRESHOLD, 5))
            .result_dir
        )
        assert "cluster_threshold" in p.parts

    def test_log_path(self) -> None:
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, stage=_STAGE)
            .policy_run(_run(_STAGE, ThresholdPolicy.GLOBAL_THRESHOLD, 0))
            .log_dir
        )
        assert p == Path("outputs/logs/nbaiot_main/global_threshold/seed_0")

    def test_log_path_includes_cluster_threshold(self) -> None:
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, stage=_STAGE)
            .policy_run(_run(_STAGE, ThresholdPolicy.CLUSTER_THRESHOLD, 1))
            .log_dir
        )
        assert "cluster_threshold" in p.parts


class TestCheckpointPath:
    def test_checkpoint_path(self) -> None:
        p = ArtifactLayout(base_dir=_OUTPUTS, stage=_STAGE).checkpoint_dir(
            _cell(_STAGE, 0)
        )
        assert p == Path("outputs/checkpoints/nbaiot_main/seed_0")

    def test_checkpoint_path_has_no_policy_segment(self) -> None:
        p = ArtifactLayout(base_dir=_OUTPUTS, stage=_STAGE).checkpoint_dir(
            _cell(_STAGE, 0)
        )
        for part in p.parts:
            assert not re.match(
                r"^(global_threshold|local_threshold|cluster_threshold)$", part
            ), f"checkpoint path must not contain policy segment, got {part}"


class TestScorePath:
    def test_score_path_base(self) -> None:
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, stage=_STAGE)
            .score_cell(_cell(_STAGE, 0))
            .score_dir
        )
        assert p == Path("outputs/scores/nbaiot_main/seed_0")

    def test_score_path_with_stage(self) -> None:
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, stage=_STAGE)
            .score_cell(_cell(_STAGE, 0))
            .score_dir
            / ScoringStage.CAL.value
        )
        assert p == Path("outputs/scores/nbaiot_main/seed_0/cal")
