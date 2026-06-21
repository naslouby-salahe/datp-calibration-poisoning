from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from datp.attacks.enums import ThresholdPolicy
from datp.config.stages import ExperimentStage
from datp.core.identity import TrainingCellId
from datp.experiments.enums import ContingencyDecision
from datp.experiments.models import (
    ContingencyRecord,
    PipelineRequest,
    SharedPipelineContext,
)

_STAGE = ExperimentStage.NBAIOT_MAIN


class TestPipelineRequest:
    def _make_cfg(self) -> MagicMock:
        cfg = MagicMock()
        cfg.threshold.n_min = 100
        cfg.threshold.q = 0.95
        return cfg

    def test_fields_accessible(self, tmp_path: Path) -> None:
        key = TrainingCellId(stage=_STAGE, seed=3)
        cfg = self._make_cfg()
        req = PipelineRequest(
            key=key,
            policy=ThresholdPolicy.GLOBAL_THRESHOLD,
            cfg=cfg,
            base_dir=tmp_path,
            prepared_dir=tmp_path / "prepared",
            checkpoint_round=None,
        )
        assert req.key is key
        assert req.policy == ThresholdPolicy.GLOBAL_THRESHOLD
        assert req.cfg is cfg
        assert req.base_dir == tmp_path
        assert req.prepared_dir == tmp_path / "prepared"

    def test_key_carried_through(self, tmp_path: Path) -> None:
        key = TrainingCellId(stage=_STAGE, seed=9)
        cfg = self._make_cfg()
        req = PipelineRequest(
            key=key,
            policy=ThresholdPolicy.LOCAL_THRESHOLD,
            cfg=cfg,
            base_dir=tmp_path,
            prepared_dir=tmp_path,
            checkpoint_round=50,
        )
        assert req.key.stage == _STAGE
        assert req.key.seed == 9

    def test_immutable(self, tmp_path: Path) -> None:
        key = TrainingCellId(stage=_STAGE, seed=1)
        req = PipelineRequest(
            key=key,
            policy=ThresholdPolicy.GLOBAL_THRESHOLD,
            cfg=self._make_cfg(),
            base_dir=tmp_path,
            prepared_dir=tmp_path,
            checkpoint_round=None,
        )
        with pytest.raises((AttributeError, TypeError)):
            req.policy = ThresholdPolicy.LOCAL_THRESHOLD  # type: ignore[misc]


class TestSharedPipelineContext:
    def _make_key(self) -> TrainingCellId:
        return TrainingCellId(stage=_STAGE, seed=1)

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
            cv_fpr_global=0.45,
            cv_fpr_local=0.32,
            delta_cv_fpr=0.13,
            dispersion_threshold=0.10,
            rationale="GLOBAL_THRESHOLD CV(FPR) exceeds dispersion threshold",
        )
        assert record.decision == ContingencyDecision.GO
        assert record.cv_fpr_global == pytest.approx(0.45)
        assert record.cv_fpr_local == pytest.approx(0.32)
        assert record.delta_cv_fpr == pytest.approx(0.13)
        assert record.is_preliminary_diagnostic is True

    def test_valid_contingency_decision(self) -> None:
        record = ContingencyRecord(
            decision=ContingencyDecision.CONTINGENCY,
            cv_fpr_global=0.05,
            cv_fpr_local=0.04,
            delta_cv_fpr=0.01,
            dispersion_threshold=0.10,
            rationale="GLOBAL_THRESHOLD CV(FPR) below dispersion threshold — abort",
        )
        assert record.decision == ContingencyDecision.CONTINGENCY

    def test_immutable(self) -> None:
        record = ContingencyRecord(
            decision=ContingencyDecision.GO,
            cv_fpr_global=0.45,
            cv_fpr_local=0.32,
            delta_cv_fpr=0.13,
            dispersion_threshold=0.10,
            rationale="test",
        )
        with pytest.raises((AttributeError, TypeError, ValueError)):
            record.decision = ContingencyDecision.CONTINGENCY  # type: ignore[misc]

    def test_is_preliminary_diagnostic_default(self) -> None:
        record = ContingencyRecord(
            decision=ContingencyDecision.GO,
            cv_fpr_global=0.1,
            cv_fpr_local=0.1,
            delta_cv_fpr=0.0,
            dispersion_threshold=0.10,
            rationale="test",
        )
        assert record.is_preliminary_diagnostic is True
