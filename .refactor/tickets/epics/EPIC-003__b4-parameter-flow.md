# EPIC-003 — B4 Parameter Flow and Typed Configuration Ownership

## Metadata

- Status: GROUP_ONLY
- Phase: Phase A
- Parent epic: none
- Priority: P0
- Scientific-contract sensitivity: High
- Artifact and serialization sensitivity: High
- Public-interface sensitivity: Medium

## Purpose

This parent preserves the original master-backlog planning theme for b4 parameter flow and typed configuration ownership. It groups child tickets but is not itself executable.

## Why This Is Not Executable Directly

The original parent combined multiple independently verifiable ownership, compatibility, validation, artifact, public-interface, or scientific boundaries. Executing it directly would force an implementation agent to make unrelated design decisions in one change and would make rollback/audit attribution unclear.

## Child Tickets

- TKT-014: B4 Default and Protocol Lock Ownership. Purpose: Assign canonical CP2 ownership for B4 K, n_init, max_iter, and random_state. Dependency position: depends on TKT-007, TKT-012, TKT-003; blocks TKT-016, TKT-019.
- TKT-016: B4 Typed Configuration Validation Boundary. Purpose: Make B4ClusterConfig the validated CP2 boundary or document the already-equivalent boundary. Dependency position: depends on TKT-014, TKT-010; blocks TKT-019, TKT-021, TKT-051.
- TKT-019: B4 Recompute Call Path Normalization. Purpose: Normalize compute_b4_pair callers around the validated B4 config boundary. Dependency position: depends on TKT-016; blocks TKT-051.
- TKT-021: B4 Manifest Provenance Compatibility. Purpose: Ensure persisted CP2 manifests record or validate effective B4 configuration without breaking existing schemas. Dependency position: depends on TKT-016, TKT-005; blocks TKT-034, TKT-037.
- TKT-024: B4 Determinism and Decomposition Regression Protection. Purpose: Harden tests around deterministic B4 behavior and decomposition identity after B4 flow changes. Dependency position: depends on TKT-019, TKT-003; blocks TKT-051, TKT-055.

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

- TKT-014: covers a separately executable part of B4 Parameter Flow and Typed Configuration Ownership.
- TKT-016: covers a separately executable part of B4 Parameter Flow and Typed Configuration Ownership.
- TKT-019: covers a separately executable part of B4 Parameter Flow and Typed Configuration Ownership.
- TKT-021: covers a separately executable part of B4 Parameter Flow and Typed Configuration Ownership.
- TKT-024: covers a separately executable part of B4 Parameter Flow and Typed Configuration Ownership.

## Execution Restriction

This epic must not be executed directly.


## Identifier History

- Final identifier: EPIC-003
- Legacy identifier(s):
  - TKT-003
- Identifier migration date: 2026-06-18
- Crosswalk: [../TICKET_ID_CROSSWALK.md](../TICKET_ID_CROSSWALK.md)

## Execution Record

Reserved for the execution agent.

- Group status:
- Child completion summary:
- Remaining risks:
