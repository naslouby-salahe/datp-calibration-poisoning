from __future__ import annotations

from datp.attacks.score_containers import ScoreCollection
from datp.attacks.types import AurocRecord, AurocSet
from datp.evaluation.ranking import compute_binary_ranking_metrics


def compute_auroc_records(
    collection: ScoreCollection,
) -> AurocSet:
    records: list[AurocRecord] = []
    for cid in collection.eligible_ids:
        c = collection.for_client(cid)
        ranking = compute_binary_ranking_metrics(c.test_benign, c.test_attack)
        records.append(AurocRecord(client_id=cid, auroc=ranking.auroc))
    return AurocSet(records=tuple(records))
