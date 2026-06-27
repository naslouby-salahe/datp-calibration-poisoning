"""Existence checks for precomputed results with staleness validation."""

from __future__ import annotations

import json
from contextlib import suppress
from pathlib import Path

from datp.artifacts.layout import ArtifactLayout
from datp.config.models import ExperimentStage
from datp.core.enums import PayloadKey, ThresholdPolicy
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.evaluation.artifact_validation import validate_metrics_payload


def results_exist(
    policy: ThresholdPolicy,
    stage: ExperimentStage,
    seed: int,
    *,
    base_dir: Path,
) -> bool:
    """Return True only when metrics.json is valid and non-stale."""
    run = PolicyRunId(cell=TrainingCellId(stage=stage, seed=seed), policy=policy)
    path = ArtifactLayout(base_dir=base_dir, stage=stage).policy_run(run).metrics_path

    if not path.is_file() or path.stat().st_size == 0:
        return False

    with suppress(json.JSONDecodeError, KeyError, TypeError, AttributeError):
        data = json.loads(path.read_text())
        per_client = data[PayloadKey.PER_CLIENT]
        first = next(
            iter(per_client.values() if isinstance(per_client, dict) else per_client),
            None,
        )

        return not validate_metrics_payload(data, module="artifacts.results") and (
            first is None or PayloadKey.CONFUSION_MATRIX in first
        )

    return False
