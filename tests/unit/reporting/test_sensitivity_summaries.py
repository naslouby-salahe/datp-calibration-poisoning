"""Unit tests for sensitivity-manifest summaries."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from datp.artifacts.layout import sensitivity_manifest_path
from datp.attacks.enums import (
    AttackerObjective,
    PoisoningSourceStrategy,
    ReservoirDraw,
)
from datp.attacks.manifests.run_manifest import ProvenanceRecord
from datp.attacks.manifests.sensitivity_manifest import (
    ClusterStabilityRow,
    DrawVariantRow,
    ScaleNormalizationRow,
    SensitivityManifest,
    TrustBoundaryRow,
)
from datp.core.enums import ThresholdPolicy
from datp.core.provenance import REPOSITORY_NAME
from datp.reporting.poisoning import build_sensitivity_summaries

_BASE = {
    "victim_id": "c0",
    "source": PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
    "objective": AttackerObjective.THRESHOLD_RAISE,
    "fraction": 0.4,
}


def _manifest() -> SensitivityManifest:
    cluster = tuple(
        ClusterStabilityRow(
            **_BASE,
            training_seed=0,
            k=3,
            n_init=10,
            random_state=rs,
            victim_delta_tau=0.1 * (rs + 1),
            fixed_victim_delta_tau=0.05,
            victim_size_clean=2,
            victim_size_poisoned=1 if rs == 0 else 2,
            n_reassigned=3 if rs == 0 else 0,
            silhouette_clean=0.4,
            silhouette_poisoned=0.3,
            sizes_clean=(4, 3, 2),
            sizes_poisoned=(4, 4, 1),
        )
        for rs in range(2)
    )
    scale = (
        ScaleNormalizationRow(
            **_BASE,
            training_seed=0,
            tau_local_cv_clean=0.5,
            tau_local_max_min_ratio_clean=3.0,
            score_scale_cv_clean=0.6,
            raw_global_victim_delta_tau=0.2,
            normalized_global_victim_delta_tau=0.1,
            raw_global_victim_delta_fpr=0.02,
            normalized_global_victim_delta_fpr=0.01,
            raw_global_cv_fpr_clean=1.0,
            normalized_global_cv_fpr_clean=0.5,
            raw_global_cv_fpr_poisoned=1.2,
            normalized_global_cv_fpr_poisoned=0.6,
        ),
    )
    variants = (
        DrawVariantRow(
            **_BASE,
            training_seed=0,
            policy=ThresholdPolicy.LOCAL_THRESHOLD,
            draw=ReservoirDraw.WITHOUT_REPLACEMENT,
            requested_n_replaced=40,
            effective_n_replaced=10,
            pool_size=10,
            delta_tau_with_replacement=0.4,
            delta_tau_variant=0.1,
            duplicate_rate_with_replacement=0.3,
            duplicate_rate_variant=0.0,
        ),
        DrawVariantRow(
            **_BASE,
            training_seed=0,
            policy=ThresholdPolicy.LOCAL_THRESHOLD,
            draw=ReservoirDraw.INTERPOLATED_TAIL,
            requested_n_replaced=40,
            effective_n_replaced=40,
            pool_size=10,
            delta_tau_with_replacement=0.4,
            delta_tau_variant=0.3,
            duplicate_rate_with_replacement=0.3,
            duplicate_rate_variant=0.0,
        ),
    )
    trust = (
        TrustBoundaryRow(
            **_BASE,
            training_seed=0,
            policy=ThresholdPolicy.LOCAL_THRESHOLD,
            delta_tau_undefended=0.4,
            delta_tau_trim_primary=0.1,
            delta_tau_trim_appendix=0.0,
            residual_vs_clean_trim_primary=0.3,
            residual_vs_clean_trim_appendix=0.2,
            overwrite_reference_shift=0.8,
            buffer_to_overwrite_ratio=0.5,
        ),
    )
    return SensitivityManifest(
        generated_at_utc="2026-07-01T00:00:00+00:00",
        provenance=ProvenanceRecord(
            local_epochs=1, repository=REPOSITORY_NAME, code_commit="test-commit"
        ),
        config_hash="hash",
        cluster_stability=cluster,
        scale_normalization=scale,
        draw_variants=variants,
        trust_boundary=trust,
    )


def _write(base_dir: Path) -> None:
    path = sensitivity_manifest_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_manifest().model_dump_json())


def _load(base_dir: Path, stem: str) -> list[dict]:
    return json.loads((base_dir / "analysis" / f"{stem}.json").read_text())


def test_missing_manifest_is_reported(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="sensitivity manifest"):
        build_sensitivity_summaries(tmp_path)


def test_cluster_sensitivity_summary(tmp_path: Path) -> None:
    _write(tmp_path)
    build_sensitivity_summaries(tmp_path)
    row = _load(tmp_path, "cluster_stability_sensitivity")[0]
    assert row["k"] == 3
    assert row["victim_singleton_poisoned_rate"] == pytest.approx(0.5)
    assert row["reassignment_rate"] == pytest.approx(0.5)
    assert row["mean_init_sd_victim_delta_tau"] == pytest.approx(0.0707106781, rel=1e-6)


def test_scale_normalization_summary(tmp_path: Path) -> None:
    _write(tmp_path)
    build_sensitivity_summaries(tmp_path)
    row = _load(tmp_path, "scale_normalization_summary")[0]
    assert row["raw_global_victim_delta_tau"] == pytest.approx(0.2)
    assert row["normalized_global_victim_delta_tau"] == pytest.approx(0.1)
    assert row["mean_tau_local_max_min_ratio_clean"] == pytest.approx(3.0)


def test_draw_variant_summary(tmp_path: Path) -> None:
    _write(tmp_path)
    build_sensitivity_summaries(tmp_path)
    rows = {r["draw"]: r for r in _load(tmp_path, "draw_variant_summary")}
    distinct = rows[ReservoirDraw.WITHOUT_REPLACEMENT.value]
    assert distinct["full_budget_feasible_rate"] == 0.0
    assert distinct["mean_duplicate_rate_variant"] == 0.0
    assert distinct["variant_to_baseline_ratio"] == pytest.approx(0.25)
    assert distinct["synthesized_values"] is False
    interpolated = rows[ReservoirDraw.INTERPOLATED_TAIL.value]
    assert interpolated["synthesized_values"] is True
    assert interpolated["full_budget_feasible_rate"] == 1.0


def test_trust_boundary_summary(tmp_path: Path) -> None:
    _write(tmp_path)
    build_sensitivity_summaries(tmp_path)
    row = _load(tmp_path, "trust_boundary_summary")[0]
    assert row["mean_delta_tau_undefended"] == pytest.approx(0.4)
    assert row["trim_primary_reduction"] == pytest.approx(0.75)
    assert row["mean_buffer_to_overwrite_ratio"] == pytest.approx(0.5)
