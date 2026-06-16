"""provenance gate — enforces E=1 and validates clean-artifact presence.

Read-only module: inspects file paths and manifest content, never writes.
Call ``assert_provenance_gate`` before any poisoned run reads clean
artifacts. It raises ``ProvenanceError`` on any FAIL-level violation.

MISSING and BLOCKED_PENDING_RUN results are not raised — they indicate that
artifacts are not yet available, not a protocol violation.
"""

from __future__ import annotations

import enum
import json
from pathlib import Path

from pydantic import ValidationError

from datp.attacks.run_manifest import (
    SPLIT_SEMANTICS,
    RunManifest,
)
from datp.validation.enums import AuditStatus
from datp.validation.schemas import ValidationCheck


class ProvenanceCheckCode(enum.StrEnum):
    """Check codes for each gate assertion."""

    MANIFEST_PRESENT = "manifest_present"
    MANIFEST_PARSEABLE = "manifest_parseable"
    LOCAL_EPOCHS_E1 = "local_epochs_e1"
    PIPELINE_GENERATED_FLAG = "pipeline_generated_flag"
    SPLIT_SEMANTICS = "split_semantics"
    POLICY_NOT_B3 = "policy_not_b3"
    CAL_SCORES_PRESENT = "cal_scores_present"
    TEST_SCORES_PRESENT = "test_scores_present"


class ProvenanceError(ValueError):
    """Raised when any FAIL-level provenance check fires."""

    def __init__(self, message: str, failed_checks: list[ValidationCheck]) -> None:
        super().__init__(message)
        self.failed_checks: list[ValidationCheck] = failed_checks


# ---------------------------------------------------------------------------
# Internal per-check helpers
# ---------------------------------------------------------------------------


def _check_manifest_present(manifest_path: Path) -> ValidationCheck:
    if not manifest_path.exists():
        return ValidationCheck(
            code=ProvenanceCheckCode.MANIFEST_PRESENT,
            status=AuditStatus.MISSING,
            detail=f"manifest absent at {manifest_path}",
        )
    return ValidationCheck(
        code=ProvenanceCheckCode.MANIFEST_PRESENT,
        status=AuditStatus.PASS,
    )


def _parse_manifest(
    manifest_path: Path,
) -> tuple[RunManifest | None, ValidationCheck]:
    """Parse and schema-validate the manifest.

    Returns (None, FAIL check) on JSON error or Pydantic schema violation.
    Pydantic's ``ProvenanceRecord`` validator already rejects E=5 — any
    E!=1 value is caught here and reported as FAIL.
    """
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return (
            None,
            ValidationCheck(
                code=ProvenanceCheckCode.MANIFEST_PARSEABLE,
                status=AuditStatus.FAIL,
                detail=f"JSON parse error: {exc}",
            ),
        )
    try:
        manifest = RunManifest.model_validate(raw)
    except ValidationError as exc:
        return (
            None,
            ValidationCheck(
                code=ProvenanceCheckCode.MANIFEST_PARSEABLE,
                status=AuditStatus.FAIL,
                detail=f"Schema validation failed (E=5 or unknown field): {exc}",
            ),
        )
    return (
        manifest,
        ValidationCheck(
            code=ProvenanceCheckCode.MANIFEST_PARSEABLE,
            status=AuditStatus.PASS,
        ),
    )


def _check_local_epochs_e1(manifest: RunManifest) -> ValidationCheck:
    """Defence-in-depth E=1 check (schema already enforces this)."""
    e = manifest.provenance.local_epochs
    if e != 1:
        return ValidationCheck(
            code=ProvenanceCheckCode.LOCAL_EPOCHS_E1,
            status=AuditStatus.FAIL,
            detail=f"local_epochs={e}; E={e} rejected — only E=1 permitted",
        )
    return ValidationCheck(
        code=ProvenanceCheckCode.LOCAL_EPOCHS_E1,
        status=AuditStatus.PASS,
    )


def _check_pipeline_generated_flag(manifest: RunManifest) -> ValidationCheck:
    if not manifest.provenance.pipeline_generated:
        return ValidationCheck(
            code=ProvenanceCheckCode.PIPELINE_GENERATED_FLAG,
            status=AuditStatus.FAIL,
            detail=(
                "provenance.pipeline_generated is not True; "
                "artifact may originate from a journal run"
            ),
        )
    return ValidationCheck(
        code=ProvenanceCheckCode.PIPELINE_GENERATED_FLAG,
        status=AuditStatus.PASS,
    )


def _check_split_semantics(manifest: RunManifest) -> ValidationCheck:
    actual = manifest.provenance.split_semantics
    if actual != SPLIT_SEMANTICS:
        return ValidationCheck(
            code=ProvenanceCheckCode.SPLIT_SEMANTICS,
            status=AuditStatus.FAIL,
            detail=(
                f"split_semantics {actual!r} does not match "
                f"canonical {SPLIT_SEMANTICS!r}"
            ),
        )
    return ValidationCheck(
        code=ProvenanceCheckCode.SPLIT_SEMANTICS,
        status=AuditStatus.PASS,
    )


