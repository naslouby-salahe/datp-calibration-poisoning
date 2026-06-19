from __future__ import annotations

import json
from pathlib import Path

import pytest

from datp.artifacts.names import ArtifactFile
from datp.checkpointing.enums import ConvergenceStatus, ConvergenceSummaryKey
from datp.validation.convergence import ConvergencePayload, convergence_payload


def _write_summary(
    ckpt_dir: Path,
    *,
    convergence_round: int | None = 5,
    convergence_criterion_value: float | None = 0.01,
    convergence_status: str = "converged",
) -> Path:
    summary = {
        ConvergenceSummaryKey.ROUNDS_INITIAL: 5,
        ConvergenceSummaryKey.ROUNDS_MAX: 100,
        ConvergenceSummaryKey.RELATIVE_THRESHOLD: 0.03,
        ConvergenceSummaryKey.WINDOW: 4,
        ConvergenceSummaryKey.ACTUAL_ROUNDS: 20,
        ConvergenceSummaryKey.CONVERGENCE_ROUND: convergence_round,
        ConvergenceSummaryKey.CONVERGENCE_CRITERION: convergence_criterion_value,
        ConvergenceSummaryKey.CONVERGENCE_STATUS: convergence_status,
        ConvergenceSummaryKey.WEIGHTED_LOSS: [1.0, 0.8, 0.6, 0.5],
    }
    path = ckpt_dir / ArtifactFile.CONVERGENCE_SUMMARY
    path.write_text(json.dumps(summary), encoding="utf-8")
    return path


def _write_curve(ckpt_dir: Path) -> Path:
    path = ckpt_dir / ArtifactFile.CONVERGENCE_CURVE
    path.write_text("round,fedavg_weighted_benign_val_loss\n1,1.0\n", encoding="utf-8")
    return path


class TestConvergencePayload:
    def test_construction(self, tmp_path: Path) -> None:
        curve_path = str(tmp_path / "curve.csv")
        p = ConvergencePayload(
            convergence_round=5,
            convergence_criterion_value=0.01,
            convergence_status=ConvergenceStatus.CONVERGED,
            curve_path=curve_path,
        )
        assert p.convergence_round == 5
        assert p.convergence_criterion_value == pytest.approx(0.01)
        assert p.convergence_status == ConvergenceStatus.CONVERGED
        assert p.curve_path == curve_path

    def test_construction_with_none_round_and_value(self) -> None:
        p = ConvergencePayload(
            convergence_round=None,
            convergence_criterion_value=None,
            convergence_status=ConvergenceStatus.BLOCKED_PENDING_RUN,
            curve_path=None,
        )
        assert p.convergence_round is None
        assert p.convergence_criterion_value is None
        assert p.convergence_status == ConvergenceStatus.BLOCKED_PENDING_RUN
        assert p.curve_path is None

    def test_is_frozen(self) -> None:
        p = ConvergencePayload(
            convergence_round=5,
            convergence_criterion_value=0.01,
            convergence_status=ConvergenceStatus.CONVERGED,
            curve_path=None,
        )
        with pytest.raises(Exception):
            p.convergence_round = 10  # type: ignore[misc]


class TestConvergencePayloadMissingCheckpoint:
    def test_no_checkpoint_no_summary(self, tmp_path: Path) -> None:
        checkpoint = tmp_path / "nonexistent" / ArtifactFile.MODEL_CHECKPOINT
        result = convergence_payload(checkpoint)
        assert result.convergence_round is None
        assert result.convergence_criterion_value is None
        assert result.convergence_status == ConvergenceStatus.MISSING_CHECKPOINT
        assert result.curve_path is None

    def test_checkpoint_exists_no_summary(self, tmp_path: Path) -> None:
        ckpt_dir = tmp_path / "checkpoints/a/seed_0"
        ckpt_dir.mkdir(parents=True)
        checkpoint = ckpt_dir / ArtifactFile.MODEL_CHECKPOINT
        checkpoint.write_bytes(b"model")
        result = convergence_payload(checkpoint)
        assert result.convergence_round is None
        assert result.convergence_criterion_value is None
        assert result.convergence_status == ConvergenceStatus.BLOCKED_PENDING_RUN
        assert result.curve_path is None

    def test_checkpoint_exists_no_summary_no_curve(self, tmp_path: Path) -> None:
        ckpt_dir = tmp_path / "checkpoints/a/seed_0"
        ckpt_dir.mkdir(parents=True)
        checkpoint = ckpt_dir / ArtifactFile.MODEL_CHECKPOINT
        checkpoint.write_bytes(b"model")
        # No curve file
        result = convergence_payload(checkpoint)
        assert result.curve_path is None


class TestConvergencePayloadWithSummary:
    def test_converged_with_curve(self, tmp_path: Path) -> None:
        ckpt_dir = tmp_path / "checkpoints/a/seed_0"
        ckpt_dir.mkdir(parents=True)
        checkpoint = ckpt_dir / ArtifactFile.MODEL_CHECKPOINT
        checkpoint.write_bytes(b"model")
        _write_summary(ckpt_dir, convergence_round=8, convergence_criterion_value=0.02)
        _write_curve(ckpt_dir)

        result = convergence_payload(checkpoint)
        assert result.convergence_round == 8
        assert result.convergence_criterion_value == pytest.approx(0.02)
        assert result.convergence_status == ConvergenceStatus.CONVERGED
        assert result.curve_path is not None
        assert str(ckpt_dir / ArtifactFile.CONVERGENCE_CURVE) == result.curve_path

    def test_not_converged_no_curve(self, tmp_path: Path) -> None:
        ckpt_dir = tmp_path / "checkpoints/a/seed_0"
        ckpt_dir.mkdir(parents=True)
        checkpoint = ckpt_dir / ArtifactFile.MODEL_CHECKPOINT
        checkpoint.write_bytes(b"model")
        _write_summary(
            ckpt_dir,
            convergence_round=None,
            convergence_criterion_value=None,
            convergence_status="not_converged",
        )
        # No curve file

        result = convergence_payload(checkpoint)
        assert result.convergence_round is None
        assert result.convergence_criterion_value is None
        assert result.convergence_status == ConvergenceStatus.NOT_CONVERGED
        assert result.curve_path is None

    def test_unknown_status_from_json(self, tmp_path: Path) -> None:
        ckpt_dir = tmp_path / "checkpoints/a/seed_0"
        ckpt_dir.mkdir(parents=True)
        checkpoint = ckpt_dir / ArtifactFile.MODEL_CHECKPOINT
        checkpoint.write_bytes(b"model")
        _write_summary(
            ckpt_dir,
            convergence_round=None,
            convergence_criterion_value=None,
            convergence_status="bogus_status_xyz",
        )

        result = convergence_payload(checkpoint)
        assert result.convergence_status == ConvergenceStatus.UNKNOWN

    def test_curve_present_but_summary_absent_is_blocked(self, tmp_path: Path) -> None:
        """If curve.csv exists but summary.json does not, we still get BLOCKED_PENDING_RUN."""
        ckpt_dir = tmp_path / "checkpoints/a/seed_0"
        ckpt_dir.mkdir(parents=True)
        checkpoint = ckpt_dir / ArtifactFile.MODEL_CHECKPOINT
        checkpoint.write_bytes(b"model")
        _write_curve(ckpt_dir)
        # No summary

        result = convergence_payload(checkpoint)
        assert result.convergence_status == ConvergenceStatus.BLOCKED_PENDING_RUN
        assert result.curve_path is None  # curve_path only set when summary exists
