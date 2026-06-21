from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from datp.config.stages import ExperimentStage
from datp.data.catalog import DatasetID
from datp.data.datasets.ciciot2023.spec import (
    CAP_ATTACK_RESERVE,
    CAP_TOTAL,
    FEATURE_COLUMNS,
    NUM_CLIENTS,
)
from datp.data.datasets.nbaiot.spec import NBAIOT_SPEC
from datp.data.splits import SPLIT_FILENAME, Split
from datp.validation.constants import NBAIOT_CONFOUND_SUMMARY
from datp.validation.datasets import (
    ClusterAssignments,
    build_ciciot_protocol,
    build_nbaiot_per_device,
    chronological_flags_for,
    compute_cluster_stability,
    confound_summary_for,
)


def _assignments(
    *items: tuple[int, tuple[tuple[str, int], ...]],
) -> tuple[ClusterAssignments, ...]:
    return tuple(
        ClusterAssignments(seed=seed, assignments=client_assignments)
        for seed, client_assignments in items
    )


def _write_parquet(path: Path, n_rows: int) -> None:
    table = pa.table({"x": list(range(n_rows))})
    pq.write_table(table, path)


class TestConfoundSummaryFor:
    def test_nbaiot_main_returns_nbaiot_summary(self) -> None:
        result = confound_summary_for()
        assert result == NBAIOT_CONFOUND_SUMMARY


class TestChronologicalFlagsFor:
    def test_nbaiot_main_is_chronological(self) -> None:
        assert chronological_flags_for() == (True, True)


class TestBuildCiciotProtocol:
    def test_returns_ciciot2023_dataset(self) -> None:
        record = build_ciciot_protocol()
        assert record.dataset == DatasetID.CICIOT2023

    def test_feature_count_matches_spec(self) -> None:
        record = build_ciciot_protocol()
        assert record.feature_count == len(FEATURE_COLUMNS)

    def test_feature_list_matches_spec(self) -> None:
        record = build_ciciot_protocol()
        assert record.feature_list == list(FEATURE_COLUMNS)

    def test_cap_values_match_spec(self) -> None:
        record = build_ciciot_protocol()
        assert record.cap_total == CAP_TOTAL
        assert record.cap_attack_reserve == CAP_ATTACK_RESERVE

    def test_n_clients_matches_spec(self) -> None:
        record = build_ciciot_protocol()
        assert record.n_clients == NUM_CLIENTS

    def test_feature_list_hash_is_stable(self) -> None:
        r1 = build_ciciot_protocol()
        r2 = build_ciciot_protocol()
        assert r1.feature_list_hash == r2.feature_list_hash

    def test_dropped_columns_note_is_present(self) -> None:
        record = build_ciciot_protocol()
        assert record.dropped_columns_note


class TestBuildNbaiotPerDevice:
    def test_returns_one_record_per_device(self, tmp_path: Path) -> None:
        records = build_nbaiot_per_device(tmp_path, [])
        assert len(records) == len(NBAIOT_SPEC.device_ids)

    def test_all_counts_none_when_no_parquet_files(self, tmp_path: Path) -> None:
        records = build_nbaiot_per_device(tmp_path, [])
        for rec in records:
            assert rec.benign_train is None
            assert rec.benign_cal is None
            assert rec.benign_test is None
            assert rec.attack_test_total is None
            assert rec.benign_class_imbalance_ratio is None

    def test_counts_populated_from_parquet_footers(self, tmp_path: Path) -> None:
        device = NBAIOT_SPEC.device_ids[0]
        device_dir = tmp_path / device
        device_dir.mkdir()
        _write_parquet(device_dir / SPLIT_FILENAME[Split.TRAIN], 100)
        _write_parquet(device_dir / SPLIT_FILENAME[Split.CAL], 20)
        _write_parquet(device_dir / SPLIT_FILENAME[Split.TEST_BENIGN], 30)
        _write_parquet(device_dir / SPLIT_FILENAME[Split.TEST_ATTACK], 70)

        records = build_nbaiot_per_device(tmp_path, [])
        target = next(r for r in records if r.device == device)

        assert target.benign_train == 100
        assert target.benign_cal == 20
        assert target.benign_test == 30
        assert target.attack_test_total == 70

    def test_class_imbalance_ratio_computed(self, tmp_path: Path) -> None:
        device = NBAIOT_SPEC.device_ids[0]
        device_dir = tmp_path / device
        device_dir.mkdir()
        _write_parquet(device_dir / SPLIT_FILENAME[Split.TEST_BENIGN], 30)
        _write_parquet(device_dir / SPLIT_FILENAME[Split.TEST_ATTACK], 70)

        records = build_nbaiot_per_device(tmp_path, [])
        target = next(r for r in records if r.device == device)

        assert target.benign_class_imbalance_ratio == pytest.approx(30 / 100)

    def test_attack_files_by_family_parsed_from_hash_keys(self, tmp_path: Path) -> None:
        device = NBAIOT_SPEC.device_ids[0]
        file_hash_keys = [
            f"{device}/gafgyt_attacks/combo.txt",
            f"{device}/mirai_attacks/ack.txt",
            f"{device}/mirai_attacks/syn.txt",
        ]
        records = build_nbaiot_per_device(tmp_path, file_hash_keys)
        target = next(r for r in records if r.device == device)

        assert target.attack_files_by_family["gafgyt_attacks"] == ["combo.txt"]
        assert target.attack_files_by_family["mirai_attacks"] == ["ack.txt", "syn.txt"]

    def test_device_family_assigned_from_spec(self, tmp_path: Path) -> None:
        assert NBAIOT_SPEC.family_map is not None
        records = build_nbaiot_per_device(tmp_path, [])
        for rec in records:
            assert rec.family == NBAIOT_SPEC.family_map[rec.device]

    def test_class_imbalance_ratio_none_when_both_counts_zero(
        self, tmp_path: Path
    ) -> None:
        device = NBAIOT_SPEC.device_ids[0]
        device_dir = tmp_path / device
        device_dir.mkdir()
        _write_parquet(device_dir / SPLIT_FILENAME[Split.TEST_BENIGN], 0)
        _write_parquet(device_dir / SPLIT_FILENAME[Split.TEST_ATTACK], 0)

        records = build_nbaiot_per_device(tmp_path, [])
        target = next(r for r in records if r.device == device)
        assert target.benign_class_imbalance_ratio is None


