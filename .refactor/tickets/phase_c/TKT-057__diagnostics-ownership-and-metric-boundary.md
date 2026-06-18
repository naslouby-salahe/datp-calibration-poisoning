# TKT-057 — Diagnostics Ownership and Metric Boundary

## Metadata

- Status: NEEDS_VERIFICATION
- Type: implementation
- Phase: Phase C
- Parent epic: EPIC-013
- Priority: P1
- Dependencies: TKT-053
- Blocks: TKT-062
- Scientific-contract sensitivity: Medium
- Artifact and serialization sensitivity: Low
- Public-interface sensitivity: Low
- Estimated change boundary: src/datp/attacks/diagnostics.py; tests/unit/attacks/test_diagnostics.py
- Evidence classification: CONFIRMED_SOURCE_EVIDENCE

## Why This Is a Separate Ticket

ASR (Attack Success Rate), blast radius, and spillover are diagnostic metrics computed over `MetricResult`. They are distinct from the primary CV(FPR) endpoint and the mu_flag threshold. Independently testable, separable from metric engine, inference, and reporting.

## Problem Statement

`src/datp/attacks/diagnostics.py` implements ASR, blast radius, and spillover as pure functions over `MetricResult`. The module lacks explicit ownership documentation, edge-case tests (empty result set, zero-victim scenarios, all-successful/all-failed attacks), and deterministic-output tests for known inputs.

## Confirmed Evidence

- Source location: `src/datp/attacks/diagnostics.py` — ASR, blast radius, spillover functions.
- Tests: `tests/unit/attacks/test_diagnostics.py` exists.
- Input: `MetricResult` from `metric_engine.py`.

## Unresolved Evidence Requiring Execution-Time Verification

- Confirm whether edge-case tests exist (empty result set, zero victims, all-successful, all-failed).
- Confirm deterministic-output tests lock exact diagnostic values for known inputs.
- Confirm no duplicate computation with metrics in `metric_engine.py`.

## Failure Mechanism

- Wrong interpretation: diagnostic metrics drift from their definitions without regression detection.
- Duplicate computation: same metric computed in diagnostics and elsewhere with different results.

## Target Outcome

Diagnostics module has documented ownership, edge-case tests, deterministic-output tests, and no overlap with metric engine.

## Scope

### In Scope

- Add edge-case tests if missing.
- Add deterministic-output tests.
- Document diagnostic metric definitions.

### Explicitly Out of Scope

- Changes to metric engine, inference, or reporting.
- New diagnostic metrics.

## Ownership Decision

- Current owner: `datp.attacks.diagnostics`.
- Intended canonical owner: `datp.attacks.diagnostics`.

## Validation Plan

- unit tests: edge-case and deterministic-output.

## Required Post-Ticket Audits

### Audit 1 — Confirm edge-case tests cover empty results, zero victims.
### Audit 2 — Confirm no duplicate metric definitions with metric_engine.py.
### Audit 3 — Confirm all existing tests pass.

## Acceptance Criteria

- Edge-case tests exist and pass.
- Deterministic-output tests lock exact diagnostic values.
- No duplicate metric definitions with metric_engine.py.


## Identifier History

- Final identifier: TKT-057
- Legacy identifier(s):
  - TKT-013-03
- Identifier migration date: 2026-06-18
- Crosswalk: [../TICKET_ID_CROSSWALK.md](../TICKET_ID_CROSSWALK.md)

## Execution Record

Reserved for the execution agent.
