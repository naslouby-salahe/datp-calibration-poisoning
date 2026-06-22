from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TypeVar, cast

from datp.artifacts.names import ArtifactFile
from datp.core.enums import ScoringStage
from datp.core.errors import fmt
from datp.scoring.manifest import (
    ScoringColumnDtype,
    ScoringManifest,
    ScoringManifestCoverage,
    ScoringRecord,
)
from datp.scoring.paths import resolve_within_base
from datp.scoring.schema import (
    SCORE_COLUMN,
    SCORING_MANIFEST_NOT_PROVIDED,
    ScoringManifestStatus,
)

_MODULE = "scoring.manifest_validation"
_SequenceItemT = TypeVar("_SequenceItemT")


def _check_manifest_coverage(
    manifest: ScoringManifest,
    score_base: Path,
) -> ScoringManifestCoverage:
    expected = {
        (cid, split)
        for cid in manifest.expected_client_ids
        for split in manifest.expected_splits
    }
    actual = {(row.client_id, row.split.value) for row in manifest.records}
    missing = sorted(expected - actual)

    missing_files: list[str] = []
    invalid_files: list[str] = []
    for row in manifest.records:
        path = Path(row.path)
        try:
            resolved_path = resolve_within_base(score_base, path)
        except ValueError:
            invalid_files.append(str(path))
            continue
        if not resolved_path.exists():
            missing_files.append(str(path))

    missing_files.sort()
    invalid_files.sort()
    return ScoringManifestCoverage(
        missing_pairs=tuple(missing),
        missing_files=tuple(missing_files),
        invalid_files=tuple(invalid_files),
    )


def _required(payload: Mapping[str, object], key: str) -> object:
    if key not in payload:
        raise KeyError(key)
    return payload[key]


def _required_text(payload: Mapping[str, object], key: str) -> str:
    return str(_required(payload, key))


def _required_int(payload: Mapping[str, object], key: str) -> int:
    value = _required(payload, key)
    if isinstance(value, bool):
        raise TypeError(f"{key} must be an integer, not bool")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        return int(value)
    raise TypeError(f"{key} must be convertible to int")


def _sequence(
    value: object, item_type: type[_SequenceItemT]
) -> tuple[_SequenceItemT, ...]:
    if isinstance(value, (str, bytes)):
        raise TypeError("expected a sequence, not text")
    if not isinstance(value, Sequence):
        raise TypeError("expected a sequence")
    if not all(isinstance(item, item_type) for item in value):
        raise TypeError(f"expected a sequence of {item_type.__name__}")
    return tuple(value)


def _required_sequence(
    payload: Mapping[str, object], key: str, item_type: type[_SequenceItemT]
) -> tuple[_SequenceItemT, ...]:
    return _sequence(_required(payload, key), item_type)


def _optional_sequence(
    payload: Mapping[str, object], key: str, item_type: type[_SequenceItemT]
) -> tuple[_SequenceItemT, ...]:
    return _sequence(payload.get(key, ()), item_type)


def _optional_text(payload: Mapping[str, object], key: str) -> str:
    return str(payload.get(key, SCORING_MANIFEST_NOT_PROVIDED))


def _optional_int(payload: Mapping[str, object], key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    return _required_int(payload, key)


def _optional_float(payload: Mapping[str, object], key: str) -> float | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        raise TypeError(f"{key} must be numeric, not bool")
    if isinstance(value, (int, float, str)):
        return float(value)
    raise TypeError(f"{key} must be convertible to float")


def _text_tuple(payload: Mapping[str, object], key: str) -> tuple[str, ...]:
    return tuple(str(item) for item in _required_sequence(payload, key, object))


def _dtype_entries(raw: object) -> tuple[ScoringColumnDtype, ...]:
    if isinstance(raw, Mapping):
        return tuple(
            ScoringColumnDtype(column=str(column), dtype=str(dtype))
            for column, dtype in raw.items()
        )
    rows = _sequence(raw, Mapping)  # type: ignore[type-abstract]
    return tuple(
        ScoringColumnDtype(
            column=_required_text(row, "column"),
            dtype=_required_text(row, "dtype"),
        )
        for row in rows
    )


def _record_from_payload(payload: Mapping[str, object]) -> ScoringRecord:
    return ScoringRecord(
        client_id=_required_text(payload, "client_id"),
        split=ScoringStage(_required_text(payload, "split")),
        path=_required_text(payload, "path"),
        row_count=_required_int(payload, "row_count"),
        columns=_text_tuple(payload, "columns"),
        dtypes=_dtype_entries(_required(payload, "dtypes")),
        score_min=_optional_float(payload, "score_min"),
        score_max=_optional_float(payload, "score_max"),
        score_nan_count=_required_int(payload, "score_nan_count"),
        file_hash=_required_text(payload, "file_hash"),
    )


def _manifest_from_payload(payload: Mapping[str, object]) -> ScoringManifest:
    records = tuple(
        _record_from_payload(row)
        for row in _required_sequence(payload, "records", Mapping)  # type: ignore[type-abstract]
    )
    return ScoringManifest(
        schema_version=_required_text(payload, "schema_version"),
        dataset=str(payload.get("dataset", SCORING_MANIFEST_NOT_PROVIDED)),
        stage=str(payload.get("stage", SCORING_MANIFEST_NOT_PROVIDED)),
        seed=_optional_int(payload, "seed"),
        model_checkpoint_path=_optional_text(payload, "model_checkpoint_path"),
        model_checkpoint_hash=_optional_text(payload, "model_checkpoint_hash"),
        checkpoint_round=_optional_int(payload, "checkpoint_round"),
        scoring_code_version=_optional_text(payload, "scoring_code_version"),
        score_column_name=str(payload.get("score_column_name", SCORE_COLUMN)),
        expected_client_ids=_text_tuple(payload, "expected_client_ids"),
        expected_splits=_text_tuple(payload, "expected_splits"),
        actual_client_ids=tuple(
            str(item)
            for item in _optional_sequence(payload, "actual_client_ids", object)
        ),
        actual_splits=tuple(
            str(item) for item in _optional_sequence(payload, "actual_splits", object)
        ),
        records=records,
        completion_status=_required_text(payload, "completion_status"),
        generated_at_utc=_optional_text(payload, "generated_at_utc"),
    )


def validate_scoring_manifest(score_base: Path) -> ScoringManifest:
    score_base = Path(score_base)
    manifest_path = score_base / ArtifactFile.SCORING_MANIFEST
    if not manifest_path.exists():
        raise FileNotFoundError(
            fmt(_MODULE, "Scoring manifest missing", str(manifest_path), "missing file")
        )
    manifest = _manifest_from_payload(
        cast(
            Mapping[str, object], json.loads(manifest_path.read_text(encoding="utf-8"))
        )
    )
    coverage = _check_manifest_coverage(manifest, score_base)
    if (
        manifest.completion_status != ScoringManifestStatus.COMPLETE
        or coverage.missing_pairs
        or coverage.missing_files
        or coverage.invalid_files
    ):
        raise ValueError(
            fmt(
                _MODULE,
                "Scoring manifest incomplete",
                "complete manifest with all expected score files",
                f"status={manifest.completion_status}, missing={coverage.missing_pairs}, missing_files={coverage.missing_files}, invalid_files={coverage.invalid_files}",
            )
        )
    return manifest
