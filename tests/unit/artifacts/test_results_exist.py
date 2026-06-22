from __future__ import annotations
from datp.core.enums import ThresholdPolicy

import json
from pathlib import Path

import pytest

from datp.artifacts.existence import results_exist
from datp.config.stages import ExperimentStage
from tests.fixtures.payloads import valid_metrics_dict

_STAGE = ExperimentStage.NBAIOT_MAIN


class TestResultsExist:
    def test_completed_run(self, tmp_path: Path) -> None:
        rdir = tmp_path / "results" / "nbaiot_main" / "global_threshold" / "seed_42"
        rdir.mkdir(parents=True)
        (rdir / "metrics.json").write_text(json.dumps(valid_metrics_dict()))

        assert (
            results_exist(
                ThresholdPolicy.GLOBAL_THRESHOLD, _STAGE, 42, base_dir=tmp_path
            )
            is True
        )

    def test_stale_pre_schema_payload_returns_false(self, tmp_path: Path) -> None:
        rdir = tmp_path / "results" / "nbaiot_main" / "global_threshold" / "seed_42"
        rdir.mkdir(parents=True)
        (rdir / "metrics.json").write_text(json.dumps({"auroc": 0.99}))

        assert (
            results_exist(
                ThresholdPolicy.GLOBAL_THRESHOLD, _STAGE, 42, base_dir=tmp_path
            )
            is False
        )

    def test_unknown_provenance_returns_false(self, tmp_path: Path) -> None:
        rdir = tmp_path / "results" / "nbaiot_main" / "global_threshold" / "seed_42"
        rdir.mkdir(parents=True)
        payload = valid_metrics_dict()
        payload["provenance"]["config_identity"] = "UNKNOWN"
        (rdir / "metrics.json").write_text(json.dumps(payload))

        assert (
            results_exist(
                ThresholdPolicy.GLOBAL_THRESHOLD, _STAGE, 42, base_dir=tmp_path
            )
            is False
        )

    def test_missing_hash_provenance_returns_false(self, tmp_path: Path) -> None:
        rdir = tmp_path / "results" / "nbaiot_main" / "global_threshold" / "seed_42"
        rdir.mkdir(parents=True)
        payload = valid_metrics_dict()
        payload["provenance"]["score_artifact_identity"] = "MISSING_SCORE_HASH"
        (rdir / "metrics.json").write_text(json.dumps(payload))

        assert (
            results_exist(
                ThresholdPolicy.GLOBAL_THRESHOLD, _STAGE, 42, base_dir=tmp_path
            )
            is False
        )

    @pytest.mark.parametrize(
        "missing_key",
        [
            "eligible_ids",
            "pending_ids",
            "eval_incomplete_ids",
        ],
    )
    def test_missing_required_id_list_returns_false(
        self, tmp_path: Path, missing_key: str
    ) -> None:
        rdir = tmp_path / "results" / "nbaiot_main" / "global_threshold" / "seed_42"
        rdir.mkdir(parents=True)
        payload = valid_metrics_dict()
        del payload[missing_key]
        (rdir / "metrics.json").write_text(json.dumps(payload))

        assert (
            results_exist(
                ThresholdPolicy.GLOBAL_THRESHOLD, _STAGE, 42, base_dir=tmp_path
            )
            is False
        )

    def test_missing_metrics(self, tmp_path: Path) -> None:
        assert (
            results_exist(
                ThresholdPolicy.GLOBAL_THRESHOLD, _STAGE, 42, base_dir=tmp_path
            )
            is False
        )

    def test_empty_metrics(self, tmp_path: Path) -> None:
        rdir = tmp_path / "results" / "nbaiot_main" / "global_threshold" / "seed_42"
        rdir.mkdir(parents=True)
        (rdir / "metrics.json").touch()

        assert (
            results_exist(
                ThresholdPolicy.GLOBAL_THRESHOLD, _STAGE, 42, base_dir=tmp_path
            )
            is False
        )

    def test_tmp_placeholder_not_counted(self, tmp_path: Path) -> None:
        rdir = tmp_path / "results" / "nbaiot_main" / "global_threshold" / "seed_42"
        rdir.mkdir(parents=True)
        (rdir / "metrics.json.tmp").write_text('{"partial": true}')

        assert (
            results_exist(
                ThresholdPolicy.GLOBAL_THRESHOLD, _STAGE, 42, base_dir=tmp_path
            )
            is False
        )

    def test_different_policy_not_found(self, tmp_path: Path) -> None:
        rdir = tmp_path / "results" / "nbaiot_main" / "global_threshold" / "seed_42"
        rdir.mkdir(parents=True)
        (rdir / "metrics.json").write_text(json.dumps(valid_metrics_dict()))

        assert (
            results_exist(
                ThresholdPolicy.GLOBAL_THRESHOLD, _STAGE, 42, base_dir=tmp_path
            )
            is True
        )
        assert (
            results_exist(
                ThresholdPolicy.LOCAL_THRESHOLD, _STAGE, 42, base_dir=tmp_path
            )
            is False
        )
