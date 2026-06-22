"""Enforcement tests: scientific policy constants live only in datp.core.

These tests fail immediately if policy constants leak into other modules,
preventing drift back to the pre-canonicalization state.
"""

from __future__ import annotations
from datp.core.enums import ThresholdPolicy

import datp.checkpointing.enums as checkpointing_enums
import datp.core.enums as core_enums
import datp.reporting.enums as reporting_enums
from datp.checkpointing.enums import EvidenceRole
from datp.core.enums import (
    CONTROLLED_POLICIES,
    SeedScope,
)
from datp.reporting.enums import FigureName


class TestControlledPoliciesOwnership:
    def test_controlled_policies_defined_in_core(self) -> None:
        assert hasattr(core_enums, "CONTROLLED_POLICIES")

    def test_controlled_policies_global_local_cluster(self) -> None:
        assert set(CONTROLLED_POLICIES) == {
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
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
        assert SeedScope.ALL_SEEDS == "all_seeds"

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
