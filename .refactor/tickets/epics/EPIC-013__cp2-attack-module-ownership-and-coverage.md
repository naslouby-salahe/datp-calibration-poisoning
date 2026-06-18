# EPIC-013 — CP2 Attack Module Ownership and Behavioral Coverage

## Metadata

- Status: GROUP_ONLY
- Phase: Phase A
- Parent epic: none
- Priority: P1
- Scientific-contract sensitivity: High
- Artifact and serialization sensitivity: Medium
- Public-interface sensitivity: Low

## Purpose

Establish ownership, validation, test coverage, and compatibility protection for the CP2 attack submodules that were not explicitly covered by the TKT-001–TKT-012 decomposition:

- `datp.attacks.compromise_patterns` — multi-client compromise pattern selection (pairs, triples)
- `datp.attacks.defenses` — trimmed-calibration defense (`TRIMMED_CALIBRATION`)
- `datp.attacks.diagnostics` — ASR, blast radius, spillover computation
- `datp.attacks.inference` — two-layer statistical inference (seed deltas, seed aggregates, bootstrap, sign test, Holm)
- `datp.attacks.source_strategies` — source dispatch, near-null criterion, objective-for-source mapping

## Why This Is Not Executable Directly

The parent ticket combined five independently executable modules with different ownership boundaries, different test regimes, and different compatibility sensitivity. Each module has a distinct scientific contract and validation surface.

## Child Tickets (Phase A: TKT-013, TKT-017; Phase C: TKT-056, TKT-057, TKT-058)

| Identifier | Title | Purpose | Dependency Position |
|---|---|---|---|
| TKT-017 | Compromise Pattern Ownership and Determinism | Own multi-client compromise pattern selection; lock SeedSequence derivation | After TKT-008 (seed pool ownership) |
| TKT-056 | Defenses Module Ownership and Validation | Own trimmed-calibration defense; validate defense configuration path | After TKT-048 (policy dispatch) |
| TKT-057 | Diagnostics Ownership and Metric Boundary | Own ASR, blast radius, spillover; separate from core metric engine | After TKT-053 (metric delegation) |
| TKT-058 | Inference Module Ownership and Statistical Lock | Own two-layer inference; lock seed-aggregate bootstrap, sign-test, Holm semantics | After TKT-053 (metric delegation) |
| TKT-013 | Source Strategies Ownership and Dispatch Boundary | Own source dispatch, near-null criterion; validate objective-to-source mapping | After TKT-011 (enum migration) |

## Shared Constraints

- All five modules belong to `datp.attacks` and are CP2-specific.
- No module may import from `datp.testsupport`, `datp.app.cli`, or `datp.reporting`.
- No module may perform artifact I/O that duplicates generic transport in `datp.artifacts.io`.
- Each module must have a clear public interface that is independently testable.
- Reservoir and injector boundaries are owned by TKT-007 and TKT-010 children, not by these tickets.
- Statistical inference must remain two-layer (per-victim deltas → seed aggregates → bootstrap on 5 aggregates).
- B4 decomposition inference must not be merged into generic inference.

## Group Completion Criteria

All five child tickets have completed implementation, validation tests, post-ticket audits, and progress records. Each module has a documented owner, public interface, test coverage, and compatibility preservation.

## Coverage Mapping

- Repository discovery found five `datp.attacks` submodules without explicit executable tickets in the EPIC-001–EPIC-012 decomposition.
- These submodules are scientifically critical (inference determines CP2 conclusions; compromise patterns determine victim selection).
- No EPIC-001–EPIC-012 child ticket names these modules in scope.


## Identifier History

- Final identifier: EPIC-013
- Legacy identifier(s):
  - TKT-013
- Identifier migration date: 2026-06-18
- Crosswalk: [../TICKET_ID_CROSSWALK.md](../TICKET_ID_CROSSWALK.md)

## Execution Restriction

This epic must not be executed directly.
