"""Tests verifying trimmed calibration defenses against training/calibration score poisoning attacks."""

from __future__ import annotations

import math

import numpy as np
import pytest

from datp.attacks.enums import (
    PoisoningDefense,
    PoisoningSourceStrategy,
)
from datp.attacks.execution.cell_runner import (
    InjectionSpec,
    inject_single_victim,
    recompute_pair,
)
from datp.attacks.injection.defenses import (
    apply_defense,
    build_defended_collection,
    trimmed_calibration,
)
from datp.attacks.score_containers import build_score_collection
from datp.attacks.types import PoisonedCalibrationSet
from datp.core.enums import ThresholdPolicy
from datp.core.seeds import SeedPair
from datp.testsupport.synthetic_scores import (
    StandardScoreSetRequest,
    make_standard_score_set,
)


def test_trim_zero_fraction_returns_equal_copy() -> None:
    """Verify that trimming with a 0.0 fraction returns a sorted or identical copy."""
    cal = np.array([0.1, 0.9, 0.3, 0.5, 0.2])
    out = trimmed_calibration(cal, 0.0)
    assert np.array_equal(np.sort(cal), np.sort(out)) or np.array_equal(cal, out)
    assert out is not cal


def test_trim_does_not_mutate_input() -> None:
    """Verify that trimming does not modify the original input array in-place."""
    cal = np.array([0.1, 0.9, 0.3, 0.5, 0.2])
    before = cal.copy()
    trimmed_calibration(cal, 0.2)
    assert np.array_equal(cal, before)


def test_trim_drops_floor_k_from_each_tail() -> None:
    """Verify that trimming drops floor(N * fraction) elements from both high and low tails."""
    cal = np.arange(10, dtype=np.float64)
    out = trimmed_calibration(cal, 0.1)
    assert np.array_equal(out, np.array([1, 2, 3, 4, 5, 6, 7, 8], dtype=np.float64))


def test_trim_removes_extreme_outliers() -> None:
    """Verify that extreme outliers are successfully pruned by the trimming defense."""
    cal = np.concatenate([np.full(90, 0.05), np.full(10, 100.0)])

    out = trimmed_calibration(cal, 0.10)
    assert out.max() < 1.0


def test_trim_rejects_out_of_range_fraction() -> None:
    """Verify that invalid trimming fractions (outside [0, 0.5)) raise ValueError."""
    cal = np.arange(10, dtype=np.float64)
    with pytest.raises(ValueError, match="0, 0.5"):
        trimmed_calibration(cal, 0.5)
    with pytest.raises(ValueError, match="0, 0.5"):
        trimmed_calibration(cal, -0.1)


def _make_collection() -> object:
    """Helper to build a synthetic client score collection."""
    ss = make_standard_score_set(StandardScoreSetRequest(n_eligible=9, n_pending=1))
    raw = {c.client_id: (c.cal, c.test_benign, c.test_attack) for c in ss.clients}
    return build_score_collection(raw)


def test_defended_collection_trims_cal_keeps_test_arrays() -> None:
    """Verify that defended collection trims only the calibration splits, leaving test splits intact."""
    col = _make_collection()
    defended = build_defended_collection(col, 0.10)
    for cid in col.all_ids:
        assert defended.clients[cid].cal.shape[0] < col.clients[cid].cal.shape[0]
        assert np.array_equal(
            defended.clients[cid].test_attack, col.clients[cid].test_attack
        )


def test_apply_defense_none_is_identity() -> None:
    """Verify that applying PoisoningDefense.NONE acts as a no-op identity."""
    col = _make_collection()
    victim = col.eligible_ids[0]
    outcome = inject_single_victim(
        col,
        victim_id=victim,
        spec=InjectionSpec(
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            fraction=0.10,
            seed_pair=SeedPair(training_seed=0, poisoning_seed=100),
            objective=None,
        ),
    )
    poisoned_cal = {
        cid: outcome.poisoned_cal_set.for_client(cid).cal
        for cid in outcome.poisoned_cal_set.client_ids
    }
    col2, pois2 = apply_defense(
        col, poisoned_cal, defense=PoisoningDefense.NONE, trim_fraction=0.05
    )
    assert col2 is col
    assert pois2 is poisoned_cal


_Q = 0.95


def _build_tail_contaminated_cal(
    clean: np.ndarray, *, fraction: float, value: float, rng: np.random.Generator
) -> np.ndarray:
    """Helper to poison a target calibration array with outlier values."""
    poisoned = clean.copy()
    m = max(1, round(fraction * clean.shape[0]))
    positions = rng.choice(clean.shape[0], size=m, replace=False)
    poisoned[positions] = value
    return poisoned


def _abs_delta_tau_for_poisoned(
    col: object, victim: str, poisoned_victim_cal: np.ndarray, *, defended: bool
) -> float:
    """Helper to compute the absolute threshold delta between poisoned and clean victim."""
    poisoned_cal = {
        cid: (poisoned_victim_cal if cid == victim else col.clients[cid].cal.copy())
        for cid in col.eligible_ids
    }
    work_col, work_pois = col, poisoned_cal
    if defended:
        work_col, work_pois = apply_defense(
            col,
            poisoned_cal,
            defense=PoisoningDefense.TRIMMED_CALIBRATION,
            trim_fraction=0.15,
        )
    pair = recompute_pair(
        work_col,
        PoisonedCalibrationSet.from_mapping(work_pois),
        ThresholdPolicy.LOCAL_THRESHOLD,
    )
    return abs(pair.thresholds_pois[victim] - pair.thresholds_clean[victim])


def test_trimming_reduces_abs_delta_tau_high_contamination() -> None:
    """Verify that trimming defense reduces threshold delta under poisoning."""
    col = _make_collection()
    victim = col.eligible_ids[0]
    rng = np.random.default_rng(0)
    poisoned = _build_tail_contaminated_cal(
        col.clients[victim].cal, fraction=0.10, value=0.5, rng=rng
    )
    undefended = _abs_delta_tau_for_poisoned(col, victim, poisoned, defended=False)
    defended = _abs_delta_tau_for_poisoned(col, victim, poisoned, defended=True)
    assert undefended > 0.0
    assert defended < undefended


def test_trimming_neutralizes_injected_low_tail() -> None:
    """Verify that trimming neutralizes low-tail injection values."""
    base = np.full(100, 0.5)
    poisoned = base.copy()
    poisoned[:10] = 0.0
    assert int((poisoned < 0.4).sum()) == 10
    trimmed = trimmed_calibration(poisoned, 0.15)
    assert int((trimmed < 0.4).sum()) == 0


def test_defense_runs_end_to_end_through_recompute_pipeline() -> None:
    """Verify end-to-end execution of trimmed calibration defense in the recompute pipeline."""
    col = _make_collection()
    victim = col.eligible_ids[0]
    outcome = inject_single_victim(
        col,
        victim_id=victim,
        spec=InjectionSpec(
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            fraction=0.20,
            seed_pair=SeedPair(training_seed=0, poisoning_seed=100),
            objective=None,
        ),
    )
    work_col, work_pois = apply_defense(
        col,
        {
            cid: outcome.poisoned_cal_set.for_client(cid).cal
            for cid in outcome.poisoned_cal_set.client_ids
        },
        defense=PoisoningDefense.TRIMMED_CALIBRATION,
        trim_fraction=0.05,
    )
    pair = recompute_pair(
        work_col,
        PoisonedCalibrationSet.from_mapping(work_pois),
        ThresholdPolicy.LOCAL_THRESHOLD,
    )
    assert math.isfinite(pair.thresholds_clean[victim])
    assert math.isfinite(pair.thresholds_pois[victim])


def test_defended_victim_still_eligible_after_trim() -> None:
    """Verify that victims are still eligible and coverage ratio remains close after trimming."""
    col = _make_collection()
    defended = build_defended_collection(col, 0.15)

    assert col.eligible_ids[0] in defended.eligible_ids
    assert math.isclose(defended.coverage_ratio, col.coverage_ratio)
