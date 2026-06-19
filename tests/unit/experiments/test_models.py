from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from datp.core.enums import (
    Baseline,
    Regime,
)
from datp.core.identity import TrainingCellId
from datp.experiments.enums import ContingencyDecision
from datp.experiments.models import (
    ContingencyRecord,
    PipelineRequest,
    SharedPipelineContext,
)


class TestPipelineRequest:
    def _make_cfg(self) -> MagicMock:
        cfg = MagicMock()
        cfg.threshold.n_min = 100
        cfg.threshold.q = 0.95
        return cfg

    def test_fields_accessible(self, tmp_path: Path) -> None:
        key = TrainingCellId(regime=Regime.A, seed=3, alpha=None)
        cfg = self._make_cfg()
        req = PipelineRequest(
            key=key,
            baseline=Baseline.B1,
            cfg=cfg,
            base_dir=tmp_path,
            prepared_dir=tmp_path / "prepared",
            checkpoint_round=None,
        )
        assert req.key is key
        assert req.baseline == Baseline.B1
        assert req.cfg is cfg
        assert req.base_dir == tmp_path
        assert req.prepared_dir == tmp_path / "prepared"

    def test_key_carried_through(self, tmp_path: Path) -> None:
        key = TrainingCellId(regime=Regime.C, seed=9, alpha=0.1)
        cfg = self._make_cfg()
        req = PipelineRequest(
            key=key,
            baseline=Baseline.B2,
            cfg=cfg,
            base_dir=tmp_path,
            prepared_dir=tmp_path,
            checkpoint_round=50,
        )
        assert req.key.regime == Regime.C
        assert req.key.seed == 9
        assert req.key.alpha == pytest.approx(0.1)

    def test_immutable(self, tmp_path: Path) -> None:
        key = TrainingCellId(regime=Regime.A, seed=1, alpha=None)
        req = PipelineRequest(
            key=key,
            baseline=Baseline.B1,
            cfg=self._make_cfg(),
            base_dir=tmp_path,
            prepared_dir=tmp_path,
            checkpoint_round=None,
        )
        with pytest.raises((AttributeError, TypeError)):
            req.baseline = Baseline.B2  # type: ignore[misc]


class TestSharedPipelineContext:
    def _make_key(self) -> TrainingCellId:
        return TrainingCellId(regime=Regime.A, seed=1, alpha=None)

    def test_fields_accessible(self, tmp_path: Path) -> None:
        from datp.scoring.loading import ScoreProvider

        key = self._make_key()
        errors = {"c0": np.array([0.1, 0.2]), "c1": np.array([0.3])}
        taus = {"c0": 0.15, "c1": 0.28}
        provider = ScoreProvider(tmp_path)

        ctx = SharedPipelineContext(
            key=key,
            client_errors=errors,
            eligible=["c0", "c1"],
            pending=[],
            client_taus=taus,
            tau_global=0.20,
            score_provider=provider,
            checkpoint_round=25,
        )

        assert ctx.key is key
        assert ctx.eligible == ["c0", "c1"]
        assert ctx.pending == []
        assert ctx.tau_global == pytest.approx(0.20)
        assert set(ctx.client_taus) == {"c0", "c1"}
        assert ctx.score_provider is provider

    def test_pending_clients_tracked(self, tmp_path: Path) -> None:
        from datp.scoring.loading import ScoreProvider

        key = self._make_key()
        ctx = SharedPipelineContext(
            key=key,
            client_errors={"c0": np.array([0.1])},
            eligible=[],
            pending=["c0"],
            client_taus={},
            tau_global=0.0,
            score_provider=ScoreProvider(tmp_path),
            checkpoint_round=None,
        )
        assert "c0" in ctx.pending
        assert ctx.eligible == []

    def test_mutable(self, tmp_path: Path) -> None:
        from datp.scoring.loading import ScoreProvider

        key = self._make_key()
        ctx = SharedPipelineContext(
            key=key,
            client_errors={},
            eligible=[],
            pending=[],
            client_taus={},
            tau_global=0.0,
            score_provider=ScoreProvider(tmp_path),
            checkpoint_round=None,
        )
        ctx.tau_global = 0.99
        assert ctx.tau_global == pytest.approx(0.99)

    def test_no_eager_score_arrays(self, tmp_path: Path) -> None:
        from datp.scoring.loading import ScoreProvider

        ctx = SharedPipelineContext(
            key=self._make_key(),
            client_errors={},
            eligible=[],
            pending=[],
            client_taus={},
            tau_global=0.0,
            score_provider=ScoreProvider(tmp_path),
            checkpoint_round=None,
        )
        assert not hasattr(ctx, "test_scores"), "test_scores must be removed"


