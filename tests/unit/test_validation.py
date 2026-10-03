from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import numpy as np
import pandas as pd
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from sklearn.metrics import f1_score

import datp.validation as results
from datp.config import BASE_CONFIG, ExperimentStage
from datp.core import (
    ClientThreshold,
    PolicyRunId,
    hash_file,
    hash_jsonable,
    set_seeds,
    source_hash,
)
from datp.data import (
    DEVICE_FAMILY_MAP,
    NBAIOT_SPEC,
    Split,
    filename_for_split,
    write_artifact,
)
from datp.enums import (
    POLICY_THRESHOLD_SOURCE,
    ArtifactDir,
    ArtifactFile,
    AuditArtifact,
    AuditSeverity,
    AuditStatus,
    ClientStatus,
    ConvergenceStatus,
    ConvergenceSummaryKey,
    DatasetID,
    DenominatorStatus,
    MetricName,
    NormalizationScope,
    ScoringStage,
    ThresholdAggregationMethod,
    ThresholdPolicy,
    WarningCode,
    WorstDirection,
)
from datp.evaluation import compute_client_record
from datp.scoring import ScoringColumn
from datp.thresholding import ThresholdDerivation, derive_threshold
from datp.types import ClientId, ClusterId, RandomSeed
from datp.validation import (
    METRICS_SOURCE_FILES,
    SCORING_SOURCE_FILES,
    THRESHOLD_SOURCE_FILES,
    CellPanel,
    ClusterAssignments,
    ConvergencePayload,
    InvariantHashes,
    InvariantKey,
    RecomputationParams,
    RunManifestRecord,
    ScoreArtifactHash,
    WarningRecord,
    WorstClientRecord,
    append_recomputation_records,
    build_invariant_results,
    build_nbaiot_per_device,
    check_local_threshold_utility_tradeoff,
    completed_metric_paths,
    compute_cluster_stability,
    convergence_payload,
    emit_flat_cv_tpr_warnings,
    emit_worst_client_stability_warnings,
    parse_metric_path,
    run_results_audit,
)

_STAGE = ExperimentStage.NBAIOT_MAIN


def test_flat_cv_tpr_warning_emitted() -> None:
    """Verify FLAT_CV_TPR_SUSPICIOUS warning is emitted when all policies yield identical CV TPR."""
    warnings_out: list[WarningRecord] = []
    cell_panel: dict[tuple[ExperimentStage, int, ThresholdPolicy], CellPanel] = {
        (_STAGE, 0, ThresholdPolicy.GLOBAL_THRESHOLD): CellPanel(cv_tpr=0.5),
        (_STAGE, 0, ThresholdPolicy.LOCAL_THRESHOLD): CellPanel(cv_tpr=0.5),
        (_STAGE, 0, ThresholdPolicy.CLUSTER_THRESHOLD): CellPanel(cv_tpr=0.5),
    }
    emit_flat_cv_tpr_warnings(cell_panel, warnings_out)
    assert any(w.code == "FLAT_CV_TPR_SUSPICIOUS" for w in warnings_out)


def test_no_flat_cv_tpr_warning_when_different() -> None:
    """Verify no FLAT_CV_TPR_SUSPICIOUS warning is emitted when policies yield differing CV TPR."""
    warnings_out: list[WarningRecord] = []
    cell_panel: dict[tuple[ExperimentStage, int, ThresholdPolicy], CellPanel] = {
        (_STAGE, 0, ThresholdPolicy.GLOBAL_THRESHOLD): CellPanel(cv_tpr=0.3),
        (_STAGE, 0, ThresholdPolicy.LOCAL_THRESHOLD): CellPanel(cv_tpr=0.6),
        (_STAGE, 0, ThresholdPolicy.CLUSTER_THRESHOLD): CellPanel(cv_tpr=0.4),
    }
    emit_flat_cv_tpr_warnings(cell_panel, warnings_out)
    assert not any(w.code == "FLAT_CV_TPR_SUSPICIOUS" for w in warnings_out)


def _worst_client_records(
    client_id_fn: Callable[[int], str],
) -> list[WorstClientRecord]:
    """Helper to build list of WorstClientRecord instances."""
    return [
        WorstClientRecord(
            run_id=f"nbaiot_main_global_seed{s}",
            seed=s,
            stage=_STAGE,
            policy=ThresholdPolicy.GLOBAL_THRESHOLD,
            metric=MetricName.FPR,
            direction=WorstDirection.MAX_IS_WORST,
            worst_client_id=client_id_fn(s),
            worst_value=0.9,
            eligible_pool_size=4,
        )
        for s in range(5)
    ]


def test_worst_client_stability_warning_when_always_same() -> None:
    """Verify WORST_CLIENT_STABLE warning is emitted when the worst client is identical across runs."""
    warnings_out: list[WarningRecord] = []
    emit_worst_client_stability_warnings(
        _worst_client_records(lambda _: "Danmini_Doorbell"), warnings_out
    )
    assert "WORST_CLIENT_STABLE" in [w.code for w in warnings_out]


def test_worst_client_varies_info_when_different() -> None:
    """Verify WORST_CLIENT_VARIES info is emitted when the worst client varies across runs."""
    warnings_out: list[WarningRecord] = []
    emit_worst_client_stability_warnings(
        _worst_client_records(lambda s: f"Client_{s}"), warnings_out
    )
    codes = [w.code for w in warnings_out]
    assert "WORST_CLIENT_VARIES" in codes
    assert "WORST_CLIENT_STABLE" not in codes


def test_check_local_threshold_utility_tradeoff_warns_when_local_improves_cv_fpr_but_worsens_utility() -> (
    None
):
    """Verify local utility tradeoff warnings are emitted when local threshold improves CV FPR but degrades macro F1 or PR-AUC."""
    warnings_out: list[WarningRecord] = []
    global_panel = CellPanel(
        cv_fpr=0.3, macro_f1_mean=0.85, pr_auc_mean=0.90, auroc_mean=0.92, cv_tpr=0.80
    )
    local_panel = CellPanel(
        cv_fpr=0.2, macro_f1_mean=0.80, pr_auc_mean=0.88, auroc_mean=0.91, cv_tpr=0.78
    )
    check_local_threshold_utility_tradeoff(
        (_STAGE, 0), global_panel, local_panel, warnings_out
    )
    codes = [w.code for w in warnings_out]
    assert WarningCode.LOCAL_UTILITY_TRADEOFF in codes
    msg = warnings_out[0].message
    assert "macro_f1" in msg
    assert "pr_auc" in msg


def test_check_local_threshold_utility_tradeoff_no_warning_when_cv_fpr_not_improved() -> (
    None
):
    """Verify no local utility tradeoff warning is emitted if local threshold does not improve CV FPR."""
    warnings_out: list[WarningRecord] = []
    global_panel = CellPanel(cv_fpr=0.2, macro_f1_mean=0.80)
    local_panel = CellPanel(cv_fpr=0.3, macro_f1_mean=0.85)
    check_local_threshold_utility_tradeoff(
        (_STAGE, 0), global_panel, local_panel, warnings_out
    )
    assert len(warnings_out) == 0


