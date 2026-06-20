from __future__ import annotations

import numpy as np
import pytest

from datp.evaluation.metrics import compute_per_attack_tpr


def _family(label: str) -> str | None:
    return {"DDoS_TCP": "DDoS", "Mirai_Bot": "Mirai"}.get(label)


class TestPerAttackTPR:
    def test_correct_tpr_per_label(self) -> None:
        scores = np.array([0.1, 0.2, 0.9, 0.8, 0.05, 0.7], dtype=float)
        labels = np.array(
            ["DDoS_TCP", "DDoS_TCP", "DDoS_TCP", "Mirai_Bot", "Mirai_Bot", "Mirai_Bot"]
        )
        results = compute_per_attack_tpr("c1", scores, labels, 0.5, _family)
        by_label = {r.attack_label: r for r in results}
        assert by_label["DDoS_TCP"].detected_count == 1
        assert by_label["DDoS_TCP"].denominator == 3
        assert by_label["DDoS_TCP"].tpr == pytest.approx(1 / 3)
        assert by_label["Mirai_Bot"].detected_count == 2
        assert by_label["Mirai_Bot"].denominator == 3
        assert by_label["Mirai_Bot"].tpr == pytest.approx(2 / 3)

    def test_family_set_correctly(self) -> None:
        scores = np.array([0.9], dtype=float)
        labels = np.array(["DDoS_TCP"])
        results = compute_per_attack_tpr("c1", scores, labels, 0.5, _family)
        assert results[0].family == "DDoS"

    def test_unknown_label_family_is_none(self) -> None:
        scores = np.array([0.9], dtype=float)
        labels = np.array(["UNKNOWN_XYZ"])
        results = compute_per_attack_tpr("c1", scores, labels, 0.5, _family)
        assert results[0].family is None

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="mismatch"):
            compute_per_attack_tpr(
                "c1", np.array([0.1, 0.2]), np.array(["DDoS_TCP"]), 0.5, _family
            )

    def test_empty_inputs_return_empty_list(self) -> None:
        results = compute_per_attack_tpr("c1", np.array([]), np.array([]), 0.5, _family)
        assert results == []

    def test_client_id_propagated(self) -> None:
        scores = np.array([0.9], dtype=float)
        labels = np.array(["DDoS_TCP"])
        results = compute_per_attack_tpr("my_client", scores, labels, 0.5, _family)
        assert results[0].client_id == "my_client"
