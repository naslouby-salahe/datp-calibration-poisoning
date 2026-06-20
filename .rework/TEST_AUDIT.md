# Test Audit — datp-cp

Audit of the test suite.

---

## Verdict

Not yet audited.

---

## Required Test Coverage

Tests must verify:

    REPLACE_FIXED_BUDGET injection: correct m_i = max(1, round(f * n_i)), correct cardinality
    clean array immutability: poisoned array is a copy; original unchanged
    victim-local reservoir: only victim's own calibration scores used
    seed scheme: SeedSequence([training_seed, poisoning_seed, client_id, scope_id]) used
    no integer seed addition
    AUROC invariance: poisoned AUROC == clean AUROC within tolerance
    Calibration-Pending fallback: clients below n_min receive global threshold
    Calibration-Pending exclusion: these clients excluded from eligible set
    coverage ratio reporting: coverage ratio field present in results
    threshold policy correctness: GLOBAL_THRESHOLD, LOCAL_THRESHOLD, CLUSTER_THRESHOLD each computed correctly
    cluster delta: client-indexed deltas used, not raw cluster label IDs
    enum membership: obsolete values fail fast at boundary
    config validation: invalid configs raise errors
    artifact paths: constructed from named constants, not inline strings
    DONE marker: only written when all artifacts are complete

---

## Forbidden Test Patterns

    tests for removed code (B3, old regime targets, old CLI flags)
    tests with skip or xfail hiding real failures
    tests asserting mocks instead of behavior
    tests that weaken to pass (assertions loosened to accommodate bugs)
    tests importing from obsolete module paths

---

## Findings

### Status: not yet audited

Agents: inspect tests/:

    find tests/ -name "*.py" | sort
    grep -RIn --include="*.py" -E "skip|xfail|pytest.mark.skip" tests/
    grep -RIn --include="*.py" -E "REGIME_|B1_|B2_|B3_|B4_|NBAIOT_BOUNDED" tests/

Write findings here and create CLAUDE tasks for violations.
