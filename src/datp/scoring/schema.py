from __future__ import annotations

import enum

SCORE_COLUMN: str = "reconstruction_error"
SCORING_MANIFEST_SCHEMA_VERSION: str = "1"
SCORING_MANIFEST_NOT_PROVIDED: str = "NOT_PROVIDED"


class ScoringManifestStatus(enum.StrEnum):
    COMPLETE = "complete"
