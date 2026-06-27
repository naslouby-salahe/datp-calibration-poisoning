"""Dataset-level audit helpers: N-BaIoT device counts and cluster-stability records."""

from __future__ import annotations

import dataclasses
from collections.abc import Iterator, Mapping
from pathlib import Path

import pyarrow.parquet as pq

from datp.config.models import ExperimentStage
from datp.data.datasets.nbaiot.spec import NBAIOT_SPEC
from datp.data.splits import Split, split_path
from datp.validation.schemas import ClusterStabilityRecord, NBaIoTDeviceCounts

_MODULE = "validation.datasets"


def _parquet_num_rows(path: Path) -> int | None:
    return int(pq.read_metadata(path).num_rows) if path.exists() else None


def _attack_files_mapping(file_hash_keys: list[str], device: str) -> AttackFilesMapping:
    prefix = f"{device}/"
    grouped: dict[str, list[str]] = {f: [] for f in NBAIOT_SPEC.attack_family_dirs}

    for key in file_hash_keys:
        if key.startswith(prefix):
            rest = key[len(prefix) :]
            for family in NBAIOT_SPEC.attack_family_dirs:
                if rest.startswith(f"{family}/"):
                    grouped[family].append(rest[len(family) + 1 :])
                    break

    return AttackFilesMapping(
        tuple((fam, sorted(files)) for fam, files in grouped.items())
    )


def build_nbaiot_per_device(
    processed_root: Path, file_hash_keys: list[str]
) -> list[NBaIoTDeviceCounts]:
    """Build per-device N-BaIoT row counts and attack-file mappings for audit validation."""
    family_map = NBAIOT_SPEC.family_map
    if family_map is None:
        raise ValueError(
            f"[{_MODULE}] N-BaIoT spec must have family_map. Expected: non-null family_map. Got: {repr(family_map)}."
        )

    out: list[NBaIoTDeviceCounts] = []
    for device in NBAIOT_SPEC.device_ids:
        device_dir = processed_root / device
        train_n = _parquet_num_rows(split_path(device_dir, Split.TRAIN))
        cal_n = _parquet_num_rows(split_path(device_dir, Split.CAL))
        benign_test_n = _parquet_num_rows(split_path(device_dir, Split.TEST_BENIGN))
        attack_test_n = _parquet_num_rows(split_path(device_dir, Split.TEST_ATTACK))

        ratio: float | None = None
        if benign_test_n is not None and attack_test_n is not None:
            denom = benign_test_n + attack_test_n
            ratio = float(benign_test_n / denom) if denom > 0 else None

        out.append(
            NBaIoTDeviceCounts(
                device=device,
                family=family_map[device],
                benign_train=train_n,
                benign_cal=cal_n,
                benign_test=benign_test_n,
                attack_test_total=attack_test_n,
                benign_class_imbalance_ratio=ratio,
                attack_files_by_family=_attack_files_mapping(file_hash_keys, device),
            )
        )
    return out


@dataclasses.dataclass(frozen=True, slots=True)
class AttackFilesMapping(Mapping[str, list[str]]):
    """Immutable mapping from attack family names to lists of attack file keys."""

    entries: tuple[tuple[str, list[str]], ...]

    @property
    def _dict(self) -> dict[str, list[str]]:
        return dict(self.entries)

    def __getitem__(self, key: str) -> list[str]:
        """Return the list of attack file keys for a given family name."""
        return self._dict[key]

    def __iter__(self) -> Iterator[str]:
        """Iterate over the attack family names."""
        return iter(self._dict)

    def __len__(self) -> int:
        """Return the number of attack families."""
        return len(self.entries)


@dataclasses.dataclass(frozen=True, slots=True)
class ClusterAssignments:
    """Cluster label assignments for a single random seed."""

    seed: int
    assignments: tuple[tuple[str, int], ...]


def compute_cluster_stability(
    cluster_assignments_by_seed: tuple[ClusterAssignments, ...],
    stage: ExperimentStage,
) -> list[ClusterStabilityRecord]:
    """Compute pairwise adjusted Rand index across seeds to quantify cluster stability."""
    from sklearn.metrics import (
        adjusted_rand_score,  # type: ignore[import-untyped]  # noqa: PLC0415
    )

    seed_to_assigns = {
        item.seed: dict(item.assignments) for item in cluster_assignments_by_seed
    }
    seeds = sorted(seed_to_assigns.keys())
    records: list[ClusterStabilityRecord] = []

    for i, seed_a in enumerate(seeds):
        assigns_a = seed_to_assigns[seed_a]
        for seed_b in seeds[i + 1 :]:
            assigns_b = seed_to_assigns[seed_b]
            common = sorted(assigns_a.keys() & assigns_b.keys())

            if len(common) < 2:
                continue

            labels_a = [assigns_a[client_id] for client_id in common]
            labels_b = [assigns_b[client_id] for client_id in common]

            records.append(
                ClusterStabilityRecord(
                    stage=stage,
                    seed_a=seed_a,
                    seed_b=seed_b,
                    adjusted_rand_index=float(adjusted_rand_score(labels_a, labels_b)),
                )
            )
    return records
