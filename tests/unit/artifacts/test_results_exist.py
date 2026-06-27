"""Unit tests for metrics output file existence and schema completeness checks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from datp.artifacts.existence import results_exist
from datp.config.models import ExperimentStage
from datp.core.enums import ThresholdPolicy
from tests.fixtures.payloads import valid_metrics_dict

_STAGE = ExperimentStage.NBAIOT_MAIN


class TestResultsExist:
    """Tests verifying whether output metrics exist and validate against the schema constraints."""

    def test_completed_run(self, tmp_path: Path) -> None:
        """Verify that a completed run with a valid schema-abiding metrics file returns True."""
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
        """Verify that old/stale metrics payloads failing schema checks return False."""
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
        """Verify that metrics files with UNKNOWN provenance identities return False."""
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
        """Verify that metrics with missing score hash signatures return False."""
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
        """Verify that missing key lists like eligible_ids or pending_ids return False."""
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
        """Verify that when no metrics file exists, results_exist returns False."""
        assert (
            results_exist(
                ThresholdPolicy.GLOBAL_THRESHOLD, _STAGE, 42, base_dir=tmp_path
            )
            is False
        )

    def test_empty_metrics(self, tmp_path: Path) -> None:
        """Verify that an empty/zero-byte metrics.json file returns False."""
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
        """Verify that temp files (metrics.json.tmp) do not count as completed results."""
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
        """Verify that checking status of one policy doesn't mistakenly match other policy folders."""
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
