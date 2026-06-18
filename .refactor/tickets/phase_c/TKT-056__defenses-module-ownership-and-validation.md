# TKT-056 — Defenses Module Ownership and Validation

## Metadata

- Status: NEEDS_VERIFICATION
- Type: implementation
- Phase: Phase C
- Parent epic: EPIC-013
- Priority: P1
- Dependencies: TKT-048
- Blocks: TKT-063
- Scientific-contract sensitivity: Medium
- Artifact and serialization sensitivity: Low
- Public-interface sensitivity: Low
- Estimated change boundary: src/datp/attacks/defenses.py; tests/unit/attacks/ (likely test_threshold_recompute.py or new test_defenses.py)
- Evidence classification: CONFIRMED_SOURCE_EVIDENCE

## Why This Is a Separate Ticket

The trimmed-calibration defense (`TRIMMED_CALIBRATION`) is a distinct CP2 scientific module with its own validation surface (trim fractions, edge cases, interaction with calibration-pending clients). Independently testable and separable from policy dispatch, metric computation, and inference.

## Problem Statement

`src/datp/attacks/defenses.py` implements `trimmed_calibration()` and `build_defended_collection()`. The module lacks explicit ownership documentation, validation for trim-fraction edge cases (fraction=0, fraction=1, fraction resulting in empty collection), and tests for interaction with calibration-pending clients.

Realistic failure scenario: a change to the trim-fraction constant in `poison_names.py` changes defense behavior silently because no regression test locks the defended score distribution for a known input.

## Confirmed Evidence

- Source location: `src/datp/attacks/defenses.py` — `trimmed_calibration()`, `build_defended_collection()`.
- Constants: `TRIM_FRACTION_PRIMARY = 0.05`, `TRIM_FRACTION_APPENDIX = 0.10` in `src/datp/artifacts/poison_names.py`.
- Defense is activated through `PoisoningDefense.TRIMMED_CALIBRATION` in `src/datp/core/poison_enums.py`.
- No dedicated test file `test_defenses.py` exists; defense tests are likely embedded in other test modules.

## Unresolved Evidence Requiring Execution-Time Verification

- Exact module or surface to inspect: `defenses.py` — verify exact function signatures, edge-case handling, and calibration-pending interaction.
- Exact condition that authorizes a change: missing edge-case tests, missing ownership documentation, or missing deterministic-output tests.
- Exact condition that closes the ticket with no code change: tests already cover trim=0, trim=1, empty-after-trim, and edge cases; module has clear docstring.
- Exact condition that requires blocking: defense introduces mutation of clean calibration arrays.

## Failure Mechanism

- Protocol drift: trim fraction changes silently alter defense behavior.
- Wrong scientific result: edge case (trim removes all scores) silently returns empty collection instead of raising.
- Calibration-pending mixing: defense accidentally applied to or withheld from calibration-pending clients incorrectly.

## Target Outcome

The defense module has documented ownership, edge-case tests for all trim fractions, deterministic-output tests for known inputs, and clear interaction with calibration-pending clients.

## Scope

### In Scope

- Add dedicated test file with edge-case tests (trim=0, trim=1, trim > n_samples, trimmed collection empty).
- Add deterministic-output tests: lock defended score count and distribution for known input.
- Document defense semantics and trim-fraction interpretation in module docstring.
- Verify calibration-pending interaction (defense should not affect pending status).

### Explicitly Out of Scope

- New defense families beyond trimmed calibration.
- Changes to metric computation, inference, or reservoir modules.
- Changes to CLI defense configuration or YAML.

## Protected Contracts

- SC-CP2-SCOPE: Calibration-channel-only CP2 scope. Status: validated.
- SC-SCORES: Defense does not use training or test scores. Status: validated.

## Ownership Decision

- Current owner: `datp.attacks.defenses`.
- Intended canonical owner: `datp.attacks.defenses`.

## Detailed Implementation Plan

1. Inspect `defenses.py` for exact function signatures and edge-case handling.
2. Add dedicated `test_defenses.py` with edge-case tests.
3. Add deterministic-output tests for known input.
4. Document defense semantics in module docstring.

## Validation Plan

- unit tests: deterministic-output tests; edge-case tests.

## Required Post-Ticket Audits

### Audit 1 — Implementation and Contract Correctness
- Confirm dedicated test file exists with edge-case coverage.
- Confirm no clean-array mutation.

### Audit 2 — Cross-Package and Protocol Safety
- Confirm calibration-pending interaction is documented and correct.

### Audit 3 — Tests and Documentation Integrity
- Confirm all existing tests still pass.

## Acceptance Criteria

- Dedicated defense test file exists.
- Edge-case tests pass (trim=0, trim=1, trim > n_samples, empty after trim).
- Deterministic-output test locks exact behavior for known input.
- Module docstring documents defense semantics.


## Identifier History

- Final identifier: TKT-056
- Legacy identifier(s):
  - TKT-013-02
- Identifier migration date: 2026-06-18
- Crosswalk: [../TICKET_ID_CROSSWALK.md](../TICKET_ID_CROSSWALK.md)

## Execution Record

Reserved for the execution agent.