class TestContingencyRecord:
    def test_valid_go_decision(self) -> None:
        record = ContingencyRecord(
            decision=ContingencyDecision.GO,
            cv_fpr_b1=0.45,
            cv_fpr_b2=0.32,
            delta_cv_fpr=0.13,
            dispersion_threshold=0.10,
            rationale="B1 CV(FPR) exceeds dispersion threshold",
        )
        assert record.decision == ContingencyDecision.GO
        assert record.cv_fpr_b1 == pytest.approx(0.45)
        assert record.cv_fpr_b2 == pytest.approx(0.32)
        assert record.delta_cv_fpr == pytest.approx(0.13)
        assert record.is_preliminary_diagnostic is True

    def test_valid_contingency_decision(self) -> None:
        record = ContingencyRecord(
            decision=ContingencyDecision.CONTINGENCY,
            cv_fpr_b1=0.05,
            cv_fpr_b2=0.04,
            delta_cv_fpr=0.01,
            dispersion_threshold=0.10,
            rationale="B1 CV(FPR) below dispersion threshold — abort",
        )
        assert record.decision == ContingencyDecision.CONTINGENCY

    def test_immutable(self) -> None:
        record = ContingencyRecord(
            decision=ContingencyDecision.GO,
            cv_fpr_b1=0.45,
            cv_fpr_b2=0.32,
            delta_cv_fpr=0.13,
            dispersion_threshold=0.10,
            rationale="test",
        )
        with pytest.raises((AttributeError, TypeError, ValueError)):
            record.decision = ContingencyDecision.CONTINGENCY  # type: ignore[misc]

    def test_is_preliminary_diagnostic_default(self) -> None:
        """is_preliminary_diagnostic defaults to True and is always True for this record type."""
        record = ContingencyRecord(
            decision=ContingencyDecision.GO,
            cv_fpr_b1=0.45,
            cv_fpr_b2=0.32,
            delta_cv_fpr=0.13,
            dispersion_threshold=0.10,
            rationale="preliminary check only",
        )
        assert record.is_preliminary_diagnostic is True

    def test_explicit_preliminary_false_still_allowed(self) -> None:
        """The field can be set explicitly even though the default is True."""
        record = ContingencyRecord(
            decision=ContingencyDecision.GO,
            cv_fpr_b1=0.45,
            cv_fpr_b2=0.32,
            delta_cv_fpr=0.13,
            dispersion_threshold=0.10,
            rationale="test",
            is_preliminary_diagnostic=False,
        )
        assert record.is_preliminary_diagnostic is False

    def test_model_dump_json(self) -> None:
        record = ContingencyRecord(
            decision=ContingencyDecision.GO,
            cv_fpr_b1=0.45,
            cv_fpr_b2=0.32,
            delta_cv_fpr=0.13,
            dispersion_threshold=0.10,
            rationale="B1 CV(FPR) exceeds dispersion threshold",
        )
        data = record.model_dump(mode="json")
        assert data["decision"] == "go"
        assert data["cv_fpr_b1"] == pytest.approx(0.45)
        assert data["is_preliminary_diagnostic"] is True

    def test_equality_same_values(self) -> None:
        r1 = ContingencyRecord(
            decision=ContingencyDecision.GO,
            cv_fpr_b1=0.45,
            cv_fpr_b2=0.32,
            delta_cv_fpr=0.13,
            dispersion_threshold=0.10,
            rationale="test",
        )
        r2 = ContingencyRecord(
            decision=ContingencyDecision.GO,
            cv_fpr_b1=0.45,
            cv_fpr_b2=0.32,
            delta_cv_fpr=0.13,
            dispersion_threshold=0.10,
            rationale="test",
        )
        assert r1 == r2

    def test_inequality_different_decision(self) -> None:
        r1 = ContingencyRecord(
            decision=ContingencyDecision.GO,
            cv_fpr_b1=0.45,
            cv_fpr_b2=0.32,
            delta_cv_fpr=0.13,
            dispersion_threshold=0.10,
            rationale="test",
        )
        r2 = ContingencyRecord(
            decision=ContingencyDecision.CONTINGENCY,
            cv_fpr_b1=0.45,
            cv_fpr_b2=0.32,
            delta_cv_fpr=0.13,
            dispersion_threshold=0.10,
            rationale="test",
        )
        assert r1 != r2
