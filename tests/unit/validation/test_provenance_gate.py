"""Tests verifying the provenance validation gate, manifest parsing audits, and split-semantics conformity checks."""

from __future__ import annotations

import json
from typing import Any
from pathlib import Path

import pytest

from datp.attacks.enums import (
    AttackerObjective,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
)
from datp.attacks.manifests.run_manifest import (
    SPLIT_SEMANTICS,
    ProvenanceRecord,
    RunManifest,
)
from datp.core.enums import ThresholdPolicy
from datp.core.seeds import SeedPair, SeedRecord, derive_seed_record
from datp.config.models import ExperimentStage
from datp.validation.enums import AuditStatus
from datp.validation.provenance_gate import (
    ProvenanceCheckCode,
    ProvenanceError,
    assert_provenance_gate,
    check_provenance,
)


def _provenance(**overrides: Any) -> ProvenanceRecord:
    """Helper to build ProvenanceRecord instances."""
    defaults: dict[str, Any] = {
        "local_epochs": 1,
        "repository": "/repo/datp-calibration-poisoning",
    }
    defaults.update(overrides)
    return ProvenanceRecord(**defaults)


def _seed_model(
    training_seed: int = 0,
    poisoning_seed: int = 100,
    client_idx: int = 0,
    scope_idx: int = 0,
) -> SeedRecord:
    """Helper to build SeedRecord instances from SeedPair configurations."""
    return derive_seed_record(
        SeedPair(training_seed=training_seed, poisoning_seed=poisoning_seed),
        client_idx=client_idx,
        scope_idx=scope_idx,
    )


def _manifest(**overrides: Any) -> RunManifest:
    """Helper to build standard RunManifest instances."""
    defaults: dict[str, Any] = {
        "dataset": "nbaiot",
        "stage": ExperimentStage.NBAIOT_MAIN,
        "policy": ThresholdPolicy.GLOBAL_THRESHOLD,
        "objective": AttackerObjective.THRESHOLD_RAISE,
        "source": PoisoningSourceStrategy.RANDOM_BENIGN,
        "fraction": 0.10,
        "target_scope": PoisoningTargetScope.SINGLE_CLIENT,
        "training_seed": 0,
        "poisoning_seed": 100,
        "client_idx": 0,
        "scope_idx": 0,
        "provenance": _provenance(),
        "mu_flag_threshold": None,
        "seed_record": _seed_model(),
        "generated_at_utc": "2026-06-16T00:00:00Z",
    }
    defaults.update(overrides)
    return RunManifest(**defaults)


def _write_manifest(path: Path, manifest: RunManifest) -> None:
    """Helper to write serialised RunManifest to JSON."""
    path.write_text(manifest.model_dump_json())


class TestManifestPresent:
    """Tests verifying presence checking of the manifest file."""

    def test_missing_file_returns_missing(self, tmp_path: Path) -> None:
        """Verify manifest audit status is MISSING if file doesn't exist."""
        checks = check_provenance(tmp_path / "does_not_exist.json")
        assert checks[0].code == ProvenanceCheckCode.MANIFEST_PRESENT
        assert checks[0].status == AuditStatus.MISSING

    def test_missing_file_stops_early(self, tmp_path: Path) -> None:
        """Verify provenance check stops early if the manifest file is missing."""
        checks = check_provenance(tmp_path / "does_not_exist.json")
        assert len(checks) == 1

    def test_valid_manifest_passes(self, tmp_path: Path) -> None:
        """Verify provenance check passes for a complete valid manifest."""
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest())
        checks = check_provenance(p)
        present = next(
            c for c in checks if c.code == ProvenanceCheckCode.MANIFEST_PRESENT
        )
        assert present.status == AuditStatus.PASS


class TestManifestParseable:
    """Tests verifying JSON parse and schema validation audits."""

    def test_invalid_json_returns_fail(self, tmp_path: Path) -> None:
        """Verify parse status is FAIL if manifest JSON is malformed."""
        p = tmp_path / "manifest.json"
        p.write_text("NOT VALID JSON")
        checks = check_provenance(p)
        parseable = next(
            c for c in checks if c.code == ProvenanceCheckCode.MANIFEST_PARSEABLE
        )
        assert parseable.status == AuditStatus.FAIL

    def test_e5_manifest_fails_parseable(self, tmp_path: Path) -> None:
        """Verify schema validation fails if local epochs setting violates the E=1 constraint."""
        m = _manifest()
        raw = json.loads(m.model_dump_json())
        raw["provenance"]["local_epochs"] = 5
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(raw))
        checks = check_provenance(p)
        parseable = next(
            c for c in checks if c.code == ProvenanceCheckCode.MANIFEST_PARSEABLE
        )
        assert parseable.status == AuditStatus.FAIL
        assert "E=" in parseable.detail or "Schema" in parseable.detail

    def test_extra_field_fails_parseable(self, tmp_path: Path) -> None:
        """Verify schema validation fails if manifest contains unrecognized extra keys."""
        m = _manifest()
        raw = json.loads(m.model_dump_json())
        raw["unexpected_field"] = "should_be_rejected"
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(raw))
        checks = check_provenance(p)
        parseable = next(
            c for c in checks if c.code == ProvenanceCheckCode.MANIFEST_PARSEABLE
        )
        assert parseable.status == AuditStatus.FAIL


