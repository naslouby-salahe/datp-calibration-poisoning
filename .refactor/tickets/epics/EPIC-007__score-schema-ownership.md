# EPIC-007 — Persisted Score Schema and CP2 Runtime Score Containers

## Metadata

- Status: GROUP_ONLY
- Phase: Phase B
- Parent epic: none
- Priority: P1
- Scientific-contract sensitivity: High
- Artifact and serialization sensitivity: High
- Public-interface sensitivity: Medium

## Purpose

This parent preserves the original master-backlog planning theme for persisted score schema and cp2 runtime score containers. It groups child tickets but is not itself executable.

## Why This Is Not Executable Directly

The original parent combined multiple independently verifiable ownership, compatibility, validation, artifact, public-interface, or scientific boundaries. Executing it directly would force an implementation agent to make unrelated design decisions in one change and would make rollback/audit attribution unclear.

## Child Tickets

- TKT-026: Persisted Score Schema Ownership. Purpose: Confirm scoring.schema is the sole owner of persisted score column vocabulary and manifest schema constants. Dependency position: depends on TKT-006, TKT-012; blocks TKT-028, TKT-032.
- TKT-028: Generic Score Loading Boundary. Purpose: Make generic score loading own persisted Parquet read/validation behavior. Dependency position: depends on TKT-026; blocks TKT-032, TKT-044.
- TKT-032: CP2 Runtime Score Collection Adapter. Purpose: Keep CP2 ClientScores and ScoreCollection as runtime adapters over validated generic scores. Dependency position: depends on TKT-028; blocks TKT-053.
- TKT-035: Score Stage Routing Validation. Purpose: Validate calibration, benign-test, and attack-test stage routing before CP2 adaptation. Dependency position: depends on TKT-028, TKT-006; blocks TKT-062.
- TKT-038: Reservoir Source Enforcement. Purpose: Enforce that reservoirs use victim-local benign calibration scores only. Dependency position: depends on TKT-032, TKT-006; blocks TKT-053.
- TKT-040: Malformed Score Artifact Handling. Purpose: Define exact failure behavior for missing, empty, malformed, and schema-invalid score artifacts. Dependency position: depends on TKT-028, TKT-035; blocks TKT-062.

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

- TKT-026: covers a separately executable part of Persisted Score Schema and CP2 Runtime Score Containers.
- TKT-028: covers a separately executable part of Persisted Score Schema and CP2 Runtime Score Containers.
- TKT-032: covers a separately executable part of Persisted Score Schema and CP2 Runtime Score Containers.
- TKT-035: covers a separately executable part of Persisted Score Schema and CP2 Runtime Score Containers.
- TKT-038: covers a separately executable part of Persisted Score Schema and CP2 Runtime Score Containers.
- TKT-040: covers a separately executable part of Persisted Score Schema and CP2 Runtime Score Containers.

## Execution Restriction

This epic must not be executed directly.


## Identifier History

- Final identifier: EPIC-007
- Legacy identifier(s):
  - TKT-007
- Identifier migration date: 2026-06-18
- Crosswalk: [../TICKET_ID_CROSSWALK.md](../TICKET_ID_CROSSWALK.md)

## Execution Record

Reserved for the execution agent.

- Group status:
- Child completion summary:
- Remaining risks:
