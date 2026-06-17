from __future__ import annotations

import math

import pytest

from datp.artifacts.names import PathToken
from datp.core.enums import Baseline, Regime
from datp.core.identity import (
    AlphaLabel,
    BaselineRunId,
    TrainingCellId,
    TrainingKey,
    alpha_from_label,
    alpha_label,
    format_alpha_dir,
    make_run_id,
    parse_alpha_dir,
    seed_segment,
)


class TestTrainingCellId:
    def test_label_without_alpha(self) -> None:
        key = TrainingCellId(regime=Regime.A, seed=42, alpha=None)
        label = key.label()
        assert "regime=a" in label
        assert "seed=42" in label
        assert "alpha" not in label

    def test_label_with_alpha(self) -> None:
        key = TrainingCellId(regime=Regime.B, seed=7, alpha=0.5)
        label = key.label()
        assert "regime=b" in label
        assert "seed=7" in label
        assert "alpha=0.5" in label

    def test_label_with_alpha_zero(self) -> None:
        key = TrainingCellId(regime=Regime.C, seed=1, alpha=0.0)
        label = key.label()
        assert "alpha=0" in label

    def test_immutable(self) -> None:
        key = TrainingCellId(regime=Regime.A, seed=42, alpha=None)
        with pytest.raises((AttributeError, TypeError)):
            key.regime = Regime.B # type: ignore[misc]

    def test_equality(self) -> None:
        k1 = TrainingCellId(regime=Regime.A, seed=1, alpha=0.3)
        k2 = TrainingCellId(regime=Regime.A, seed=1, alpha=0.3)
        assert k1 == k2

    def test_inequality_different_seed(self) -> None:
        k1 = TrainingCellId(regime=Regime.A, seed=1, alpha=None)
        k2 = TrainingCellId(regime=Regime.A, seed=2, alpha=None)
        assert k1 != k2

    def test_alpha_default_is_none(self) -> None:
        key = TrainingCellId(regime=Regime.A, seed=0, alpha=None)
        assert key.alpha is None

    def test_hashable(self) -> None:
        k1 = TrainingCellId(regime=Regime.A, seed=1, alpha=0.5)
        k2 = TrainingCellId(regime=Regime.A, seed=2, alpha=None)
        s: set[TrainingCellId] = {k1, k2}
        assert len(s) == 2

    def test_regime_is_enum(self) -> None:
        key = TrainingCellId(regime=Regime.A, seed=1, alpha=None)
        assert key.regime == Regime.A

    def test_used_as_dict_key(self) -> None:
        """TrainingCellId must be usable as a dict key (hashable + eq)."""
        k1 = TrainingCellId(regime=Regime.A, seed=0, alpha=None)
        k2 = TrainingCellId(regime=Regime.A, seed=0, alpha=None)
        d: dict[TrainingCellId, str] = {k1: "shared"}
        assert d[k2] == "shared"


class TestBaselineRunId:
    def test_construction_and_properties(self) -> None:
        cell = TrainingCellId(regime=Regime.A, seed=42, alpha=None)
        run = BaselineRunId(cell=cell, baseline=Baseline.B1)
        assert run.regime == Regime.A
        assert run.seed == 42
        assert run.alpha is None
        assert run.baseline == Baseline.B1
        assert run.cell is cell

    def test_construction_with_alpha(self) -> None:
        cell = TrainingCellId(regime=Regime.C, seed=3, alpha=0.5)
        run = BaselineRunId(cell=cell, baseline=Baseline.B2)
        assert run.regime == Regime.C
        assert run.seed == 3
        assert run.alpha == 0.5

    def test_equality(self) -> None:
        cell = TrainingCellId(regime=Regime.A, seed=1, alpha=None)
        r1 = BaselineRunId(cell=cell, baseline=Baseline.B1)
        r2 = BaselineRunId(cell=cell, baseline=Baseline.B1)
        assert r1 == r2

    def test_inequality_different_baseline(self) -> None:
        cell = TrainingCellId(regime=Regime.A, seed=1, alpha=None)
        r1 = BaselineRunId(cell=cell, baseline=Baseline.B1)
        r2 = BaselineRunId(cell=cell, baseline=Baseline.B2)
        assert r1 != r2

    def test_inequality_different_cell(self) -> None:
        c1 = TrainingCellId(regime=Regime.A, seed=1, alpha=None)
        c2 = TrainingCellId(regime=Regime.A, seed=2, alpha=None)
        r1 = BaselineRunId(cell=c1, baseline=Baseline.B1)
        r2 = BaselineRunId(cell=c2, baseline=Baseline.B1)
        assert r1 != r2

    def test_immutable(self) -> None:
        cell = TrainingCellId(regime=Regime.A, seed=42, alpha=None)
        run = BaselineRunId(cell=cell, baseline=Baseline.B1)
        with pytest.raises((AttributeError, TypeError)):
            run.baseline = Baseline.B2 # type: ignore[misc]

    def test_hashable(self) -> None:
        cell = TrainingCellId(regime=Regime.A, seed=1, alpha=0.5)
        r1 = BaselineRunId(cell=cell, baseline=Baseline.B1)
        r2 = BaselineRunId(cell=cell, baseline=Baseline.B2)
        s: set[BaselineRunId] = {r1, r2}
        assert len(s) == 2

    def test_label(self) -> None:
        cell = TrainingCellId(regime=Regime.A, seed=42, alpha=None)
        run = BaselineRunId(cell=cell, baseline=Baseline.B1)
        label = run.label()
        assert "regime=a" in label
        assert "baseline=b1" in label
        assert "seed=42" in label

    def test_label_with_alpha(self) -> None:
        cell = TrainingCellId(regime=Regime.C, seed=3, alpha=0.5)
        run = BaselineRunId(cell=cell, baseline=Baseline.B2)
        label = run.label()
        assert "alpha=0.5" in label

    def test_audit_id_without_alpha(self) -> None:
        cell = TrainingCellId(regime=Regime.A, seed=42, alpha=None)
        run = BaselineRunId(cell=cell, baseline=Baseline.B1)
        assert run.audit_id() == "a_b1_seed42"

    def test_audit_id_with_alpha(self) -> None:
        cell = TrainingCellId(regime=Regime.C, seed=3, alpha=0.5)
        run = BaselineRunId(cell=cell, baseline=Baseline.B2)
        assert run.audit_id() == "c_b2_seed3_alpha0.5"

    def test_tracking_name_without_alpha(self) -> None:
        cell = TrainingCellId(regime=Regime.A, seed=42, alpha=None)
        run = BaselineRunId(cell=cell, baseline=Baseline.B1)
        assert run.tracking_name() == "a_b1_seed42"

    def test_tracking_name_with_alpha(self) -> None:
        cell = TrainingCellId(regime=Regime.C, seed=3, alpha=0.5)
        run = BaselineRunId(cell=cell, baseline=Baseline.B2)
        assert run.tracking_name() == "c_b2_seed3_alpha0.5"

    def test_shared_training_key_returns_cell(self) -> None:
        cell = TrainingCellId(regime=Regime.A, seed=1, alpha=None)
        run = BaselineRunId(cell=cell, baseline=Baseline.B1)
        assert run.shared_training_key() is cell


class TestAlphaLabel:
    def test_none_returns_none(self) -> None:
        assert alpha_label(None) is None

    def test_inf_returns_iid(self) -> None:
        assert alpha_label(math.inf) == "iid"

    def test_float_returns_formatted(self) -> None:
        assert alpha_label(0.5) == "0.5"

    def test_zero_returns_zero(self) -> None:
        assert alpha_label(0.0) == "0"


class TestAlphaFromLabel:
    def test_none_returns_none(self) -> None:
        assert alpha_from_label(None) is None

    def test_iid_returns_inf(self) -> None:
        assert math.isinf(alpha_from_label("iid")) # type: ignore[arg-type]

    def test_numeric_returns_float(self) -> None:
        assert alpha_from_label("0.5") == 0.5

    def test_zero_returns_zero(self) -> None:
        assert alpha_from_label("0") == 0.0


class TestFormatAlphaDir:
    def test_finite_alpha(self) -> None:
        assert format_alpha_dir(0.5) == "alpha_0.5"

    def test_inf_alpha(self) -> None:
        assert format_alpha_dir(math.inf) == PathToken.ALPHA_IID


class TestParseAlphaDir:
    def test_non_alpha_prefix_returns_none(self) -> None:
        assert parse_alpha_dir("seed_42") is None

    def test_iid_returns_inf(self) -> None:
        assert math.isinf(parse_alpha_dir(PathToken.ALPHA_IID)) # type: ignore[arg-type]

    def test_numeric_returns_float(self) -> None:
        assert parse_alpha_dir("alpha_0.5") == 0.5

    def test_empty_string_returns_none(self) -> None:
        assert parse_alpha_dir("") is None


class TestSeedSegment:
    def test_returns_seed_prefix(self) -> None:
        assert seed_segment(42) == "seed_42"

    def test_zero_seed(self) -> None:
        assert seed_segment(0) == "seed_0"


class TestMakeRunId:
    def test_includes_regime_and_seed(self) -> None:
        rid = make_run_id(Regime.A, seed=42)
        assert rid.startswith("a_seed42_")

    def test_includes_alpha_when_present(self) -> None:
        rid = make_run_id(Regime.C, seed=3, alpha=0.5)
        assert "alpha0.5" in rid

    def test_no_alpha_when_none(self) -> None:
        rid = make_run_id(Regime.A, seed=42, alpha=None)
        assert "alpha" not in rid

    def test_unique_timestamps(self) -> None:
        import time
        id1 = make_run_id(Regime.A, seed=0)
        time.sleep(0.002)
        id2 = make_run_id(Regime.A, seed=0)
        assert id1 != id2


class TestIIDAlphaLabel:
    def test_is_canonical_string(self) -> None:
        assert AlphaLabel.IID == "iid"

    def test_display_property(self) -> None:
        assert AlphaLabel.IID.display == "IID"

    def test_path_dir_property(self) -> None:
        assert AlphaLabel.IID.path_dir == "alpha_iid"

    def test_is_str_enum(self) -> None:
        assert isinstance(AlphaLabel.IID, str)


class TestTrainingKeyAlias:
    def test_training_key_is_training_cell_id(self) -> None:
        """TrainingKey must be the same type as TrainingCellId (not a raw tuple)."""
        key: TrainingKey = TrainingCellId(regime=Regime.A, seed=0, alpha=None)
        assert isinstance(key, TrainingCellId)
        assert key.regime == Regime.A
        assert key.seed == 0
        assert key.alpha is None
