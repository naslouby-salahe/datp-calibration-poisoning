# Code Quality Audit — datp-cp

Audit of the codebase for violations of the code quality rules in .rework/prompts/CODE_QUALITY_RULES.md.

---

## Verdict

Not yet audited.

---

## Checklist

    enums for all closed vocabularies:                  [ ] not audited
    frozen dataclasses for structured data:             [ ] not audited
    precise types (no broad Any/object/dict in core):   [ ] not audited
    no compatibility unions:                            [ ] not audited
    no hardcoded scientific values in logic:            [ ] not audited
    no magic strings:                                   [ ] not audited
    no hidden defaults changing behavior:               [ ] not audited
    no global mutable state:                            [ ] not audited
    no AI-generated filler docstrings:                  [ ] not audited
    no useless comments:                                [ ] not audited
    no stale imports:                                   [ ] not audited
    no dead code:                                       [ ] not audited
    ruff passes:                                        [ ] not run
    pyright passes:                                     [ ] not run
    no obsolete active naming:                          [ ] not audited

---

## Search Commands

    python -m ruff check src/ tests/ 2>&1 | head -40
    python -m pyright 2>&1 | tail -20
    grep -RIn --include="*.py" -E "Any\b" src/datp/ | grep -v "# type:" | head -20
    grep -RIn --include="*.py" -E "Dict\[|Mapping\[str,\s*Any" src/datp/ | head -20
    grep -RIn --include="*.py" -E "@dataclass(?!\()" src/datp/ | head -20
    grep -RIn --include="*.py" "This module provides\|This class is responsible\|Here we" src/datp/ | head -20

---

## Findings

### Status: not yet audited

### Finding Template

    ### CQ-NNN — <description>
    Severity: CRITICAL / HIGH / MEDIUM / LOW
    File: <path>
    Line: <line>
    Rule violated: <from CODE_QUALITY_RULES.md>
    Evidence: <the offending code>
    Required fix: <what must change>
    Status: TODO
