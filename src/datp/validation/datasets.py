from __future__ import annotations

import dataclasses
import json
import math
from pathlib import Path
from typing import TYPE_CHECKING, cast

import numpy as np
import pyarrow.parquet as pq

from datp.artifacts.names import ArtifactFile
from datp.data.catalog import DatasetID
from datp.validation.constants import NBAIOT_CONFOUND_SUMMARY

if TYPE_CHECKING:
    from datp.data.contracts import (
        RegimeCManifestMetadata,  # type: ignore[attr-defined]
    )
from datp.core.enums import Regime
from datp.core.errors import fmt
from datp.core.identity import alpha_from_label, alpha_label
from datp.core.provenance import hash_jsonable
from datp.data.datasets.ciciot2023.spec import CICIOT2023_SPEC
from datp.data.datasets.nbaiot.spec import NBAIOT_SPEC
from datp.data.splits import Split, split_path
from datp.statistics.divergence import (
    JSSummary,
    pairwise_js_from_distributions,
    pairwise_js_summary,
)
from datp.validation.enums import (
    HomogeneityVerdict,
    OutcomeVariable,
    SeverityTrendStatus,
    SeverityVariable,
)
from datp.validation.schemas import (
    B4ClusterStabilityRecord,
    CICIoTProtocolAudit,
    NBaIoTDeviceCounts,
    RegimeCAlphaAuditRecord,
    RegimeCSeverityTrendRecord,
)

_MODULE = "validation.datasets"


def _parquet_num_rows(path: Path) -> int | None:
    if not path.exists():
        return None
    return int(pq.read_metadata(path).num_rows)


def _attack_files_by_family(
    file_hash_keys: list[str], device: str
) -> dict[str, list[str]]:
    by_family: dict[str, list[str]] = {
        family: [] for family in NBAIOT_SPEC.attack_family_dirs
    }
    prefix = f"{device}/"
    for key in file_hash_keys:
        if not key.startswith(prefix):
            continue
        rest = key[len(prefix) :]
        for family in NBAIOT_SPEC.attack_family_dirs:
            if rest.startswith(f"{family}/"):
                subtype = rest[len(family) + 1 :]
                by_family[family].append(subtype)
                break
    return {k: sorted(v) for k, v in by_family.items()}


def build_nbaiot_per_device(
    processed_root: Path,
    file_hash_keys: list[str],
) -> list[NBaIoTDeviceCounts]:
    # Reads only parquet footers (no payload) to keep audit fast.
    family_map = NBAIOT_SPEC.family_map
    if family_map is None:
        raise ValueError(
            fmt(
                _MODULE,
                "N-BaIoT spec must have family_map",
                "non-null family_map",
                repr(family_map),
            )
        )
    out: list[NBaIoTDeviceCounts] = []
    for device in NBAIOT_SPEC.device_ids:
        device_dir = processed_root / device
        train_n = _parquet_num_rows(split_path(device_dir, Split.TRAIN))
        cal_n = _parquet_num_rows(split_path(device_dir, Split.CAL))
        benign_test_n = _parquet_num_rows(split_path(device_dir, Split.TEST_BENIGN))
        attack_test_n = _parquet_num_rows(split_path(device_dir, Split.TEST_ATTACK))
        ratio: float | None = None
        if benign_test_n is not None and attack_test_n is not None:
            denom = benign_test_n + attack_test_n
            ratio = float(benign_test_n / denom) if denom > 0 else None
        out.append(
            NBaIoTDeviceCounts(
                device=device,
                family=family_map[device],
                benign_train=train_n,
                benign_cal=cal_n,
                benign_test=benign_test_n,
                attack_test_total=attack_test_n,
                benign_class_imbalance_ratio=ratio,
                attack_files_by_family=_attack_files_by_family(file_hash_keys, device),
            )
        )
    return out


def _feature_list_hash(feature_list: list[str]) -> str:
    return hash_jsonable({"features": feature_list})


def build_ciciot_protocol() -> CICIoTProtocolAudit:
    cap_policy = CICIOT2023_SPEC.cap_policy
    if cap_policy is None:
        raise RuntimeError(
            fmt(
                _MODULE,
                "CICIoT2023 cap policy missing in dataset spec",
                "non-null CapPolicy",
                repr(cap_policy),
            )
        )

    feature_list = (
        list(CICIOT2023_SPEC.feature_columns) if CICIOT2023_SPEC.feature_columns else []
    )
    expected_count = CICIOT2023_SPEC.expected_client_count
    assert expected_count is not None, "CICIoT2023 spec must have expected_client_count"
    return CICIoTProtocolAudit(
        dataset=DatasetID.CICIOT2023,
        feature_count=len(feature_list),
        feature_list=feature_list,
        dropped_columns_note=(
            "Prepare keeps only the canonical 39 FEATURE_COLUMNS plus the Label column. "
            "Any other column present in the raw merged CSV (typical raw layout has "
            "additional flow-statistics columns) is dropped at load time. Exact dropped "
            "column names depend on the source CSV header and are not persisted to the "
            "manifest; verify with `head -1` on a raw merged CSV against FEATURE_COLUMNS."
        ),
        feature_list_hash=_feature_list_hash(feature_list),
        client_identity_source=CICIOT2023_SPEC.client_identity,
        n_clients=expected_count,
        cap_total=cap_policy.total,
        cap_attack_reserve=cap_policy.attack_reserve,
        cap_strategy=cap_policy.strategy.value,
    )


@dataclasses.dataclass(frozen=True)
class HomogeneitySummary:
    js_summary: JSSummary
    verdict: HomogeneityVerdict


def compute_ciciot_homogeneity(
    cal_errors_by_client: dict[str, "np.ndarray"],
    *,
    n_bins: int,
    threshold: float,
) -> HomogeneitySummary:
    arrays = [arr for arr in cal_errors_by_client.values() if arr.size > 0]
    summary: JSSummary = pairwise_js_summary(arrays, n_bins=n_bins)

    if summary.n_compared < 2:
        return HomogeneitySummary(
            js_summary=summary,
            verdict=HomogeneityVerdict.BLOCKED_PENDING_RUN,
        )

    _mean = 0.0 if summary.mean is None else summary.mean
    return HomogeneitySummary(
        js_summary=summary,
        verdict=(
            HomogeneityVerdict.HOMOGENEOUS
            if _mean < threshold
            else HomogeneityVerdict.HETEROGENEOUS
        ),
    )


def confound_summary_for(regime: Regime) -> str | None:
    if regime in (Regime.A, Regime.C):
        return NBAIOT_CONFOUND_SUMMARY
    return None


def chronological_flags_for(
    regime: Regime,
) -> tuple[bool | None, bool | None]:
    # N-BaIoT (A/C): chronological; CICIoT2023 (B): stratified random split.
    if regime in (Regime.A, Regime.C):
        _ = NBAIOT_SPEC  # Explicitly tie the claim to canonical spec ownership.
        return True, True
    if regime == Regime.B:
        return False, False
    return None, None


@dataclasses.dataclass(frozen=True)
class _AlphaAuditMetrics:
    n_clients: int
    n_eligible: int
    n_pending: int
    device_mixture: dict[str, dict[str, float]]
    pending_client_ids: list[str]
    js_divergence_mean: float | None
    device_mixture_js_summary: JSSummary | None


def _load_alpha_audit_data(prepared_dir: Path) -> RegimeCManifestMetadata | None:
    from datp.data.contracts import (
        RegimeCManifestMetadata,  # type: ignore[attr-defined]
    )

    manifest_path = prepared_dir / ArtifactFile.MANIFEST
    if not manifest_path.exists():
        return None
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        return RegimeCManifestMetadata.model_validate(payload["metadata"])
    except (KeyError, ValueError):
        return None


def _compute_alpha_metrics(metadata: RegimeCManifestMetadata) -> _AlphaAuditMetrics:
    n_clients = metadata.n_clients
    n_eligible = 0
    n_pending = 0
    device_mixture: dict[str, dict[str, float]] = {}
    pending_client_ids: list[str] = []

    for cs in metadata.client_summaries:
        if cs.calibration_pending:
            n_pending += 1
            pending_client_ids.append(cs.client_id)
        else:
            n_eligible += 1
        device_mixture[cs.client_id] = dict(cs.device_mixture_proportions)

    js_mean = metadata.js_divergence

    device_mixture_js_summary: JSSummary | None = None
    if len(device_mixture) >= 2:
        all_devices = sorted({d for m in device_mixture.values() for d in m})
        if all_devices:
            mixture_vectors = [
                np.array(
                    [
                        device_mixture[cid][d] if d in device_mixture[cid] else 0.0
                        for d in all_devices
                    ],
                    dtype=np.float64,
                )
                for cid in sorted(device_mixture.keys())
            ]
            device_mixture_js_summary = pairwise_js_from_distributions(mixture_vectors)

    return _AlphaAuditMetrics(
        n_clients=n_clients,
        n_eligible=n_eligible,
        n_pending=n_pending,
        device_mixture=device_mixture,
        pending_client_ids=pending_client_ids,
        js_divergence_mean=js_mean,
        device_mixture_js_summary=device_mixture_js_summary,
    )


def _build_alpha_record(
    alpha: float,
    seed: int,
    metrics: _AlphaAuditMetrics,
) -> RegimeCAlphaAuditRecord:
    alpha_text = alpha_label(alpha)
    coverage = (
        f"{metrics.n_eligible}/{metrics.n_clients}" if metrics.n_clients > 0 else "0/0"
    )

    dmjs = metrics.device_mixture_js_summary
    return RegimeCAlphaAuditRecord(
        alpha=alpha_text or "",
        seed=seed,
        n_clients=metrics.n_clients,
        n_eligible=metrics.n_eligible,
        n_calibration_pending=metrics.n_pending,
        coverage_ratio=coverage,
        js_divergence_mean=metrics.js_divergence_mean,
        device_mixture_proportions=metrics.device_mixture,
        pending_client_ids=metrics.pending_client_ids,
        device_mixture_js_mean=dmjs.mean if dmjs is not None else None,
        device_mixture_js_std=dmjs.std if dmjs is not None else None,
        device_mixture_js_p50=dmjs.p50 if dmjs is not None else None,
        device_mixture_js_p95=dmjs.p95 if dmjs is not None else None,
        device_mixture_js_max=dmjs.max if dmjs is not None else None,
    )


def build_regime_c_alpha_audit(
    prepared_dir: Path,
    alpha: float,
    seed: int,
) -> RegimeCAlphaAuditRecord | None:
    payload = _load_alpha_audit_data(prepared_dir)
    if payload is None:
        return None
    metrics = _compute_alpha_metrics(payload)
    return _build_alpha_record(alpha, seed, metrics)


_SEVERITY_FIELD: dict[SeverityVariable, str] = {
    SeverityVariable.DEVICE_MIXTURE_JS_MEAN: "device_mixture_js_mean",
    SeverityVariable.RECON_ERROR_JS_MEAN: "recon_error_js_mean",
}

_OUTCOME_FIELD: dict[OutcomeVariable, str] = {
    OutcomeVariable.DELTA_B1_B2: "delta_b1_b2",
}


def _try_extract_severity(
    record: RegimeCAlphaAuditRecord,
    sev_var: SeverityVariable,
    alpha_numeric: float,
) -> float | None:
    if sev_var == SeverityVariable.ALPHA_NUMERIC:
        if math.isinf(alpha_numeric) or math.isnan(alpha_numeric):
            return None
        return alpha_numeric
    field = _SEVERITY_FIELD[sev_var]
    raw = getattr(record, field)
    if raw is None:
        return None
    val = float(raw)
    if math.isnan(val):
        return None
    return val


def _try_extract_outcome(
    record: RegimeCAlphaAuditRecord,
    outcome_var: OutcomeVariable,
) -> float | None:
    field = _OUTCOME_FIELD[outcome_var]
    raw = getattr(record, field)
    if raw is None:
        return None
    val = float(raw)
    if math.isnan(val):
        return None
    return val


