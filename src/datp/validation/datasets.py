from __future__ import annotations

import dataclasses
import json
import math
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, cast

import numpy as np
import pyarrow.parquet as pq

from datp.artifacts.names import ArtifactFile
from datp.data.catalog import DatasetID
from datp.validation.constants import NBAIOT_CONFOUND_SUMMARY

if TYPE_CHECKING:
    from datp.data.contracts import RegimeCManifestMetadata  # type: ignore[attr-defined]
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


def _device_family_subtype(rest: str) -> tuple[str, str] | None:
    """Return (family, subtype) for a device-relative path, or None if no family matches."""
    for family in NBAIOT_SPEC.attack_family_dirs:
        if rest.startswith(f"{family}/"):
            return family, rest[len(family) + 1 :]
    return None


def _attack_files_by_family(
    file_hash_keys: list[str], device: str
) -> tuple[AttackFamilyFiles, ...]:
    return tuple(
        AttackFamilyFiles(
            family=family,
            files=tuple(
                sorted(_attack_subtypes_for_family(file_hash_keys, device, family))
            ),
        )
        for family in NBAIOT_SPEC.attack_family_dirs
    )


def _attack_subtypes_for_family(
    file_hash_keys: list[str], device: str, target_family: str
) -> tuple[str, ...]:
    prefix = f"{device}/"
    subtypes: list[str] = []
    for key in file_hash_keys:
        if not key.startswith(prefix):
            continue
        match = _device_family_subtype(key[len(prefix) :])
        if match is None:
            continue
        family, subtype = match
        if family == target_family:
            subtypes.append(subtype)
    return tuple(subtypes)


def _attack_files_mapping(
    attack_files: tuple[AttackFamilyFiles, ...],
) -> AttackFilesMapping:
    return AttackFilesMapping(
        tuple((entry.family, list(entry.files)) for entry in attack_files)
    )


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
                attack_files_by_family=_attack_files_mapping(
                    _attack_files_by_family(file_hash_keys, device)
                ),
            )
        )
    return out


def _feature_list_hash(feature_list: list[str]) -> str:
    return hash_jsonable((("features", tuple(feature_list)),))


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


@dataclasses.dataclass(frozen=True, slots=True)
class AttackFamilyFiles:
    family: str
    files: tuple[str, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class AttackFilesMapping(Mapping[str, list[str]]):
    entries: tuple[tuple[str, list[str]], ...]

    def __getitem__(self, key: str) -> list[str]:
        for family, files in self.entries:
            if family == key:
                return files
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (family for family, _ in self.entries)

    def __len__(self) -> int:
        return len(self.entries)


@dataclasses.dataclass(frozen=True, slots=True)
class ClientDeviceMixture:
    client_id: str
    proportions: tuple[tuple[str, float], ...]


@dataclasses.dataclass(frozen=True, slots=True)
class DeviceProportionMapping(Mapping[str, float]):
    entries: tuple[tuple[str, float], ...]

    def __getitem__(self, key: str) -> float:
        for device, proportion in self.entries:
            if device == key:
                return proportion
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (device for device, _ in self.entries)

    def __len__(self) -> int:
        return len(self.entries)


@dataclasses.dataclass(frozen=True, slots=True)
class DeviceMixtureMapping(Mapping[str, DeviceProportionMapping]):
    entries: tuple[tuple[str, DeviceProportionMapping], ...]

    def __getitem__(self, key: str) -> DeviceProportionMapping:
        for client_id, proportions in self.entries:
            if client_id == key:
                return proportions
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (client_id for client_id, _ in self.entries)

    def __len__(self) -> int:
        return len(self.entries)


@dataclasses.dataclass(frozen=True, slots=True)
class ClientSummaryClassification:
    n_eligible: int
    n_pending: int
    pending_ids: tuple[str, ...]
    device_mixture: tuple[ClientDeviceMixture, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class ClusterAssignments:
    seed: int
    assignments: tuple[tuple[str, int], ...]


def compute_ciciot_homogeneity(
    cal_errors_by_client: Mapping[str, "np.ndarray"],
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
    device_mixture: tuple[ClientDeviceMixture, ...]
    pending_client_ids: tuple[str, ...]
    js_divergence_mean: float | None
    device_mixture_js_summary: JSSummary | None


def _load_alpha_audit_data(prepared_dir: Path) -> RegimeCManifestMetadata | None:
    from datp.data.contracts import RegimeCManifestMetadata  # type: ignore[attr-defined]

    manifest_path = prepared_dir / ArtifactFile.MANIFEST
    if not manifest_path.exists():
        return None
    try:
        payload = cast(
            Mapping[str, object],
            json.loads(manifest_path.read_text(encoding="utf-8")),
        )
        return RegimeCManifestMetadata.model_validate(payload.get("metadata"))
    except (KeyError, ValueError):
        return None


def _classify_client_summaries(
    client_summaries: list[object],
) -> ClientSummaryClassification:
    """Partition client summaries into eligible vs pending counts and collect device mixtures."""
    n_eligible = 0
    n_pending = 0
    pending_ids: list[str] = []
    device_mixture: list[ClientDeviceMixture] = []
    for cs in client_summaries:  # type: ignore[attr-defined]
        if cs.calibration_pending:  # type: ignore[union-attr]
            n_pending += 1
            pending_ids.append(cs.client_id)  # type: ignore[union-attr]
        else:
            n_eligible += 1
        device_mixture.append(
            ClientDeviceMixture(
                client_id=cs.client_id,  # type: ignore[union-attr]
                proportions=tuple(
                    sorted(cs.device_mixture_proportions.items())  # type: ignore[union-attr]
                ),
            )
        )
    return ClientSummaryClassification(
        n_eligible=n_eligible,
        n_pending=n_pending,
        pending_ids=tuple(pending_ids),
        device_mixture=tuple(device_mixture),
    )


def _device_mixture_js(
    device_mixture: tuple[ClientDeviceMixture, ...],
) -> JSSummary | None:
    if len(device_mixture) < 2:
        return None
    all_devices = sorted(
        {device for mixture in device_mixture for device, _ in mixture.proportions}
    )
    if not all_devices:
        return None
    mixture_vectors = [
        np.array(
            [_mixture_value(mixture, device) for device in all_devices],
            dtype=np.float64,
        )
        for mixture in sorted(device_mixture, key=lambda item: item.client_id)
    ]
    return pairwise_js_from_distributions(mixture_vectors)


def _mixture_value(mixture: ClientDeviceMixture, device: str) -> float:
    for candidate, value in mixture.proportions:
        if candidate == device:
            return value
    return 0.0


def _device_mixture_mapping(
    device_mixture: tuple[ClientDeviceMixture, ...],
) -> DeviceMixtureMapping:
    return DeviceMixtureMapping(
        tuple(
            (
                mixture.client_id,
                DeviceProportionMapping(mixture.proportions),
            )
            for mixture in device_mixture
        )
    )


def _compute_alpha_metrics(metadata: RegimeCManifestMetadata) -> _AlphaAuditMetrics:
    classification = _classify_client_summaries(metadata.client_summaries)
    return _AlphaAuditMetrics(
        n_clients=metadata.n_clients,
        n_eligible=classification.n_eligible,
        n_pending=classification.n_pending,
        device_mixture=classification.device_mixture,
        pending_client_ids=classification.pending_ids,
        js_divergence_mean=metadata.js_divergence,
        device_mixture_js_summary=_device_mixture_js(classification.device_mixture),
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
        device_mixture_proportions=_device_mixture_mapping(metrics.device_mixture),
        pending_client_ids=list(metrics.pending_client_ids),
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


def _try_extract_severity(
    record: RegimeCAlphaAuditRecord,
    sev_var: SeverityVariable,
    alpha_numeric: float,
) -> float | None:
    if sev_var == SeverityVariable.ALPHA_NUMERIC:
        if math.isinf(alpha_numeric) or math.isnan(alpha_numeric):
            return None
        return alpha_numeric
    raw = _severity_value(record, sev_var)
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
    raw = _outcome_value(record, outcome_var)
    if raw is None:
        return None
    val = float(raw)
    if math.isnan(val):
        return None
    return val


def _severity_value(
    record: RegimeCAlphaAuditRecord, sev_var: SeverityVariable
) -> float | None:
    match sev_var:
        case SeverityVariable.DEVICE_MIXTURE_JS_MEAN:
            return record.device_mixture_js_mean
        case SeverityVariable.RECON_ERROR_JS_MEAN:
            return record.recon_error_js_mean
        case SeverityVariable.ALPHA_NUMERIC:
            raise ValueError("alpha numeric is derived from the alpha label")


def _outcome_value(
    record: RegimeCAlphaAuditRecord, outcome_var: OutcomeVariable
) -> float | None:
    match outcome_var:
        case OutcomeVariable.DELTA_B1_B2:
            return record.delta_b1_b2


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


@dataclasses.dataclass(frozen=True, slots=True)
class _SeverityTestResult:
    sev_var: SeverityVariable
    outcome_var: OutcomeVariable
    n_cells: int
    rho: float | None
    p_value: float | None
    sig_alpha: float


def _build_severity_record(result: _SeverityTestResult) -> RegimeCSeverityTrendRecord:
    if result.rho is None:
        return RegimeCSeverityTrendRecord(
            severity_variable=result.sev_var,
            comparison=result.outcome_var,
            n_cells=result.n_cells,
            spearman_rho=None,
            p_value=None,
            status=SeverityTrendStatus.INSUFFICIENT_DATA,
        )
    significant = result.p_value is not None and result.p_value < result.sig_alpha
    return RegimeCSeverityTrendRecord(
        severity_variable=result.sev_var,
        comparison=result.outcome_var,
        n_cells=result.n_cells,
        spearman_rho=result.rho,
        p_value=result.p_value,
        status=(
            SeverityTrendStatus.SIGNIFICANT
            if significant
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
                    _SeverityTestResult(
                        sev_var, outcome_var, n_cells, None, None, sig_alpha
                    )
                )
            )
            continue

        x = np.array([p[0] for p in pairs])
        y = np.array([p[1] for p in pairs])
        sr = spearman_correlation(x, y, significance_alpha=sig_alpha)
        results.append(
            _build_severity_record(
                _SeverityTestResult(
                    sev_var, outcome_var, n_cells, sr.rho, sr.p_value, sig_alpha
                )
            )
        )

    return results


def compute_b4_cluster_stability(
    cluster_assignments_by_seed: tuple[ClusterAssignments, ...],
    regime: Regime,
    alpha: str | None,
) -> list[B4ClusterStabilityRecord]:
    from sklearn.metrics import adjusted_rand_score  # type: ignore[import-untyped]  # noqa: PLC0415

    seeds = sorted({item.seed for item in cluster_assignments_by_seed})
    records: list[B4ClusterStabilityRecord] = []
    for i, seed_a in enumerate(seeds):
        for seed_b in seeds[i + 1 :]:
            assigns_a = _assignments_for_seed(cluster_assignments_by_seed, seed_a)
            assigns_b = _assignments_for_seed(cluster_assignments_by_seed, seed_b)
            client_ids_a = {client_id for client_id, _ in assigns_a}
            client_ids_b = {client_id for client_id, _ in assigns_b}
            common = sorted(client_ids_a & client_ids_b)
            if len(common) < 2:
                continue
            labels_a = [
                _assignment_for_client(assigns_a, client_id) for client_id in common
            ]
            labels_b = [
                _assignment_for_client(assigns_b, client_id) for client_id in common
            ]
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


def _assignments_for_seed(
    cluster_assignments_by_seed: tuple[ClusterAssignments, ...], seed: int
) -> tuple[tuple[str, int], ...]:
    for item in cluster_assignments_by_seed:
        if item.seed == seed:
            return tuple(sorted(item.assignments))
    raise KeyError(seed)


def _assignment_for_client(
    assignments: tuple[tuple[str, int], ...], client_id: str
) -> int:
    for candidate, cluster in assignments:
        if candidate == client_id:
            return cluster
    raise KeyError(client_id)
