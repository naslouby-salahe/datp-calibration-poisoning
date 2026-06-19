from __future__ import annotations

import json
from pathlib import Path

from datp.core.enums import Regime
from datp.data.common.audit import audit_partitions
from datp.data.contracts import PartitionResult

REQUIRED_CLIENT_FIELDS = {
    "benign_train_count",
    "benign_cal_count",
    "test_benign_count",
    "test_attack_count",
    "attack_classes",
    "calibration_pending",
    "evaluation_incomplete",
}


def _make_partition_results(
    n_clients: int = 3,
    cal_count: int = 200,
    eval_incomplete: bool = False,
) -> dict[str, PartitionResult]:
    results = {}
    for i in range(n_clients):
        results[f"device_{i}"] = PartitionResult(
            benign_train_count=1000 + i,
            benign_cal_count=cal_count + i,
            test_benign_count=500 + i,
            test_attack_count=800 + i,
            attack_classes=[f"atk_a_{i}", f"atk_b_{i}"],
            calibration_pending=cal_count + i < 100,
            evaluation_incomplete=eval_incomplete,
        )
    return results


class TestAuditWritesJson:
    def test_audit_writes_json(self, tmp_path: Path) -> None:
        results = _make_partition_results()
        audit_partitions(results, regime=Regime.A, output_dir=tmp_path, n_min=100)
        audit_file = tmp_path / "data_audit" / "a_audit.json"
        assert audit_file.exists()
        data = json.loads(audit_file.read_text())
        assert data["regime"] == "a"
        assert data["n_clients"] == 3


class TestAuditSummaryCounts:
    def test_audit_summary_counts(self, tmp_path: Path) -> None:
        results = _make_partition_results(n_clients=4, cal_count=150)
        audit = audit_partitions(
            results, regime=Regime.B, output_dir=tmp_path, n_min=100
        )

        assert audit.summary.total_benign_train == sum(
            c.benign_train_count for c in audit.clients.values()
        )
        assert audit.summary.total_benign_cal == sum(
            c.benign_cal_count for c in audit.clients.values()
        )
        assert audit.summary.total_test_benign == sum(
            c.test_benign_count for c in audit.clients.values()
        )
        assert audit.summary.total_test_attack == sum(
            c.test_attack_count for c in audit.clients.values()
        )


class TestAuditFlagsCalibrationPending:
    def test_audit_flags_calibration_pending(self, tmp_path: Path) -> None:
        results = _make_partition_results(n_clients=2, cal_count=50)
        # cal_count=50 and 51 — both below default n_min=100
        audit = audit_partitions(
            results, regime=Regime.A, output_dir=tmp_path, n_min=100
        )

        for client_info in audit.clients.values():
            assert client_info.calibration_pending is True

        assert audit.summary.calibration_pending_count == 2
        assert audit.summary.all_above_n_min is False


class TestAuditAllAboveNMin:
    def test_audit_all_above_n_min(self, tmp_path: Path) -> None:
        results = _make_partition_results(n_clients=3, cal_count=200)
        audit = audit_partitions(
            results, regime=Regime.A, output_dir=tmp_path, n_min=100
        )

        assert audit.summary.all_above_n_min is True
        assert audit.summary.calibration_pending_count == 0


class TestAuditRequiredFields:
    def test_audit_includes_all_required_fields(self, tmp_path: Path) -> None:
        results = _make_partition_results(n_clients=2, cal_count=300)
        audit = audit_partitions(
            results, regime=Regime.C, output_dir=tmp_path, n_min=100
        )

        for client_id, client_info in audit.clients.items():
            missing = REQUIRED_CLIENT_FIELDS - {
                f for f in REQUIRED_CLIENT_FIELDS if hasattr(client_info, f)
            }
            assert not missing, f"{client_id} missing fields: {missing}"

        # Top-level required attributes
        assert audit.regime is not None
        assert audit.n_clients >= 0
        assert audit.n_min >= 0
        assert audit.summary is not None
        assert audit.clients is not None
