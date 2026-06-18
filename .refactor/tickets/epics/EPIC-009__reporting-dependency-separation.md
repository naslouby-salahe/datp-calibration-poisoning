# EPIC-009 — CP2 Report Preparation and Generic Reporting Rendering Separation

## Metadata

- Status: GROUP_ONLY
- Phase: Phase C
- Parent epic: none
- Priority: P1
- Scientific-contract sensitivity: Medium
- Artifact and serialization sensitivity: High
- Public-interface sensitivity: Medium

## Purpose

This parent preserves the original master-backlog planning theme for cp2 report preparation and generic reporting rendering separation. It groups child tickets but is not itself executable.

## Why This Is Not Executable Directly

The original parent combined multiple independently verifiable ownership, compatibility, validation, artifact, public-interface, or scientific boundaries. Executing it directly would force an implementation agent to make unrelated design decisions in one change and would make rollback/audit attribution unclear.

## Child Tickets

- TKT-042: Reporting Import Classification. Purpose: Classify current reporting imports and verify whether reporting imports CP2 attack modules. Dependency position: depends on TKT-041; blocks TKT-047, TKT-046.
- TKT-047: CP2 Report Preparation Adapter. Purpose: Introduce a CP2-specific report-preparation adapter only if reporting must consume CP2 manifests. Dependency position: depends on TKT-042, TKT-037; blocks TKT-046, TKT-062.
- TKT-046: Generic Rendering Input Model Boundary. Purpose: Ensure generic reporting rendering receives prepared data, not raw CP2 scientific objects. Dependency position: depends on TKT-042; blocks TKT-054, TKT-059.
- TKT-054: Reporting Validation Boundary. Purpose: Keep report input validation separate from generic metric validation and CP2 protocol validation. Dependency position: depends on TKT-046, TKT-052; blocks TKT-062.
- TKT-059: Report Output Compatibility and CLI Routing. Purpose: Preserve report file names, sidecars, table/figure outputs, and report CLI routes after boundary cleanup. Dependency position: depends on TKT-046, TKT-054; blocks TKT-062.

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

- TKT-042: covers a separately executable part of CP2 Report Preparation and Generic Reporting Rendering Separation.
- TKT-047: covers a separately executable part of CP2 Report Preparation and Generic Reporting Rendering Separation.
- TKT-046: covers a separately executable part of CP2 Report Preparation and Generic Reporting Rendering Separation.
- TKT-054: covers a separately executable part of CP2 Report Preparation and Generic Reporting Rendering Separation.
- TKT-059: covers a separately executable part of CP2 Report Preparation and Generic Reporting Rendering Separation.

## Execution Restriction

This epic must not be executed directly.


## Identifier History

- Final identifier: EPIC-009
- Legacy identifier(s):
  - TKT-009
- Identifier migration date: 2026-06-18
- Crosswalk: [../TICKET_ID_CROSSWALK.md](../TICKET_ID_CROSSWALK.md)

## Execution Record

Reserved for the execution agent.

- Group status:
- Child completion summary:
- Remaining risks:
