# EPIC-002 — CP2 Protocol Value Ownership and Semantic Classification

## Metadata

- Status: GROUP_ONLY
- Phase: Phase A
- Parent epic: none
- Priority: P0
- Scientific-contract sensitivity: High
- Artifact and serialization sensitivity: High
- Public-interface sensitivity: High

## Purpose

This parent preserves the original master-backlog planning theme for cp2 protocol value ownership and semantic classification. It groups child tickets but is not itself executable.

## Why This Is Not Executable Directly

The original parent combined multiple independently verifiable ownership, compatibility, validation, artifact, public-interface, or scientific boundaries. Executing it directly would force an implementation agent to make unrelated design decisions in one change and would make rollback/audit attribution unclear.

## Child Tickets

- TKT-007: CP2 Protocol Value Ownership Register. Purpose: Classify every repeated CP2 value before any consolidation ticket changes code. Dependency position: depends on TKT-001, TKT-003; blocks TKT-008, TKT-009, TKT-010, TKT-011, TKT-012.
- TKT-008: Seed Pool Ownership and Typed Propagation. Purpose: Establish one semantic owner and one typed propagation path for CP2 seed pools. Dependency position: depends on TKT-007, TKT-002; blocks TKT-018, TKT-039, TKT-061.
- TKT-009: Fraction Grid and Policy Matrix Ownership. Purpose: Make matrix condition ownership explicit for policies, sources, objectives, fractions, and target scope. Dependency position: depends on TKT-007, TKT-003; blocks TKT-015, TKT-064.
- TKT-010: YAML to Typed CP2 Effective Configuration Validation. Purpose: Prevent YAML/generic config from silently overriding CP2 protocol locks. Dependency position: depends on TKT-007; blocks TKT-039, TKT-061.
- TKT-011: Raw Domain String to Enum Control Flow Migration. Purpose: Replace internal raw control-flow strings with canonical enums while preserving boundary strings. Dependency position: depends on TKT-007; blocks TKT-015, TKT-048, TKT-061.
- TKT-012: Scientific Constant Classification and Documentation. Purpose: Document protocol locks, compatibility constants, generic settings, and coincidental literals after classification. Dependency position: depends on TKT-007; blocks TKT-014, TKT-026, TKT-053.

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

- EPIC-007: covers a separately executable part of CP2 Protocol Value Ownership and Semantic Classification.
- EPIC-008: covers a separately executable part of CP2 Protocol Value Ownership and Semantic Classification.
- EPIC-009: covers a separately executable part of CP2 Protocol Value Ownership and Semantic Classification.
- EPIC-010: covers a separately executable part of CP2 Protocol Value Ownership and Semantic Classification.
- EPIC-011: covers a separately executable part of CP2 Protocol Value Ownership and Semantic Classification.
- EPIC-012: covers a separately executable part of CP2 Protocol Value Ownership and Semantic Classification.

## Execution Restriction

This epic must not be executed directly.


## Identifier History

- Final identifier: EPIC-002
- Legacy identifier(s):
  - TKT-002
- Identifier migration date: 2026-06-18
- Crosswalk: [../TICKET_ID_CROSSWALK.md](../TICKET_ID_CROSSWALK.md)

## Execution Record

Reserved for the execution agent.

- Group status:
- Child completion summary:
- Remaining risks:
