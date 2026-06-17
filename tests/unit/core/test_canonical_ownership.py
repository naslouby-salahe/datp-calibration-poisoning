"""Enforcement tests: scientific policy constants live only in datp.core.

These tests fail immediately if policy constants leak into other modules,
preventing drift back to the pre-canonicalization state.
"""

from __future__ import annotations

import datp.checkpointing.enums as checkpointing_enums
import datp.core.enums as core_enums
import datp.reporting.enums as reporting_enums
from datp.checkpointing.enums import EvidenceRole
from datp.core.enums import (
    CONTROLLED_BASELINES,
    ISOLATED_BASELINES,
    REGIME_BASELINES,
    STATS_REPORTING_BASELINES,
    Baseline,
    Regime,
    SeedScope,
)
from datp.reporting.enums import FigureName


class TestRegimeBaselinesOwnership:
    def test_regime_baselines_defined_in_core(self) -> None:
        assert hasattr(core_enums, "REGIME_BASELINES")

    def test_controlled_baselines_defined_in_core(self) -> None:
        assert hasattr(core_enums, "CONTROLLED_BASELINES")

    def test_stats_reporting_baselines_defined_in_core(self) -> None:
        assert hasattr(core_enums, "STATS_REPORTING_BASELINES")

    def test_isolated_baselines_defined_in_core(self) -> None:
        assert hasattr(core_enums, "ISOLATED_BASELINES")

    def test_stats_baselines_a_excludes_b0_and_b3(self) -> None:
        stats_a = STATS_REPORTING_BASELINES[Regime.A]
        assert Baseline.B0 not in stats_a
        assert Baseline.B3 not in stats_a
        assert Baseline.B1 in stats_a
        assert Baseline.B2 in stats_a
        assert Baseline.B4 in stats_a

    def test_stats_baselines_b_excludes_b0(self) -> None:
        stats_b = STATS_REPORTING_BASELINES[Regime.B]
        assert Baseline.B0 not in stats_b
        assert Baseline.B1 in stats_b
        assert Baseline.B2 in stats_b
        assert Baseline.B4 in stats_b

    def test_stats_baselines_c_excludes_b0(self) -> None:
        stats_c = STATS_REPORTING_BASELINES[Regime.C]
        assert Baseline.B0 not in stats_c

    def test_stats_baselines_all_regimes_present(self) -> None:
        for regime in (Regime.A, Regime.B, Regime.C):
            assert regime in STATS_REPORTING_BASELINES

    def test_stats_baselines_subset_of_regime_baselines(self) -> None:
        for regime in STATS_REPORTING_BASELINES:
            assert STATS_REPORTING_BASELINES[regime].issubset(REGIME_BASELINES[regime])

    def test_isolated_baselines_excluded_from_stats(self) -> None:
        for regime in STATS_REPORTING_BASELINES:
            assert not (STATS_REPORTING_BASELINES[regime] & ISOLATED_BASELINES)

    def test_controlled_baselines_b1_b2_b3_b4(self) -> None:
        assert set(CONTROLLED_BASELINES) == {
            Baseline.B1,
            Baseline.B2,
            Baseline.B3,
            Baseline.B4,
        }


class TestEnumOwnership:
    def test_evidence_role_defined_in_checkpointing(self) -> None:
        assert hasattr(checkpointing_enums, "EvidenceRole")
        assert not hasattr(core_enums, "EvidenceRole")

    def test_seed_scope_defined_in_core(self) -> None:
        assert hasattr(core_enums, "SeedScope")

    def test_figure_name_defined_in_reporting(self) -> None:
        assert hasattr(reporting_enums, "FigureName")
        assert not hasattr(core_enums, "FigureName")

    def test_evidence_role_values(self) -> None:
        assert EvidenceRole.DESCRIPTIVE == "descriptive"
        assert EvidenceRole.SECONDARY == "secondary"
        assert (
            EvidenceRole.DESCRIPTIVE_WITH_CONFIRMATORY_SIDECAR_DELTA
            == "descriptive_with_confirmatory_sidecar_delta"
        )

    def test_seed_scope_values(self) -> None:
        assert SeedScope.REPRESENTATIVE_SEED == "representative_seed"
        assert SeedScope.ALL_SEED == "all_seed"

    def test_figure_name_values(self) -> None:
        assert FigureName.FIGURE_1 == "figure_1"
        assert FigureName.FIGURE_2 == "figure_2"
        assert FigureName.FIGURE_3 == "figure_3"
        assert FigureName.FIGURE_4 == "figure_4"


class TestDirectoryConstantOwnership:
    def test_figures_dir_in_artifacts(self) -> None:
        from datp.artifacts.names import ArtifactDir

        assert ArtifactDir.FIGURES == "figures"

    def test_tables_dir_in_artifacts(self) -> None:
        from datp.artifacts.names import ArtifactDir

        assert ArtifactDir.TABLES == "tables"

    def test_analysis_dir_in_artifacts(self) -> None:
        from datp.artifacts.names import ArtifactDir

        assert ArtifactDir.ANALYSIS == "analysis"
