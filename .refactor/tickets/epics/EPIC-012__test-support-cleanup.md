# EPIC-012 — Test Support Ownership, Architecture Tests, and datp.analyses Decision

## Metadata

- Status: GROUP_ONLY
- Phase: Phase E
- Parent epic: none
- Priority: P2
- Scientific-contract sensitivity: Medium
- Artifact and serialization sensitivity: Low
- Public-interface sensitivity: Medium

## Purpose

This parent preserves the original master-backlog planning theme for test support ownership, architecture tests, and datp.analyses decision. It groups child tickets but is not itself executable.

## Why This Is Not Executable Directly

The original parent combined multiple independently verifiable ownership, compatibility, validation, artifact, public-interface, or scientific boundaries. Executing it directly would force an implementation agent to make unrelated design decisions in one change and would make rollback/audit attribution unclear.

## Child Tickets

- TKT-066: Testsupport Fixture Taxonomy. Purpose: Classify reusable testsupport fixtures versus intentionally local scientific edge-case fixtures. Dependency position: depends on TKT-062; blocks TKT-067, TKT-068.
- TKT-067: Runtime Testsupport Import Prohibition. Purpose: Ensure production runtime modules do not import datp.testsupport except explicitly test-only smoke-fixture paths if approved. Dependency position: depends on TKT-066; blocks TKT-068.
- TKT-068: Architecture Test Semantic Hardening. Purpose: Update architecture tests to assert semantic ownership and dependency rules after refactors. Dependency position: depends on TKT-066, TKT-045, TKT-065, TKT-062; blocks TKT-070.
- TKT-069: datp.analyses Namespace Decision. Purpose: Decide whether empty datp.analyses is removed or retained as compatibility namespace. Dependency position: depends on TKT-068; blocks TKT-070.
- TKT-070: Stale Naming and Documentation Cleanup within Allowed Scope. Purpose: Clean stale names and docs only where they directly document completed remediation decisions. Dependency position: depends on TKT-068, TKT-069; blocks none.

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

- TKT-066: covers a separately executable part of Test Support Ownership, Architecture Tests, and datp.analyses Decision.
- TKT-067: covers a separately executable part of Test Support Ownership, Architecture Tests, and datp.analyses Decision.
- TKT-068: covers a separately executable part of Test Support Ownership, Architecture Tests, and datp.analyses Decision.
- TKT-069: covers a separately executable part of Test Support Ownership, Architecture Tests, and datp.analyses Decision.
- TKT-070: covers a separately executable part of Test Support Ownership, Architecture Tests, and datp.analyses Decision.

## Execution Restriction

This epic must not be executed directly.


## Identifier History

- Final identifier: EPIC-012
- Legacy identifier(s):
  - TKT-012
- Identifier migration date: 2026-06-18
- Crosswalk: [../TICKET_ID_CROSSWALK.md](../TICKET_ID_CROSSWALK.md)

## Execution Record

Reserved for the execution agent.

- Group status:
- Child completion summary:
- Remaining risks:
