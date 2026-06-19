"""Unit tests for datp.core.regime.enforce_regime."""

from __future__ import annotations

import pytest

from datp.core.enums import Regime
from datp.core.regime import enforce_regime


@enforce_regime(Regime.A)
def _single_a(*, regime: Regime) -> str:
    return f"a:{regime.value}"


@enforce_regime(Regime.A, Regime.B)
def _multi_ab(*, regime: Regime) -> str:
    return f"ab:{regime.value}"


@enforce_regime(Regime.A, Regime.B, Regime.C)
def _all_regimes(*, regime: Regime) -> str:
    return f"all:{regime.value}"


class TestEnforceRegimeDecoration:
    """Errors detected at decoration time (invalid allowed values)."""

    def test_non_regime_allowed_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="allowed values must be Regime"):
            enforce_regime("a")  # type: ignore[arg-type]

    def test_mixed_regime_and_string_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="allowed values must be Regime"):
            enforce_regime(Regime.A, "b")  # type: ignore[arg-type]


class TestEnforceRegimeHappyPath:
    def test_single_allowed_passes(self) -> None:
        assert _single_a(regime=Regime.A) == "a:a"

    def test_multi_allowed_first_passes(self) -> None:
        assert _multi_ab(regime=Regime.A) == "ab:a"

    def test_multi_allowed_second_passes(self) -> None:
        assert _multi_ab(regime=Regime.B) == "ab:b"

    def test_all_regimes_c_passes(self) -> None:
        assert _all_regimes(regime=Regime.C) == "all:c"


class TestEnforceRegimeDisallowed:
    def test_single_disallowed_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="restricted to"):
            _single_a(regime=Regime.B)

    def test_single_disallowed_c_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="restricted to"):
            _single_a(regime=Regime.C)

    def test_multi_disallowed_c_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="restricted to"):
            _multi_ab(regime=Regime.C)


class TestEnforceRegimeMissingOrWrongType:
    def test_missing_regime_kwarg_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="requires 'regime'"):
            _single_a()  # type: ignore[call-arg]

    def test_string_instead_of_enum_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="requires regime as Regime enum"):
            _single_a(regime="a")  # type: ignore[arg-type]

    def test_none_regime_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="requires 'regime'"):
            _single_a(regime=None)  # type: ignore[arg-type]

    def test_int_instead_of_enum_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="requires regime as Regime enum"):
            _single_a(regime=42)  # type: ignore[arg-type]


class TestEnforceRegimePreservesFunction:
    """The decorator must preserve __name__, __doc__, and __module__."""

    def test_preserves_name(self) -> None:
        @enforce_regime(Regime.A)
        def _named(*, regime: Regime) -> int:
            """docstring"""
            return 1

        assert _named.__name__ == "_named"

    def test_preserves_docstring(self) -> None:
        @enforce_regime(Regime.A)
        def _docced(*, regime: Regime) -> int:
            """custom doc"""
            return 1

        assert _docced.__doc__ == "custom doc"

    def test_preserves_module(self) -> None:
        @enforce_regime(Regime.A)
        def _modded(*, regime: Regime) -> int:
            return 1

        assert _modded.__module__ == __name__


class TestEnforceRegimeEmptyAllowed:
    """Edge case: decorator called with no allowed regimes."""

    def test_empty_allowed_always_raises(self) -> None:
        @enforce_regime()
        def _none_allowed(*, regime: Regime) -> str:
            return "unreachable"

        with pytest.raises(ValueError, match="restricted to"):
            _none_allowed(regime=Regime.A)
