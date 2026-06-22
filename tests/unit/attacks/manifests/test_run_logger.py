"""Tests for manifest emission and run logging ."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

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
from datp.attacks.enums import (
    AttackerObjective,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ThresholdPolicy,
)
from datp.config.stages import ExperimentStage


def _build_manifest(
    *,
    mu_flag_threshold: float | None,
    local_epochs: int = 1,
) -> RunManifest:
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
            repository="datp-calibration-poisoning",
            mu_flag_threshold=mu_flag_threshold,
            local_epochs=local_epochs,
        )
    )


class TestBuildManifest:
    def test_returns_manifest(self) -> None:
        m = _build_manifest(mu_flag_threshold=0.005)
        assert isinstance(m, RunManifest)

    def test_mu_flag_threshold_recorded(self) -> None:
        m = _build_manifest(mu_flag_threshold=0.005)
        assert m.mu_flag_threshold == pytest.approx(0.005)

    def test_mu_flag_threshold_none_allowed_at_build(self) -> None:
        # Building with None is allowed; emission enforces non-None.
        m = _build_manifest(mu_flag_threshold=None)
        assert m.mu_flag_threshold is None

    def test_seed_entropy_matches_inputs(self) -> None:
        m = _build_manifest(mu_flag_threshold=0.005)
        assert m.seed_record.training_seed == 0
        assert m.seed_record.poisoning_seed == 100
        assert m.seed_record.client_idx == 0
        assert m.seed_record.scope_idx == 0
        assert m.seed_record.entropy == (0, 100, 0, 0)

    def test_provenance_e1_enforced(self) -> None:
        with pytest.raises(ValueError, match="E=5 rejected"):
            _build_manifest(mu_flag_threshold=0.005, local_epochs=5)

    def test_fraction_recorded(self) -> None:
        m = _build_manifest(mu_flag_threshold=0.005)
        assert m.fraction == pytest.approx(0.40)

    def test_generated_at_utc_present(self) -> None:
        m = _build_manifest(mu_flag_threshold=0.005)
        assert m.generated_at_utc  # non-empty ISO string

    def test_schema_version_is_1(self) -> None:
        m = _build_manifest(mu_flag_threshold=0.005)
        assert m.schema_version == "1"


class TestEmitManifest:
    def test_writes_file(self, tmp_path: Path) -> None:
        m = _build_manifest(mu_flag_threshold=0.005)
        path = emit_manifest(m, tmp_path)
        assert path.exists()

    def test_roundtrip(self, tmp_path: Path) -> None:
        m = _build_manifest(mu_flag_threshold=0.005)
        emit_manifest(m, tmp_path)
        loaded = load_manifest(tmp_path)
        assert loaded.mu_flag_threshold == pytest.approx(0.005)
        assert loaded.seed_record.entropy == m.seed_record.entropy
        assert loaded.fraction == m.fraction

    def test_raises_if_mu_flag_none(self, tmp_path: Path) -> None:
        m = _build_manifest(mu_flag_threshold=None)
        with pytest.raises(ManifestEmissionError, match="mu_flag_threshold"):
            emit_manifest(m, tmp_path)

    def test_creates_run_dir(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "some" / "nested" / "dir"
        m = _build_manifest(mu_flag_threshold=0.005)
        emit_manifest(m, run_dir)
        assert run_dir.is_dir()

    def test_json_is_valid(self, tmp_path: Path) -> None:
        m = _build_manifest(mu_flag_threshold=0.005)
        path = emit_manifest(m, tmp_path)
        data = json.loads(path.read_text())
        assert data["schema_version"] == "1"
        assert data["mu_flag_threshold"] == pytest.approx(0.005)


class TestWriteRunLog:
    def _make_entry(self, mu: float = 0.005) -> RunLogEntry:
        return RunLogEntry(
            dataset="nbaiot",
            policy="global_threshold",
            objective="threshold_raise",
            source="high_score_benign",
            fraction=0.40,
            training_seed=0,
            poisoning_seed=100,
            mu_flag_threshold=mu,
            manifest_path="/some/path/run_manifest.json",
            generated_at_utc="2026-06-16T00:00:00+00:00",
        )

    def test_creates_log_file(self, tmp_path: Path) -> None:
        log = tmp_path / "run.log"
        write_run_log_entry(self._make_entry(), log)
        assert log.exists()

    def test_appends_jsonl_lines(self, tmp_path: Path) -> None:
        log = tmp_path / "run.log"
        write_run_log_entry(self._make_entry(0.005), log)
        write_run_log_entry(self._make_entry(0.010), log)
        lines = log.read_text().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["mu_flag_threshold"] == pytest.approx(0.005)
        assert json.loads(lines[1])["mu_flag_threshold"] == pytest.approx(0.010)

    def test_log_entry_has_fraction(self, tmp_path: Path) -> None:
        log = tmp_path / "run.log"
        write_run_log_entry(self._make_entry(), log)
        record = json.loads(log.read_text().splitlines()[0])
        assert record["fraction"] == pytest.approx(0.40)

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        log = tmp_path / "deep" / "nested" / "run.log"
        write_run_log_entry(self._make_entry(), log)
        assert log.exists()
