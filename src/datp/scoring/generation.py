# SPDX-License-Identifier: Proprietary
"""Score artifacts are shared across threshold policies."""

from __future__ import annotations

from datp.scoring.artifact_writing import (
    _score_record,
    score_clients,
    score_clients_impl,
    write_scoring_manifest_and_sentinel,
)
from datp.scoring.manifest import (
    ScoringColumnDtype,
    ScoringManifest,
    ScoringManifestContext,
    ScoringManifestCoverage,
    ScoringRecord,
)
from datp.scoring.manifest_validation import validate_scoring_manifest
from datp.scoring.model_loading import load_model_from_checkpoint
from datp.scoring.paths import resolve_within_base as _resolve_within_base
from datp.scoring.paths import score_output_path as _score_output_path
from datp.scoring.reconstruction import compute_reconstruction_errors

__all__ = [
    "ScoringColumnDtype",
    "ScoringManifest",
    "ScoringManifestContext",
    "ScoringManifestCoverage",
    "ScoringRecord",
    "_resolve_within_base",
    "_score_output_path",
    "_score_record",
    "compute_reconstruction_errors",
    "load_model_from_checkpoint",
    "score_clients",
    "score_clients_impl",
    "validate_scoring_manifest",
    "write_scoring_manifest_and_sentinel",
]
