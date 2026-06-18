# EPIC-010 — CP2 Policy Dispatch and Metric Ownership Boundary

## Metadata

- Status: GROUP_ONLY
- Phase: Phase C
- Parent epic: none
- Priority: P0
- Scientific-contract sensitivity: High
- Artifact and serialization sensitivity: High
- Public-interface sensitivity: High

## Purpose

This parent preserves the original master-backlog planning theme for cp2 policy dispatch and metric ownership boundary. It groups child tickets but is not itself executable.

## Why This Is Not Executable Directly

The original parent combined multiple independently verifiable ownership, compatibility, validation, artifact, public-interface, or scientific boundaries. Executing it directly would force an implementation agent to make unrelated design decisions in one change and would make rollback/audit attribution unclear.

## Child Tickets

- TKT-048: Canonical Typed Policy Dispatch Entry Point. Purpose: Confirm or establish one CP2 policy dispatcher that routes typed policies to separate implementations. Dependency position: depends on TKT-011, TKT-019; blocks TKT-050, TKT-049, TKT-051, TKT-063.
- TKT-050: B3 Rejection Enforcement Boundary. Purpose: Ensure B3 cannot enter CP2 default policy execution at config, matrix, CLI, or dispatch boundaries. Dependency position: depends on TKT-048, TKT-003; blocks TKT-063.
- TKT-049: B1 and B2 Recompute Boundary. Purpose: Preserve B1 global and B2 personalized recomputation semantics behind dispatcher. Dependency position: depends on TKT-048; blocks TKT-053.
- TKT-051: B4 Dispatch and Typed Config Flow. Purpose: Preserve B4 cluster/effective threshold/decomposition behavior behind dispatcher using typed config. Dependency position: depends on TKT-048, TKT-019, TKT-024; blocks TKT-053.
- TKT-053: Generic Metric Delegation and CP2 Paired Metric Ownership. Purpose: Separate generic binary metric formulas from CP2 paired attack metrics. Dependency position: depends on TKT-049, TKT-051, TKT-052; blocks TKT-055, TKT-062.
- TKT-055: Mu Flag AUROC and Fleet Metric Serialization Locks. Purpose: Lock mu_flag threshold ownership, AUROC invariance, fleet metrics, and serialization mapping. Dependency position: depends on TKT-053, TKT-006; blocks TKT-031, TKT-065.

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

- TKT-048: covers a separately executable part of CP2 Policy Dispatch and Metric Ownership Boundary.
- TKT-050: covers a separately executable part of CP2 Policy Dispatch and Metric Ownership Boundary.
- TKT-049: covers a separately executable part of CP2 Policy Dispatch and Metric Ownership Boundary.
- TKT-051: covers a separately executable part of CP2 Policy Dispatch and Metric Ownership Boundary.
- TKT-053: covers a separately executable part of CP2 Policy Dispatch and Metric Ownership Boundary.
- TKT-055: covers a separately executable part of CP2 Policy Dispatch and Metric Ownership Boundary.

## Execution Restriction

This epic must not be executed directly.


## Identifier History

- Final identifier: EPIC-010
- Legacy identifier(s):
  - TKT-010
- Identifier migration date: 2026-06-18
- Crosswalk: [../TICKET_ID_CROSSWALK.md](../TICKET_ID_CROSSWALK.md)

## Execution Record

Reserved for the execution agent.

- Group status:
- Child completion summary:
- Remaining risks:
