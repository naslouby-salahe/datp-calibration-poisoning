from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from datp.core.metric_enums import ConfusionKey, PayloadKey

_REQUIRED_METRICS_KEYS: tuple[PayloadKey, ...] = (
    PayloadKey.SCHEMA_VERSION,
    PayloadKey.METRIC_SCHEMA_VERSION,
    PayloadKey.THRESHOLD_SCHEMA_VERSION,
    PayloadKey.RUN_ID,
    PayloadKey.RUN_KIND,
    PayloadKey.DATASET,
    PayloadKey.STAGE,
    PayloadKey.POLICY,
    PayloadKey.SEED,
    PayloadKey.THRESHOLD_SCOPE,
    PayloadKey.THRESHOLD_STRATEGY_NAME,
    PayloadKey.CLIENT_COUNT,
    PayloadKey.ELIGIBLE_COUNT,
    PayloadKey.PENDING_COUNT,
    PayloadKey.EVAL_INCOMPLETE_COUNT,
    PayloadKey.COVERAGE_RATIO,
    PayloadKey.ELIGIBLE_IDS,
    PayloadKey.PENDING_IDS,
    PayloadKey.EVAL_INCOMPLETE_IDS,
    PayloadKey.PER_CLIENT,
    PayloadKey.AGGREGATE_METRICS,
    PayloadKey.PROVENANCE,
)

_REQUIRED_CLIENT_KEYS: tuple[PayloadKey, ...] = (
    PayloadKey.CONFUSION_MATRIX,
    PayloadKey.N_BENIGN,
    PayloadKey.N_ATTACK,
    PayloadKey.CALIBRATION_PENDING,
    PayloadKey.EVALUATION_INCOMPLETE,
    PayloadKey.THRESHOLD_VALUE,
    PayloadKey.THRESHOLD_SOURCE,
)

_REQUIRED_PROVENANCE_KEYS: tuple[PayloadKey, ...] = (
    PayloadKey.CONFIG_IDENTITY,
    PayloadKey.SPLIT_MANIFEST_IDENTITY,
    PayloadKey.MODEL_CHECKPOINT_IDENTITY,
    PayloadKey.SCORE_ARTIFACT_IDENTITY,
    PayloadKey.METRIC_CODE_VERSION,
    PayloadKey.THRESHOLD_CODE_VERSION,
    PayloadKey.PACKAGE_VERSION,
    PayloadKey.GENERATED_AT_UTC,
)

_CONFUSION_KEYS: tuple[ConfusionKey, ...] = (
    ConfusionKey.TP,
    ConfusionKey.FP,
    ConfusionKey.TN,
    ConfusionKey.FN,
)

_VAGUE_PROVENANCE: frozenset[str] = frozenset({"UNKNOWN", "unknown"})

# MISSING_* prefix means the hash could not be resolved at serialization time.
_HASH_IDENTITY_KEYS: frozenset[PayloadKey] = frozenset(
    {
        PayloadKey.CONFIG_IDENTITY,
        PayloadKey.SPLIT_MANIFEST_IDENTITY,
        PayloadKey.MODEL_CHECKPOINT_IDENTITY,
        PayloadKey.SCORE_ARTIFACT_IDENTITY,
    }
)


@dataclass(frozen=True, slots=True)
class ValidationIds:
    eligible: set[str]
    pending: set[str]
    incomplete: set[str]
    row: set[str]


@dataclass(frozen=True, slots=True)
class ClientRowContext:
    pending_ids: set[str]
    incomplete_ids: set[str]
    module: str


def client_rows(
    payload: Mapping[str, object],
) -> list[tuple[str, Mapping[str, Any]]]:
    raw = payload[PayloadKey.PER_CLIENT]
    if isinstance(raw, Mapping):
        return [(str(cid), row) for cid, row in raw.items()]  # type: ignore[misc]
    # list-of-dicts format: each row has "client_id"
    rows: list[Any] = list(raw)  # type: ignore[arg-type]
    return [(str(row[PayloadKey.CLIENT_ID]), row) for row in rows]


def _missing_payload_fields(payload: Mapping[str, object]) -> list[str]:
    missing = [key.value for key in _REQUIRED_METRICS_KEYS if key not in payload]
    provenance = payload.get(PayloadKey.PROVENANCE)
    if isinstance(provenance, Mapping):
        missing.extend(
            f"provenance.{key.value}"
            for key in _REQUIRED_PROVENANCE_KEYS
            if key not in provenance
        )
    else:
        missing.append("provenance.*")
    return missing


def _missing_payload_error(missing: list[str], *, module: str) -> str:
    return f"[{module}] MISSING metrics fields: {', '.join(sorted(missing))}"


def _payload_validation_ids(
    payload: Mapping[str, object],
    row_ids: set[str],
) -> ValidationIds:
    return ValidationIds(
        eligible={str(cid) for cid in payload[PayloadKey.ELIGIBLE_IDS]},  # type: ignore[arg-type]
        pending={str(cid) for cid in payload[PayloadKey.PENDING_IDS]},  # type: ignore[arg-type]
        incomplete={str(cid) for cid in payload[PayloadKey.EVAL_INCOMPLETE_IDS]},  # type: ignore[arg-type]
        row=row_ids,
    )


def _client_row_context(
    validation_ids: ValidationIds,
    *,
    module: str,
) -> ClientRowContext:
    return ClientRowContext(validation_ids.pending, validation_ids.incomplete, module)


def _validate_provenance(provenance: Mapping[str, object], *, module: str) -> list[str]:
    errors: list[str] = []
    vague = [
        key.value
        for key in _REQUIRED_PROVENANCE_KEYS
        if str(provenance[key]) in _VAGUE_PROVENANCE
    ]
    if vague:
        errors.append(
            f"[{module}] FAIL vague UNKNOWN provenance fields: {', '.join(sorted(vague))}"
        )
    unresolved = [
        key.value
        for key in _HASH_IDENTITY_KEYS
        if str(provenance[key]).startswith("MISSING_")
    ]
    if unresolved:
        errors.append(
            f"[{module}] FAIL unresolved required provenance (MISSING_*) in: {', '.join(sorted(unresolved))}"
        )
    return errors


def _missing_row_ids(ids: ValidationIds) -> bool:
    return bool(
        ids.eligible - ids.row or ids.pending - ids.row or ids.incomplete - ids.row
    )


def _validate_membership_ids(ids: ValidationIds, *, module: str) -> list[str]:
    errors: list[str] = []
    if ids.eligible & ids.pending:
        errors.append(
            f"[{module}] FAIL eligible_ids overlap pending_ids: {sorted(ids.eligible & ids.pending)}"
        )
    if _missing_row_ids(ids):
        errors.append(
            f"[{module}] FAIL eligibility ids not present in per_client: "
            f"eligible={sorted(ids.eligible - ids.row)}, pending={sorted(ids.pending - ids.row)}, "
            f"eval_incomplete={sorted(ids.incomplete - ids.row)}"
        )
    return errors


def _missing_client_fields(row: Mapping[str, object]) -> list[str]:
    missing = [key.value for key in _REQUIRED_CLIENT_KEYS if key not in row]
    cm = row.get(PayloadKey.CONFUSION_MATRIX)
    if not isinstance(cm, Mapping):
        missing.append("confusion_matrix.tp/fp/tn/fn")
        return missing
    missing.extend(
        f"confusion_matrix.{key.value}" for key in _CONFUSION_KEYS if key not in cm
    )
    return missing


def _validate_client_row(
    cid: str,
    row: Mapping[str, object],
    *,
    context: ClientRowContext,
) -> list[str]:
    errors: list[str] = []
    missing_client = _missing_client_fields(row)
    if missing_client:
        errors.append(
            f"[{context.module}] MISSING per-client fields for {cid}: {', '.join(sorted(missing_client))}"
        )
    if (
        cid in context.pending_ids
        and row.get(PayloadKey.CALIBRATION_PENDING) is not True
    ):
        errors.append(
            f"[{context.module}] FAIL pending client {cid} missing calibration_pending=true"
        )
    if (
        cid in context.incomplete_ids
        and row.get(PayloadKey.EVALUATION_INCOMPLETE) is not True
    ):
        errors.append(
            f"[{context.module}] FAIL eval-incomplete client {cid} missing evaluation_incomplete=true"
        )
    return errors


def validate_metrics_payload(
    payload: Mapping[str, object], *, module: str
) -> list[str]:
    missing = _missing_payload_fields(payload)
    provenance = payload.get(PayloadKey.PROVENANCE)
    if missing:
        return [_missing_payload_error(missing, module=module)]

    errors: list[str] = []
    if isinstance(provenance, Mapping):
        errors.extend(_validate_provenance(provenance, module=module))
    rows = client_rows(payload)
    row_ids = {cid for cid, _ in rows}
    validation_ids = _payload_validation_ids(payload, row_ids)
    errors.extend(_validate_membership_ids(validation_ids, module=module))
    row_context = _client_row_context(validation_ids, module=module)
    for cid, row in rows:
        errors.extend(
            _validate_client_row(
                cid,
                row,
                context=row_context,
            )
        )
    return errors