def test_check_local_threshold_utility_tradeoff_no_warning_when_no_utility_worsened() -> (
    None
):
    """Verify no local utility tradeoff warning is emitted if no utility metrics degrade."""
    warnings_out: list[WarningRecord] = []
    global_panel = CellPanel(
        cv_fpr=0.3, macro_f1_mean=0.80, auroc_mean=0.90, cv_tpr=0.75
    )
    local_panel = CellPanel(
        cv_fpr=0.2, macro_f1_mean=0.85, auroc_mean=0.92, cv_tpr=0.80
    )
    check_local_threshold_utility_tradeoff(
        (_STAGE, 0), global_panel, local_panel, warnings_out
    )
    assert len(warnings_out) == 0


def _write_summary(
    score_dir: Path,
    *,
    convergence_round: int | None = 5,
    convergence_criterion_value: float | None = 0.01,
    convergence_status: str = "converged",
) -> Path:
    """Helper to write a mock convergence summary JSON file to the target score directory."""
    summary = {
        ConvergenceSummaryKey.ROUNDS_INITIAL: 5,
        ConvergenceSummaryKey.ROUNDS_MAX: 100,
        ConvergenceSummaryKey.RELATIVE_THRESHOLD: 0.03,
        ConvergenceSummaryKey.WINDOW: 4,
        ConvergenceSummaryKey.ACTUAL_ROUNDS: 20,
        ConvergenceSummaryKey.CONVERGENCE_ROUND: convergence_round,
        ConvergenceSummaryKey.CONVERGENCE_CRITERION: convergence_criterion_value,
        ConvergenceSummaryKey.CONVERGENCE_STATUS: convergence_status,
        ConvergenceSummaryKey.WEIGHTED_LOSS: [1.0, 0.8, 0.6, 0.5],
    }
    path = score_dir / ArtifactFile.CONVERGENCE_SUMMARY
    path.write_text(json.dumps(summary))
    return path


def _write_curve(score_dir: Path) -> Path:
    """Helper to write a mock convergence curve CSV file to the target score directory."""
    path = score_dir / ArtifactFile.CONVERGENCE_CURVE
    path.write_text("round,fedavg_weighted_benign_val_loss\n1,1.0\n")
    return path


class TestConvergencePayload:
    """Tests verifying properties of the ConvergencePayload dataclass."""

    def test_construction(self, tmp_path: Path) -> None:
        """Verify that ConvergencePayload properties match construction arguments."""
        curve_path = str(tmp_path / "curve.csv")
        p = ConvergencePayload(
            convergence_round=5,
            convergence_criterion_value=0.01,
            convergence_status=ConvergenceStatus.CONVERGED,
            curve_path=curve_path,
        )
        assert p.convergence_round == 5
        assert p.convergence_criterion_value == pytest.approx(0.01)
        assert p.convergence_status == ConvergenceStatus.CONVERGED
        assert p.curve_path == curve_path

    def test_construction_with_none_round_and_value(self) -> None:
        """Verify ConvergencePayload can handle None rounds and values when training failed to converge."""
        p = ConvergencePayload(
            convergence_round=None,
            convergence_criterion_value=None,
            convergence_status=ConvergenceStatus.MISSING_SUMMARY,
            curve_path=None,
        )
        assert p.convergence_round is None
        assert p.convergence_criterion_value is None
        assert p.convergence_status == ConvergenceStatus.MISSING_SUMMARY
        assert p.curve_path is None

    def test_is_frozen(self) -> None:
        """Verify that ConvergencePayload fields are frozen to modification."""
        p = ConvergencePayload(
            convergence_round=5,
            convergence_criterion_value=0.01,
            convergence_status=ConvergenceStatus.CONVERGED,
            curve_path=None,
        )
        with pytest.raises(Exception):
            setattr(p, "convergence_round", 10)


class TestConvergencePayloadMissingSummary:
    """Tests verifying convergence payload behavior when the summary file is missing."""

    def test_missing_score_dir(self, tmp_path: Path) -> None:
        """Verify MISSING_SUMMARY is returned if the score directory does not exist."""
        result = convergence_payload(tmp_path / "nonexistent")
        assert result.convergence_round is None
        assert result.convergence_criterion_value is None
        assert result.convergence_status == ConvergenceStatus.MISSING_SUMMARY
        assert result.curve_path is None

    def test_curve_present_but_summary_absent(self, tmp_path: Path) -> None:
        """Verify status is MISSING_SUMMARY and curve path is ignored if summary is absent."""
        _write_curve(tmp_path)

        result = convergence_payload(tmp_path)
        assert result.convergence_status == ConvergenceStatus.MISSING_SUMMARY
        assert result.curve_path is None


class TestConvergencePayloadWithSummary:
    """Tests verifying convergence payload parsing when summary files exist."""

    def test_converged_with_curve(self, tmp_path: Path) -> None:
        """Verify convergence status, round, and curve path when convergence is successful."""
        _write_summary(tmp_path, convergence_round=8, convergence_criterion_value=0.02)
        _write_curve(tmp_path)

        result = convergence_payload(tmp_path)
        assert result.convergence_round == 8
        assert result.convergence_criterion_value == pytest.approx(0.02)
        assert result.convergence_status == ConvergenceStatus.CONVERGED
        assert result.curve_path == str(tmp_path / ArtifactFile.CONVERGENCE_CURVE)

    def test_not_converged_no_curve(self, tmp_path: Path) -> None:
        """Verify status is NOT_CONVERGED and parameters are None when simulation failed to converge."""
        _write_summary(
            tmp_path,
            convergence_round=None,
            convergence_criterion_value=None,
            convergence_status="not_converged",
        )

        result = convergence_payload(tmp_path)
        assert result.convergence_round is None
        assert result.convergence_criterion_value is None
        assert result.convergence_status == ConvergenceStatus.NOT_CONVERGED
        assert result.curve_path is None

    def test_unknown_status_from_json(self, tmp_path: Path) -> None:
        """Verify status defaults to ConvergenceStatus.UNKNOWN if summary JSON status is unrecognized."""
        _write_summary(
            tmp_path,
            convergence_round=None,
            convergence_criterion_value=None,
            convergence_status="bogus_status_xyz",
        )

        result = convergence_payload(tmp_path)
        assert result.convergence_status == ConvergenceStatus.UNKNOWN


def _assignments(
    *items: tuple[int, tuple[tuple[str, int], ...]],
) -> tuple[ClusterAssignments, ...]:
    return tuple(
        ClusterAssignments(
            seed=RandomSeed(seed),
            assignments={
                ClientId(client): ClusterId(str(cluster))
                for client, cluster in client_assignments
            },
        )
        for seed, client_assignments in items
    )


def _write_parquet(path: Path, n_rows: int) -> None:
    """Helper to write a mock Parquet table containing standard schema with specific rows."""
    table = pa.table({"x": list(range(n_rows))})
    pq.write_table(table, path)