class TestComputeClusterThresholdClusterStability:
    def test_empty_assignments_returns_empty(self) -> None:
        result = compute_cluster_stability((), ExperimentStage.NBAIOT_MAIN)
        assert result == []

    def test_single_seed_returns_empty(self) -> None:
        result = compute_cluster_stability(
            _assignments((0, (("c1", 0), ("c2", 1), ("c3", 0)))),
            ExperimentStage.NBAIOT_MAIN,
        )
        assert result == []

    def test_two_seeds_produces_one_record(self) -> None:
        assignments = _assignments(
            (0, (("c1", 0), ("c2", 1), ("c3", 0))),
            (1, (("c1", 0), ("c2", 1), ("c3", 0))),
        )
        result = compute_cluster_stability(assignments, ExperimentStage.NBAIOT_MAIN)
        assert len(result) == 1
        assert result[0].seed_a == 0
        assert result[0].seed_b == 1

    def test_ari_is_one_for_identical_assignments(self) -> None:
        assignments = _assignments(
            (0, (("c1", 0), ("c2", 1), ("c3", 0))),
            (1, (("c1", 0), ("c2", 1), ("c3", 0))),
        )
        result = compute_cluster_stability(assignments, ExperimentStage.NBAIOT_MAIN)
        assert result[0].adjusted_rand_index == pytest.approx(1.0)

    def test_stage_stored_in_record(self) -> None:
        assignments = _assignments(
            (0, (("c1", 0), ("c2", 1), ("c3", 0))),
            (1, (("c1", 0), ("c2", 0), ("c3", 1))),
        )
        result = compute_cluster_stability(assignments, ExperimentStage.NBAIOT_MAIN)
        assert result[0].stage == ExperimentStage.NBAIOT_MAIN

    def test_three_seeds_produces_three_pairs(self) -> None:
        assignments = _assignments(
            (0, (("c1", 0), ("c2", 1))),
            (1, (("c1", 0), ("c2", 1))),
            (2, (("c1", 1), ("c2", 0))),
        )
        result = compute_cluster_stability(assignments, ExperimentStage.NBAIOT_MAIN)
        assert len(result) == 3

    def test_fewer_than_two_common_clients_skipped(self) -> None:
        assignments = _assignments((0, (("c1", 0),)), (1, (("c1", 0),)))
        result = compute_cluster_stability(assignments, ExperimentStage.NBAIOT_MAIN)
        assert result == []

    def test_non_overlapping_clients_skipped(self) -> None:
        assignments = _assignments(
            (0, (("c1", 0), ("c2", 1))),
            (1, (("c3", 0), ("c4", 1))),
        )
        result = compute_cluster_stability(assignments, ExperimentStage.NBAIOT_MAIN)
        assert result == []

    def test_partially_overlapping_clients_uses_common_only(self) -> None:
        assignments = _assignments(
            (0, (("c1", 0), ("c2", 1), ("only_in_0", 0))),
            (1, (("c1", 0), ("c2", 1), ("only_in_1", 0))),
        )
        result = compute_cluster_stability(assignments, ExperimentStage.NBAIOT_MAIN)
        assert len(result) == 1
        assert result[0].adjusted_rand_index == pytest.approx(1.0)
