from __future__ import annotations

import pytest

from datp.reporting.engine import format_mean_std, render

# ── format_mean_std ──────────────────────────────────────────────

def test_format_mean_std_normal() -> None:
    result = format_mean_std(0.123, 0.045, bold=False)
    assert "\\textbf" not in result
    assert "0.123" in result
    assert "±" in result
    assert "0.045" in result


def test_format_mean_std_bold() -> None:
    result = format_mean_std(0.123, 0.045, bold=True)
    assert "\\textbf" in result
    assert "0.123" in result
    assert "0.045" in result


def test_format_mean_std_nan_returns_dash() -> None:
    result = format_mean_std(float("nan"), 0.045, bold=False)
    assert result == "---"


def test_format_mean_std_nan_ignores_bold() -> None:
    result = format_mean_std(float("nan"), 0.045, bold=True)
    assert result == "---"


def test_format_mean_std_zero_std() -> None:
    result = format_mean_std(0.5, 0.0, bold=False)
    assert "0.500" in result
    assert "0.000" in result


def test_format_mean_std_inf_values_do_not_crash() -> None:
    """format_mean_std should produce a string for inf/-inf without raising."""
    result = format_mean_std(float("inf"), 0.0, bold=False)
    assert isinstance(result, str)
    assert len(result) > 0

    result_neg = format_mean_std(float("-inf"), 0.0, bold=False)
    assert isinstance(result_neg, str)
    assert len(result_neg) > 0


# ── render ───────────────────────────────────────────────────────

def test_render_table_main_template() -> None:
    """render must resolve the table_main.tex.j2 template and substitute values."""
    from datp.reporting.tables import LatexTableRow

    rows = [
        LatexTableRow(
            label="B1 (Global)",
            cv_fpr="0.120 ± 0.030",
            cv_tpr="0.950 ± 0.020",
            worst_ba="0.800 ± 0.050",
            macro_f1="0.750 ± 0.060",
            coverage="0.83 (5/6)",
        ),
    ]

    output = render(
        "table_main.tex.j2",
        title="Test Table",
        caption="Test Caption",
        header="H1 & H2 & H3 & H4 & H5 & H6",
        rows=rows,
        footnote="Test footnote.",
        comments=["comment one", "comment two"],
    )

    assert "Test Table" in output
    assert "Test Caption" in output
    assert "H1 & H2 & H3 & H4 & H5 & H6" in output
    assert "B1 (Global)" in output
    assert "0.120 ± 0.030" in output
    assert "Test footnote." in output
    assert "% comment one" in output
    assert "% comment two" in output


def test_render_missing_template_raises() -> None:
    with pytest.raises(Exception):
        render("nonexistent_template.tex.j2")
