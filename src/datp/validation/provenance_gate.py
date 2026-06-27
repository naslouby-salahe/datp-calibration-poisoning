"""Provenance gate: run-manifest checks for identity, split semantics, and score presence."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from datp.attacks.manifests.run_manifest import SPLIT_SEMANTICS, RunManifest
from datp.validation.enums import AuditStatus, ProvenanceCheckCode
from datp.validation.schemas import ValidationCheck


class ProvenanceError(ValueError):
    """ValueError subclass that carries the list of failed provenance validation checks."""

    def __init__(self, message: str, failed_checks: list[ValidationCheck]) -> None:
        """Initialize with an error message and the list of failed validation checks."""
        super().__init__(message)
        self.failed_checks = failed_checks


def check_scores_present(
    score_root: Path | None, code: ProvenanceCheckCode, subdir: str, label: str
) -> ValidationCheck:
    """Validate that Parquet score files exist under the given subdirectory."""
    if score_root is None:
        return ValidationCheck(
            code=code,
            status=AuditStatus.BLOCKED_PENDING_RUN,
            detail=f"score_root not provided; {label} score check deferred",
        )

    score_dir = score_root / subdir
    parquets = list(score_dir.glob("*.parquet")) if score_dir.is_dir() else []

    if not parquets:
        return ValidationCheck(
            code=code,
            status=AuditStatus.MISSING,
            detail=f"No {label} parquets found under {score_dir}",
        )

    return ValidationCheck(
        code=code,
        status=AuditStatus.PASS,
        detail=f"{len(parquets)} {label} parquet(s) present",
    )


def run_gate(
    manifest_path: Path, score_root: Path | None
) -> tuple[list[ValidationCheck], RunManifest | None]:
    """Run all provenance gate checks on a manifest and return checks plus parsed manifest."""
    checks: list[ValidationCheck] = []

    if not manifest_path.exists():
        checks.append(
            ValidationCheck(
                code=ProvenanceCheckCode.MANIFEST_PRESENT,
                status=AuditStatus.MISSING,
                detail=f"manifest absent at {manifest_path}",
            )
        )
        return checks, None

    checks.append(
        ValidationCheck(
            code=ProvenanceCheckCode.MANIFEST_PRESENT, status=AuditStatus.PASS
        )
    )

    try:
        raw = json.loads(manifest_path.read_text())
        manifest = RunManifest.model_validate(raw)
        checks.append(
            ValidationCheck(
                code=ProvenanceCheckCode.MANIFEST_PARSEABLE, status=AuditStatus.PASS
            )
        )
    except (OSError, json.JSONDecodeError) as exc:
        checks.append(
            ValidationCheck(
                code=ProvenanceCheckCode.MANIFEST_PARSEABLE,
                status=AuditStatus.FAIL,
                detail=f"JSON parse error: {exc}",
            )
        )
        return checks, None
    except ValidationError as exc:
        checks.append(
            ValidationCheck(
                code=ProvenanceCheckCode.MANIFEST_PARSEABLE,
                status=AuditStatus.FAIL,
                detail=f"Schema validation failed: {exc}",
            )
        )
        return checks, None

    epochs = manifest.provenance.local_epochs
    checks.append(
        ValidationCheck(
            code=ProvenanceCheckCode.LOCAL_EPOCHS_E1,
            status=AuditStatus.PASS if epochs == 1 else AuditStatus.FAIL,
            detail=""
            if epochs == 1
            else f"local_epochs={epochs}; E={epochs} rejected — only E=1 permitted",
        )
    )

    generated = manifest.provenance.pipeline_generated
    checks.append(
        ValidationCheck(
            code=ProvenanceCheckCode.PIPELINE_GENERATED_FLAG,
            status=AuditStatus.PASS if generated else AuditStatus.FAIL,
            detail=""
            if generated
            else "provenance.pipeline_generated is not True; artifact may originate from legacy pipeline",
        )
    )

    actual_split = manifest.provenance.split_semantics
    checks.append(
        ValidationCheck(
            code=ProvenanceCheckCode.SPLIT_SEMANTICS,
            status=AuditStatus.PASS
            if actual_split == SPLIT_SEMANTICS
            else AuditStatus.FAIL,
            detail=""
            if actual_split == SPLIT_SEMANTICS
            else f"split_semantics {actual_split!r} does not match canonical {SPLIT_SEMANTICS!r}",
        )
    )

    checks.append(
        check_scores_present(
            score_root,
            ProvenanceCheckCode.CAL_SCORES_PRESENT,
            "calibration",
            "calibration",
        )
    )
    checks.append(
        check_scores_present(
            score_root, ProvenanceCheckCode.TEST_SCORES_PRESENT, "test", "test"
        )
    )

    return checks, manifest


def check_provenance(
    manifest_path: Path, *, score_root: Path | None = None
) -> list[ValidationCheck]:
    """Run provenance checks and return the list of validation results without raising."""
    return run_gate(manifest_path, score_root)[0]


def assert_provenance_gate(
    manifest_path: Path, *, score_root: Path | None = None
) -> RunManifest:
    """Run provenance checks and return parsed manifest, raising ProvenanceError on failure."""
    checks, manifest = run_gate(manifest_path, score_root)

    if failed := [c for c in checks if c.status == AuditStatus.FAIL]:
        raise ProvenanceError(
            f"provenance gate: {len(failed)} FAIL check(s): {', '.join(c.code for c in failed)}",
            failed_checks=failed,
        )

    if manifest is None:
        raise ProvenanceError(
            "provenance gate: manifest absent or unparseable",
            failed_checks=[c for c in checks if c.status == AuditStatus.MISSING],
        )

    return manifest
