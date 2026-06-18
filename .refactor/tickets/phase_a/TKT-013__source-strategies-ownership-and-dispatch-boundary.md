# TKT-013 — Source Strategies Ownership and Dispatch Boundary

## Metadata

- Status: NEEDS_VERIFICATION
- Type: implementation
- Phase: Phase A
- Parent epic: EPIC-013
- Priority: P1
- Dependencies: TKT-011
- Blocks: TKT-064
- Scientific-contract sensitivity: Medium
- Artifact and serialization sensitivity: Low
- Public-interface sensitivity: Low
- Estimated change boundary: src/datp/attacks/source_strategies.py; tests/unit/attacks/test_source_strategies.py
- Evidence classification: CONFIRMED_SOURCE_EVIDENCE

## Why This Is a Separate Ticket

Source strategies (RANDOM_BENIGN, HIGH_SCORE_BENIGN, LOW_SCORE_BENIGN, LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY) have their own dispatch logic, near-null criterion, and objective-to-source mapping. Independently testable from injector, reservoir, metrics, and inference.

## Problem Statement

`src/datp/attacks/source_strategies.py` implements source dispatch, `is_near_null_criterion()`, `objective_for_source()`, and `DiagnosticSourceError`. The module lacks explicit ownership documentation, edge-case tests (empty reservoir, source selection with zero available positions), and deterministic-output tests for known inputs.

## Confirmed Evidence

- Source location: `src/datp/attacks/source_strategies.py`.
- Tests: `tests/unit/attacks/test_source_strategies.py` exists.
- Enums: `PoisoningSourceStrategy` in `src/datp/core/poison_enums.py`.
- Diagnostic-only source: `LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY`.

## Unresolved Evidence Requiring Execution-Time Verification

- Confirm exact function signatures and dispatch logic.
- Confirm edge-case tests exist (empty reservoir, zero available positions).
- Confirm deterministic-output tests lock exact source positions for known inputs.
- Confirm diagnostic-only source cannot be used in bounded/full runs.

## Failure Mechanism

- Wrong source positions: dispatch logic change produces wrong reservoir indices.
- Diagnostic source leak: diagnostic-only source used in bounded/full run.

## Target Outcome

Source strategies module has documented ownership, edge-case tests, deterministic-output tests, and diagnostic-source enforcement.

## Scope

### In Scope

- Add edge-case tests if missing.
- Add deterministic-output tests.
- Add diagnostic-source enforcement test.
- Document source semantics in module docstring.

### Explicitly Out of Scope

- New source strategies.
- Changes to injector, reservoir, or metric modules.

## Ownership Decision

- Current owner: `datp.attacks.source_strategies`.
- Intended canonical owner: `datp.attacks.source_strategies`.

## Validation Plan

- unit tests: edge-case and deterministic-output; diagnostic-only enforcement.

## Required Post-Ticket Audits

### Audit 1 — Confirm edge-case tests exist and pass.
### Audit 2 — Confirm diagnostic-only source cannot enter bounded/full execution.
### Audit 3 — Confirm all existing tests pass.

## Acceptance Criteria

- Edge-case tests pass (empty reservoir, zero available positions).
- Deterministic-output tests lock exact source positions.
- Diagnostic-source enforcement test passes.
- All existing tests pass.


## Identifier History

- Final identifier: TKT-013
- Legacy identifier(s):
  - TKT-013-05
- Identifier migration date: 2026-06-18
- Crosswalk: [../TICKET_ID_CROSSWALK.md](../TICKET_ID_CROSSWALK.md)

## Execution Record

Reserved for the execution agent.