def _build_severity_pairs(
    records: list[RegimeCAlphaAuditRecord],
    sev_var: SeverityVariable,
    outcome_var: OutcomeVariable,
    alpha_numerics: list[float],
) -> list[tuple[float, float]]:
    pairs: list[tuple[float, float]] = []
    for i, r in enumerate(records):
        sev = _try_extract_severity(r, sev_var, alpha_numerics[i])
        if sev is None:
            continue
        out = _try_extract_outcome(r, outcome_var)
        if out is None:
            continue
        pairs.append((sev, out))
    return pairs


def _build_severity_record(
    sev_var: SeverityVariable,
    outcome_var: OutcomeVariable,
    n_cells: int,
    *,
    rho: float | None,
    p_value: float | None,
    sig_alpha: float,
) -> RegimeCSeverityTrendRecord:
    if rho is None:
        return RegimeCSeverityTrendRecord(
            severity_variable=sev_var,
            comparison=outcome_var,
            n_cells=n_cells,
            spearman_rho=None,
            p_value=None,
            status=SeverityTrendStatus.INSUFFICIENT_DATA,
        )
    return RegimeCSeverityTrendRecord(
        severity_variable=sev_var,
        comparison=outcome_var,
        n_cells=n_cells,
        spearman_rho=rho,
        p_value=p_value,
        status=(
            SeverityTrendStatus.SIGNIFICANT
            if p_value is not None and p_value < sig_alpha
            else SeverityTrendStatus.NOT_SIGNIFICANT
        ),
    )


def compute_regime_c_severity_trend(
    records: list[RegimeCAlphaAuditRecord],
    *,
    significance_alpha: float,
) -> list[RegimeCSeverityTrendRecord]:
    from datp.statistics.spearman import spearman_correlation  # noqa: PLC0415

    sig_alpha = float(significance_alpha)
    alpha_numerics = [cast(float, alpha_from_label(r.alpha)) for r in records]

    tests: list[tuple[SeverityVariable, OutcomeVariable]] = [
        (SeverityVariable.DEVICE_MIXTURE_JS_MEAN, OutcomeVariable.DELTA_B1_B2),
        (SeverityVariable.RECON_ERROR_JS_MEAN, OutcomeVariable.DELTA_B1_B2),
        (SeverityVariable.ALPHA_NUMERIC, OutcomeVariable.DELTA_B1_B2),
    ]

    results: list[RegimeCSeverityTrendRecord] = []
    for sev_var, outcome_var in tests:
        pairs = _build_severity_pairs(records, sev_var, outcome_var, alpha_numerics)
        n_cells = len(pairs)
        if n_cells < 3:
            results.append(
                _build_severity_record(
                    sev_var,
                    outcome_var,
                    n_cells,
                    rho=None,
                    p_value=None,
                    sig_alpha=sig_alpha,
                )
            )
            continue

        x = np.array([p[0] for p in pairs])
        y = np.array([p[1] for p in pairs])
        sr = spearman_correlation(x, y, significance_alpha=sig_alpha)
        results.append(
            _build_severity_record(
                sev_var,
                outcome_var,
                n_cells,
                rho=sr.rho,
                p_value=sr.p_value,
                sig_alpha=sig_alpha,
            )
        )

    return results


def compute_b4_cluster_stability(
    cluster_assignments_by_seed: dict[int, dict[str, int]],
    regime: Regime,
    alpha: str | None,
) -> list[B4ClusterStabilityRecord]:
    from sklearn.metrics import adjusted_rand_score  # noqa: PLC0415

    seeds = sorted(cluster_assignments_by_seed.keys())
    records: list[B4ClusterStabilityRecord] = []
    for i, seed_a in enumerate(seeds):
        for seed_b in seeds[i + 1 :]:
            assigns_a = cluster_assignments_by_seed[seed_a]
            assigns_b = cluster_assignments_by_seed[seed_b]
            common = sorted(set(assigns_a) & set(assigns_b))
            if len(common) < 2:
                continue
            labels_a = [assigns_a[c] for c in common]
            labels_b = [assigns_b[c] for c in common]
            ari = float(adjusted_rand_score(labels_a, labels_b))
            records.append(
                B4ClusterStabilityRecord(
                    regime=regime,
                    alpha=alpha,
                    seed_a=seed_a,
                    seed_b=seed_b,
                    adjusted_rand_index=ari,
                )
            )
    return records
