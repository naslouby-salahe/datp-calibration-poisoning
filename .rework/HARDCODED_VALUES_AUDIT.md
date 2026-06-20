# Hardcoded Values Audit — datp-cp

Audit of hardcoded values embedded in logic rather than defined as named constants.

Goal: zero magic numbers or inline strings for scientific parameters in core logic.

---

## Verdict

Not yet audited.

---

## Search Commands

Run these to find candidates:

    grep -RIn --include="*.py" -E "= 100[^0-9]|n_min|min_cal|min_samples" src/datp/
    grep -RIn --include="*.py" -E "seed\s*=\s*[0-9]|random_state\s*=\s*[0-9]" src/datp/
    grep -RIn --include="*.py" -E "0\.(10|20|40|05)[^0-9]" src/datp/
    grep -RIn --include="*.py" -E "K\s*=\s*3|k\s*=\s*3|n_clusters\s*=\s*3" src/datp/
    grep -RIn --include="*.py" -E '"GLOBAL|"LOCAL|"CLUSTER|"THRESHOLD_RAISE|"THRESHOLD_LOWER"' src/datp/
    grep -RIn --include="*.py" -E '"RANDOM_BENIGN|"HIGH_SCORE|"LOW_SCORE"' src/datp/
    grep -RIn --include="*.py" -E "outputs/|conference_calibration" src/datp/

---

## Finding Template

    ### HV-NNN — <description>
    File: <path>
    Line: <line number>
    Value: <the hardcoded value>
    Should be: <named constant name>
    Severity: CRITICAL / HIGH / MEDIUM / LOW
    Status: TODO

---

## Findings

### Status: not yet audited

Agents: run the search commands above and populate findings here.

Create CLAUDE tasks for all CRITICAL and HIGH findings.