class TestLocalEpochsE1:
    """Tests verifying enforcement of local epoch count constraints."""

    def test_e1_passes(self, tmp_path: Path) -> None:
        """Verify epoch checks pass when local epochs equals 1."""
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest())
        checks = check_provenance(p)
        e1 = next(c for c in checks if c.code == ProvenanceCheckCode.LOCAL_EPOCHS_E1)
        assert e1.status == AuditStatus.PASS

    def test_e5_caught_at_parse_level(self, tmp_path: Path) -> None:
        """Verify that invalid epoch counts fail schema checks at parsing phase."""
        m = _manifest()
        raw = json.loads(m.model_dump_json())
        raw["provenance"]["local_epochs"] = 5
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(raw))
        checks = check_provenance(p)
        codes = {c.code for c in checks}
        assert ProvenanceCheckCode.LOCAL_EPOCHS_E1 not in codes
        parseable = next(
            c for c in checks if c.code == ProvenanceCheckCode.MANIFEST_PARSEABLE
        )
        assert parseable.status == AuditStatus.FAIL


class TestGeneratedFlag:
    """Tests verifying generated metadata flag audits."""

    def test_true_by_default_passes(self, tmp_path: Path) -> None:
        """Verify checks pass when pipeline_generated metadata is True."""
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest())
        checks = check_provenance(p)
        flag = next(
            c for c in checks if c.code == ProvenanceCheckCode.PIPELINE_GENERATED_FLAG
        )
        assert flag.status == AuditStatus.PASS

    def test_false_returns_fail(self, tmp_path: Path) -> None:
        """Verify checks fail when pipeline_generated metadata is False."""
        m = _manifest()
        raw = json.loads(m.model_dump_json())
        raw["provenance"]["pipeline_generated"] = False
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(raw))
        checks = check_provenance(p)
        flag = next(
            c for c in checks if c.code == ProvenanceCheckCode.PIPELINE_GENERATED_FLAG
        )
        assert flag.status == AuditStatus.FAIL
        assert "pipeline_generated" in flag.detail


class TestSplitSemantics:
    """Tests verifying split-semantics schema validations."""

    def test_canonical_semantics_passes(self, tmp_path: Path) -> None:
        """Verify split-semantics checks pass when using the standard split schema."""
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest())
        checks = check_provenance(p)
        ss = next(c for c in checks if c.code == ProvenanceCheckCode.SPLIT_SEMANTICS)
        assert ss.status == AuditStatus.PASS

    def test_wrong_semantics_fails(self, tmp_path: Path) -> None:
        """Verify split-semantics checks fail when using an unrecognized split string."""
        m = _manifest()
        raw = json.loads(m.model_dump_json())
        raw["provenance"]["split_semantics"] = "wrong_split"
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(raw))
        checks = check_provenance(p)
        ss = next(c for c in checks if c.code == ProvenanceCheckCode.SPLIT_SEMANTICS)
        assert ss.status == AuditStatus.FAIL
        assert SPLIT_SEMANTICS in ss.detail


class TestArtifactPresenceNoRoot:
    """Tests verifying score directory existence checks when root paths are not provided."""

    def test_cal_scores_blocked_when_no_root(self, tmp_path: Path) -> None:
        """Verify calibration scores check is marked BLOCKED if score root path is None."""
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest())
        checks = check_provenance(p, score_root=None)
        cal = next(
            c for c in checks if c.code == ProvenanceCheckCode.CAL_SCORES_PRESENT
        )
        assert cal.status == AuditStatus.BLOCKED_PENDING_RUN

    def test_test_scores_blocked_when_no_root(self, tmp_path: Path) -> None:
        """Verify test scores check is marked BLOCKED if score root path is None."""
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest())
        checks = check_provenance(p, score_root=None)
        test = next(
            c for c in checks if c.code == ProvenanceCheckCode.TEST_SCORES_PRESENT
        )
        assert test.status == AuditStatus.BLOCKED_PENDING_RUN


