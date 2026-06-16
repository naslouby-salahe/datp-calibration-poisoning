"""Tests for canonical run-path builder."""

from __future__ import annotations

from pathlib import Path

import pytest

from datp.artifacts.poison_layout import CellId, PoisonLayout
from datp.artifacts.poison_names import (
    B4_K,
    B4_MAX_ITER,
    B4_N_INIT,
    B4_RANDOM_STATE,
    COMPROMISE_PATTERN_SEED,
    MATERIALITY_FACTOR,
    N_MIN,
    CALIBRATION_POISONING_OUTPUT_ROOT,
    TAIL_MASS,
    ManifestFile,
    RunFile,
)
from datp.attacks.poison_enums import (
    BOUNDED_SWEEP_FRACTIONS,
    AttackerObjective,
    ExperimentScale,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ThresholdPolicy,
)


def _cell(
    fraction: float = 0.10,
    training_seed: int = 0,
    poisoning_seed: int = 100,
) -> CellId:
    return CellId(
        scale=ExperimentScale.BOUNDED,
        dataset="nbaiot",
        policy=ThresholdPolicy.B1_GLOBAL,
        objective=AttackerObjective.THRESHOLD_RAISE,
        source=PoisoningSourceStrategy.RANDOM_BENIGN,
        fraction=fraction,
        target_scope=PoisoningTargetScope.SINGLE_CLIENT,
        training_seed=training_seed,
        poisoning_seed=poisoning_seed,
    )


_BASE = Path("/tmp/outputs")
_LAYOUT = PoisonLayout(base_dir=_BASE)


class TestLayout:
    def test_root_under_base(self) -> None:
        assert _LAYOUT.poison_output_root == _BASE / CALIBRATION_POISONING_OUTPUT_ROOT

    def test_run_dir_contains_scale(self) -> None:
        d = _LAYOUT.run_dir(_cell())
        assert "bounded" in d.parts

    def test_run_dir_contains_dataset(self) -> None:
        d = _LAYOUT.run_dir(_cell())
        assert "nbaiot" in d.parts

    def test_run_dir_contains_policy(self) -> None:
        d = _LAYOUT.run_dir(_cell())
        assert "b1_global" in d.parts

    def test_run_dir_contains_objective(self) -> None:
        d = _LAYOUT.run_dir(_cell())
        assert "threshold_raise" in d.parts

    def test_run_dir_contains_source(self) -> None:
        d = _LAYOUT.run_dir(_cell())
        assert "random_benign" in d.parts

    def test_fraction_segment_two_decimals(self) -> None:
        d = _LAYOUT.run_dir(_cell(fraction=0.10))
        assert "f_0.10" in d.parts

    def test_fraction_zero_formatted(self) -> None:
        d = _LAYOUT.run_dir(_cell(fraction=0.0))
        assert "f_0.00" in d.parts

    def test_fraction_forty_percent(self) -> None:
        d = _LAYOUT.run_dir(_cell(fraction=0.40))
        assert "f_0.40" in d.parts

    def test_scope_segment(self) -> None:
        d = _LAYOUT.run_dir(_cell())
        assert "scope_single_client" in d.parts

    def test_training_seed_segment(self) -> None:
        d = _LAYOUT.run_dir(_cell(training_seed=2))
        assert "train_2" in d.parts

    def test_poisoning_seed_segment(self) -> None:
        d = _LAYOUT.run_dir(_cell(poisoning_seed=102))
        assert "poison_102" in d.parts

    def test_run_dir_depth(self) -> None:
        d = _LAYOUT.run_dir(_cell())
        relative = d.relative_to(_LAYOUT.poison_output_root)
        assert len(relative.parts) == 9

    def test_different_seeds_produce_different_paths(self) -> None:
        d0 = _LAYOUT.run_dir(_cell(training_seed=0, poisoning_seed=100))
        d1 = _LAYOUT.run_dir(_cell(training_seed=1, poisoning_seed=101))
        assert d0 != d1

    def test_different_fractions_produce_different_paths(self) -> None:
        d10 = _LAYOUT.run_dir(_cell(fraction=0.10))
        d20 = _LAYOUT.run_dir(_cell(fraction=0.20))
        assert d10 != d20


class TestCellPaths:
    def test_all_files_under_run_dir(self) -> None:
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
        paths = _LAYOUT.cell_paths(_cell())
        assert paths.poisoned_scores.suffix == ".parquet"

    def test_metrics_is_json(self) -> None:
        paths = _LAYOUT.cell_paths(_cell())
        assert paths.cell_metrics.suffix == ".json"


class TestManifestPaths:
    def test_project_audit_report_under_root(self) -> None:
        p = _LAYOUT.project_audit_report()
        assert p.parent == _LAYOUT.poison_output_root
        assert p.name == ManifestFile.PROJECT_AUDIT_REPORT

    def test_clean_score_artifacts_under_root(self) -> None:
        p = _LAYOUT.clean_score_artifacts_manifest()
        assert p.parent == _LAYOUT.poison_output_root
        assert p.name == ManifestFile.CLEAN_SCORE_ARTIFACTS

    def test_nbaiot_bounded_sweep_manifest_under_root(self) -> None:
        p = _LAYOUT.nbaiot_bounded_sweep_manifest()
        assert p.parent == _LAYOUT.poison_output_root

    def test_paper_figure_manifest_under_root(self) -> None:
        p = _LAYOUT.paper_figure_manifest()
        assert p.parent == _LAYOUT.poison_output_root


class TestCellId:
    def test_fraction_outside_bounds_raises(self) -> None:
        with pytest.raises(ValueError, match="outside"):
            CellId(
                scale=ExperimentScale.BOUNDED,
                dataset="nbaiot",
                policy=ThresholdPolicy.B1_GLOBAL,
                objective=AttackerObjective.THRESHOLD_RAISE,
                source=PoisoningSourceStrategy.RANDOM_BENIGN,
                fraction=1.5,
                target_scope=PoisoningTargetScope.SINGLE_CLIENT,
                training_seed=0,
                poisoning_seed=100,
            )

    def test_empty_dataset_raises(self) -> None:
        with pytest.raises(ValueError, match="dataset"):
            CellId(
                scale=ExperimentScale.BOUNDED,
                dataset="",
                policy=ThresholdPolicy.B1_GLOBAL,
                objective=AttackerObjective.THRESHOLD_RAISE,
                source=PoisoningSourceStrategy.RANDOM_BENIGN,
                fraction=0.10,
                target_scope=PoisoningTargetScope.SINGLE_CLIENT,
                training_seed=0,
                poisoning_seed=100,
            )


class TestConstants:
    def test_n_min(self) -> None:
        assert N_MIN == 100

    def test_tail_mass(self) -> None:
        assert abs(TAIL_MASS - 0.10) < 1e-9

    def test_materiality_factor(self) -> None:
        assert abs(MATERIALITY_FACTOR - 0.1) < 1e-9

    def test_b4_k(self) -> None:
        assert B4_K == 3

    def test_b4_n_init(self) -> None:
        assert B4_N_INIT == 10

    def test_b4_max_iter(self) -> None:
        assert B4_MAX_ITER == 300

    def test_b4_random_state(self) -> None:
        assert B4_RANDOM_STATE == 42

    def test_compromise_pattern_seed(self) -> None:
        assert COMPROMISE_PATTERN_SEED == 400

    def test_bounded_fraction_grid(self) -> None:
        assert BOUNDED_SWEEP_FRACTIONS == (0.0, 0.10, 0.20, 0.40)

    def test_output_root_name(self) -> None:
        assert CALIBRATION_POISONING_OUTPUT_ROOT == "conference_calibration_poisoning"

    def test_manifest_file_names(self) -> None:
        assert ManifestFile.PROJECT_AUDIT_REPORT == "project_audit_report.json"
        assert ManifestFile.CLEAN_SCORE_ARTIFACTS == "clean_score_artifacts.json"
        assert ManifestFile.NBAIOT_BOUNDED_SWEEP_MANIFEST == "nbaiot_bounded_sweep_manifest.json"
        assert ManifestFile.PAPER_FIGURE_MANIFEST == "paper_figure_manifest.json"

    def test_run_file_names(self) -> None:
        assert RunFile.POISONED_SCORES.endswith(".parquet")
        assert RunFile.THRESHOLD_DELTAS.endswith(".json")
        assert RunFile.CELL_METRICS.endswith(".json")
