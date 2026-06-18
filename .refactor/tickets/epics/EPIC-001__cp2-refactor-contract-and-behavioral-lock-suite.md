# EPIC-001 — CP2 Refactor Contract and Behavioral Lock Suite

## Metadata

- Status: GROUP_ONLY
- Phase: Phase 00
- Parent epic: none
- Priority: P0
- Scientific-contract sensitivity: High
- Artifact and serialization sensitivity: High
- Public-interface sensitivity: Low

## Purpose

This parent preserves the original master-backlog planning theme for cp2 refactor contract and behavioral lock suite. It groups child tickets but is not itself executable.

## Why This Is Not Executable Directly

The original parent combined multiple independently verifiable ownership, compatibility, validation, artifact, public-interface, or scientific boundaries. Executing it directly would force an implementation agent to make unrelated design decisions in one change and would make rollback/audit attribution unclear.

## Child Tickets

- TKT-001: CP2 Protocol Lock Inventory and Test Mapping. Purpose: Build the prerequisite contract-to-test inventory before adding or modifying any behavioral lock tests. Dependency position: depends on none; blocks TKT-002, TKT-003, TKT-004, TKT-005, TKT-006.
- TKT-002: Seed and Paired Comparison Regression Locks. Purpose: Lock deterministic seed derivation and clean-versus-poisoned pairing behavior independently from policy and artifact tests. Dependency position: depends on TKT-001; blocks TKT-008, TKT-018.
- TKT-003: B1 B2 B4 and B3 Exclusion Behavioral Locks. Purpose: Lock policy semantics before policy dispatch changes. Dependency position: depends on TKT-001; blocks TKT-048, TKT-050, TKT-049, TKT-051.
- TKT-004: Artifact Path and Lifecycle Compatibility Locks. Purpose: Lock path strings, marker states, and corruption behavior independently from manifest schema tests. Dependency position: depends on TKT-001; blocks TKT-027, TKT-025, TKT-029, TKT-033.
- TKT-005: Manifest Schema and Resume Compatibility Locks. Purpose: Lock manifest round trips, provenance, mu_flag persistence, and resume eligibility. Dependency position: depends on TKT-001; blocks TKT-031, TKT-034, TKT-037, TKT-065.
- TKT-006: Score Stage Reservoir and AUROC Invariance Locks. Purpose: Lock score-stage separation, reservoir safety, and AUROC test-score invariance. Dependency position: depends on TKT-001; blocks TKT-035, TKT-038, TKT-055.

## Shared Constraints

- Preserve calibration-channel-only CP2 scope.
- Preserve clean training, scoring, and test behavior.
- Preserve paired clean-versus-poisoned comparisons.
- Preserve B1, B2, and B4 as distinct policies.
- Preserve B3 exclusion from the default CP2 policy matrix.
- Preserve artifact paths, manifest keys, enum values, lifecycle markers, CLI routes, and public imports unless a child explicitly authorizes an additive compatibility path.
- Do not implement production changes from this group record.

## Group Completion Criteria

This epic is complete only when every child is AUDITED, REJECTED, DEFERRED, or SUPERSEDED through the execution workflow, and the group-level contracts above remain satisfied.

## Coverage Mapping

- EPIC-001: covers a separately executable part of CP2 Refactor Contract and Behavioral Lock Suite.
- EPIC-002: covers a separately executable part of CP2 Refactor Contract and Behavioral Lock Suite.
- EPIC-003: covers a separately executable part of CP2 Refactor Contract and Behavioral Lock Suite.
- EPIC-004: covers a separately executable part of CP2 Refactor Contract and Behavioral Lock Suite.
- EPIC-005: covers a separately executable part of CP2 Refactor Contract and Behavioral Lock Suite.
- EPIC-006: covers a separately executable part of CP2 Refactor Contract and Behavioral Lock Suite.

## Execution Restriction

This epic must not be executed directly.


## Identifier History

- Final identifier: EPIC-001
- Legacy identifier(s):
  - TKT-001
- Identifier migration date: 2026-06-18
- Crosswalk: [../TICKET_ID_CROSSWALK.md](../TICKET_ID_CROSSWALK.md)

## Execution Record

Reserved for the execution agent.

- Group status:
- Child completion summary:
- Remaining risks:
