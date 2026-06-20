from __future__ import annotations

import json
from pathlib import Path

from datp.core.enums import Regime
from datp.evaluation.confusion import save_confusion_matrices
from tests.unit.evaluation._builders import (
    _EvalSpec,
    _make_client_record,
    _make_eval_result,
)


def test_confusion_matrix_saved_before_averaging(tmp_path: Path) -> None:
    c1 = _make_client_record("c1", fpr=0.1, tpr=0.9)
    c2 = _make_client_record("c2", fpr=0.2, tpr=0.8)
    ev = _make_eval_result([c1, c2], ["c1", "c2"], [])

    out = save_confusion_matrices(ev, tmp_path)
    assert out.exists()

    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["per_client"]) == 2
    for entry in data["per_client"]:
        assert "confusion_matrix" in entry
        cm = entry["confusion_matrix"]
        assert all(k in cm for k in ("tp", "fp", "tn", "fn"))


def test_confusion_matrix_write_is_atomic(tmp_path: Path) -> None:
    c1 = _make_client_record("c1", fpr=0.1, tpr=0.9)
    ev = _make_eval_result([c1], ["c1"], [])
    out = save_confusion_matrices(ev, tmp_path)
    assert len(list(out.parent.glob("*.tmp.json"))) == 0


def test_regime_c_confusion_includes_alpha(tmp_path: Path) -> None:
    c1 = _make_client_record("c1", fpr=0.1, tpr=0.9)
    ev_c = _make_eval_result(
        [c1], ["c1"], [], spec=_EvalSpec(regime=Regime.C, alpha=0.5)
    )
    out = save_confusion_matrices(ev_c, tmp_path)
    assert "alpha0.5" in out.name

    ev_a = _make_eval_result([c1], ["c1"], [], spec=_EvalSpec(regime=Regime.A))
    out_no_alpha = save_confusion_matrices(ev_a, tmp_path)
    assert "alpha" not in out_no_alpha.name
