# EPIC-005 — CP2 Artifact Layout and Lifecycle Ownership

## Metadata

- Status: GROUP_ONLY
- Phase: Phase B
- Parent epic: none
- Priority: P1
- Scientific-contract sensitivity: High
- Artifact and serialization sensitivity: High
- Public-interface sensitivity: Medium

## Purpose

This parent preserves the original master-backlog planning theme for cp2 artifact layout and lifecycle ownership. It groups child tickets but is not itself executable.

## Why This Is Not Executable Directly

The original parent combined multiple independently verifiable ownership, compatibility, validation, artifact, public-interface, or scientific boundaries. Executing it directly would force an implementation agent to make unrelated design decisions in one change and would make rollback/audit attribution unclear.

## Child Tickets

- TKT-027: CP2 Path Projection Stabilization. Purpose: Stabilize CP2 path construction as an identity projection with exact compatibility snapshots. Dependency position: depends on TKT-022; blocks TKT-029, TKT-036, TKT-034.
- TKT-025: Lifecycle Marker State Classification. Purpose: Define one lifecycle state interpreter for absent, in-progress, done, aborted, and corrupt markers. Dependency position: depends on TKT-004; blocks TKT-029, TKT-033, TKT-065.
- TKT-029: Artifact Completeness and Corruption Detection. Purpose: Define completeness checks for CP2 run and aggregate artifacts, including corrupt partial outputs. Dependency position: depends on TKT-027, TKT-025; blocks TKT-033, TKT-039, TKT-065.
- TKT-033: Resume Eligibility Validation. Purpose: Define when a CP2 run may resume, skip, rerun, or block. Dependency position: depends on TKT-025, TKT-029; blocks TKT-065.
- TKT-036: Artifact Discovery and Path Uniqueness Compatibility. Purpose: Validate discovery surfaces and uniqueness for current and historical CP2 artifacts. Dependency position: depends on TKT-027, TKT-020; blocks TKT-065.

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

- TKT-027: covers a separately executable part of CP2 Artifact Layout and Lifecycle Ownership.
- TKT-025: covers a separately executable part of CP2 Artifact Layout and Lifecycle Ownership.
- TKT-029: covers a separately executable part of CP2 Artifact Layout and Lifecycle Ownership.
- TKT-033: covers a separately executable part of CP2 Artifact Layout and Lifecycle Ownership.
- TKT-036: covers a separately executable part of CP2 Artifact Layout and Lifecycle Ownership.

## Execution Restriction

This epic must not be executed directly.


## Identifier History

- Final identifier: EPIC-005
- Legacy identifier(s):
  - TKT-005
- Identifier migration date: 2026-06-18
- Crosswalk: [../TICKET_ID_CROSSWALK.md](../TICKET_ID_CROSSWALK.md)

## Execution Record

Reserved for the execution agent.

- Group status:
- Child completion summary:
- Remaining risks:
