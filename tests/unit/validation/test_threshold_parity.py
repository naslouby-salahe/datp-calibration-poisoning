"""Regression tests: audit _threshold_result must equal canonical derive_threshold."""

from __future__ import annotations

import numpy as np
import pytest

from datp.config.compose import BASE_CONFIG
from datp.config.models import DatpConfig
from datp.core.enums import Baseline, Regime
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


def _config_with_b4_mode(mode: str) -> DatpConfig:
    """Return a config with a specific b4_regime_a_mode."""
    cfg_dict = BASE_CONFIG.model_dump()
    cfg_dict["threshold"]["b4_regime_a_mode"] = mode
    return DatpConfig.model_validate(cfg_dict)


@pytest.mark.parametrize(
    "baseline", [Baseline.B1, Baseline.B2, Baseline.B3, Baseline.B4]
)
def test_threshold_result_equals_derive_threshold_regime_a(baseline: Baseline) -> None:
    """_threshold_result must delegate to derive_threshold identically."""
    cal_errors = _make_cal_errors()
    tau_global = 0.15
    cfg = BASE_CONFIG

    audit_result = _threshold_result(
        baseline,
        Regime.A,
        cal_errors,
        tau_global,
        cfg=cfg,
    )
    canonical_result = derive_threshold(
        _DeriveInput(
            baseline=baseline,
            client_errors=cal_errors,
            n_min=cfg.threshold.n_min,
            q=cfg.threshold.q,
            tau_global=tau_global,
            regime=Regime.A,
            threshold_cfg=cfg.threshold,
        )
    )

    assert audit_result is not None, f"audit returned None for {baseline}"
    assert canonical_result is not None
    assert audit_result.run.baseline == canonical_result.run.baseline
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


def test_b4_silhouette_mode_parity() -> None:
    """B4 Regime A with silhouette mode: audit must match canonical."""
    cal_errors = _make_cal_errors()
    tau_global = 0.15
    cfg = _config_with_b4_mode("silhouette")

    audit_result = _threshold_result(
        Baseline.B4,
        Regime.A,
        cal_errors,
        tau_global,
        cfg=cfg,
    )
    canonical_result = derive_threshold(
        _DeriveInput(
            baseline=Baseline.B4,
            client_errors=cal_errors,
            n_min=cfg.threshold.n_min,
            q=cfg.threshold.q,
            tau_global=tau_global,
            regime=Regime.A,
            threshold_cfg=cfg.threshold,
        )
    )

    assert audit_result is not None
    assert canonical_result is not None
    assert audit_result.run.baseline == canonical_result.run.baseline
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


def test_b4_fixed_mode_parity() -> None:
    """B4 Regime A with fixed mode: audit must match canonical with explicit k."""
    cal_errors = _make_cal_errors()
    tau_global = 0.15
    cfg = _config_with_b4_mode("fixed")

    audit_result = _threshold_result(
        Baseline.B4,
        Regime.A,
        cal_errors,
        tau_global,
        cfg=cfg,
    )
    canonical_result = derive_threshold(
        _DeriveInput(
            baseline=Baseline.B4,
            client_errors=cal_errors,
            n_min=cfg.threshold.n_min,
            q=cfg.threshold.q,
            tau_global=tau_global,
            regime=Regime.A,
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
