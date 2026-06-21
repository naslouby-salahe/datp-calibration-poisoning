"""Regression tests: audit _threshold_result must equal canonical derive_threshold."""

from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

import numpy as np
import pytest

from datp.config.compose import BASE_CONFIG
from datp.data.datasets.nbaiot.spec import DEVICE_FAMILY_MAP
from datp.thresholding.thresholds import _DeriveInput, derive_threshold
from datp.validation._audit_helpers import _threshold_result

_REAL_DEVICES = list(DEVICE_FAMILY_MAP.keys())  # 9 real N-BaIoT device names


def _make_cal_errors(
    n_clients: int | None = None, n_samples: int = 120
) -> dict[str, np.ndarray]:
    """Synthetic calibration errors for N-BaIoT-style clients using real device names."""
    rng = np.random.default_rng(42)
    devices = _REAL_DEVICES[:n_clients] if n_clients is not None else _REAL_DEVICES
    return {
        name: rng.normal(loc=0.1 + i * 0.03, scale=0.05, size=n_samples)
        for i, name in enumerate(devices)
    }


@pytest.mark.parametrize(
    "policy",
    [
        ThresholdPolicy.GLOBAL_THRESHOLD,
        ThresholdPolicy.LOCAL_THRESHOLD,
        ThresholdPolicy.CLUSTER_THRESHOLD,
        ThresholdPolicy.CLUSTER_THRESHOLD,
    ],
)
def test_threshold_result_equals_derive_threshold(policy: ThresholdPolicy) -> None:
    """_threshold_result must delegate to derive_threshold identically."""
    cal_errors = _make_cal_errors()
    tau_global = 0.15
    cfg = BASE_CONFIG

    audit_result = _threshold_result(
        policy,
        cal_errors,
        tau_global,
        cfg=cfg,
    )
    canonical_result = derive_threshold(
        _DeriveInput(
            policy=policy,
            client_errors=cal_errors,
            n_min=cfg.threshold.n_min,
            q=cfg.threshold.q,
            tau_global=tau_global,
            threshold_cfg=cfg.threshold,
        )
    )

    assert audit_result is not None, f"audit returned None for {policy}"
    assert canonical_result is not None
    assert audit_result.run.policy == canonical_result.run.policy
    assert audit_result.tau_global == pytest.approx(canonical_result.tau_global)
    assert audit_result.eligible_count == canonical_result.eligible_count
    assert audit_result.pending_count == canonical_result.pending_count
    assert len(audit_result.client_thresholds) == len(
        canonical_result.client_thresholds
    )
    for act, exp in zip(
        sorted(audit_result.client_thresholds, key=lambda x: x.client_id),
        sorted(canonical_result.client_thresholds, key=lambda x: x.client_id),
    ):
        assert act.client_id == exp.client_id
        assert act.threshold == pytest.approx(exp.threshold, abs=1e-12)
        assert act.calibration_pending == exp.calibration_pending
        assert act.strategy == exp.strategy


def test_cluster_silhouette_mode_parity() -> None:
    """CLUSTER_THRESHOLD N-BaIoT main: audit must match canonical."""
    cal_errors = _make_cal_errors()
    tau_global = 0.15
    cfg = BASE_CONFIG

    audit_result = _threshold_result(
        ThresholdPolicy.CLUSTER_THRESHOLD,
        cal_errors,
        tau_global,
        cfg=cfg,
    )
    canonical_result = derive_threshold(
        _DeriveInput(
            policy=ThresholdPolicy.CLUSTER_THRESHOLD,
            client_errors=cal_errors,
            n_min=cfg.threshold.n_min,
            q=cfg.threshold.q,
            tau_global=tau_global,
            threshold_cfg=cfg.threshold,
        )
    )

    assert audit_result is not None
    assert canonical_result is not None
    assert audit_result.run.policy == canonical_result.run.policy
    # Both should agree on tau_global, eligible/pending counts, and per-client thresholds
    assert audit_result.tau_global == pytest.approx(canonical_result.tau_global)
    assert audit_result.eligible_count == canonical_result.eligible_count
    assert audit_result.pending_count == canonical_result.pending_count
    for act, exp in zip(
        sorted(audit_result.client_thresholds, key=lambda x: x.client_id),
        sorted(canonical_result.client_thresholds, key=lambda x: x.client_id),
    ):
        assert act.client_id == exp.client_id
        assert act.threshold == pytest.approx(exp.threshold, abs=1e-12)
        assert act.calibration_pending == exp.calibration_pending


def test_cluster_fixed_mode_parity() -> None:
    """CLUSTER_THRESHOLD N-BaIoT main: audit must match canonical with explicit k."""
    cal_errors = _make_cal_errors()
    tau_global = 0.15
    cfg = BASE_CONFIG

    audit_result = _threshold_result(
        ThresholdPolicy.CLUSTER_THRESHOLD,
        cal_errors,
        tau_global,
        cfg=cfg,
    )
    canonical_result = derive_threshold(
        _DeriveInput(
            policy=ThresholdPolicy.CLUSTER_THRESHOLD,
            client_errors=cal_errors,
            n_min=cfg.threshold.n_min,
            q=cfg.threshold.q,
            tau_global=tau_global,
            threshold_cfg=cfg.threshold,
        )
    )

    assert audit_result is not None
    assert canonical_result is not None
    for act, exp in zip(
        sorted(audit_result.client_thresholds, key=lambda x: x.client_id),
        sorted(canonical_result.client_thresholds, key=lambda x: x.client_id),
    ):
        assert act.threshold == pytest.approx(exp.threshold, abs=1e-12)
