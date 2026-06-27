"""Tests verifying canonical definition ownership of enums and directory constants."""

from __future__ import annotations
from datp.core.enums import ThresholdPolicy

import datp.checkpointing.enums as checkpointing_enums
import datp.core.enums as core_enums
import datp.reporting.enums as reporting_enums
from datp.core.enums import CONTROLLED_POLICIES


class TestControlledPoliciesOwnership:
    """Tests verifying the ownership and composition of controlled threshold policy enums."""

    def test_controlled_policies_defined_in_core(self) -> None:
        """Confirm CONTROLLED_POLICIES is defined under core enums module."""
        assert hasattr(core_enums, "CONTROLLED_POLICIES")

    def test_controlled_policies_global_local_cluster(self) -> None:
        """Ensure controlled policies consist exactly of global, local, and cluster thresholds."""
        assert set(CONTROLLED_POLICIES) == {
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        }


class TestEnumOwnership:
    """Tests verifying the module ownership boundaries of various system enums."""

    def test_evidence_role_defined_in_checkpointing(self) -> None:
        """Confirm EvidenceRole is defined in checkpointing and not core."""
        assert hasattr(checkpointing_enums, "EvidenceRole")
        assert not hasattr(core_enums, "EvidenceRole")

    def test_seed_scope_defined_in_core(self) -> None:
        """Confirm SeedScope is owned by the core enums module."""
        assert hasattr(core_enums, "SeedScope")

    def test_figure_name_defined_in_reporting(self) -> None:
        """Confirm FigureName is owned by reporting and not core."""
        assert hasattr(reporting_enums, "FigureName")
        assert not hasattr(core_enums, "FigureName")


class TestDirectoryConstantOwnership:
    """Tests verifying the canonical names of directory constants in artifacts."""

    def test_figures_dir_in_artifacts(self) -> None:
        """Verify that FIGURES directory constant maps to the 'figures' string."""
        from datp.artifacts.names import ArtifactDir

        assert ArtifactDir.FIGURES == "figures"

    def test_tables_dir_in_artifacts(self) -> None:
        """Verify that TABLES directory constant maps to the 'tables' string."""
        from datp.artifacts.names import ArtifactDir

        assert ArtifactDir.TABLES == "tables"

    def test_analysis_dir_in_artifacts(self) -> None:
        """Verify that ANALYSIS directory constant maps to the 'analysis' string."""
        from datp.artifacts.names import ArtifactDir

        assert ArtifactDir.ANALYSIS == "analysis"
