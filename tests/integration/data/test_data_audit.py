from __future__ import annotations

import json
from pathlib import Path

import pytest

from datp.config.stages import ExperimentStage
from datp.data.common.audit import audit_partitions
from datp.data.contracts import PartitionResult
from datp.data.datasets.nbaiot import DEVICE_DIRS

REQUIRED_CLIENT_FIELDS = {
    "benign_train_count",
    "benign_cal_count",
    "test_benign_count",
    "test_attack_count",
    "attack_classes",
    "calibration_pending",
}

N_EXPECTED_DEVICES = 9


def _make_nbaiot_partition_results(
    cal_count: int = 200,
    eval_incomplete: bool = False,
) -> dict[str, PartitionResult]:
    results: dict[str, PartitionResult] = {}
    for i, device_id in enumerate(DEVICE_DIRS):
        results[device_id] = PartitionResult(
            benign_train_count=5000 + i * 100,
            benign_cal_count=cal_count + i * 10,
            test_benign_count=2000 + i * 50,
            test_attack_count=3000 + i * 200,
            attack_classes=["gafgyt_combo", "gafgyt_junk", "mirai_ack"],
            calibration_pending=(cal_count + i * 10) < 100,
            evaluation_incomplete=eval_incomplete,
        )
    return results


@pytest.mark.integration
class TestAuditJsonSchema:
    def test_audit_writes_json_with_all_devices(self, tmp_path: Path) -> None:
        results = _make_nbaiot_partition_results()
        audit = audit_partitions(
            results, stage=ExperimentStage.NBAIOT_MAIN, output_dir=tmp_path, n_min=100
        )

        audit_file = tmp_path / "data_audit" / "nbaiot_main_audit.json"
        assert audit_file.exists()

        assert audit.n_clients == N_EXPECTED_DEVICES
        assert len(audit.clients) == N_EXPECTED_DEVICES

        for device_id in DEVICE_DIRS:
            assert device_id in audit.clients, f"Device {device_id} missing from audit"

    def test_audit_per_client_required_fields(self, tmp_path: Path) -> None:
        results = _make_nbaiot_partition_results()
        audit = audit_partitions(
            results, stage=ExperimentStage.NBAIOT_MAIN, output_dir=tmp_path, n_min=100
        )

        for client_id, client_info in audit.clients.items():
            missing = REQUIRED_CLIENT_FIELDS - set(
                type(client_info).model_fields.keys()
            )
            assert not missing, f"Client {client_id} missing required fields: {missing}"

    def test_audit_field_types(self, tmp_path: Path) -> None:
        results = _make_nbaiot_partition_results()
        audit = audit_partitions(
            results, stage=ExperimentStage.NBAIOT_MAIN, output_dir=tmp_path, n_min=100
        )

        for client_id, info in audit.clients.items():
            assert isinstance(info.benign_train_count, int)
            assert isinstance(info.benign_cal_count, int)
            assert isinstance(info.test_benign_count, int)
            assert isinstance(info.test_attack_count, int)
            assert isinstance(info.attack_classes, list)
            assert isinstance(info.calibration_pending, bool)

    def test_audit_json_roundtrip(self, tmp_path: Path) -> None:
        results = _make_nbaiot_partition_results()
        audit_partitions(results, stage=ExperimentStage.NBAIOT_MAIN, output_dir=tmp_path, n_min=100)

        audit_file = tmp_path / "data_audit" / "nbaiot_main_audit.json"
        loaded = json.loads(audit_file.read_text())

        assert loaded["stage"] == "nbaiot_main"
        assert loaded["n_clients"] == N_EXPECTED_DEVICES
        assert loaded["n_min"] == 100
        assert "summary" in loaded
        assert "clients" in loaded

        # Verify summary fields (JSON roundtrip uses plain dict)
        summary = loaded["summary"]
        assert "total_benign_train" in summary
        assert "total_benign_cal" in summary
        assert "total_test_benign" in summary
        assert "total_test_attack" in summary
        assert "calibration_pending_count" in summary

    def test_audit_calibration_pending_flag(self, tmp_path: Path) -> None:
        results = _make_nbaiot_partition_results(cal_count=50)
        audit = audit_partitions(
            results, stage=ExperimentStage.NBAIOT_MAIN, output_dir=tmp_path, n_min=100
        )

        for client_id, info in audit.clients.items():
            if info.benign_cal_count < 100:
                assert info.calibration_pending is True, (
                    f"Client {client_id} with cal={info.benign_cal_count} "
                    f"should be calibration_pending"
                )

        assert audit.summary.calibration_pending_count > 0

    def test_audit_summary_totals_match(self, tmp_path: Path) -> None:
        results = _make_nbaiot_partition_results()
        audit = audit_partitions(
            results, stage=ExperimentStage.NBAIOT_MAIN, output_dir=tmp_path, n_min=100
        )

        clients = audit.clients
        summary = audit.summary

        assert summary.total_benign_train == sum(
            c.benign_train_count for c in clients.values()
        )
        assert summary.total_benign_cal == sum(
            c.benign_cal_count for c in clients.values()
        )
        assert summary.total_test_benign == sum(
            c.test_benign_count for c in clients.values()
        )
        assert summary.total_test_attack == sum(
            c.test_attack_count for c in clients.values()
        )
