"""Per-client Auroc record computation."""

from __future__ import annotations

from datp.attacks.score_containers import ScoreCollection
from datp.attacks.types import AurocRecord, AurocSet
from datp.evaluation.metrics import compute_binary_ranking_metrics


def compute_auroc_records(collection: ScoreCollection) -> AurocSet:
    """Compute per-client Auroc records from test-benign and test-attack scores."""
    records: list[AurocRecord] = []
    for cid in collection.eligible_ids:
        c = collection.for_client(cid)
        records.append(
            AurocRecord(
                client_id=cid,
                auroc=compute_binary_ranking_metrics(
                    c.test_benign, c.test_attack
                ).auroc,
            )
        )
    return AurocSet.from_records(records)
