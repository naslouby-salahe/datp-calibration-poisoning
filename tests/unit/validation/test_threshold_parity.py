"""Tests verifying threshold derivation parity between auditing functions and canonical thresholding modules."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import cast

import numpy as np
import pytest

from datp.config.compose import BASE_CONFIG
from datp.core.enums import MetricName, ScoringStage, ThresholdPolicy
from datp.data.datasets.nbaiot.spec import DEVICE_FAMILY_MAP
from datp.thresholding.thresholds import _DeriveInput, derive_threshold
from datp.validation import results

_REAL_DEVICES = list(DEVICE_FAMILY_MAP.keys())


def _make_cal_errors(n_samples: int = 120) -> dict[str, np.ndarray]:
    """Helper to build synthetic client calibration error values."""
    rng = np.random.default_rng(42)
    return {
        name: rng.normal(loc=0.1 + i * 0.03, scale=0.05, size=n_samples)
        for i, name in enumerate(_REAL_DEVICES)
    }


@pytest.mark.parametrize(
    "policy",
    [
        ThresholdPolicy.GLOBAL_THRESHOLD,
        ThresholdPolicy.LOCAL_THRESHOLD,
        ThresholdPolicy.CLUSTER_THRESHOLD,
    ],
)
def test_load_score_arrays_thresholds_match_derive_threshold(
    monkeypatch: pytest.MonkeyPatch,
    policy: ThresholdPolicy,
) -> None:
    """Verify loaded score thresholds match derive_threshold outputs for all policies."""
    cal_errors = _make_cal_errors()
    tau_global = 0.15
    cfg = BASE_CONFIG

    def fake_stage_files(_score_root: Path, stage: ScoringStage) -> list[Path]:
        if stage == ScoringStage.CAL:
            return [Path(f"{client_id}.parquet") for client_id in cal_errors]
        return []

    monkeypatch.setattr(results, "score_stage_files", fake_stage_files)
    monkeypatch.setattr(
        results,
        "read_scores",
        lambda path: cal_errors[path.stem],
    )

    arrays = results.load_score_arrays(
        cast(results.AuditAccumulator, SimpleNamespace(warnings=[])),
        cast(
            results.RunContext,
            SimpleNamespace(
                score_root=Path("scores"),
                policy=policy,
                metrics={MetricName.TAU_GLOBAL: tau_global},
                seed=0,
                run_id="run",
            ),
        ),
        cfg,
    )
    canonical_result = derive_threshold(
        _DeriveInput(
            policy=policy,
            client_errors=cal_errors,
            n_min=cfg.threshold.n_min,
            q=cfg.threshold.q,
            tau_global=tau_global,
            threshold_cfg=cfg.threshold,
            seed=0,
        )
    )

    assert arrays.threshold_result is not None
    assert arrays.threshold_result.run.policy == canonical_result.run.policy
    assert arrays.threshold_result.tau_global == pytest.approx(
        canonical_result.tau_global
    )
    assert arrays.threshold_result.eligible_count == canonical_result.eligible_count
    assert arrays.threshold_result.pending_count == canonical_result.pending_count
    for actual, expected in zip(
        sorted(
            arrays.threshold_result.client_thresholds,
            key=lambda item: item.client_id,
        ),
        sorted(canonical_result.client_thresholds, key=lambda item: item.client_id),
    ):
        assert actual.client_id == expected.client_id
        assert actual.threshold == pytest.approx(expected.threshold, abs=1e-12)
        assert actual.calibration_pending == expected.calibration_pending
