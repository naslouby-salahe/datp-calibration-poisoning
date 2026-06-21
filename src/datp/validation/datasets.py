from __future__ import annotations

import dataclasses
from collections.abc import Iterator, Mapping
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

from datp.data.catalog import DatasetID
from datp.validation.constants import NBAIOT_CONFOUND_SUMMARY

from datp.config.stages import ExperimentStage
from datp.core.errors import fmt
from datp.core.provenance import hash_jsonable
from datp.data.datasets.ciciot2023.spec import CICIOT2023_SPEC
from datp.data.datasets.nbaiot.spec import NBAIOT_SPEC
from datp.data.splits import Split, split_path
from datp.statistics.divergence import (
    JSSummary,
    pairwise_js_summary,
)
from datp.validation.enums import (
    HomogeneityVerdict,
)
from datp.validation.schemas import (
    ClusterStabilityRecord,
    CICIoTProtocolAudit,
    NBaIoTDeviceCounts,
)

_MODULE = "validation.datasets"


def _parquet_num_rows(path: Path) -> int | None:
    if not path.exists():
        return None
    return int(pq.read_metadata(path).num_rows)


def _device_family_subtype(rest: str) -> tuple[str, str] | None:
    """Return (family, subtype) for a device-relative path, or None if no family matches."""
    for family in NBAIOT_SPEC.attack_family_dirs:
        if rest.startswith(f"{family}/"):
            return family, rest[len(family) + 1 :]
    return None


def _attack_files_by_family(
    file_hash_keys: list[str], device: str
) -> tuple[AttackFamilyFiles, ...]:
    return tuple(
        AttackFamilyFiles(
            family=family,
            files=tuple(
                sorted(_attack_subtypes_for_family(file_hash_keys, device, family))
            ),
        )
        for family in NBAIOT_SPEC.attack_family_dirs
    )


def _attack_subtypes_for_family(
    file_hash_keys: list[str], device: str, target_family: str
) -> tuple[str, ...]:
    prefix = f"{device}/"
    subtypes: list[str] = []
    for key in file_hash_keys:
        if not key.startswith(prefix):
            continue
        match = _device_family_subtype(key[len(prefix) :])
        if match is None:
            continue
        family, subtype = match
        if family == target_family:
            subtypes.append(subtype)
    return tuple(subtypes)


def _attack_files_mapping(
    attack_files: tuple[AttackFamilyFiles, ...],
) -> AttackFilesMapping:
    return AttackFilesMapping(
        tuple((entry.family, list(entry.files)) for entry in attack_files)
    )


def build_nbaiot_per_device(
    processed_root: Path,
    file_hash_keys: list[str],
) -> list[NBaIoTDeviceCounts]:
    # Reads only parquet footers (no payload) to keep audit fast.
    family_map = NBAIOT_SPEC.family_map
    if family_map is None:
        raise ValueError(
            fmt(
                _MODULE,
                "N-BaIoT spec must have family_map",
                "non-null family_map",
                repr(family_map),
            )
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
                attack_files_by_family=_attack_files_mapping(
                    _attack_files_by_family(file_hash_keys, device)
                ),
            )
        )
    return out


def _feature_list_hash(feature_list: list[str]) -> str:
    return hash_jsonable((("features", tuple(feature_list)),))


def build_ciciot_protocol() -> CICIoTProtocolAudit:
    cap_policy = CICIOT2023_SPEC.cap_policy
    if cap_policy is None:
        raise RuntimeError(
            fmt(
                _MODULE,
                "CICIoT2023 cap policy missing in dataset spec",
                "non-null CapPolicy",
                repr(cap_policy),
            )
        )

    feature_list = (
        list(CICIOT2023_SPEC.feature_columns) if CICIOT2023_SPEC.feature_columns else []
    )
    expected_count = CICIOT2023_SPEC.expected_client_count
    assert expected_count is not None, "CICIoT2023 spec must have expected_client_count"
    return CICIoTProtocolAudit(
        dataset=DatasetID.CICIOT2023,
        feature_count=len(feature_list),
        feature_list=feature_list,
        dropped_columns_note=(
            "Prepare keeps only the canonical 39 FEATURE_COLUMNS plus the Label column. "
            "Any other column present in the raw merged CSV (typical raw layout has "
            "additional flow-statistics columns) is dropped at load time. Exact dropped "
            "column names depend on the source CSV header and are not persisted to the "
            "manifest; verify with `head -1` on a raw merged CSV against FEATURE_COLUMNS."
        ),
        feature_list_hash=_feature_list_hash(feature_list),
        client_identity_source=CICIOT2023_SPEC.client_identity,
        n_clients=expected_count,
        cap_total=cap_policy.total,
        cap_attack_reserve=cap_policy.attack_reserve,
        cap_strategy=cap_policy.strategy.value,
    )


