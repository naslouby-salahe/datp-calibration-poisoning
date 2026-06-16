"""Unit tests for the provenance gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from datp.attacks.run_manifest import (
    SPLIT_SEMANTICS,
    ProvenanceRecord,
    RunManifest,
    SeedRecordModel,
)
from datp.attacks.poison_enums import (
    AttackerObjective,
    ExperimentScale,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ThresholdPolicy,
)
from datp.core.seed_sequence import derive_seed_record
from datp.validation.provenance_gate import (
    ProvenanceCheckCode,
    ProvenanceError,
    assert_provenance_gate,
    check_provenance,
)
from datp.validation.enums import AuditStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _provenance(**overrides: object) -> ProvenanceRecord:
    defaults: dict[str, object] = {
        "local_epochs": 1,
        "repository": "/repo/datp-calibration-poisoning",
    }
    defaults.update(overrides)
    return ProvenanceRecord(**defaults) # type: ignore[arg-type]


def _seed_model(
    training_seed: int = 0,
    poisoning_seed: int = 100,
    client_idx: int = 0,
    scope_idx: int = 0,
) -> SeedRecordModel:
    record = derive_seed_record(
        training_seed=training_seed,
        poisoning_seed=poisoning_seed,
        client_idx=client_idx,
        scope_idx=scope_idx,
    )
    return SeedRecordModel.from_record(record)


def _manifest(**overrides: object) -> RunManifest:
    defaults: dict[str, object] = {
        "dataset": "nbaiot",
        "scale": ExperimentScale.BOUNDED,
        "policy": ThresholdPolicy.B1_GLOBAL,
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
    return RunManifest(**defaults) # type: ignore[arg-type]


def _write_manifest(path: Path, manifest: RunManifest) -> None:
    path.write_text(manifest.model_dump_json(), encoding="utf-8")


# ---------------------------------------------------------------------------
# Manifest presence checks
# ---------------------------------------------------------------------------


class TestManifestPresent:
    def test_missing_file_returns_missing(self, tmp_path: Path) -> None:
        checks = check_provenance(tmp_path / "does_not_exist.json")
        assert checks[0].code == ProvenanceCheckCode.MANIFEST_PRESENT
        assert checks[0].status == AuditStatus.MISSING

    def test_missing_file_stops_early(self, tmp_path: Path) -> None:
        checks = check_provenance(tmp_path / "does_not_exist.json")
        # Only the MANIFEST_PRESENT check should be returned.
        assert len(checks) == 1

    def test_valid_manifest_passes(self, tmp_path: Path) -> None:
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest())
        checks = check_provenance(p)
        present = next(c for c in checks if c.code == ProvenanceCheckCode.MANIFEST_PRESENT)
        assert present.status == AuditStatus.PASS


# ---------------------------------------------------------------------------
# Manifest parse / schema checks
# ---------------------------------------------------------------------------


class TestManifestParseable:
    def test_invalid_json_returns_fail(self, tmp_path: Path) -> None:
        p = tmp_path / "manifest.json"
        p.write_text("NOT VALID JSON", encoding="utf-8")
        checks = check_provenance(p)
        parseable = next(c for c in checks if c.code == ProvenanceCheckCode.MANIFEST_PARSEABLE)
        assert parseable.status == AuditStatus.FAIL

    def test_e5_manifest_fails_parseable(self, tmp_path: Path) -> None:
        # Construct raw dict with local_epochs=5 to bypass Pydantic on manifest build.
        m = _manifest()
        raw = json.loads(m.model_dump_json())
        raw["provenance"]["local_epochs"] = 5
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(raw), encoding="utf-8")
        checks = check_provenance(p)
        parseable = next(c for c in checks if c.code == ProvenanceCheckCode.MANIFEST_PARSEABLE)
        assert parseable.status == AuditStatus.FAIL
        assert "E=" in parseable.detail or "Schema" in parseable.detail

    def test_extra_field_fails_parseable(self, tmp_path: Path) -> None:
        m = _manifest()
        raw = json.loads(m.model_dump_json())
        raw["unexpected_field"] = "should_be_rejected"
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(raw), encoding="utf-8")
        checks = check_provenance(p)
        parseable = next(c for c in checks if c.code == ProvenanceCheckCode.MANIFEST_PARSEABLE)
        assert parseable.status == AuditStatus.FAIL


# ---------------------------------------------------------------------------
# E=1 checks
# ---------------------------------------------------------------------------


class TestLocalEpochsE1:
    def test_e1_passes(self, tmp_path: Path) -> None:
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest())
        checks = check_provenance(p)
        e1 = next(c for c in checks if c.code == ProvenanceCheckCode.LOCAL_EPOCHS_E1)
        assert e1.status == AuditStatus.PASS

    def test_e5_caught_at_parse_level(self, tmp_path: Path) -> None:
        # When E=5 is in the file, it is caught at MANIFEST_PARSEABLE; LOCAL_EPOCHS_E1
        # check never runs (manifest is None after parse failure).
        m = _manifest()
        raw = json.loads(m.model_dump_json())
        raw["provenance"]["local_epochs"] = 5
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(raw), encoding="utf-8")
        checks = check_provenance(p)
        codes = {c.code for c in checks}
        assert ProvenanceCheckCode.LOCAL_EPOCHS_E1 not in codes
        parseable = next(c for c in checks if c.code == ProvenanceCheckCode.MANIFEST_PARSEABLE)
        assert parseable.status == AuditStatus.FAIL


# ---------------------------------------------------------------------------
# pipeline-generated flag
# ---------------------------------------------------------------------------


class TestGeneratedFlag:
    def test_true_by_default_passes(self, tmp_path: Path) -> None:
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest())
        checks = check_provenance(p)
        flag = next(c for c in checks if c.code == ProvenanceCheckCode.PIPELINE_GENERATED_FLAG)
        assert flag.status == AuditStatus.PASS

    def test_false_returns_fail(self, tmp_path: Path) -> None:
        m = _manifest()
        raw = json.loads(m.model_dump_json())
        raw["provenance"]["pipeline_generated"] = False
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(raw), encoding="utf-8")
        checks = check_provenance(p)
        flag = next(c for c in checks if c.code == ProvenanceCheckCode.PIPELINE_GENERATED_FLAG)
        assert flag.status == AuditStatus.FAIL
        assert "journal" in flag.detail


# ---------------------------------------------------------------------------
# Split semantics
# ---------------------------------------------------------------------------


class TestSplitSemantics:
    def test_canonical_semantics_passes(self, tmp_path: Path) -> None:
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest())
        checks = check_provenance(p)
        ss = next(c for c in checks if c.code == ProvenanceCheckCode.SPLIT_SEMANTICS)
        assert ss.status == AuditStatus.PASS

    def test_wrong_semantics_fails(self, tmp_path: Path) -> None:
        m = _manifest()
        raw = json.loads(m.model_dump_json())
        raw["provenance"]["split_semantics"] = "wrong_split"
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(raw), encoding="utf-8")
        checks = check_provenance(p)
        ss = next(c for c in checks if c.code == ProvenanceCheckCode.SPLIT_SEMANTICS)
        assert ss.status == AuditStatus.FAIL
        assert SPLIT_SEMANTICS in ss.detail


# ---------------------------------------------------------------------------
# Policy not B3
# ---------------------------------------------------------------------------


class TestPolicyNotB3:
    def test_b1_global_passes(self, tmp_path: Path) -> None:
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest(policy=ThresholdPolicy.B1_GLOBAL))
        checks = check_provenance(p)
        b3 = next(c for c in checks if c.code == ProvenanceCheckCode.POLICY_NOT_B3)
        assert b3.status == AuditStatus.PASS

    def test_b2_personalized_passes(self, tmp_path: Path) -> None:
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest(policy=ThresholdPolicy.B2_PERSONALIZED))
        checks = check_provenance(p)
        b3 = next(c for c in checks if c.code == ProvenanceCheckCode.POLICY_NOT_B3)
        assert b3.status == AuditStatus.PASS

    def test_b4_cluster_passes(self, tmp_path: Path) -> None:
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest(policy=ThresholdPolicy.B4_CLUSTER))
        checks = check_provenance(p)
        b3 = next(c for c in checks if c.code == ProvenanceCheckCode.POLICY_NOT_B3)
        assert b3.status == AuditStatus.PASS


# ---------------------------------------------------------------------------
# Artifact presence checks (no score_root)
# ---------------------------------------------------------------------------


class TestArtifactPresenceNoRoot:
    def test_cal_scores_blocked_when_no_root(self, tmp_path: Path) -> None:
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest())
        checks = check_provenance(p, score_root=None)
        cal = next(c for c in checks if c.code == ProvenanceCheckCode.CAL_SCORES_PRESENT)
        assert cal.status == AuditStatus.BLOCKED_PENDING_RUN

    def test_test_scores_blocked_when_no_root(self, tmp_path: Path) -> None:
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest())
        checks = check_provenance(p, score_root=None)
        test = next(c for c in checks if c.code == ProvenanceCheckCode.TEST_SCORES_PRESENT)
        assert test.status == AuditStatus.BLOCKED_PENDING_RUN


# ---------------------------------------------------------------------------
# Artifact presence checks (with score_root)
# ---------------------------------------------------------------------------


class TestArtifactPresenceWithRoot:
    def test_cal_scores_missing_when_dir_absent(self, tmp_path: Path) -> None:
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest())
        checks = check_provenance(p, score_root=tmp_path / "scores")
        cal = next(c for c in checks if c.code == ProvenanceCheckCode.CAL_SCORES_PRESENT)
        assert cal.status == AuditStatus.MISSING

    def test_test_scores_missing_when_dir_absent(self, tmp_path: Path) -> None:
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest())
        checks = check_provenance(p, score_root=tmp_path / "scores")
        test = next(c for c in checks if c.code == ProvenanceCheckCode.TEST_SCORES_PRESENT)
        assert test.status == AuditStatus.MISSING

    def test_cal_scores_pass_when_parquet_present(self, tmp_path: Path) -> None:
        score_root = tmp_path / "scores"
        cal_dir = score_root / "calibration"
        cal_dir.mkdir(parents=True)
        (cal_dir / "device_1.parquet").touch()
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest())
        checks = check_provenance(p, score_root=score_root)
        cal = next(c for c in checks if c.code == ProvenanceCheckCode.CAL_SCORES_PRESENT)
        assert cal.status == AuditStatus.PASS

    def test_test_scores_pass_when_parquet_present(self, tmp_path: Path) -> None:
        score_root = tmp_path / "scores"
        test_dir = score_root / "test"
        test_dir.mkdir(parents=True)
        (test_dir / "device_1.parquet").touch()
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest())
        checks = check_provenance(p, score_root=score_root)
        test = next(c for c in checks if c.code == ProvenanceCheckCode.TEST_SCORES_PRESENT)
        assert test.status == AuditStatus.PASS


# ---------------------------------------------------------------------------
# assert_provenance_gate
# ---------------------------------------------------------------------------


class TestAssertProvenanceGate:
    def test_valid_manifest_returns_manifest(self, tmp_path: Path) -> None:
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest())
        result = assert_provenance_gate(p)
        assert isinstance(result, RunManifest)
        assert result.provenance.local_epochs == 1

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ProvenanceError):
            assert_provenance_gate(tmp_path / "absent.json")

    def test_e5_in_file_raises(self, tmp_path: Path) -> None:
        m = _manifest()
        raw = json.loads(m.model_dump_json())
        raw["provenance"]["local_epochs"] = 5
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(raw), encoding="utf-8")
        with pytest.raises(ProvenanceError):
            assert_provenance_gate(p)

    def test_wrong_split_semantics_raises(self, tmp_path: Path) -> None:
        m = _manifest()
        raw = json.loads(m.model_dump_json())
        raw["provenance"]["split_semantics"] = "journal_split_semantics"
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(raw), encoding="utf-8")
        with pytest.raises(ProvenanceError) as exc_info:
            assert_provenance_gate(p)
        assert ProvenanceCheckCode.SPLIT_SEMANTICS in exc_info.value.args[0]

    def test_false_pipeline_generated_raises(self, tmp_path: Path) -> None:
        m = _manifest()
        raw = json.loads(m.model_dump_json())
        raw["provenance"]["pipeline_generated"] = False
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(raw), encoding="utf-8")
        with pytest.raises(ProvenanceError) as exc_info:
            assert_provenance_gate(p)
        assert len(exc_info.value.failed_checks) >= 1

    def test_blocked_pending_run_does_not_raise(self, tmp_path: Path) -> None:
        # BLOCKED_PENDING_RUN for cal/test scores should NOT raise.
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest())
        # No score_root → BLOCKED_PENDING_RUN for both artifact checks.
        result = assert_provenance_gate(p, score_root=None)
        assert isinstance(result, RunManifest)

    def test_missing_scores_does_not_raise(self, tmp_path: Path) -> None:
        # MISSING for scores should NOT raise (scores just aren't there yet).
        score_root = tmp_path / "scores"
        score_root.mkdir()
        # No parquets inside — both artifact checks will be MISSING.
        p = tmp_path / "manifest.json"
        _write_manifest(p, _manifest())
        result = assert_provenance_gate(p, score_root=score_root)
        assert isinstance(result, RunManifest)

    def test_failed_checks_attribute_contains_failed(self, tmp_path: Path) -> None:
        m = _manifest()
        raw = json.loads(m.model_dump_json())
        raw["provenance"]["pipeline_generated"] = False
        raw["provenance"]["split_semantics"] = "wrong"
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(raw), encoding="utf-8")
        with pytest.raises(ProvenanceError) as exc_info:
            assert_provenance_gate(p)
        assert len(exc_info.value.failed_checks) >= 2

    def test_all_checks_present_in_output(self, tmp_path: Path) -> None:
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
            ProvenanceCheckCode.POLICY_NOT_B3,
            ProvenanceCheckCode.CAL_SCORES_PRESENT,
            ProvenanceCheckCode.TEST_SCORES_PRESENT,
        }
        assert expected == codes