class TestArtifactPresenceWithRoot:
    """Tests verifying score file presence audits when root path is populated."""

    def test_cal_scores_missing_when_dir_absent(self, tmp_path: Path) -> None:
        """Verify calibration scores check status is MISSING if calibration directory does not exist."""
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest())
        checks = check_provenance(p, score_root=tmp_path / "scores")
        cal = next(
            c for c in checks if c.code == ProvenanceCheckCode.CAL_SCORES_PRESENT
        )
        assert cal.status == AuditStatus.MISSING

    def test_test_scores_missing_when_dir_absent(self, tmp_path: Path) -> None:
        """Verify test scores check status is MISSING if test scores directory does not exist."""
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest())
        checks = check_provenance(p, score_root=tmp_path / "scores")
        test = next(
            c for c in checks if c.code == ProvenanceCheckCode.TEST_SCORES_PRESENT
        )
        assert test.status == AuditStatus.MISSING

    def test_cal_scores_pass_when_parquet_present(self, tmp_path: Path) -> None:
        """Verify calibration scores pass check when at least one Parquet file exists."""
        score_root = tmp_path / "scores"
        cal_dir = score_root / "calibration"
        cal_dir.mkdir(parents=True)
        (cal_dir / "device_1.parquet").touch()
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest())
        checks = check_provenance(p, score_root=score_root)
        cal = next(
            c for c in checks if c.code == ProvenanceCheckCode.CAL_SCORES_PRESENT
        )
        assert cal.status == AuditStatus.PASS

    def test_test_scores_pass_when_parquet_present(self, tmp_path: Path) -> None:
        """Verify test scores pass check when at least one Parquet file exists."""
        score_root = tmp_path / "scores"
        test_dir = score_root / "test"
        test_dir.mkdir(parents=True)
        (test_dir / "device_1.parquet").touch()
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest())
        checks = check_provenance(p, score_root=score_root)
        test = next(
            c for c in checks if c.code == ProvenanceCheckCode.TEST_SCORES_PRESENT
        )
        assert test.status == AuditStatus.PASS


class TestAssertProvenanceGate:
    """Tests verifying the assert_provenance_gate exception boundary raises."""

    def test_valid_manifest_returns_manifest(self, tmp_path: Path) -> None:
        """Verify gate returns the successfully parsed RunManifest for valid files."""
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest())
        result = assert_provenance_gate(p)
        assert isinstance(result, RunManifest)
        assert result.provenance.local_epochs == 1

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """Verify ProvenanceError is raised if the target manifest file does not exist."""
        with pytest.raises(ProvenanceError):
            assert_provenance_gate(tmp_path / "absent.json")

    def test_e5_in_file_raises(self, tmp_path: Path) -> None:
        """Verify ProvenanceError is raised if epochs constraint is violated in manifest."""
        m = _manifest()
        raw = json.loads(m.model_dump_json())
        raw["provenance"]["local_epochs"] = 5
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(raw))
        with pytest.raises(ProvenanceError):
            assert_provenance_gate(p)

    def test_wrong_split_semantics_raises(self, tmp_path: Path) -> None:
        """Verify ProvenanceError is raised if split semantics deviate from standard split string."""
        m = _manifest()
        raw = json.loads(m.model_dump_json())
        raw["provenance"]["split_semantics"] = "invalid_split_semantics"
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(raw))
        with pytest.raises(ProvenanceError) as exc_info:
            assert_provenance_gate(p)
        assert ProvenanceCheckCode.SPLIT_SEMANTICS in exc_info.value.args[0]

    def test_false_pipeline_generated_raises(self, tmp_path: Path) -> None:
        """Verify ProvenanceError is raised if pipeline_generated is False."""
        m = _manifest()
        raw = json.loads(m.model_dump_json())
        raw["provenance"]["pipeline_generated"] = False
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(raw))
        with pytest.raises(ProvenanceError) as exc_info:
            assert_provenance_gate(p)
        assert len(exc_info.value.failed_checks) >= 1

    def test_blocked_pending_run_does_not_raise(self, tmp_path: Path) -> None:
        """Verify gate does not raise errors on BLOCKED scores checks when no score path is checked."""
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest())

        result = assert_provenance_gate(p, score_root=None)
        assert isinstance(result, RunManifest)

    def test_missing_scores_does_not_raise(self, tmp_path: Path) -> None:
        """Verify gate does not raise error on MISSING score outputs since check is informational only."""
        score_root = tmp_path / "scores"
        score_root.mkdir()

        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest())
        result = assert_provenance_gate(p, score_root=score_root)
        assert isinstance(result, RunManifest)

    def test_failed_checks_attribute_contains_failed(self, tmp_path: Path) -> None:
        """Verify ProvenanceError exposes the list of all failed sub-checks."""
        m = _manifest()
        raw = json.loads(m.model_dump_json())
        raw["provenance"]["pipeline_generated"] = False
        raw["provenance"]["split_semantics"] = "wrong"
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(raw))
        with pytest.raises(ProvenanceError) as exc_info:
            assert_provenance_gate(p)
        assert len(exc_info.value.failed_checks) >= 2

    def test_all_checks_present_in_output(self, tmp_path: Path) -> None:
        """Verify check_provenance outputs verification status for all seven schema checks."""
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest())
        checks = check_provenance(p)
        codes = {c.code for c in checks}
        expected = {
            ProvenanceCheckCode.MANIFEST_PRESENT,
            ProvenanceCheckCode.MANIFEST_PARSEABLE,
            ProvenanceCheckCode.LOCAL_EPOCHS_E1,
            ProvenanceCheckCode.PIPELINE_GENERATED_FLAG,
            ProvenanceCheckCode.SPLIT_SEMANTICS,
            ProvenanceCheckCode.CAL_SCORES_PRESENT,
            ProvenanceCheckCode.TEST_SCORES_PRESENT,
        }
        assert expected == codes
