"""Tests verifying build, emission, loading, and appending of individual run manifests and loggers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from datp.attacks.enums import (
    AttackerObjective,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
)
from datp.attacks.manifests.run_logger import (
    ManifestBuildRequest,
    ManifestEmissionError,
    RunLogEntry,
    build_manifest,
    emit_manifest,
    load_manifest,
    write_run_log_entry,
)
from datp.attacks.manifests.run_manifest import RunManifest
from datp.config.models import ExperimentStage
from datp.core.enums import ThresholdPolicy
from datp.core.provenance import REPOSITORY_NAME


def _build_manifest(
    *,
    mu_flag_threshold: float | None,
    local_epochs: int = 1,
) -> RunManifest:
    """Helper to build standard RunManifest mock instances."""
    return build_manifest(
        ManifestBuildRequest(
            dataset="nbaiot",
            stage=ExperimentStage.SYNTHETIC_SMOKE,
            policy=ThresholdPolicy.GLOBAL_THRESHOLD,
            objective=AttackerObjective.THRESHOLD_RAISE,
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            fraction=0.40,
            target_scope=PoisoningTargetScope.SINGLE_CLIENT,
            training_seed=0,
            poisoning_seed=100,
            client_idx=0,
            scope_idx=0,
            repository=REPOSITORY_NAME,
            mu_flag_threshold=mu_flag_threshold,
            local_epochs=local_epochs,
        )
    )


class TestBuildManifest:
    """Tests verifying manifest builder properties, parameter storage, and validators."""

    def test_returns_manifest(self) -> None:
        """Verify that build_manifest returns a validated RunManifest instance."""
        m = _build_manifest(mu_flag_threshold=0.005)
        assert isinstance(m, RunManifest)

    def test_mu_flag_threshold_recorded(self) -> None:
        """Verify that the provided mu flag threshold is correctly recorded."""
        m = _build_manifest(mu_flag_threshold=0.005)
        assert m.mu_flag_threshold == pytest.approx(0.005)

    def test_mu_flag_threshold_none_allowed_at_build(self) -> None:
        """Verify that None is accepted as a temporary mu flag threshold value during builds."""
        m = _build_manifest(mu_flag_threshold=None)
        assert m.mu_flag_threshold is None

    def test_seed_entropy_matches_inputs(self) -> None:
        """Verify that seed entropy tuple is derived correctly from training/poison seeds."""
        m = _build_manifest(mu_flag_threshold=0.005)
        assert m.seed_record.training_seed == 0
        assert m.seed_record.poisoning_seed == 100
        assert m.seed_record.client_idx == 0
        assert m.seed_record.scope_idx == 0
        assert m.seed_record.entropy == (0, 100, 0, 0)

    def test_provenance_e1_enforced(self) -> None:
        """Verify that validation rejects local epoch values other than 1."""
        with pytest.raises(ValueError, match="E=5 rejected"):
            _build_manifest(mu_flag_threshold=0.005, local_epochs=5)

    def test_fraction_recorded(self) -> None:
        """Verify that poisoning sweep fraction matches input argument value."""
        m = _build_manifest(mu_flag_threshold=0.005)
        assert m.fraction == pytest.approx(0.40)

    def test_generated_at_utc_present(self) -> None:
        """Verify that the generated timestamp string is populated on builds."""
        m = _build_manifest(mu_flag_threshold=0.005)
        assert m.generated_at_utc

    def test_schema_version_is_1(self) -> None:
        """Verify that the generated manifest schema version string equals 1."""
        m = _build_manifest(mu_flag_threshold=0.005)
        assert m.schema_version == "1"


class TestEmitManifest:
    """Tests verifying serializing and writing manifests to disk."""

    def test_writes_file(self, tmp_path: Path) -> None:
        """Verify that emit_manifest writes a file to the expected path."""
        m = _build_manifest(mu_flag_threshold=0.005)
        path = emit_manifest(m, tmp_path)
        assert path.exists()

    def test_roundtrip(self, tmp_path: Path) -> None:
        """Verify that emitted manifests load back with matching parameters."""
        m = _build_manifest(mu_flag_threshold=0.005)
        emit_manifest(m, tmp_path)
        loaded = load_manifest(tmp_path)
        assert loaded.mu_flag_threshold == pytest.approx(0.005)
        assert loaded.seed_record.entropy == m.seed_record.entropy
        assert loaded.fraction == m.fraction

    def test_raises_if_mu_flag_none(self, tmp_path: Path) -> None:
        """Verify that emission raises a error if mu_flag_threshold is None."""
        m = _build_manifest(mu_flag_threshold=None)
        with pytest.raises(ManifestEmissionError, match="mu_flag_threshold"):
            emit_manifest(m, tmp_path)

    def test_creates_run_dir(self, tmp_path: Path) -> None:
        """Verify that emit_manifest automatically creates nested output folders if they do not exist."""
        run_dir = tmp_path / "some" / "nested" / "dir"
        m = _build_manifest(mu_flag_threshold=0.005)
        emit_manifest(m, run_dir)
        assert run_dir.is_dir()

    def test_json_is_valid(self, tmp_path: Path) -> None:
        """Verify that emitted output is valid json and contains schema version key."""
        m = _build_manifest(mu_flag_threshold=0.005)
        path = emit_manifest(m, tmp_path)
        data = json.loads(path.read_text())
        assert data["schema_version"] == "1"
        assert data["mu_flag_threshold"] == pytest.approx(0.005)


class TestWriteRunLog:
    """Tests verifying appending entries to JSONL run log summaries."""

    def _make_entry(self, mu: float = 0.005) -> RunLogEntry:
        """Helper to create a RunLogEntry instance."""
        return RunLogEntry(
            dataset="nbaiot",
            policy=ThresholdPolicy.GLOBAL_THRESHOLD,
            objective=AttackerObjective.THRESHOLD_RAISE,
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            fraction=0.40,
            training_seed=0,
            poisoning_seed=100,
            mu_flag_threshold=mu,
            manifest_path="/some/path/run_manifest.json",
            generated_at_utc="2026-06-16T00:00:00+00:00",
        )

    def test_creates_log_file(self, tmp_path: Path) -> None:
        """Verify that write_run_log_entry creates the log file on disk."""
        log = tmp_path / "run.log"
        write_run_log_entry(self._make_entry(), log)
        assert log.exists()

    def test_appends_jsonl_lines(self, tmp_path: Path) -> None:
        """Verify that subsequent entries append new lines rather than overwriting file."""
        log = tmp_path / "run.log"
        write_run_log_entry(self._make_entry(0.005), log)
        write_run_log_entry(self._make_entry(0.010), log)
        lines = log.read_text().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["mu_flag_threshold"] == pytest.approx(0.005)
        assert json.loads(lines[1])["mu_flag_threshold"] == pytest.approx(0.010)

    def test_log_entry_has_fraction(self, tmp_path: Path) -> None:
        """Verify that the written log line includes fraction parameter values."""
        log = tmp_path / "run.log"
        write_run_log_entry(self._make_entry(), log)
        record = json.loads(log.read_text().splitlines()[0])
        assert record["fraction"] == pytest.approx(0.40)

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Verify that writing logs automatically creates intermediate nested directory folders."""
        log = tmp_path / "deep" / "nested" / "run.log"
        write_run_log_entry(self._make_entry(), log)
        assert log.exists()
