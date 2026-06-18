# EPIC-004 — Canonical CP2 Condition and Run Identity with Boundary Projections

## Metadata

- Status: GROUP_ONLY
- Phase: Phase A
- Parent epic: none
- Priority: P0
- Scientific-contract sensitivity: High
- Artifact and serialization sensitivity: High
- Public-interface sensitivity: High

## Purpose

This parent preserves the original master-backlog planning theme for canonical cp2 condition and run identity with boundary projections. It groups child tickets but is not itself executable.

## Why This Is Not Executable Directly

The original parent combined multiple independently verifiable ownership, compatibility, validation, artifact, public-interface, or scientific boundaries. Executing it directly would force an implementation agent to make unrelated design decisions in one change and would make rollback/audit attribution unclear.

## Child Tickets

- TKT-015: CP2 Condition Identity Semantic Owner. Purpose: Define the condition-level CP2 semantic identity and keep boundary projections separate. Dependency position: depends on TKT-009, TKT-011; blocks TKT-018, TKT-022, TKT-023.
- TKT-018: CP2 Run Identity and Seed Pairing Owner. Purpose: Define run identity around condition, training seed, poisoning seed, and victim/victim plan. Dependency position: depends on TKT-015, TKT-008; blocks TKT-022, TKT-020, TKT-039.
- TKT-022: Identity to Path Projection. Purpose: Make CP2 path projection derive from canonical identity while preserving exact current path strings. Dependency position: depends on TKT-018, TKT-004; blocks TKT-027, TKT-036.
- TKT-023: Identity to Manifest and Result Projection. Purpose: Make persisted flat fields derive from canonical identity without changing JSON keys. Dependency position: depends on TKT-018, TKT-005; blocks TKT-031, TKT-034, TKT-037.
- TKT-020: Pair Grouping and Victim Plan Identity Validation. Purpose: Validate that result grouping preserves victim or victim-plan identity across clean and poisoned pairs. Dependency position: depends on TKT-018; blocks TKT-064, TKT-065.

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

- TKT-015: covers a separately executable part of Canonical CP2 Condition and Run Identity with Boundary Projections.
- TKT-018: covers a separately executable part of Canonical CP2 Condition and Run Identity with Boundary Projections.
- TKT-022: covers a separately executable part of Canonical CP2 Condition and Run Identity with Boundary Projections.
- TKT-023: covers a separately executable part of Canonical CP2 Condition and Run Identity with Boundary Projections.
- TKT-020: covers a separately executable part of Canonical CP2 Condition and Run Identity with Boundary Projections.

## Execution Restriction

This epic must not be executed directly.


## Identifier History

- Final identifier: EPIC-004
- Legacy identifier(s):
  - TKT-004
- Identifier migration date: 2026-06-18
- Crosswalk: [../TICKET_ID_CROSSWALK.md](../TICKET_ID_CROSSWALK.md)

## Execution Record

Reserved for the execution agent.

- Group status:
- Child completion summary:
- Remaining risks:
