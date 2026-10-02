from __future__ import annotations
from datp.types import (
    ClientId,
    Index,
    JsonRecord,
    NarrativeText,
)

from collections.abc import Sequence

from pydantic import ValidationError
from pydantic_core import ErrorDetails

from datp.core.enums import PayloadKey, PayloadValidationErrorType


def _client_id_from_payload(
    payload: JsonRecord, row_index: Index
) -> ClientId | None:
    rows = payload.get(PayloadKey.PER_CLIENT)
    if isinstance(rows, Sequence) and not isinstance(rows, str | bytes):
        if row_index < len(rows):
            row = rows[row_index]
            if isinstance(row, dict):
                client_id = row.get(PayloadKey.CLIENT_ID)
            else:
                return None
            if isinstance(client_id, str):
                return ClientId(client_id)
    return None


def _validation_message(
    payload: JsonRecord, error: ErrorDetails, module: NarrativeText
) -> NarrativeText:
    location = error["loc"]
    parts = tuple(str(part) for part in location)
    message = error["msg"]
    if error["type"] == PayloadValidationErrorType.MISSING:
        if (
            parts
            and parts[0] == PayloadKey.PER_CLIENT
            and len(location) > 1
            and isinstance(location[1], int)
        ):
            client_id = _client_id_from_payload(payload, location[1])
            field = ".".join(parts[2:])
            client_label = client_id if client_id is not None else f"row {location[1]}"
            return f"[{module}] MISSING per-client fields for {client_label}: {field}"
        if parts and parts[0] == PayloadKey.PROVENANCE:
            field = ".".join(parts)
            return f"[{module}] MISSING metrics fields: {field}"
        field = ", ".join(parts)
        return f"[{module}] MISSING metrics fields: {field}"
    return f"[{module}] INVALID metrics payload at {'.'.join(parts)}: {message}"


def validate_metrics_payload(payload: JsonRecord, *, module: NarrativeText) -> list[NarrativeText]:
    from datp.thresholding.metrics_serialization import SweepMetrics

    try:
        SweepMetrics.model_validate(payload)
    except ValidationError as error:
        return [_validation_message(payload, detail, module) for detail in error.errors()]
    return []
