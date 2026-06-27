"""Tests verifying calibration poisoning layout directories, nested fraction formats, and config constants."""

from __future__ import annotations

from pathlib import Path

import pytest

from datp.artifacts.poison_layout import CellId, PoisonLayout
from datp.artifacts.poison_names import (
    CALIBRATION_POISONING_OUTPUT_ROOT,
    ManifestFile,
    RunFile,
)
from datp.attacks.constants import (
    CLUSTER_K_NBAIOT,
    CLUSTER_MAX_ITER,
    CLUSTER_N_INIT,
    CLUSTER_RANDOM_STATE,
    COMPROMISE_PATTERN_SEED,
    MATERIALITY_FACTOR,
    N_MIN,
    NBAIOT_MAIN_SWEEP_FRACTIONS,
    TAIL_MASS,
)
from datp.attacks.enums import (
    AttackerObjective,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
)
from datp.config.models import ExperimentStage
from datp.core.enums import ThresholdPolicy
from datp.core.seeds import SeedPair
from datp.data.catalog import DatasetID


def _cell(
    fraction: float = 0.10,
    training_seed: int = 0,
    poisoning_seed: int = 100,
) -> CellId:
    """Helper to build CellId instances for poisoning runs."""
    return CellId(
        stage=ExperimentStage.NBAIOT_MAIN,
        dataset=DatasetID.NBAIOT,
        policy=ThresholdPolicy.GLOBAL_THRESHOLD,
        objective=AttackerObjective.THRESHOLD_RAISE,
        source=PoisoningSourceStrategy.RANDOM_BENIGN,
        fraction=fraction,
        target_scope=PoisoningTargetScope.SINGLE_CLIENT,
        seed_pair=SeedPair(
            training_seed=training_seed,
            poisoning_seed=poisoning_seed,
        ),
    )


_BASE = Path("outputs")
_LAYOUT = PoisonLayout(base_dir=_BASE)


class TestLayout:
    """Tests verifying subdirectory strings and path depths of the nested poison run directories."""

    def test_root_under_base(self) -> None:
        """Verify that poison output root lies directly under the base output folder."""
        assert _LAYOUT.poison_output_root == _BASE / CALIBRATION_POISONING_OUTPUT_ROOT

    def test_run_dir_contains_scale(self) -> None:
        """Verify run directory path contains the stage name segment."""
        d = _LAYOUT.run_dir(_cell())
        assert "nbaiot_main" in d.parts

    def test_run_dir_contains_dataset(self) -> None:
        """Verify run directory path contains the dataset segment."""
        d = _LAYOUT.run_dir(_cell())
        assert "nbaiot" in d.parts

    def test_run_dir_contains_policy(self) -> None:
        """Verify run directory path contains the threshold policy name."""
        d = _LAYOUT.run_dir(_cell())
        assert "global_threshold" in d.parts

    def test_run_dir_contains_objective(self) -> None:
        """Verify run directory path contains the attacker objective name."""
        d = _LAYOUT.run_dir(_cell())
        assert "threshold_raise" in d.parts

    def test_run_dir_contains_source(self) -> None:
        """Verify run directory path contains the poisoning source strategy segment."""
        d = _LAYOUT.run_dir(_cell())
        assert "random_benign" in d.parts

    def test_fraction_segment_two_decimals(self) -> None:
        """Verify that the fraction segment is formatted with exactly two decimal places."""
        d = _LAYOUT.run_dir(_cell(fraction=0.10))
        assert "f_0.10" in d.parts

    def test_fraction_zero_formatted(self) -> None:
        """Verify that zero fraction is formatted to two decimal places."""
        d = _LAYOUT.run_dir(_cell(fraction=0.0))
        assert "f_0.00" in d.parts

    def test_fraction_forty_percent(self) -> None:
        """Verify formatting of larger fractions (e.g. 0.40)."""
        d = _LAYOUT.run_dir(_cell(fraction=0.40))
        assert "f_0.40" in d.parts

    def test_scope_segment(self) -> None:
        """Verify run directory path contains the poisoning target scope."""
        d = _LAYOUT.run_dir(_cell())
        assert "scope_single_client" in d.parts

    def test_training_seed_segment(self) -> None:
        """Verify run directory path contains the training seed identifier."""
        d = _LAYOUT.run_dir(_cell(training_seed=2))
        assert "train_2" in d.parts

    def test_poisoning_seed_segment(self) -> None:
        """Verify run directory path contains the poisoning seed identifier."""
        d = _LAYOUT.run_dir(_cell(poisoning_seed=102))
        assert "poison_102" in d.parts

    def test_run_dir_depth(self) -> None:
        """Verify that the relative run directory from poison root has a depth of nine segments."""
        d = _LAYOUT.run_dir(_cell())
        relative = d.relative_to(_LAYOUT.poison_output_root)
        assert len(relative.parts) == 9

    def test_different_seeds_produce_different_paths(self) -> None:
        """Verify that different training or poisoning seeds result in unique directory paths."""
        d0 = _LAYOUT.run_dir(_cell(training_seed=0, poisoning_seed=100))
        d1 = _LAYOUT.run_dir(_cell(training_seed=1, poisoning_seed=101))
        assert d0 != d1

    def test_different_fractions_produce_different_paths(self) -> None:
        """Verify that different poisoning fractions map to distinct folder paths."""
        d10 = _LAYOUT.run_dir(_cell(fraction=0.10))
        d20 = _LAYOUT.run_dir(_cell(fraction=0.20))
        assert d10 != d20


class TestCellPaths:
    """Tests verifying output file path structures for individual cells."""

    def test_all_files_under_run_dir(self) -> None:
        """Verify that all cell output paths resolve to subfiles under the run directory."""
        paths = _LAYOUT.cell_paths(_cell())
        rd = paths.run_dir
        assert paths.poisoned_scores.parent == rd
        assert paths.threshold_deltas.parent == rd
        assert paths.cell_metrics.parent == rd
        assert paths.seed_record.parent == rd
        assert paths.provenance.parent == rd
        assert paths.run_done.parent == rd
        assert paths.run_in_progress.parent == rd

    def test_poisoned_scores_is_parquet(self) -> None:
        """Verify that poisoned scores use the Parquet file extension."""
        paths = _LAYOUT.cell_paths(_cell())
        assert paths.poisoned_scores.suffix == ".parquet"

    def test_metrics_is_json(self) -> None:
        """Verify that cell metrics files use the JSON extension."""
        paths = _LAYOUT.cell_paths(_cell())
        assert paths.cell_metrics.suffix == ".json"


class TestManifestPaths:
    """Tests verifying root level manifest file naming and directories."""

    def test_project_audit_report_under_root(self) -> None:
        """Verify that the project audit report path resolves under the poison root directory."""
        p = _LAYOUT.project_audit_report()
        assert p.parent == _LAYOUT.poison_output_root
        assert p.name == ManifestFile.PROJECT_AUDIT_REPORT

    def test_clean_score_artifacts_under_root(self) -> None:
        """Verify that the clean score artifacts manifest path resolves under the poison root directory."""
        p = _LAYOUT.clean_score_artifacts_manifest()
        assert p.parent == _LAYOUT.poison_output_root
        assert p.name == ManifestFile.CLEAN_SCORE_ARTIFACTS

    def test_nbaiot_main_manifest_under_root(self) -> None:
        """Verify that the NBAIoT main sweep manifest resolves under the poison root directory."""
        p = _LAYOUT.nbaiot_main_manifest()
        assert p.parent == _LAYOUT.poison_output_root

    def test_paper_figure_manifest_under_root(self) -> None:
        """Verify that the paper figures manifest resolves under the poison root directory."""
        p = _LAYOUT.paper_figure_manifest()
        assert p.parent == _LAYOUT.poison_output_root


class TestCellId:
    """Tests verifying validation constraints on CellId fields."""

    def test_fraction_outside_bounds_raises(self) -> None:
        """Verify that a poisoning fraction value greater than 1.0 raises a ValueError."""
        with pytest.raises(ValueError, match="outside"):
            CellId(
                stage=ExperimentStage.NBAIOT_MAIN,
                dataset=DatasetID.NBAIOT,
                policy=ThresholdPolicy.GLOBAL_THRESHOLD,
                objective=AttackerObjective.THRESHOLD_RAISE,
                source=PoisoningSourceStrategy.RANDOM_BENIGN,
                fraction=1.5,
                target_scope=PoisoningTargetScope.SINGLE_CLIENT,
                seed_pair=SeedPair(training_seed=0, poisoning_seed=100),
            )

    def test_invalid_dataset_string_rejected(self) -> None:
        """Verify that initialization raises a ValueError for unsupported dataset strings."""
        with pytest.raises(ValueError):
            DatasetID("not_a_dataset")


class TestConstants:
    """Tests verifying project configuration constants."""

    def test_n_min(self) -> None:
        """Verify minimum sample count constant default value."""
        assert N_MIN == 100

    def test_tail_mass(self) -> None:
        """Verify default tail mass calibration percentile value."""
        assert abs(TAIL_MASS - 0.10) < 1e-9

    def test_materiality_factor(self) -> None:
        """Verify threshold raising materiality factor constant."""
        assert abs(MATERIALITY_FACTOR - 0.1) < 1e-9

    def test_cluster_k(self) -> None:
        """Verify default K-Means cluster count for NBAIoT datasets."""
        assert CLUSTER_K_NBAIOT == 3

    def test_cluster_n_init(self) -> None:
        """Verify default K-Means initialization iterations."""
        assert CLUSTER_N_INIT == 10

    def test_cluster_max_iter(self) -> None:
        """Verify default K-Means max iteration parameter."""
        assert CLUSTER_MAX_ITER == 300

    def test_cluster_random_state(self) -> None:
        """Verify random seed constant for clustering stability."""
        assert CLUSTER_RANDOM_STATE == 42

    def test_compromise_pattern_seed(self) -> None:
        """Verify compromise client indexing seed constant."""
        assert COMPROMISE_PATTERN_SEED == 400

    def test_bounded_fraction_grid(self) -> None:
        """Verify default fraction grid points used in evaluations."""
        assert NBAIOT_MAIN_SWEEP_FRACTIONS == (0.0, 0.10, 0.20, 0.40)

    def test_output_root_name(self) -> None:
        """Verify the conference output folder root directory name."""
        assert CALIBRATION_POISONING_OUTPUT_ROOT == "conference_calibration_poisoning"

    def test_manifest_file_names(self) -> None:
        """Verify default string names for all output manifests."""
        assert ManifestFile.PROJECT_AUDIT_REPORT == "project_audit_report.json"
        assert ManifestFile.CLEAN_SCORE_ARTIFACTS == "clean_score_artifacts.json"
        assert ManifestFile.NBAIOT_MAIN_MANIFEST == "nbaiot_main_manifest.json"
        assert ManifestFile.PAPER_FIGURE_MANIFEST == "paper_figure_manifest.json"

    def test_run_file_names(self) -> None:
        """Verify expected file extension formats for run-level outputs."""
        assert RunFile.POISONED_SCORES.endswith(".parquet")
        assert RunFile.THRESHOLD_DELTAS.endswith(".json")
        assert RunFile.CELL_METRICS.endswith(".json")