def _check_policy_not_b3(manifest: RunManifest) -> ValidationCheck:
    """Defence-in-depth: B3 is excluded from the ThresholdPolicy enum."""
    policy_str = str(manifest.policy)
    if "b3" in policy_str.lower():
        return ValidationCheck(
            code=ProvenanceCheckCode.POLICY_NOT_B3,
            status=AuditStatus.FAIL,
            detail=f"B3 is excluded; policy={policy_str!r}",
        )
    return ValidationCheck(
        code=ProvenanceCheckCode.POLICY_NOT_B3,
        status=AuditStatus.PASS,
    )


def _check_cal_scores_present(score_root: Path | None) -> ValidationCheck:
    """Check for at least one calibration score parquet.

    Returns BLOCKED_PENDING_RUN when score_root is not provided.
    Returns MISSING when the directory exists but contains no parquets.
    """
    if score_root is None:
        return ValidationCheck(
            code=ProvenanceCheckCode.CAL_SCORES_PRESENT,
            status=AuditStatus.BLOCKED_PENDING_RUN,
            detail="score_root not provided; calibration score check deferred",
        )
    cal_dir = score_root / "calibration"
    parquets = list(cal_dir.glob("*.parquet")) if cal_dir.is_dir() else []
    if not parquets:
        return ValidationCheck(
            code=ProvenanceCheckCode.CAL_SCORES_PRESENT,
            status=AuditStatus.MISSING,
            detail=f"No calibration parquets found under {cal_dir}",
        )
    return ValidationCheck(
        code=ProvenanceCheckCode.CAL_SCORES_PRESENT,
        status=AuditStatus.PASS,
        detail=f"{len(parquets)} calibration parquet(s) present",
    )


def _check_test_scores_present(score_root: Path | None) -> ValidationCheck:
    """Check for at least one clean test score parquet.

    Returns BLOCKED_PENDING_RUN when score_root is not provided.
    Returns MISSING when the directory exists but contains no parquets.
    """
    if score_root is None:
        return ValidationCheck(
            code=ProvenanceCheckCode.TEST_SCORES_PRESENT,
            status=AuditStatus.BLOCKED_PENDING_RUN,
            detail="score_root not provided; test score check deferred",
        )
    test_dir = score_root / "test"
    parquets = list(test_dir.glob("*.parquet")) if test_dir.is_dir() else []
    if not parquets:
        return ValidationCheck(
            code=ProvenanceCheckCode.TEST_SCORES_PRESENT,
            status=AuditStatus.MISSING,
            detail=f"No test parquets found under {test_dir}",
        )
    return ValidationCheck(
        code=ProvenanceCheckCode.TEST_SCORES_PRESENT,
        status=AuditStatus.PASS,
        detail=f"{len(parquets)} test parquet(s) present",
    )


# ---------------------------------------------------------------------------
# Private orchestrator
# ---------------------------------------------------------------------------


def _run_gate(
    manifest_path: Path,
    score_root: Path | None,
) -> tuple[list[ValidationCheck], RunManifest | None]:
    checks: list[ValidationCheck] = []

    present_check = _check_manifest_present(manifest_path)
    checks.append(present_check)
    if present_check.status == AuditStatus.MISSING:
        return checks, None

    manifest, parseable_check = _parse_manifest(manifest_path)
    checks.append(parseable_check)
    if manifest is None:
        return checks, None

    checks.append(_check_local_epochs_e1(manifest))
    checks.append(_check_pipeline_generated_flag(manifest))
    checks.append(_check_split_semantics(manifest))
    checks.append(_check_policy_not_b3(manifest))
    checks.append(_check_cal_scores_present(score_root))
    checks.append(_check_test_scores_present(score_root))

    return checks, manifest


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_provenance(
    manifest_path: Path,
    *,
    score_root: Path | None = None,
) -> list[ValidationCheck]:
    """Run all provenance gate checks and return structured results.

    Does not raise. Use ``assert_provenance_gate`` to enforce failures.

    Args:
        manifest_path: Path to the ``run_manifest.json`` file.
        score_root: Optional directory containing ``calibration/`` and
            ``test/`` sub-directories of score parquets. When ``None``,
            artifact-presence checks return BLOCKED_PENDING_RUN.
    """
    checks, _ = _run_gate(manifest_path, score_root)
    return checks


def assert_provenance_gate(
    manifest_path: Path,
    *,
    score_root: Path | None = None,
) -> RunManifest:
    """Enforce the provenance gate; raise ``ProvenanceError`` on FAIL.

    MISSING and BLOCKED_PENDING_RUN results are not raised — they indicate
    that artifacts are not yet available, not a protocol violation.

    Args:
        manifest_path: Path to the ``run_manifest.json`` file.
        score_root: Passed through for artifact-presence checks.

    Returns:
        The parsed ``RunManifest`` on success.

    Raises:
        ProvenanceError: If any FAIL-level check fires.
    """
    checks, manifest = _run_gate(manifest_path, score_root)
    failed = [c for c in checks if c.status == AuditStatus.FAIL]
    if failed:
        codes = ", ".join(c.code for c in failed)
        raise ProvenanceError(
            f"provenance gate: {len(failed)} FAIL check(s): {codes}",
            failed_checks=failed,
        )
    if manifest is None:
        missing = [c for c in checks if c.status == AuditStatus.MISSING]
        raise ProvenanceError(
            "provenance gate: manifest absent or unparseable",
            failed_checks=missing,
        )
    return manifest
