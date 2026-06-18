# TKT-058 — Inference Module Ownership and Statistical Lock

## Metadata

- Status: NEEDS_VERIFICATION
- Type: implementation
- Phase: Phase C
- Parent epic: EPIC-013
- Priority: P0
- Dependencies: TKT-053
- Blocks: TKT-062, TKT-047
- Scientific-contract sensitivity: High
- Artifact and serialization sensitivity: Low
- Public-interface sensitivity: Low
- Estimated change boundary: src/datp/attacks/inference.py; tests/unit/attacks/test_inference.py
- Evidence classification: CONFIRMED_SOURCE_EVIDENCE

## Why This Is a Separate Ticket

Two-layer statistical inference (seed-level aggregates → bootstrap CI on 5 aggregates) is the CP2 primary analysis method. It is scientifically critical, independently testable, and must be locked before policy dispatch, reporting, or paper-figure tickets execute. Mixing it with metric computation or diagnostics would create rollback conflicts.

## Problem Statement

`src/datp/attacks/inference.py` implements two-layer statistics: per-victim paired deltas → 5 seed-level aggregates → bootstrap CI (percentile default), sign test (≥4/5), and Holm-adjusted p-values. The CP2 protocol requires seed-level aggregates as the inference unit (not 45 independent samples), Bootstrap CI on 5 aggregates, sign test supporting evidence only, and Holm p-values descriptive only.

Realistic failure scenario: an execution agent refactors inference to use raw per-victim deltas instead of seed-level aggregates, producing artificially narrow CIs and invalid statistical conclusions. No regression test locks the seed-aggregate inference boundary.

## Confirmed Evidence

- Source location: `src/datp/attacks/inference.py` — `compute_seed_deltas()`, `compute_seed_aggregates()`, `bootstrap_ci_aggregates()`, `sign_test()`, `apply_holm_correction()`.
- Protocol source: `docs/DATP_CP_Roadmap.md` §9 — two-layer statistics, seed-level aggregates, bootstrap CI (percentile), sign test supporting evidence only.
- Tests: `tests/unit/attacks/test_inference.py` exists.

## Unresolved Evidence Requiring Execution-Time Verification

- Confirm whether inference operates on 5 seed-level aggregates (not 45 raw deltas) for policy-level conclusions.
- Confirm bootstrap uses percentile default (not BCa or other method).
- Confirm sign test is treated as supporting only (not primary).
- Confirm Holm-adjusted p-values are descriptive only.
- Confirm no alternative inference path bypasses seed aggregation.
- Confirm edge-case tests exist (single seed, zero victim deltas, all-same deltas).

## Failure Mechanism

- Scientific invalidity: inference unit changes from 5 seed aggregates to 45 raw deltas, producing false confidence.
- Protocol violation: bootstrap method changes from percentile to BCa without protocol authorization.
- Overclaim: sign test or Holm p-values presented as primary evidence.

## Target Outcome

Inference module has documented two-layer protocol, seed-level aggregation boundary, deterministic-output tests, edge-case tests, and explicit compliance with CP2 §9.

## Scope

### In Scope

- Add deterministic-output tests that lock exact CI bounds for known seed deltas.
- Add edge-case tests (single seed, zero deltas, all-same deltas).
- Add architecture test that inference cannot receive raw 45-delta input without seed aggregation.
- Document protocol compliance (two-layer, 5 aggregates, percentile, sign test supporting, Holm descriptive).

### Explicitly Out of Scope

- New inference methods.
- Changes to bootstrap implementation in `datp/statistics/bootstrap.py`.
- Changes to metric engine, diagnostics, or reporting.

## Ownership Decision

- Current owner: `datp.attacks.inference`.
- Intended canonical owner: `datp.attacks.inference`.
- Consumers: CP2 report preparation (TKT-047), analysis scripts, paper figure generation.

## Validation Plan

- unit tests: deterministic-output for known seed deltas; edge-case for degenerate inputs.
- architecture/import tests: verify inference cannot bypass seed aggregation.

## Required Post-Ticket Audits

### Audit 1 — Implementation and Contract Correctness
- Confirm inference uses 5 seed-level aggregates, not 45 raw deltas.
- Confirm bootstrap uses percentile, sign test supporting only, Holm descriptive only.

### Audit 2 — Cross-Package and Protocol Safety
- Confirm no alternative inference path bypasses seed aggregation.
- Confirm reporting cannot consume raw deltas for policy-level conclusions.

### Audit 3 — Tests and Documentation Integrity
- Confirm deterministic-output and edge-case tests pass.
- Confirm docstring documents CP2 §9 protocol compliance.

## Acceptance Criteria

- Deterministic-output tests lock CI bounds for known seed delta input.
- Edge-case tests pass for single seed, zero deltas, all-same deltas.
- Architecture test prevents bypass of seed aggregation.
- Module docstring documents two-layer protocol and method defaults.
- All existing tests pass.


## Identifier History

- Final identifier: TKT-058
- Legacy identifier(s):
  - TKT-013-04
- Identifier migration date: 2026-06-18
- Crosswalk: [../TICKET_ID_CROSSWALK.md](../TICKET_ID_CROSSWALK.md)

## Execution Record

Reserved for the execution agent.
