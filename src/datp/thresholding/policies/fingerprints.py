from __future__ import annotations

import numpy as np
from scipy import stats as sp_stats
from sklearn.preprocessing import StandardScaler

from datp.core.enums import CLUSTER_FINGERPRINT_FEATURES
from datp.core.errors import fmt

_MODULE = "thresholding.cluster_threshold.fingerprints"

assert len(CLUSTER_FINGERPRINT_FEATURES) == 4, (
    f"CLUSTER_FINGERPRINT_FEATURES must have exactly 4 elements, got {len(CLUSTER_FINGERPRINT_FEATURES)}"
)


def compute_fingerprints(
    client_errors: dict[str, np.ndarray],
    eligible: list[str],
    *,
    q: float,
) -> dict[str, np.ndarray]:
    fingerprints: dict[str, np.ndarray] = {}
    for cid in eligible:
        e = np.asarray(client_errors[cid], dtype=np.float64)
        mean_e = float(np.mean(e))
        std_e = float(np.std(e, ddof=1)) if e.size >= 2 else 0.0
        raw_skew = float(sp_stats.skew(e)) if (e.size >= 2 and std_e > 0.0) else 0.0
        skew_e = 0.0 if (not np.isfinite(raw_skew)) else raw_skew
        p95_e = float(np.percentile(e, q * 100))
        fingerprints[cid] = np.array([mean_e, std_e, skew_e, p95_e], dtype=np.float64)
    return fingerprints


def _validate_fingerprint_matrix(fingerprint_matrix: np.ndarray) -> None:
    if not np.isfinite(fingerprint_matrix).all():
        raise ValueError(
            fmt(
                _MODULE,
                "Invalid fingerprint values",
                "finite mean/std/skew/p95",
                "NaN or inf",
            )
        )
    unique_rows = np.unique(fingerprint_matrix, axis=0)
    if unique_rows.shape[0] < 2:
        raise ValueError(
            fmt(
                _MODULE,
                "Degenerate fingerprints: all eligible clients have identical fingerprints",
                "at least 2 distinct eligible fingerprints",
                str(unique_rows.shape[0]),
            )
        )


def scaled_fingerprints(
    client_errors: dict[str, np.ndarray],
    eligible_ids: list[str],
    *,
    q: float,
) -> tuple[dict[str, np.ndarray], np.ndarray]:
    fingerprints = compute_fingerprints(client_errors, eligible_ids, q=q)
    fingerprint_matrix = np.array([fingerprints[cid] for cid in eligible_ids])
    _validate_fingerprint_matrix(fingerprint_matrix)
    fingerprint_scaled = StandardScaler().fit_transform(fingerprint_matrix)
    if not np.isfinite(fingerprint_scaled).all():
        raise ValueError(
            fmt(
                _MODULE,
                "Invalid scaled fingerprints",
                "finite values after scaling",
                "NaN or inf",
            )
        )
    return fingerprints, fingerprint_scaled
