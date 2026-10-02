from __future__ import annotations

import json
from pathlib import Path

import pytest

from datp.core.enums import ConfusionKey, PayloadKey, ThresholdPolicy
from datp.validation.metric_reproducer import read_metrics_json, select_stored_summary
from datp.validation.schemas import StoredMetricsSnapshot


def _metrics_payload(per_client: object) -> dict[str, object]:
    return {
        "policy": ThresholdPolicy.LOCAL_THRESHOLD.value,
        "stage": "nbaiot_main",
        "seed": 7,
        "dataset": "nbaiot",
        "cv_fpr": 0.2,
        "coverage_ratio": 1.0,
        "client_count": 1,
        "eligible_count": 1,
        "pending_count": 0,
        "eligible_ids": ["client-0"],
        "pending_ids": [],
        "per_client": per_client,
    }


def _client_row(client_id: str) -> dict[str, object]:
    return {
        "client_id": client_id,
        "confusion_matrix": {
            ConfusionKey.TP.value: 8,
            ConfusionKey.FP.value: 2,
            ConfusionKey.TN.value: 8,
            ConfusionKey.FN.value: 2,
        },
        "threshold_value": 0.5,
    }


def _read(tmp_path: Path, payload: dict[str, object]):
    path = tmp_path / "metrics.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return read_metrics_json(path)


def test_metrics_json_list_rows_become_typed_snapshot(tmp_path: Path) -> None:
    stored = _read(tmp_path, _metrics_payload([_client_row("client-0")]))

    assert stored.policy is ThresholdPolicy.LOCAL_THRESHOLD
    assert stored.per_client[next(iter(stored.per_client))].confusion == {
        ConfusionKey.TP: 8,
        ConfusionKey.FP: 2,
        ConfusionKey.TN: 8,
        ConfusionKey.FN: 2,
    }
    summary = select_stored_summary(stored)
    assert isinstance(summary, StoredMetricsSnapshot)
    assert summary.model_dump(mode="json") == {
        "policy": "local_threshold",
        "stage": "nbaiot_main",
        "seed": 7,
        "dataset": "nbaiot",
        "tau_global": None,
        "coverage_ratio": 1.0,
        "cv_fpr": 0.2,
        "cv_tpr": None,
        "mean_fpr": None,
        "std_fpr": None,
        "iqr_fpr": None,
        "iqr_tpr": None,
        "max_min_fpr_gap": None,
        "worst_client_fpr": None,
        "worst_client_id": None,
        "worst_ba": None,
        "p10_macro_f1": None,
        "client_count": 1,
        "eligible_count": 1,
        "pending_count": 0,
        "eligible_ids": ["client-0"],
        "pending_ids": [],
    }


def test_keyed_per_client_rows_use_the_key_as_canonical_client_id(
    tmp_path: Path,
) -> None:
    payload = _metrics_payload({"client-0": _client_row("ignored-row-id")})
    stored = _read(tmp_path, payload)

    assert tuple(stored.per_client) == ("client-0",)


def test_malformed_per_client_row_fails_at_json_boundary(tmp_path: Path) -> None:
    with pytest.raises(TypeError, match="entries must be JSON objects"):
        _read(tmp_path, _metrics_payload(["invalid-row"]))


def test_invalid_confusion_count_fails_at_json_boundary(tmp_path: Path) -> None:
    row = _client_row("client-0")
    matrix = row[PayloadKey.CONFUSION_MATRIX.value]
    assert isinstance(matrix, dict)
    matrix[ConfusionKey.TP.value] = True

    with pytest.raises(TypeError, match="Invalid confusion count"):
        _read(tmp_path, _metrics_payload([row]))