@dataclasses.dataclass(frozen=True)
class HomogeneitySummary:
    js_summary: JSSummary
    verdict: HomogeneityVerdict


@dataclasses.dataclass(frozen=True, slots=True)
class AttackFamilyFiles:
    family: str
    files: tuple[str, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class AttackFilesMapping(Mapping[str, list[str]]):
    entries: tuple[tuple[str, list[str]], ...]

    def __getitem__(self, key: str) -> list[str]:
        for family, files in self.entries:
            if family == key:
                return files
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (family for family, _ in self.entries)

    def __len__(self) -> int:
        return len(self.entries)


@dataclasses.dataclass(frozen=True, slots=True)
class ClusterAssignments:
    seed: int
    assignments: tuple[tuple[str, int], ...]


def compute_ciciot_homogeneity(
    cal_errors_by_client: Mapping[str, "np.ndarray"],
    *,
    n_bins: int,
    threshold: float,
) -> HomogeneitySummary:
    arrays = [arr for arr in cal_errors_by_client.values() if arr.size > 0]
    summary: JSSummary = pairwise_js_summary(arrays, n_bins=n_bins)

    if summary.n_compared < 2:
        return HomogeneitySummary(
            js_summary=summary,
            verdict=HomogeneityVerdict.BLOCKED_PENDING_RUN,
        )

    _mean = 0.0 if summary.mean is None else summary.mean
    return HomogeneitySummary(
        js_summary=summary,
        verdict=(
            HomogeneityVerdict.HOMOGENEOUS
            if _mean < threshold
            else HomogeneityVerdict.HETEROGENEOUS
        ),
    )


def confound_summary_for(stage: ExperimentStage) -> str | None:
    return NBAIOT_CONFOUND_SUMMARY


def chronological_flags_for(
    stage: ExperimentStage,
) -> tuple[bool | None, bool | None]:
    # All active N-BaIoT stages use chronological split.
    _ = NBAIOT_SPEC  # Explicitly tie the claim to canonical spec ownership.
    return True, True


def compute_cluster_stability(
    cluster_assignments_by_seed: tuple[ClusterAssignments, ...],
    stage: ExperimentStage,
) -> list[ClusterStabilityRecord]:
    from sklearn.metrics import adjusted_rand_score  # type: ignore[import-untyped]  # noqa: PLC0415

    seeds = sorted({item.seed for item in cluster_assignments_by_seed})
    records: list[ClusterStabilityRecord] = []
    for i, seed_a in enumerate(seeds):
        for seed_b in seeds[i + 1 :]:
            assigns_a = _assignments_for_seed(cluster_assignments_by_seed, seed_a)
            assigns_b = _assignments_for_seed(cluster_assignments_by_seed, seed_b)
            client_ids_a = {client_id for client_id, _ in assigns_a}
            client_ids_b = {client_id for client_id, _ in assigns_b}
            common = sorted(client_ids_a & client_ids_b)
            if len(common) < 2:
                continue
            labels_a = [
                _assignment_for_client(assigns_a, client_id) for client_id in common
            ]
            labels_b = [
                _assignment_for_client(assigns_b, client_id) for client_id in common
            ]
            ari = float(adjusted_rand_score(labels_a, labels_b))
            records.append(
                ClusterStabilityRecord(
                    stage=stage,
                    seed_a=seed_a,
                    seed_b=seed_b,
                    adjusted_rand_index=ari,
                )
            )
    return records


def _assignments_for_seed(
    cluster_assignments_by_seed: tuple[ClusterAssignments, ...], seed: int
) -> tuple[tuple[str, int], ...]:
    for item in cluster_assignments_by_seed:
        if item.seed == seed:
            return tuple(sorted(item.assignments))
    raise KeyError(seed)


def _assignment_for_client(
    assignments: tuple[tuple[str, int], ...], client_id: str
) -> int:
    for candidate, cluster in assignments:
        if candidate == client_id:
            return cluster
    raise KeyError(client_id)
