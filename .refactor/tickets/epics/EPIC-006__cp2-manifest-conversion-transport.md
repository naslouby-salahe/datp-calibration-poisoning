# EPIC-006 — CP2 Manifest Conversion and JSON Transport Boundaries

## Metadata

- Status: GROUP_ONLY
- Phase: Phase B
- Parent epic: none
- Priority: P1
- Scientific-contract sensitivity: High
- Artifact and serialization sensitivity: High
- Public-interface sensitivity: Medium

## Purpose

This parent preserves the original master-backlog planning theme for cp2 manifest conversion and json transport boundaries. It groups child tickets but is not itself executable.

## Why This Is Not Executable Directly

The original parent combined multiple independently verifiable ownership, compatibility, validation, artifact, public-interface, or scientific boundaries. Executing it directly would force an implementation agent to make unrelated design decisions in one change and would make rollback/audit attribution unclear.

## Child Tickets

- TKT-031: Runtime Result to Persisted Row Conversion Owner. Purpose: Make the runtime-to-BoundedSweepResultRow conversion a single explicit owner. Dependency position: depends on TKT-023; blocks TKT-037.
- TKT-034: Per Run Manifest Construction Boundary. Purpose: Centralize RunManifest construction and emission while preserving field names. Dependency position: depends on TKT-023, TKT-027; blocks TKT-039.
- TKT-037: Aggregate Bounded Sweep Manifest Construction Boundary. Purpose: Make bounded aggregate manifest assembly and n_cells/result consistency explicit. Dependency position: depends on TKT-031, TKT-036; blocks TKT-047, TKT-063.
- TKT-030: Generic Atomic JSON and CSV Transport Delegation. Purpose: Delegate transport mechanics to generic artifact I/O where schema ownership remains CP2-specific. Dependency position: depends on TKT-025; blocks TKT-034, TKT-037.
- TKT-039: Manifest Post Read and Historical Compatibility Validation. Purpose: Validate loaded manifests against current protocol and compatibility rules. Dependency position: depends on TKT-034, TKT-037, TKT-033; blocks TKT-065.

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

- TKT-031: covers a separately executable part of CP2 Manifest Conversion and JSON Transport Boundaries.
- TKT-034: covers a separately executable part of CP2 Manifest Conversion and JSON Transport Boundaries.
- TKT-037: covers a separately executable part of CP2 Manifest Conversion and JSON Transport Boundaries.
- TKT-030: covers a separately executable part of CP2 Manifest Conversion and JSON Transport Boundaries.
- TKT-039: covers a separately executable part of CP2 Manifest Conversion and JSON Transport Boundaries.

## Execution Restriction

This epic must not be executed directly.


## Identifier History

- Final identifier: EPIC-006
- Legacy identifier(s):
  - TKT-006
- Identifier migration date: 2026-06-18
- Crosswalk: [../TICKET_ID_CROSSWALK.md](../TICKET_ID_CROSSWALK.md)

## Execution Record

Reserved for the execution agent.

- Group status:
- Child completion summary:
- Remaining risks:
