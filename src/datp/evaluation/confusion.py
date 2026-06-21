"""Atomic write of per-client confusion matrices."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from datp.artifacts.names import ArtifactDir
from datp.core.metric_enums import ConfusionKey, PayloadKey
from datp.evaluation.metrics import EvaluationResult


def save_confusion_matrices(eval_result: EvaluationResult, base_dir: Path) -> Path:
    base_dir = Path(base_dir)
    cm_dir = base_dir / ArtifactDir.CONFUSION_MATRICES / str(eval_result.stage)

    filename = f"{eval_result.policy}_seed{eval_result.seed}.json"

    out_path = cm_dir / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload: dict[str, object] = {
        PayloadKey.POLICY: eval_result.policy.value,
        PayloadKey.STAGE: eval_result.stage.value,
        PayloadKey.SEED: eval_result.seed,
        PayloadKey.COVERAGE_RATIO: eval_result.coverage_ratio,
    }
    payload[PayloadKey.PER_CLIENT] = [
        {
            PayloadKey.CLIENT_ID: cr.client_id,
            PayloadKey.CONFUSION_MATRIX: {
                ConfusionKey.TP.value: cr.confusion.tp,
                ConfusionKey.FP.value: cr.confusion.fp,
                ConfusionKey.TN.value: cr.confusion.tn,
                ConfusionKey.FN.value: cr.confusion.fn,
            },
            PayloadKey.N_BENIGN: cr.n_benign,
            PayloadKey.N_ATTACK: cr.n_attack,
        }
        for cr in eval_result.clients
    ]

    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    fd, tmp = tempfile.mkstemp(dir=out_path.parent, suffix=".tmp.json")
    try:
        with open(fd, "w", encoding="utf-8") as f:
            f.write(text)
        Path(tmp).replace(out_path)
    except OSError:
        Path(tmp).unlink(missing_ok=True)
        raise

    return out_path
