from __future__ import annotations

from pathlib import Path

from datp.artifacts.names import PathToken
from datp.core.enums import ScoringStage
from datp.core.errors import fmt

_MODULE = "scoring.paths"


def resolve_within_base(base: Path, candidate: Path) -> Path:
    resolved_base = base.resolve()
    resolved_candidate = candidate.resolve()
    if not resolved_candidate.is_relative_to(resolved_base):
        raise ValueError(
            fmt(
                _MODULE,
                "Path escapes scoring directory",
                str(resolved_base),
                str(resolved_candidate),
            )
        )
    return resolved_candidate


def score_output_path(score_base: Path, stage: ScoringStage, client_id: str) -> Path:
    filename = f"{client_id}{PathToken.PARQUET_EXT}"
    if Path(filename).name != filename:
        raise ValueError(
            fmt(
                _MODULE,
                "Invalid client id for score artifact path",
                "client id without path separators",
                client_id,
            )
        )
    out_path = Path(score_base) / stage.value / filename
    resolve_within_base(Path(score_base), out_path)
    return out_path
