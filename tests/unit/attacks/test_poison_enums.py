"""Tests verifying vocabularies and values of calibration poisoning enums and grid constants."""

from __future__ import annotations

from datp.attacks.constants import (
    DEFAULT_POLICIES,
    NBAIOT_FULL_OPTIONAL_SWEEP_FRACTIONS,
    NBAIOT_MAIN_SWEEP_FRACTIONS,
    NBAIOT_MAIN_SWEEP_OBJECTIVES,
    NBAIOT_MAIN_SWEEP_SOURCES,
)
from datp.attacks.enums import (
    AttackerObjective,
    CalibrationInjectionRule,
    PoisoningDefense,
    PoisoningKnowledge,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
)
from datp.config.models import ExperimentStage
from datp.core.enums import ThresholdPolicy


class TestCanonicalEnumVocabulary:
    """Tests verifying spelling and keys of all core poisoning policy enums."""

    def test_threshold_policy(self) -> None:
        """Verify that ThresholdPolicy values map exactly to their expected lower-case strings."""
        assert {p.name: p.value for p in ThresholdPolicy} == {
            "GLOBAL_THRESHOLD": "global_threshold",
            "LOCAL_THRESHOLD": "local_threshold",
            "CLUSTER_THRESHOLD": "cluster_threshold",
        }

    def test_attacker_objective(self) -> None:
        """Verify that AttackerObjective values match design definitions."""
        assert {o.name: o.value for o in AttackerObjective} == {
            "THRESHOLD_RAISE": "threshold_raise",
            "THRESHOLD_LOWER": "threshold_lower",
        }

    def test_poisoning_source_strategy(self) -> None:
        """Verify that PoisoningSourceStrategy options match core strategies."""
        assert {s.name: s.value for s in PoisoningSourceStrategy} == {
            "RANDOM_BENIGN": "random_benign",
            "HIGH_SCORE_BENIGN": "high_score_benign",
            "LOW_SCORE_BENIGN": "low_score_benign",
            "LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY": (
                "low_score_targeted_removal_diagnostic_only"
            ),
        }

    def test_calibration_injection_rule(self) -> None:
        """Verify that CalibrationInjectionRule values conform to design vocabs."""
        assert {r.name: r.value for r in CalibrationInjectionRule} == {
            "REPLACE_FIXED_BUDGET": "replace_fixed_budget",
        }

    def test_poisoning_knowledge(self) -> None:
        """Verify that PoisoningKnowledge keys map to their proper values."""
        assert {k.name: k.value for k in PoisoningKnowledge} == {
            "GRAY_BOX_SCORE_ACCESS": "gray_box_score_access",
            "WHITE_BOX_DIAGNOSTIC_ONLY": "white_box_diagnostic_only",
        }

    def test_poisoning_target_scope(self) -> None:
        """Verify that PoisoningTargetScope settings match target definitions."""
        assert {t.name: t.value for t in PoisoningTargetScope} == {
            "SINGLE_CLIENT": "single_client",
            "MULTI_CLIENT": "multi_client",
            "ALL_CLIENTS_DIAGNOSTIC_ONLY": "all_clients_diagnostic_only",
        }

    def test_poisoning_defense(self) -> None:
        """Verify that PoisoningDefense names and string values are correct."""
        assert {d.name: d.value for d in PoisoningDefense} == {
            "NONE": "none",
            "TRIMMED_CALIBRATION": "trimmed_calibration",
        }

    def test_experiment_stage(self) -> None:
        """Verify that ExperimentStage contains all valid audit/sweep stage identifiers."""
        assert {s.name: s.value for s in ExperimentStage} == {
            "FINAL_AUDIT": "final_audit",
            "SYNTHETIC_SMOKE": "synthetic_smoke",
            "NBAIOT_MAIN": "nbaiot_main",
            "NBAIOT_FULL_OPTIONAL": "nbaiot_full_optional",
            "STRETCH_DIAGNOSTIC_ONLY": "stretch_diagnostic_only",
        }


class TestMainSweepConstants:
    """Tests verifying evaluation sweep ranges and bounds configuration constants."""

    def test_default_policies_are_all_three(self) -> None:
        """Verify that DEFAULT_POLICIES includes all three core threshold policies."""
        assert set(DEFAULT_POLICIES) == set(ThresholdPolicy)

    def test_main_objectives_cover_both(self) -> None:
        """Verify that main sweep objectives cover raise and lower."""
        assert set(NBAIOT_MAIN_SWEEP_OBJECTIVES) == set(AttackerObjective)

    def test_main_sources_exclude_diagnostic(self) -> None:
        """Verify that main sweep sources exclude diagnostic-only strategies."""
        assert len(NBAIOT_MAIN_SWEEP_SOURCES) == 3
        assert all("diagnostic" not in s.value for s in NBAIOT_MAIN_SWEEP_SOURCES)

    def test_main_fraction_grid(self) -> None:
        """Verify that main sweep fractions are set to default grid list."""
        assert NBAIOT_MAIN_SWEEP_FRACTIONS == (0.0, 0.10, 0.20, 0.40)

    def test_full_optional_fraction_grid_adds_005(self) -> None:
        """Verify that full/optional grid contains main fractions plus the 0.05 step."""
        assert NBAIOT_FULL_OPTIONAL_SWEEP_FRACTIONS == (0.0, 0.05, 0.10, 0.20, 0.40)
        assert set(NBAIOT_MAIN_SWEEP_FRACTIONS) | {0.05} == set(
            NBAIOT_FULL_OPTIONAL_SWEEP_FRACTIONS
        )
