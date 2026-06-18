# EPIC-008 — Package Dependency Direction and Validation Scope Ownership

## Metadata

- Status: GROUP_ONLY
- Phase: Phase C
- Parent epic: none
- Priority: P1
- Scientific-contract sensitivity: Medium
- Artifact and serialization sensitivity: Medium
- Public-interface sensitivity: High

## Purpose

This parent preserves the original master-backlog planning theme for package dependency direction and validation scope ownership. It groups child tickets but is not itself executable.

## Why This Is Not Executable Directly

The original parent combined multiple independently verifiable ownership, compatibility, validation, artifact, public-interface, or scientific boundaries. Executing it directly would force an implementation agent to make unrelated design decisions in one change and would make rollback/audit attribution unclear.

## Child Tickets

- TKT-041: Import Graph Baseline and Runtime Cycle Verification. Purpose: Capture actual package dependency graph and distinguish package-level cycles from runtime circular imports. Dependency position: depends on TKT-028; blocks TKT-043, TKT-044, TKT-045.
- TKT-043: Artifact Existence versus Semantic Validation Separation. Purpose: Remove or justify lower-level artifact existence code depending on higher-level metric semantic validation. Dependency position: depends on TKT-041, TKT-029; blocks TKT-062.
- TKT-044: Score Loading versus Artifact Layout Boundary. Purpose: Clarify whether scoring may depend on artifact layout primitives or should receive resolved paths. Dependency position: depends on TKT-041, TKT-028; blocks TKT-062.
- TKT-052: Generic Metric Validation versus CP2 Metric Validation Taxonomy. Purpose: Define which package validates generic metrics, CP2 paired metrics, provenance, and report inputs. Dependency position: depends on TKT-041, TKT-053; blocks TKT-062.
- TKT-045: Public Re Export and Architecture Test Preservation. Purpose: Preserve public imports while hardening architecture tests around semantic boundaries. Dependency position: depends on TKT-041; blocks TKT-068.

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

- TKT-041: covers a separately executable part of Package Dependency Direction and Validation Scope Ownership.
- TKT-043: covers a separately executable part of Package Dependency Direction and Validation Scope Ownership.
- TKT-044: covers a separately executable part of Package Dependency Direction and Validation Scope Ownership.
- TKT-052: covers a separately executable part of Package Dependency Direction and Validation Scope Ownership.
- TKT-045: covers a separately executable part of Package Dependency Direction and Validation Scope Ownership.

## Execution Restriction

This epic must not be executed directly.


## Identifier History

- Final identifier: EPIC-008
- Legacy identifier(s):
  - TKT-008
- Identifier migration date: 2026-06-18
- Crosswalk: [../TICKET_ID_CROSSWALK.md](../TICKET_ID_CROSSWALK.md)

## Execution Record

Reserved for the execution agent.

- Group status:
- Child completion summary:
- Remaining risks:
