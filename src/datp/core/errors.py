"""Canonical error-message formatters for datp-cp.

Every formatter produces a ``[module] ...`` prefix so that error messages
are self-documenting about their origin.
"""


def fmt(module: str, problem: str, expected: str, got: str) -> str:
    """Return ``[module] Problem. Expected: X. Got: Y.``"""
    return f"[{module}] {problem}. Expected: {expected}. Got: {got}."


def fmt_missing(module: str, what: str) -> str:
    """Return ``[module] <what> not found.``"""
    return f"[{module}] {what} not found."