class TestBuildNbaiotPerDevice:
    """Tests verifying build_nbaiot_per_device row count outputs and schema mappings."""

    def test_returns_one_record_per_device(self, tmp_path: Path) -> None:
        """Verify that one validation record is returned per NBAIoT device."""
        records = build_nbaiot_per_device(tmp_path, [])
        assert len(records) == len(NBAIOT_SPEC.device_ids)

    def test_all_counts_none_when_no_parquet_files(self, tmp_path: Path) -> None:
        """Verify counts default to None if Parquet data directories are empty."""
        records = build_nbaiot_per_device(tmp_path, [])
        for rec in records:
            assert rec.benign_train is None
            assert rec.benign_cal is None
            assert rec.benign_test is None
            assert rec.attack_test_total is None
            assert rec.benign_class_imbalance_ratio is None

    def test_counts_populated_from_parquet_footers(self, tmp_path: Path) -> None:
        """Verify sample counts are populated correctly from Parquet split footers."""
        device = NBAIOT_SPEC.device_ids[0]
        device_dir = tmp_path / device
        device_dir.mkdir()
        _write_parquet(device_dir / filename_for_split(Split.TRAIN), 100)
        _write_parquet(device_dir / filename_for_split(Split.CAL), 20)
        _write_parquet(device_dir / filename_for_split(Split.TEST_BENIGN), 30)
        _write_parquet(device_dir / filename_for_split(Split.TEST_ATTACK), 70)

        records = build_nbaiot_per_device(tmp_path, [])
        target = next(r for r in records if r.device == device)

        assert target.benign_train == 100
        assert target.benign_cal == 20
        assert target.benign_test == 30
        assert target.attack_test_total == 70

    def test_class_imbalance_ratio_computed(self, tmp_path: Path) -> None:
        """Verify that class imbalance ratio (benign / total) is correctly computed."""
        device = NBAIOT_SPEC.device_ids[0]
        device_dir = tmp_path / device
        device_dir.mkdir()
        _write_parquet(device_dir / filename_for_split(Split.TEST_BENIGN), 30)
        _write_parquet(device_dir / filename_for_split(Split.TEST_ATTACK), 70)

        records = build_nbaiot_per_device(tmp_path, [])
        target = next(r for r in records if r.device == device)

        assert target.benign_class_imbalance_ratio == pytest.approx(30 / 100)

    def test_attack_files_by_family_parsed_from_hash_keys(self, tmp_path: Path) -> None:
        """Verify attack files are correctly grouped by attack family from resource paths."""
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
        """Verify rec.family is correctly assigned based on the device model mappings."""
        assert NBAIOT_SPEC.family_map is not None
        records = build_nbaiot_per_device(tmp_path, [])
        for rec in records:
            assert rec.family == NBAIOT_SPEC.family_map[rec.device]

    def test_class_imbalance_ratio_none_when_both_counts_zero(
        self, tmp_path: Path
    ) -> None:
        """Verify class imbalance ratio is None if benign and attack splits are empty."""
        device = NBAIOT_SPEC.device_ids[0]
        device_dir = tmp_path / device
        device_dir.mkdir()
        _write_parquet(device_dir / filename_for_split(Split.TEST_BENIGN), 0)
        _write_parquet(device_dir / filename_for_split(Split.TEST_ATTACK), 0)

        records = build_nbaiot_per_device(tmp_path, [])
        target = next(r for r in records if r.device == device)
        assert target.benign_class_imbalance_ratio is None


class TestComputeClusterThresholdClusterStability:
    """Tests verifying adjusted rand index (ARI) cluster stability measurements across seeds."""

    def test_empty_assignments_returns_empty(self) -> None:
        """Verify empty cluster assignments input returns an empty stability list."""
        result = compute_cluster_stability((), ExperimentStage.NBAIOT_MAIN)
        assert result == []

    def test_single_seed_returns_empty(self) -> None:
        """Verify no stability records are computed if only 1 seed is evaluated."""
        result = compute_cluster_stability(
            _assignments((0, (("c1", 0), ("c2", 1), ("c3", 0)))),
            ExperimentStage.NBAIOT_MAIN,
        )
        assert result == []

    def test_two_seeds_produces_one_record(self) -> None:
        """Verify 2 seeds produce exactly 1 stability pair comparison record."""
        assignments = _assignments(
            (0, (("c1", 0), ("c2", 1), ("c3", 0))),
            (1, (("c1", 0), ("c2", 1), ("c3", 0))),
        )
        result = compute_cluster_stability(assignments, ExperimentStage.NBAIOT_MAIN)
        assert len(result) == 1
        assert result[0].seed_a == 0
        assert result[0].seed_b == 1

    def test_ari_is_one_for_identical_assignments(self) -> None:
        """Verify ARI is 1.0 if client cluster assignments are identical across seeds."""
        assignments = _assignments(
            (0, (("c1", 0), ("c2", 1), ("c3", 0))),
            (1, (("c1", 0), ("c2", 1), ("c3", 0))),
        )
        result = compute_cluster_stability(assignments, ExperimentStage.NBAIOT_MAIN)
        assert result[0].adjusted_rand_index == pytest.approx(1.0)

    def test_stage_stored_in_record(self) -> None:
        """Verify ExperimentStage matches input config value in the generated record."""
        assignments = _assignments(
            (0, (("c1", 0), ("c2", 1), ("c3", 0))),
            (1, (("c1", 0), ("c2", 0), ("c3", 1))),
        )
        result = compute_cluster_stability(assignments, ExperimentStage.NBAIOT_MAIN)
        assert result[0].stage == ExperimentStage.NBAIOT_MAIN

    def test_three_seeds_produces_three_pairs(self) -> None:
        """Verify 3 seeds produce exactly 3 pairwise comparison records."""
        assignments = _assignments(
            (0, (("c1", 0), ("c2", 1))),
            (1, (("c1", 0), ("c2", 1))),
            (2, (("c1", 1), ("c2", 0))),
        )
        result = compute_cluster_stability(assignments, ExperimentStage.NBAIOT_MAIN)
        assert len(result) == 3

    def test_fewer_than_two_common_clients_skipped(self) -> None:
        """Verify pairs are skipped if they share fewer than 2 common clients in overlap."""
        assignments = _assignments((0, (("c1", 0),)), (1, (("c1", 0),)))
        result = compute_cluster_stability(assignments, ExperimentStage.NBAIOT_MAIN)
        assert result == []

    def test_non_overlapping_clients_skipped(self) -> None:
        """Verify pairs are skipped if they share zero common clients in overlap."""
        assignments = _assignments(
            (0, (("c1", 0), ("c2", 1))),
            (1, (("c3", 0), ("c4", 1))),
        )
        result = compute_cluster_stability(assignments, ExperimentStage.NBAIOT_MAIN)
        assert result == []

    def test_partially_overlapping_clients_uses_common_only(self) -> None:
        """Verify ARI computes on the common intersection of clients only."""
        assignments = _assignments(
            (0, (("c1", 0), ("c2", 1), ("only_in_0", 0))),
            (1, (("c1", 0), ("c2", 1), ("only_in_1", 0))),
        )
        result = compute_cluster_stability(assignments, ExperimentStage.NBAIOT_MAIN)
        assert len(result) == 1
        assert result[0].adjusted_rand_index == pytest.approx(1.0)


