from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from datp.core.types import (
    ClusterInfo,
    ClusterInfoTuple,
    ClusterMetadata,
    ClientFingerprint,
    ClientFingerprintTuple,
    ClientSilhouetteScore,
    ClientSilhouetteScoreTuple,
)


@dataclass(frozen=True, slots=True)
class ClusterMetadataInput:
    k: int
    client_cluster: dict[str, int]
    tau_per_cluster: dict[int, float]
    silhouette: float
    silhouette_scores: dict[int, float]
    fingerprints: dict[str, np.ndarray]
    eligible_ids: list[str]


def cluster_info(
    *,
    eligible_ids: list[str],
    client_cluster: dict[str, int],
    tau_per_cluster: dict[int, float],
) -> dict[str, ClusterInfo]:
    return {
        f"cluster_{cluster}": ClusterInfo(
            cluster_id=f"cluster_{cluster}",
            tau_cluster=tau_per_cluster[cluster],
            members=tuple(
                cid for cid in eligible_ids if client_cluster[cid] == cluster
            ),
        )
        for cluster in sorted(tau_per_cluster)
    }


def build_cluster_metadata(metadata_input: ClusterMetadataInput) -> ClusterMetadata:
    info = cluster_info(
        eligible_ids=metadata_input.eligible_ids,
        client_cluster=metadata_input.client_cluster,
        tau_per_cluster=metadata_input.tau_per_cluster,
    )
    return ClusterMetadata(
        k=metadata_input.k,
        cluster_info=ClusterInfoTuple(info.values()),
        silhouette=metadata_input.silhouette,
        silhouette_scores=ClientSilhouetteScoreTuple(
            ClientSilhouetteScore(client_id=str(k), score=v)
            for k, v in metadata_input.silhouette_scores.items()
        ),
        fingerprints=ClientFingerprintTuple(
            ClientFingerprint(
                client_id=cid,
                mean=float(metadata_input.fingerprints[cid][0]),
                variance=float(metadata_input.fingerprints[cid][1]),
                skewness=float(metadata_input.fingerprints[cid][2]),
                p95=float(metadata_input.fingerprints[cid][3]),
            )
            for cid in metadata_input.eligible_ids
        ),
    )
