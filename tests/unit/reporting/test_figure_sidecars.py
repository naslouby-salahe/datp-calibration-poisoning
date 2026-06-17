from __future__ import annotations

import json
from pathlib import Path

from datp.checkpointing.enums import EvidenceRole
from datp.core.enums import SeedScope
from datp.reporting.build import _REPRESENTATIVE_SEED_FIGURES, _validate_figure_sidecars
from datp.reporting.constants import NOT_CONFIRMATORY_WARNING
from datp.reporting.enums import FigureName, SidecarField


def _write_sidecar(figures_dir: Path, fig_name: str, data: dict) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)
    (figures_dir / f"{fig_name}_data.json").write_text(
        json.dumps(data), encoding="utf-8"
    )


def _valid_sidecar(fig_name: str) -> dict:
    return {
        "figure": fig_name,
        "title": f"{fig_name} — representative seed, descriptive only",
        "evidence_role": EvidenceRole.DESCRIPTIVE.value,
        "seed_scope": SeedScope.REPRESENTATIVE_SEED.value,
        SidecarField.NOT_CONFIRMATORY_WARNING.value: NOT_CONFIRMATORY_WARNING,
        "seeds": [0],
    }


def test_valid_sidecars_pass(tmp_path: Path) -> None:
    figures_dir = tmp_path / "figures"
    for fig in _REPRESENTATIVE_SEED_FIGURES:
        _write_sidecar(figures_dir, fig, _valid_sidecar(fig))
    errors = _validate_figure_sidecars(figures_dir)
    assert errors == []


def test_missing_sidecar_fails(tmp_path: Path) -> None:
    figures_dir = tmp_path / "figures"
    figures_dir.mkdir(parents=True)
    one_fig = sorted(_REPRESENTATIVE_SEED_FIGURES)[0]
    _write_sidecar(figures_dir, one_fig, _valid_sidecar(one_fig))
    errors = _validate_figure_sidecars(figures_dir)
    assert any("Missing figure sidecar" in e for e in errors)


def test_wrong_seed_scope_fails(tmp_path: Path) -> None:
    figures_dir = tmp_path / "figures"
    for fig in _REPRESENTATIVE_SEED_FIGURES:
        sidecar = _valid_sidecar(fig)
        sidecar["seed_scope"] = SeedScope.ALL_SEED.value
        _write_sidecar(figures_dir, fig, sidecar)
    errors = _validate_figure_sidecars(figures_dir)
    assert any("seed_scope" in e for e in errors)


def test_wrong_evidence_role_fails(tmp_path: Path) -> None:
    figures_dir = tmp_path / "figures"
    for fig in _REPRESENTATIVE_SEED_FIGURES:
        sidecar = _valid_sidecar(fig)
        sidecar["evidence_role"] = "confirmatory"
        _write_sidecar(figures_dir, fig, sidecar)
    errors = _validate_figure_sidecars(figures_dir)
    assert any("evidence_role" in e for e in errors)


def test_missing_not_confirmatory_warning_fails(tmp_path: Path) -> None:
    figures_dir = tmp_path / "figures"
    for fig in _REPRESENTATIVE_SEED_FIGURES:
        sidecar = _valid_sidecar(fig)
        del sidecar[SidecarField.NOT_CONFIRMATORY_WARNING.value]
        _write_sidecar(figures_dir, fig, sidecar)
    errors = _validate_figure_sidecars(figures_dir)
    assert any(SidecarField.NOT_CONFIRMATORY_WARNING.value in e for e in errors)


def test_title_without_representative_seed_fails(tmp_path: Path) -> None:
    figures_dir = tmp_path / "figures"
    for fig in _REPRESENTATIVE_SEED_FIGURES:
        sidecar = _valid_sidecar(fig)
        sidecar["title"] = "Plain title without the required wording"
        _write_sidecar(figures_dir, fig, sidecar)
    errors = _validate_figure_sidecars(figures_dir)
    assert any("title" in e or "representative seed" in e.lower() for e in errors)


def test_representative_seed_figures_uses_canonical_names() -> None:
    """Verify _REPRESENTATIVE_SEED_FIGURES contains only FigureName values."""
    canonical = {FigureName.FIGURE_1.value, FigureName.FIGURE_2.value}
    assert _REPRESENTATIVE_SEED_FIGURES == canonical