def _write_dummy_file(path: Path) -> None:
    """Helper to write an empty JSON file at the given target path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}")


def test_parse_metric_path_no_alpha(tmp_path: Path) -> None:
    """Verify parse_metric_path parses standard stage run IDs correctly."""
    results_root = tmp_path / ArtifactDir.RESULTS
    path = (
        results_root
        / ExperimentStage.NBAIOT_MAIN.value
        / ThresholdPolicy.GLOBAL_THRESHOLD.value
        / "seed_42"
        / ArtifactFile.METRICS
    )
    run_id = parse_metric_path(tmp_path, path)
    assert isinstance(run_id, PolicyRunId)
    assert run_id.stage == ExperimentStage.NBAIOT_MAIN
    assert run_id.policy == ThresholdPolicy.GLOBAL_THRESHOLD
    assert run_id.seed == 42


def test_parse_metric_path_with_alpha(tmp_path: Path) -> None:
    """Verify parse_metric_path parses optional stage run IDs correctly."""
    results_root = tmp_path / ArtifactDir.RESULTS
    path = (
        results_root
        / ExperimentStage.NBAIOT_MAIN.value
        / ThresholdPolicy.LOCAL_THRESHOLD.value
        / "seed_7"
        / ArtifactFile.METRICS
    )
    run_id = parse_metric_path(tmp_path, path)
    assert run_id.stage == ExperimentStage.NBAIOT_MAIN
    assert run_id.policy == ThresholdPolicy.LOCAL_THRESHOLD
    assert run_id.seed == 7


def test_parse_metric_path_invalid_seed_raises(tmp_path: Path) -> None:
    """Verify parse_metric_path raises ValueError if seed segment is malformed."""
    results_root = tmp_path / ArtifactDir.RESULTS
    path = (
        results_root
        / ExperimentStage.NBAIOT_MAIN.value
        / ThresholdPolicy.GLOBAL_THRESHOLD.value
        / "bad"
        / ArtifactFile.METRICS
    )
    with pytest.raises(ValueError, match="Expected seed segment"):
        parse_metric_path(tmp_path, path)


def test_parse_metric_path_invalid_stage_raises(tmp_path: Path) -> None:
    """Verify parse_metric_path raises ValueError if stage segment is unrecognized."""
    results_root = tmp_path / ArtifactDir.RESULTS
    path = (
        results_root
        / "x"
        / ThresholdPolicy.GLOBAL_THRESHOLD.value
        / "seed_1"
        / ArtifactFile.METRICS
    )
    with pytest.raises(ValueError):
        parse_metric_path(tmp_path, path)


def test_completed_metric_paths_empty(tmp_path: Path) -> None:
    """Verify completed_metric_paths returns an empty list when no metrics are written."""
    assert completed_metric_paths(tmp_path) == []


def test_completed_metric_paths_finds_metrics(tmp_path: Path) -> None:
    """Verify completed_metric_paths discovers all metrics.json files."""
    results = tmp_path / ArtifactDir.RESULTS
    _write_dummy_file(
        results
        / ExperimentStage.NBAIOT_MAIN.value
        / ThresholdPolicy.GLOBAL_THRESHOLD.value
        / "seed_0"
        / ArtifactFile.METRICS
    )
    _write_dummy_file(
        results
        / ExperimentStage.NBAIOT_MAIN.value
        / ThresholdPolicy.LOCAL_THRESHOLD.value
        / "seed_0"
        / ArtifactFile.METRICS
    )
    paths = completed_metric_paths(tmp_path)
    assert len(paths) == 2


def test_completed_metric_paths_with_alpha(tmp_path: Path) -> None:
    """Verify completed_metric_paths discovers metrics.json for optional stages."""
    results = tmp_path / ArtifactDir.RESULTS
    _write_dummy_file(
        results
        / ExperimentStage.NBAIOT_MAIN.value
        / ThresholdPolicy.GLOBAL_THRESHOLD.value
        / "seed_0"
        / ArtifactFile.METRICS
    )
    paths = completed_metric_paths(tmp_path)
    assert len(paths) == 1


class TestProvenanceSourcePaths:
    """Tests verifying source files lists and their non-empty hash digests."""

    def test_all_provenance_source_files_exist(self) -> None:
        """Verify that all files tracked under provenance source file paths exist on disk."""
        all_files = (
            *SCORING_SOURCE_FILES,
            *THRESHOLD_SOURCE_FILES,
            *METRICS_SOURCE_FILES,
        )
        missing = [str(p) for p in all_files if hash_file(p) == "MISSING"]
        assert not missing, f"provenance source files not found: {missing}"

    def test_provenance_hashes_are_not_missing_sentinel(self) -> None:
        """Verify that the generated source hashes do not match the missing file sentinel hash."""
        for group in (
            SCORING_SOURCE_FILES,
            THRESHOLD_SOURCE_FILES,
            METRICS_SOURCE_FILES,
        ):
            digest = source_hash(list(group))
            all_missing = source_hash([p.with_suffix(".does_not_exist") for p in group])
            assert digest != all_missing


def _base_params(**overrides: object) -> RecomputationParams:
    """Helper to build standard RecomputationParams input structures."""
    defaults: dict = {
        "run_id": "nbaiot_main_global_threshold_seed0",
        "seed": 0,
        "stage": ExperimentStage.NBAIOT_MAIN,
        "policy": ThresholdPolicy.GLOBAL_THRESHOLD,
        "client_id": "c1",
        "tp": 10,
        "fp": 0,
        "tn": 10,
        "fn": 0,
        "n_benign": 10,
        "n_attack": 10,
        "saved_fpr": 0.0,
        "saved_tpr": 1.0,
        "saved_balanced_accuracy": 1.0,
        "saved_macro_f1": 1.0,
    }
    defaults.update(overrides)
    return RecomputationParams(**defaults)


def test_recomputation_fails_on_wrong_fpr() -> None:
    """Verify that a mismatch between saved and recomputed FPR is flagged as FAIL."""
    records: list = []
    append_recomputation_records(records, _base_params(saved_fpr=0.99))
    fpr_rows = [r for r in records if r.metric == MetricName.FPR]
    assert len(fpr_rows) == 1
    assert fpr_rows[0].status == DenominatorStatus.FAIL
    assert fpr_rows[0].recomputed_value == pytest.approx(0.0)


def test_recomputation_excludes_attack_metrics_when_n_attack_zero() -> None:
    """Verify attack metrics are marked EXCLUDED_EVALUATION_INCOMPLETE if n_attack is zero."""
    records: list = []
    append_recomputation_records(
        records,
        _base_params(
            tp=0,
            fp=1,
            tn=9,
            fn=0,
            n_benign=10,
            n_attack=0,
            saved_fpr=0.1,
            saved_tpr=None,
            saved_balanced_accuracy=None,
            saved_macro_f1=None,
        ),
    )
    for m in (MetricName.TPR, MetricName.BALANCED_ACCURACY, MetricName.MACRO_F1):
        rows = [r for r in records if r.metric == m]
        assert rows[0].status == DenominatorStatus.EXCLUDED_EVALUATION_INCOMPLETE

    fpr_rows = [r for r in records if r.metric == MetricName.FPR]
    assert fpr_rows[0].status == DenominatorStatus.PASS


def test_recomputation_fails_on_denominator_mismatch() -> None:
    """Verify validation fails if denominator totals disagree with raw confusion matrix counts."""
    records: list = []

    append_recomputation_records(
        records,
        _base_params(
            tp=5,
            fp=1,
            tn=8,
            fn=1,
            n_benign=10,
            n_attack=6,
            saved_fpr=0.1,
            saved_tpr=0.9,
            saved_balanced_accuracy=0.9,
            saved_macro_f1=0.9,
        ),
    )
    fpr_rows = [r for r in records if r.metric == MetricName.FPR]
    assert len(fpr_rows) == 1
    assert fpr_rows[0].status == DenominatorStatus.FAIL
    assert fpr_rows[0].recomputed_value == pytest.approx(1 / 9)


def test_manifest_schema_validation() -> None:
    """Verify that RunManifestRecord conforms to schema and JSON serialization requirements."""
    record = RunManifestRecord(
        run_id="nbaiot_main_global_threshold_seed0",
        timestamp="2026-04-26T00:00:00+00:00",
        git_commit_hash="abc",
        seed=0,
        dataset=DatasetID.NBAIOT,
        stage=ExperimentStage.NBAIOT_MAIN,
        policy=ThresholdPolicy.GLOBAL_THRESHOLD,
        client_count=4,
        split_hash="split",
        model_hash="model",
        encoder_hash="model",
        training_config_hash="cfg",
        preprocessing_config_hash="prep",
        scoring_code_hash="score",
        threshold_code_hash="thr",
        metrics_code_hash="metrics",
        artifact_schema_version="1.0",
        convergence_round=None,
        convergence_criterion_value=None,
        convergence_status=ConvergenceStatus.MISSING_SUMMARY,
        eligible_clients=4,
        calibration_pending_clients=0,
        evaluation_incomplete_clients=0,
        feature_count=115,
        feature_list_hash="features",
        threshold_aggregation_method=ThresholdAggregationMethod.ELIGIBLE_CLIENT_ARITHMETIC_MEAN,
        normalization_scope=NormalizationScope.PER_CLIENT_ZSCORE,
        train_count=None,
        calibration_count=None,
        test_count=24,
    )
    assert record.policy == ThresholdPolicy.GLOBAL_THRESHOLD
    assert record.model_dump(mode="json")["convergence_status"] == "MISSING_SUMMARY"


def test_split_hash_stability(tmp_path: Path) -> None:
    """Verify that JSON serialization key order differences do not affect split hash outcomes."""
    manifest = tmp_path / ArtifactFile.MANIFEST
    manifest.write_text(json.dumps({"b": 2, "a": 1}))
    first = hash_jsonable(json.loads(manifest.read_text()))
    manifest.write_text(json.dumps({"a": 1, "b": 2}))
    assert hash_jsonable(json.loads(manifest.read_text())) == first


def test_fpr_and_tpr_denominators() -> None:
    """Verify that benign/attack counts sum correctly from validation confusion matrices."""
    ct = ClientThreshold(
        client_id="c",
        threshold=0.5,
        status=ClientStatus.ELIGIBLE,
        strategy=ThresholdPolicy.GLOBAL_THRESHOLD,
    )
    rec = compute_client_record("c", np.array([0.1, 0.9]), np.array([0.8, 0.2]), ct)
    assert rec.confusion.fp + rec.confusion.tn == rec.n_benign
    assert rec.confusion.tp + rec.confusion.fn == rec.n_attack


def test_binary_macro_f1_ignores_multiclass_attack_names() -> None:
    """Verify that F1 score uses binary labels even under multiclass targets."""
    benign = np.array([0.1, 0.2])
    attack = np.array([0.9, 0.3])
    ct = ClientThreshold(
        client_id="c",
        threshold=0.5,
        status=ClientStatus.ELIGIBLE,
        strategy=ThresholdPolicy.GLOBAL_THRESHOLD,
    )
    rec = compute_client_record("c", benign, attack, ct)
    expected = f1_score(
        [0, 0, 1, 1],
        [0, 0, 1, 0],
        average="macro",
        labels=[0, 1],
        zero_division=0,  # type: ignore[arg-type]
    )
    multiclass_wrong = f1_score(
        [0, 0, 2, 3],
        [0, 0, 1, 0],
        average="macro",
        zero_division=0,  # type: ignore[arg-type]
    )
    assert rec.metrics.macro_f1 == expected
    assert rec.metrics.macro_f1 != multiclass_wrong


def test_evaluation_incomplete_exclusion() -> None:
    """Verify TPR and macro F1 are NaN if the client test attack set is empty."""
    ct = ClientThreshold(
        client_id="c",
        threshold=0.5,
        status=ClientStatus.ELIGIBLE,
        strategy=ThresholdPolicy.GLOBAL_THRESHOLD,
    )
    rec = compute_client_record("c", np.array([0.1, 0.9]), np.array([]), ct)
    assert np.isnan(rec.metrics.tpr)
    assert np.isnan(rec.metrics.macro_f1)


def test_deterministic_fixture_repeatability() -> None:
    """Verify seed setting behaves deterministically across random generators."""
    set_seeds(0)
    rng = np.random.default_rng(0)
    first = rng.random(5)
    set_seeds(0)
    rng2 = np.random.default_rng(0)
    second = rng2.random(5)
    assert np.array_equal(first, second)


def test_audit_warning_generation() -> None:
    """Verify WarningRecord severity values map successfully to enum strings."""
    warning = WarningRecord(
        severity=AuditSeverity.BLOCKED_PENDING_RUN,
        code=WarningCode.MISSING_CONVERGENCE_CURVES,
        message="missing",
        exact_command="datp sweep --resume",
    )
    assert warning.severity == "BLOCKED_PENDING_RUN"


_CLIENTS = (
    "Danmini_Doorbell",
    "Ecobee_Thermostat",
    "Ennio_Doorbell",
    "Philips_B120N10_Baby_Monitor",
)


_SAFE_SCORE_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")


def _safe_score_path(root: Path, stage: str, client_id: str) -> Path:
    """Helper to build a relative-safe score parquet file path."""
    if not _SAFE_SCORE_NAME.fullmatch(client_id):
        raise ValueError(f"Unsafe client id in score fixture: {client_id}")
    base = (root / "scores/nbaiot_main/seed_0").resolve()
    path = (base / stage / f"{client_id}.parquet").resolve()
    if not path.is_relative_to(base):
        raise ValueError(f"Score fixture path escapes base: {path}")
    return path


def _write_scores(root: Path) -> None:
    """Helper to write synthetic scores across clients into workspace directories."""
    for index, client_id in enumerate(_CLIENTS):
        cal = np.linspace(0.01, 0.05 + index * 0.01, 120, dtype=float)
        benign = np.array([0.01, 0.02, 0.07], dtype=float)
        attack = np.array([0.08, 0.09, 0.10], dtype=float)
        for stage, values in {
            "cal": cal,
            "test_benign": benign,
            "test_attack": attack,
        }.items():
            write_artifact(
                pl.DataFrame({ScoringColumn.RECONSTRUCTION_ERROR: values}),
                _safe_score_path(root, stage, client_id),
            )


def _make_client_metric_entry(client_id: str, policy: ThresholdPolicy) -> dict:
    """Helper to package synthetic validation client metric dictionary entry."""
    ct = ClientThreshold(
        client_id=client_id,
        threshold=0.06,
        status=ClientStatus.ELIGIBLE,
        strategy=policy,
    )
    rec = compute_client_record(
        client_id, np.array([0.01, 0.02, 0.07]), np.array([0.08, 0.09, 0.10]), ct
    )
    return {
        "client_id": client_id,
        "fpr": rec.metrics.fpr,
        "tpr": rec.metrics.tpr,
        "tnr": rec.metrics.tnr,
        "fnr": rec.metrics.fnr,
        "precision": rec.metrics.precision,
        "recall": rec.metrics.recall,
        "balanced_accuracy": rec.metrics.balanced_accuracy,
        "macro_f1": rec.metrics.macro_f1,
        "confusion_matrix": {
            "tp": rec.confusion.tp,
            "fp": rec.confusion.fp,
            "tn": rec.confusion.tn,
            "fn": rec.confusion.fn,
        },
        "n_benign": rec.n_benign,
        "n_attack": rec.n_attack,
        "calibration_pending": False,
        "evaluation_incomplete": False,
        "threshold_value": 0.06,
        "threshold_source": POLICY_THRESHOLD_SOURCE[policy].value,
    }


def _metrics_payload(policy: ThresholdPolicy) -> dict:
    """Helper to mock metrics file payload structures for a given threshold policy."""
    per_client = [_make_client_metric_entry(cid, policy) for cid in _CLIENTS]
    return {
        "schema_version": "2",
        "metric_schema_version": "2",
        "threshold_schema_version": "1",
        "run_id": f"nbaiot_main_{policy.value}_seed0",
        "run_kind": "core_ladder",
        "dataset": "nbaiot",
        "policy": policy.value,
        "threshold_scope": "eligible_client_arithmetic_mean",
        "threshold_strategy_name": policy.value,
        "coverage_ratio": 1.0,
        "cv_fpr": 0.0 if policy == ThresholdPolicy.LOCAL_THRESHOLD else 0.1,
        "mean_fpr": 0.0,
        "std_fpr": 0.0,
        "cv_tpr": 0.0,
        "iqr_fpr": 0.0,
        "iqr_tpr": 0.0,
        "worst_client_fpr": 0.0,
        "worst_ba": 1.0,
        "p10_macro_f1": 1.0,
        "worst_client_id": _CLIENTS[0],
        "eligible_count": len(_CLIENTS),
        "client_count": len(_CLIENTS),
        "pending_count": 0,
        "eval_incomplete_count": 0,
        "eligible_ids": list(_CLIENTS),
        "pending_ids": [],
        "eval_incomplete_ids": [],
        "aggregate_metrics": {
            "cv_fpr": 0.0 if policy == ThresholdPolicy.LOCAL_THRESHOLD else 0.1
        },
        "provenance": {
            "config_identity": "fixture",
            "split_manifest_identity": "fixture",
            "model_identity": "fixture",
            "score_artifact_identity": "fixture",
            "metric_code_version": "fixture",
            "threshold_code_version": "fixture",
            "package_version": "fixture",
            "generated_at_utc": "2026-01-01T00:00:00+00:00",
        },
        "per_client": per_client,
        "stage": "nbaiot_main",
        "seed": 0,
        "tau_global": 0.06,
    }


def _write_minimal_outputs(root: Path) -> None:
    """Helper to populate mock workspace directories with manifests, configs, and scores."""
    _write_scores(root)
    manifest = {
        "dataset": "nbaiot",
        "file_hashes": {"fixture": "abc"},
        "metadata": {"n_features": 115, "n_devices": len(_CLIENTS), "n_clients": None},
        "created": "2026-04-26T00:00:00+00:00",
    }
    manifest_path = root / "data/processed/nbaiot" / ArtifactFile.MANIFEST
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest))
    scoring_manifest = root / "scores/nbaiot_main/seed_0" / ArtifactFile.SCORING_MANIFEST
    scoring_manifest.write_text(json.dumps({"model_hash": "fixture-model-hash"}))
    for policy in (
        ThresholdPolicy.GLOBAL_THRESHOLD,
        ThresholdPolicy.LOCAL_THRESHOLD,
        ThresholdPolicy.CLUSTER_THRESHOLD,
        ThresholdPolicy.CLUSTER_THRESHOLD,
    ):
        result_dir = root / "results/nbaiot_main" / policy.value / "seed_0"
        result_dir.mkdir(parents=True, exist_ok=True)
        (result_dir / ArtifactFile.METRICS).write_text(
            json.dumps(_metrics_payload(policy))
        )
        (result_dir / ArtifactFile.RESOLVED_CONFIG).write_text("seed: 0\n")


def test_results_audit_generates_core_artifacts(tmp_path: Path) -> None:
    """Verify that results audit generates all expected summary, manifests, and checks CSVs."""
    outputs = tmp_path / "outputs"
    audit_dir = tmp_path / "audit"

    _write_minimal_outputs(outputs)
    paths = run_results_audit(base_dir=outputs, audit_dir=audit_dir, cfg=BASE_CONFIG)

    from datp.enums import AuditOutputName

    assert dict(paths.items())[AuditOutputName.RUN_MANIFEST].is_file()
    assert (audit_dir / AuditArtifact.POLICY_INVARIANTS).is_file()
    assert (audit_dir / AuditArtifact.RUN_MANIFEST).is_file()
    assert (audit_dir / AuditArtifact.RECONSTRUCTION_ERROR_SUMMARY).is_file()
    assert (audit_dir / AuditArtifact.METRIC_DENOMINATOR_AUDIT).is_file()
    assert (audit_dir / AuditArtifact.THRESHOLD_VALUES).is_file()
    assert (audit_dir / AuditArtifact.WARNINGS).is_file()
    assert (audit_dir / AuditArtifact.AUDIT_SUMMARY).is_file()

    invariants = json.loads((audit_dir / AuditArtifact.POLICY_INVARIANTS).read_text())
    assert invariants[0]["status"] == "PASS"
    assert invariants[0]["split_hash_shared"] is True
    assert invariants[0]["reconstruction_error_hashes_shared"] is True

    thresholds = pd.read_csv(audit_dir / AuditArtifact.THRESHOLD_VALUES)
    assert "threshold_aggregation_method" in thresholds.columns
    assert "local_tau_i" in thresholds.columns
    global_rows = thresholds[
        thresholds["policy"] == ThresholdPolicy.GLOBAL_THRESHOLD.value
    ]
    assert set(global_rows["threshold_aggregation_method"]) == {
        "eligible_client_arithmetic_mean"
    }


def test_results_audit_generates_severity_trend_and_cluster_stability(
    tmp_path: Path,
) -> None:
    """Verify that results audit generates cluster stability CSV and includes summaries."""
    outputs = tmp_path / "outputs"
    audit_dir = tmp_path / "audit"

    _write_minimal_outputs(outputs)
    paths = run_results_audit(base_dir=outputs, audit_dir=audit_dir, cfg=BASE_CONFIG)

    assert "cluster_stability" in paths
    assert (audit_dir / AuditArtifact.CLUSTER_STABILITY).is_file()

    summary = (audit_dir / AuditArtifact.AUDIT_SUMMARY).read_text()
    assert "Controlled threshold policies share the trained encoder" in summary


def test_results_audit_generates_seed_deltas(tmp_path: Path) -> None:
    """Verify that seed deltas audit CSV is generated with all expected schema columns."""
    from datp.enums import AuditArtifact as _Art

    outputs = tmp_path / "outputs"
    audit_dir = tmp_path / "audit"

    _write_minimal_outputs(outputs)
    run_results_audit(base_dir=outputs, audit_dir=audit_dir, cfg=BASE_CONFIG)
    csv_path = audit_dir / _Art.SEED_DELTAS
    assert csv_path.is_file()
    df = pd.read_csv(csv_path)
    for col in (
        "stage",
        "seed",
        "global_cv_fpr",
        "local_cv_fpr",
        "delta_cv_fpr_global_minus_local",
        "coverage_ratio",
    ):
        assert col in df.columns


def test_results_audit_generates_metric_denominator_audit(tmp_path: Path) -> None:
    """Verify that metric denominator audit CSV file is successfully generated."""
    from datp.enums import AuditArtifact as _Art

    outputs = tmp_path / "outputs"
    audit_dir = tmp_path / "audit"

    _write_minimal_outputs(outputs)
    paths = run_results_audit(base_dir=outputs, audit_dir=audit_dir, cfg=BASE_CONFIG)
    assert (audit_dir / _Art.METRIC_DENOMINATOR_AUDIT).is_file()
    assert "metric_denominator_audit" in paths


def test_results_audit_fpr_companion_has_required_columns(tmp_path: Path) -> None:
    """Verify that FPR companion metrics audit CSV contains all expected fields."""
    from datp.enums import AuditArtifact as _Art

    outputs = tmp_path / "outputs"
    audit_dir = tmp_path / "audit"

    _write_minimal_outputs(outputs)
    run_results_audit(base_dir=outputs, audit_dir=audit_dir, cfg=BASE_CONFIG)
    df = pd.read_csv(audit_dir / _Art.FPR_COMPANION_METRICS)
    for col in (
        "cv_fpr",
        "mean_fpr",
        "std_fpr",
        "iqr_fpr",
        "worst_client_fpr",
        "coverage_ratio",
    ):
        assert col in df.columns, f"Missing FPR companion column: {col}"


def test_results_audit_generates_metric_recomputation_csv(tmp_path: Path) -> None:
    """Verify that metric recomputations audit CSV evaluates PASS/FAIL correctly."""
    from datp.enums import AuditArtifact as _Art

    outputs = tmp_path / "outputs"
    audit_dir = tmp_path / "audit"

    _write_minimal_outputs(outputs)
    paths = run_results_audit(base_dir=outputs, audit_dir=audit_dir, cfg=BASE_CONFIG)
    assert (audit_dir / _Art.METRIC_RECOMPUTATION_AUDIT).is_file()
    assert "metric_recomputation_audit" in paths
    df = pd.read_csv(audit_dir / _Art.METRIC_RECOMPUTATION_AUDIT)
    for col in (
        "run_id",
        "seed",
        "stage",
        "policy",
        "client_id",
        "metric",
        "saved_value",
        "recomputed_value",
        "abs_diff",
        "status",
    ):
        assert col in df.columns, f"Missing metric recomputation column: {col}"
    assert set(df["status"]).issubset(
        {"PASS", "FAIL", "EXCLUDED_EVALUATION_INCOMPLETE", "BLOCKED_PENDING_RUN"}
    )
    assert (df["status"] == "FAIL").sum() == 0, (
        "All saved metrics must match recomputed values"
    )


def test_naked_cv_fpr_emits_fail_warning(tmp_path: Path) -> None:
    """Verify NAKED_CV_FPR warning is emitted if metrics are missing mean/std helper stats."""
    outputs = tmp_path / "outputs"
    audit_dir = tmp_path / "audit"

    _write_minimal_outputs(outputs)
    result_dir = (
        outputs
        / "results/nbaiot_main"
        / ThresholdPolicy.GLOBAL_THRESHOLD.value
        / "seed_0"
    )
    payload = json.loads((result_dir / ArtifactFile.METRICS).read_text("utf-8"))
    del payload["mean_fpr"]
    del payload["std_fpr"]
    (result_dir / ArtifactFile.METRICS).write_text(json.dumps(payload))
    run_results_audit(base_dir=outputs, audit_dir=audit_dir, cfg=BASE_CONFIG)

    warnings_text = (audit_dir / AuditArtifact.WARNINGS).read_text()
    assert WarningCode.NAKED_CV_FPR in warnings_text, (
        "Expected NAKED_CV_FPR warning in audit output"
    )


_CELL_A = InvariantKey(stage=ExperimentStage.NBAIOT_MAIN, seed=0)


_CELL_B = InvariantKey(stage=ExperimentStage.NBAIOT_MAIN, seed=1)


_HASH_MAP_REF = frozenset(
    {
        ScoreArtifactHash(ScoringStage.CAL, "client_1", "aaa"),
        ScoreArtifactHash(ScoringStage.TEST_BENIGN, "client_1", "bbb"),
        ScoreArtifactHash(ScoringStage.TEST_ATTACK, "client_1", "ccc"),
    }
)


_HASH_MAP_ALT = frozenset(
    {
        ScoreArtifactHash(ScoringStage.CAL, "client_1", "aaa"),
        ScoreArtifactHash(ScoringStage.TEST_BENIGN, "client_1", "bbb"),
        ScoreArtifactHash(ScoringStage.TEST_ATTACK, "client_1", "XXX"),
    }
)


def _inputs(
    cell: InvariantKey,
    baselines: list[ThresholdPolicy],
    split: str = "split1",
    model: str = "model1",
    scoring: str = "score1",
    metrics: str = "metrics1",
) -> dict[InvariantKey, dict[ThresholdPolicy, InvariantHashes]]:
    """Helper to build standard invariant mock payload configurations."""
    return {
        cell: {
            b: InvariantHashes(
                split_hash=split,
                model_hash=model,
                encoder_hash=model,
                scoring_code_hash=scoring,
                metrics_code_hash=metrics,
            )
            for b in baselines
        }
    }


def _score_hashes(
    cell: InvariantKey,
    baselines: list[ThresholdPolicy],
    hash_map: frozenset[ScoreArtifactHash] | None = None,
) -> dict[InvariantKey, dict[ThresholdPolicy, frozenset[ScoreArtifactHash]]]:
    """Helper to mock score arrays hash structures for various threshold policies."""
    if hash_map is None:
        hash_map = _HASH_MAP_REF
    return {cell: {b: hash_map for b in baselines}}


class TestInvariantPass:
    """Tests verifying audit success criteria under uniform invariants."""

    def test_all_controlled_policies_pass_nbaiot_main(self) -> None:
        """Verify that matching inputs pass the invariant audit on standard NBAIoT stages."""
        baselines = [
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        ]
        results = build_invariant_results(
            _inputs(_CELL_A, baselines),
            _score_hashes(_CELL_A, baselines),
        )
        assert len(results) == 1
        assert results[0].status == AuditStatus.PASS
        assert results[0].split_hash_shared is True
        assert results[0].model_or_encoder_hash_shared is True
        assert results[0].reconstruction_error_hashes_shared is True
        assert results[0].scoring_code_hash_shared is True
        assert results[0].metrics_code_hash_shared is True
        assert results[0].disallowed_differences == []

    def test_second_seed_controlled_policies_pass(self) -> None:
        """Verify that matching inputs pass for another seed of the main stage."""
        baselines = [
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        ]
        results = build_invariant_results(
            _inputs(_CELL_B, baselines),
            _score_hashes(_CELL_B, baselines),
        )
        assert results[0].status == AuditStatus.PASS


class TestInvariantFail:
    """Tests verifying audit failure conditions under mismatching hashes/arrays."""

    def test_model_hash_differs_marks_fail(self) -> None:
        """Verify model hash mismatches result in audit FAIL status."""
        baselines = [
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        ]
        inv_inputs: dict[InvariantKey, dict[ThresholdPolicy, InvariantHashes]] = {
            _CELL_A: {
                ThresholdPolicy.GLOBAL_THRESHOLD: InvariantHashes(
                    split_hash="s1",
                    model_hash="model_A",
                    encoder_hash="model_A",
                    scoring_code_hash="sc",
                    metrics_code_hash="mc",
                ),
                ThresholdPolicy.LOCAL_THRESHOLD: InvariantHashes(
                    split_hash="s1",
                    model_hash="model_B",
                    encoder_hash="model_B",
                    scoring_code_hash="sc",
                    metrics_code_hash="mc",
                ),
                ThresholdPolicy.CLUSTER_THRESHOLD: InvariantHashes(
                    split_hash="s1",
                    model_hash="model_A",
                    encoder_hash="model_A",
                    scoring_code_hash="sc",
                    metrics_code_hash="mc",
                ),
            }
        }
        results = build_invariant_results(
            inv_inputs,
            _score_hashes(_CELL_A, baselines),
        )
        assert results[0].status == AuditStatus.FAIL
        assert "model_hash_or_encoder_hash" in results[0].disallowed_differences
        assert results[0].model_or_encoder_hash_shared is False

    def test_score_array_hash_differs_marks_fail(self) -> None:
        """Verify client score parquet array mismatches result in audit FAIL status."""
        baselines = [
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        ]
        score_hashes: dict[
            InvariantKey, dict[ThresholdPolicy, frozenset[ScoreArtifactHash]]
        ] = {
            _CELL_B: {
                ThresholdPolicy.GLOBAL_THRESHOLD: _HASH_MAP_REF,
                ThresholdPolicy.LOCAL_THRESHOLD: _HASH_MAP_ALT,
                ThresholdPolicy.CLUSTER_THRESHOLD: _HASH_MAP_REF,
            }
        }
        results = build_invariant_results(
            _inputs(_CELL_B, baselines),
            score_hashes,
        )
        assert results[0].status == AuditStatus.FAIL
        assert results[0].reconstruction_error_hashes_shared is False
        assert "reconstruction_error_arrays" in results[0].disallowed_differences

    def test_split_hash_differs_marks_fail(self) -> None:
        """Verify split configuration hash mismatches result in audit FAIL status."""
        inv_inputs: dict[InvariantKey, dict[ThresholdPolicy, InvariantHashes]] = {
            _CELL_A: {
                ThresholdPolicy.GLOBAL_THRESHOLD: InvariantHashes(
                    split_hash="s1",
                    model_hash="m1",
                    encoder_hash="m1",
                    scoring_code_hash="sc",
                    metrics_code_hash="mc",
                ),
                ThresholdPolicy.LOCAL_THRESHOLD: InvariantHashes(
                    split_hash="s2",
                    model_hash="m1",
                    encoder_hash="m1",
                    scoring_code_hash="sc",
                    metrics_code_hash="mc",
                ),
                ThresholdPolicy.CLUSTER_THRESHOLD: InvariantHashes(
                    split_hash="s1",
                    model_hash="m1",
                    encoder_hash="m1",
                    scoring_code_hash="sc",
                    metrics_code_hash="mc",
                ),
            }
        }
        results = build_invariant_results(
            inv_inputs,
            _score_hashes(
                _CELL_A,
                [
                    ThresholdPolicy.GLOBAL_THRESHOLD,
                    ThresholdPolicy.LOCAL_THRESHOLD,
                    ThresholdPolicy.CLUSTER_THRESHOLD,
                ],
            ),
        )
        assert results[0].status == AuditStatus.FAIL
        assert "split_hash" in results[0].disallowed_differences


class TestInvariantBlocked:
    """Tests verifying audit blocked/pending status when policy elements are missing."""

    def test_missing_policies_marks_blocked(self) -> None:
        """Verify audit is marked BLOCKED_PENDING_RUN if a required threshold policy is missing."""
        baselines = [ThresholdPolicy.GLOBAL_THRESHOLD, ThresholdPolicy.LOCAL_THRESHOLD]
        results = build_invariant_results(
            _inputs(_CELL_A, baselines),
            _score_hashes(_CELL_A, baselines),
        )
        assert results[0].status == AuditStatus.BLOCKED_PENDING_RUN
        assert ThresholdPolicy.CLUSTER_THRESHOLD in results[0].missing_policies

    def test_no_score_hashes_marks_blocked_not_fail(self) -> None:
        """Verify absence of score hashes marks audit as blocked rather than failing."""
        baselines = [
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        ]
        results = build_invariant_results(
            _inputs(_CELL_A, baselines),
            {},
        )
        assert results[0].status == AuditStatus.BLOCKED_PENDING_RUN
        assert results[0].reconstruction_error_hashes_shared is False


_REAL_DEVICES = list(DEVICE_FAMILY_MAP.keys())


def _make_cal_errors(n_samples: int = 120) -> dict[str, np.ndarray]:
    """Helper to build synthetic client calibration error values."""
    rng = np.random.default_rng(42)
    return {
        name: rng.normal(loc=0.1 + i * 0.03, scale=0.05, size=n_samples)
        for i, name in enumerate(_REAL_DEVICES)
    }


@pytest.mark.parametrize(
    "policy",
    [
        ThresholdPolicy.GLOBAL_THRESHOLD,
        ThresholdPolicy.LOCAL_THRESHOLD,
        ThresholdPolicy.CLUSTER_THRESHOLD,
    ],
)
def test_load_score_arrays_thresholds_match_derive_threshold(
    monkeypatch: pytest.MonkeyPatch,
    policy: ThresholdPolicy,
) -> None:
    """Verify loaded score thresholds match derive_threshold outputs for all policies."""
    cal_errors = _make_cal_errors()
    tau_global = 0.15
    cfg = BASE_CONFIG

    def fake_stage_files(_score_root: Path, stage: ScoringStage) -> list[Path]:
        if stage == ScoringStage.CAL:
            return [Path(f"{client_id}.parquet") for client_id in cal_errors]
        return []

    monkeypatch.setattr(results, "score_stage_files", fake_stage_files)
    monkeypatch.setattr(
        results,
        "read_scores",
        lambda path: cal_errors[path.stem],
    )

    arrays = results.load_score_arrays(
        cast(results.AuditAccumulator, SimpleNamespace(warnings=[])),
        cast(
            results.RunContext,
            SimpleNamespace(
                paths=SimpleNamespace(score_root=Path("scores")),
                identity=SimpleNamespace(policy=policy, seed=0, run_id="run"),
                metrics=SimpleNamespace(tau_global=tau_global),
            ),
        ),
        cfg,
    )
    canonical_result = derive_threshold(
        ThresholdDerivation(
            policy=policy,
            client_errors=cal_errors,
            n_min=cfg.threshold.n_min,
            q=cfg.threshold.q,
            tau_global=tau_global,
            threshold_cfg=cfg.threshold,
            seed=0,
        )
    )

    assert arrays.threshold_result is not None
    assert arrays.threshold_result.run.policy == canonical_result.run.policy
    assert arrays.threshold_result.tau_global == pytest.approx(
        canonical_result.tau_global
    )
    assert arrays.threshold_result.eligible_count == canonical_result.eligible_count
    assert arrays.threshold_result.pending_count == canonical_result.pending_count
    for actual, expected in zip(
        sorted(
            arrays.threshold_result.client_thresholds,
            key=lambda item: item.client_id,
        ),
        sorted(canonical_result.client_thresholds, key=lambda item: item.client_id),
    ):
        assert actual.client_id == expected.client_id
        assert actual.threshold == pytest.approx(expected.threshold, abs=1e-12)
        assert actual.status is expected.status
