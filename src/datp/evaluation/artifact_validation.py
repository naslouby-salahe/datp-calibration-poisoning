"""Structural validation of persisted metrics JSON payloads and per-client records."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, cast

from datp.core.enums import ConfusionKey, PayloadKey

_REQ_METRICS = {
    PayloadKey.SCHEMA_VERSION.value,
    PayloadKey.METRIC_SCHEMA_VERSION.value,
    PayloadKey.THRESHOLD_SCHEMA_VERSION.value,
    PayloadKey.RUN_ID.value,
    PayloadKey.RUN_KIND.value,
    PayloadKey.DATASET.value,
    PayloadKey.STAGE.value,
    PayloadKey.POLICY.value,
    PayloadKey.SEED.value,
    PayloadKey.THRESHOLD_SCOPE.value,
    PayloadKey.THRESHOLD_STRATEGY_NAME.value,
    PayloadKey.CLIENT_COUNT.value,
    PayloadKey.ELIGIBLE_COUNT.value,
    PayloadKey.PENDING_COUNT.value,
    PayloadKey.EVAL_INCOMPLETE_COUNT.value,
    PayloadKey.COVERAGE_RATIO.value,
    PayloadKey.ELIGIBLE_IDS.value,
    PayloadKey.PENDING_IDS.value,
    PayloadKey.EVAL_INCOMPLETE_IDS.value,
    PayloadKey.PER_CLIENT.value,
    PayloadKey.AGGREGATE_METRICS.value,
    PayloadKey.PROVENANCE.value,
}

_REQ_CLIENT = {
    PayloadKey.CONFUSION_MATRIX.value,
    PayloadKey.N_BENIGN.value,
    PayloadKey.N_ATTACK.value,
    PayloadKey.CALIBRATION_PENDING.value,
    PayloadKey.EVALUATION_INCOMPLETE.value,
    PayloadKey.THRESHOLD_VALUE.value,
    PayloadKey.THRESHOLD_SOURCE.value,
}

_REQ_PROV = {
    PayloadKey.CONFIG_IDENTITY.value,
    PayloadKey.SPLIT_MANIFEST_IDENTITY.value,
    PayloadKey.MODEL_CHECKPOINT_IDENTITY.value,
    PayloadKey.SCORE_ARTIFACT_IDENTITY.value,
    PayloadKey.METRIC_CODE_VERSION.value,
    PayloadKey.THRESHOLD_CODE_VERSION.value,
    PayloadKey.PACKAGE_VERSION.value,
    PayloadKey.GENERATED_AT_UTC.value,
}

_CONF_KEYS = {k.value for k in ConfusionKey}
_VAGUE = frozenset({"UNKNOWN", "unknown"})
_HASH_KEYS = frozenset(
    {
        PayloadKey.CONFIG_IDENTITY,
        PayloadKey.SPLIT_MANIFEST_IDENTITY,
        PayloadKey.MODEL_CHECKPOINT_IDENTITY,
        PayloadKey.SCORE_ARTIFACT_IDENTITY,
    }
)


def client_rows(payload: Mapping[str, object]) -> list[tuple[str, Mapping[str, Any]]]:
    """Extract per-client records from a metrics payload as (client_id, row) pairs."""
    raw = payload[PayloadKey.PER_CLIENT]
    if isinstance(raw, Mapping):
        return [(str(cid), row) for cid, row in raw.items()]  # type: ignore[misc]
    return [(str(row[PayloadKey.CLIENT_ID]), row) for row in raw]  # type: ignore[index,union-attr]


def _validate_provenance(prov: object, module: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(prov, Mapping):
        return [f"[{module}] MISSING metrics fields: provenance.*"]
    if missing_prov := _REQ_PROV - prov.keys():
        errors.append(
            f"[{module}] MISSING metrics fields: {', '.join(sorted(f'provenance.{k}' for k in missing_prov))}"
        )
    if vague := [k for k, v in prov.items() if k in _REQ_PROV and str(v) in _VAGUE]:
        errors.append(
            f"[{module}] FAIL vague UNKNOWN provenance fields: {', '.join(sorted(vague))}"
        )
    if unresolved := [
        k.value for k in _HASH_KEYS if str(prov.get(k, "")).startswith("MISSING_")
    ]:
        errors.append(
            f"[{module}] FAIL unresolved required provenance (MISSING_*) in: {', '.join(sorted(unresolved))}"
        )
    return errors


def _validate_client_row(
    cid: str, row: Mapping[str, Any], pd_ids: set[str], inc_ids: set[str], module: str
) -> list[str]:
    errors: list[str] = []
    missing_client = _REQ_CLIENT - row.keys()
    cm = row.get(PayloadKey.CONFUSION_MATRIX)
    if not isinstance(cm, Mapping):
        missing_client.add("confusion_matrix.tp/fp/tn/fn")
    else:
        missing_client.update(f"confusion_matrix.{k}" for k in _CONF_KEYS - cm.keys())
    if missing_client:
        errors.append(
            f"[{module}] MISSING per-client fields for {cid}: {', '.join(sorted(missing_client))}"
        )
    if cid in pd_ids and row.get(PayloadKey.CALIBRATION_PENDING) is not True:
        errors.append(
            f"[{module}] FAIL pending client {cid} missing calibration_pending=true"
        )
    if cid in inc_ids and row.get(PayloadKey.EVALUATION_INCOMPLETE) is not True:
        errors.append(
            f"[{module}] FAIL eval-incomplete client {cid} missing evaluation_incomplete=true"
        )
    return errors


def validate_metrics_payload(
    payload: Mapping[str, object], *, module: str
) -> list[str]:
    """Validate top-level fields, provenance, and per-client records in a metrics JSON payload."""
    errors: list[str] = []

    if missing_payload := _REQ_METRICS - payload.keys():
        return [
            f"[{module}] MISSING metrics fields: {', '.join(sorted(missing_payload))}"
        ]

    errors.extend(_validate_provenance(payload.get(PayloadKey.PROVENANCE), module))

    raw_clients = payload.get(PayloadKey.PER_CLIENT, {})
    if isinstance(raw_clients, Mapping):
        rows: list[tuple[str, Mapping[str, Any]]] = [
            (str(cid), row) for cid, row in cast(Mapping[str, Any], raw_clients).items()
        ]
    else:
        rows = [
            (str(r[PayloadKey.CLIENT_ID]), r)
            for r in cast(Iterable[Mapping[str, Any]], raw_clients)
        ]

    row_ids = {cid for cid, _ in rows}
    el_ids = {
        str(i) for i in cast(Iterable[Any], payload.get(PayloadKey.ELIGIBLE_IDS, []))
    }
    pd_ids = {
        str(i) for i in cast(Iterable[Any], payload.get(PayloadKey.PENDING_IDS, []))
    }
    inc_ids = {
        str(i)
        for i in cast(Iterable[Any], payload.get(PayloadKey.EVAL_INCOMPLETE_IDS, []))
    }

    if overlap := el_ids & pd_ids:
        errors.append(
            f"[{module}] FAIL eligible_ids overlap pending_ids: {sorted(overlap)}"
        )

    if (el_ids - row_ids) or (pd_ids - row_ids) or (inc_ids - row_ids):
        errors.append(
            f"[{module}] FAIL eligibility ids not present in per_client: eligible={sorted(el_ids - row_ids)}, pending={sorted(pd_ids - row_ids)}, eval_incomplete={sorted(inc_ids - row_ids)}"
        )

    for cid, row in rows:
        errors.extend(_validate_client_row(cid, row, pd_ids, inc_ids, module))

    return errors
