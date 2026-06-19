from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from datp.artifacts.names import ArtifactFile
from datp.checkpointing.enums import ConvergenceStatus, ConvergenceSummaryKey


@dataclasses.dataclass(frozen=True, slots=True)
class ConvergencePayload:
    """Parsed convergence information for a single training checkpoint."""

    convergence_round: int | None
    convergence_criterion_value: float | None
    convergence_status: ConvergenceStatus
    curve_path: str | None


def convergence_payload(checkpoint: Path) -> ConvergencePayload:
    ckpt_dir = checkpoint.parent
    summary_path = ckpt_dir / ArtifactFile.CONVERGENCE_SUMMARY
    curve_path = ckpt_dir / ArtifactFile.CONVERGENCE_CURVE
    if not summary_path.exists():
        status = (
            ConvergenceStatus.BLOCKED_PENDING_RUN
            if checkpoint.exists()
            else ConvergenceStatus.MISSING_CHECKPOINT
        )
        return ConvergencePayload(
            convergence_round=None,
            convergence_criterion_value=None,
            convergence_status=status,
            curve_path=None,
        )
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    raw_status = payload[ConvergenceSummaryKey.CONVERGENCE_STATUS]
    try:
        status = ConvergenceStatus(raw_status)
    except ValueError:
        status = ConvergenceStatus.UNKNOWN
    return ConvergencePayload(
        convergence_round=payload[ConvergenceSummaryKey.CONVERGENCE_ROUND],
        convergence_criterion_value=payload[
            ConvergenceSummaryKey.CONVERGENCE_CRITERION
        ],
        convergence_status=status,
        curve_path=str(curve_path) if curve_path.exists() else None,
    )
