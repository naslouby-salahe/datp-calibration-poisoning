# EPIC-011 — CP2 CLI Orchestration, Validation, Status, and Resume Behavior

## Metadata

- Status: GROUP_ONLY
- Phase: Phase D
- Parent epic: none
- Priority: P0
- Scientific-contract sensitivity: High
- Artifact and serialization sensitivity: High
- Public-interface sensitivity: High

## Purpose

This parent preserves the original master-backlog planning theme for cp2 cli orchestration, validation, status, and resume behavior. It groups child tickets but is not itself executable.

## Why This Is Not Executable Directly

The original parent combined multiple independently verifiable ownership, compatibility, validation, artifact, public-interface, or scientific boundaries. Executing it directly would force an implementation agent to make unrelated design decisions in one change and would make rollback/audit attribution unclear.

## Child Tickets

- TKT-060: CLI Command Registry and Compatibility Inventory. Purpose: Create a registry of actual Typer groups, command names, options, and compatibility aliases before CLI changes. Dependency position: depends on TKT-045; blocks TKT-061, TKT-063, TKT-062.
- TKT-061: CLI Configuration Normalization. Purpose: Normalize CLI inputs into typed config/enum objects without CLI-local protocol defaults. Dependency position: depends on TKT-060, TKT-010; blocks TKT-063, TKT-064.
- TKT-063: CLI to Orchestration Delegation. Purpose: Ensure CLI commands delegate to orchestration and do not own scientific work or manifest assembly. Dependency position: depends on TKT-061, TKT-048, TKT-037; blocks TKT-064, TKT-065.
- TKT-064: Canonical Matrix Creation and Preview Dry Run Consistency. Purpose: Make preview, dry-run, smoke, and bounded run use the same matrix definitions with mode-specific execution depth only. Dependency position: depends on TKT-063, TKT-009, TKT-020; blocks TKT-065.
- TKT-065: Status Command Lifecycle and Resume Gate Integration. Purpose: Make status and resume consume canonical lifecycle, manifest, and identity validation. Dependency position: depends on TKT-063, TKT-033, TKT-039; blocks TKT-068.
- TKT-062: Validation Routing and Error Translation. Purpose: Route CLI and orchestration validation to the correct owner and translate errors without weakening checks. Dependency position: depends on TKT-060, TKT-052, TKT-054, TKT-040; blocks TKT-068.

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

- TKT-060: covers a separately executable part of CP2 CLI Orchestration, Validation, Status, and Resume Behavior.
- TKT-061: covers a separately executable part of CP2 CLI Orchestration, Validation, Status, and Resume Behavior.
- TKT-063: covers a separately executable part of CP2 CLI Orchestration, Validation, Status, and Resume Behavior.
- TKT-064: covers a separately executable part of CP2 CLI Orchestration, Validation, Status, and Resume Behavior.
- TKT-065: covers a separately executable part of CP2 CLI Orchestration, Validation, Status, and Resume Behavior.
- TKT-062: covers a separately executable part of CP2 CLI Orchestration, Validation, Status, and Resume Behavior.

## Execution Restriction

This epic must not be executed directly.


## Identifier History

- Final identifier: EPIC-011
- Legacy identifier(s):
  - TKT-011
- Identifier migration date: 2026-06-18
- Crosswalk: [../TICKET_ID_CROSSWALK.md](../TICKET_ID_CROSSWALK.md)

## Execution Record

Reserved for the execution agent.

- Group status:
- Child completion summary:
- Remaining risks:
