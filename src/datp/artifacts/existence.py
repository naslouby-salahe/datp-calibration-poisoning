from __future__ import annotations
from datp.core.enums import ThresholdPolicy

import json
from pathlib import Path

from datp.artifacts.layout import ArtifactLayout
from datp.config.stages import ExperimentStage
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.core.metric_enums import PayloadKey
from datp.evaluation.artifact_validation import validate_metrics_payload


def results_exist(
    policy: ThresholdPolicy,
    stage: ExperimentStage,
    seed: int,
    *,
    base_dir: Path,
) -> bool:
    """True only if metrics.json is valid and per-client entries include confusion_matrix; missing it -> stale, reruns cell."""
    run = PolicyRunId(
        cell=TrainingCellId(stage=stage, seed=seed),
        policy=policy,
    )
    metrics_file = (
        ArtifactLayout(base_dir=base_dir, stage=stage).policy_run(run).metrics_path
    )
    if not (metrics_file.is_file() and metrics_file.stat().st_size > 0):
        return False
    try:
        data = json.loads(metrics_file.read_text())
        violations = validate_metrics_payload(data, module="artifacts.results")
        if violations:
            return False
        per_client = data[PayloadKey.PER_CLIENT]
        clients: list[object] = (
            list(per_client.values())
            if isinstance(per_client, dict)
            else list(per_client)
        )
        if clients and PayloadKey.CONFUSION_MATRIX not in clients[0]:  # type: ignore[operator]
            return False
    except (json.JSONDecodeError, KeyError, IndexError, TypeError, AttributeError):
        return False
    return True
