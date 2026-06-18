# TKT-068 — Architecture Test Semantic Hardening

## Metadata

- Status: NEEDS_VERIFICATION
- Type: test hardening
- Phase: Phase E
- Parent epic: EPIC-012
- Priority: P2
- Dependencies: TKT-066, TKT-045, TKT-065, TKT-062
- Blocks: TKT-070
- Scientific-contract sensitivity: High
- Artifact and serialization sensitivity: Low
- Public-interface sensitivity: Medium
- Estimated change boundary: execution-time verification required; see Expected Files and Surfaces.
- Evidence classification: CONFIRMED_SOURCE_EVIDENCE; INVENTORY_SUPPORTED_REQUIRES_EXECUTION_VERIFICATION

## Why This Is a Separate Ticket

Update architecture tests to assert semantic ownership and dependency rules after refactors. It can be implemented, tested, audited, rolled back, deferred, or rejected without completing all sibling work under TKT-012. Its primary ownership boundary is narrower than the parent epic: architecture test semantic hardening.

## Problem Statement

Architecture test hardening must wait for final package and CLI boundaries.

Realistic failure scenario: an execution agent changes this boundary while working on a neighboring concern, the repository still imports and tests superficially pass, but the affected contract no longer matches the CP2 scientific or compatibility record.

## Confirmed Evidence

- Source location: tests/unit/core/test_canonical_ownership.py, test_dataclass_architecture.py, test_model_boundary_architecture.py, and test_no_scientific_policy_leaks.py exist; tests/unit/test_makefile_targets.py inspects CLI command names.
- Symbol, behavior, schema, test, artifact, or import relationship: see the named modules and tests above.
- Observed fact: the repository contains an active implementation or test surface for this concern.
- Relevance to this ticket: the surface is the exact boundary the execution agent must inspect before changing code.

## Unresolved Evidence Requiring Execution-Time Verification

- Exact module or surface to inspect: all source and test locations named in Confirmed Evidence, plus direct callers discovered by `rg`.
- Exact condition that authorizes a change: source inspection proves two active owners, duplicate runtime behavior, missing validation, missing compatibility handling, or a confirmed test gap for this ticket's stated boundary.
- Exact condition that closes the ticket with no code change: source inspection proves the current implementation already has one owner, one validation path, and adequate tests for the protected contracts.
- Exact condition that requires blocking, rejection, or ticket-authoring revision: the source contradicts the parent epic, requires artifact migration, requires public interface removal, or would authorize work outside calibration-channel CP2 scope.
- Execution-time verification required: inspect the module responsible for architecture test semantic hardening; identify the exact constructor, call site, serializer, validator, or CLI route; confirm whether the concern exists.

## Failure Mechanism

Weak architecture tests allow future CP2 leakage and import cycles. This mechanism is limited to the evidence above. Do not infer broader cleanup or unrelated package rewrites from this ticket.

## Target Outcome

The repository has one explicit, documented, and tested owner for architecture test semantic hardening. Existing scientific behavior, artifact paths, serialized values, and public interfaces are preserved unless this ticket explicitly authorizes an additive compatibility-safe migration.

## Scope

### In Scope

- Inspect the confirmed source and test surfaces.
- Make only the minimum source changes required for architecture test semantic hardening if the decision gate authorizes changes.
- Add or update focused tests for the protected contracts listed below.
- Record compatibility decisions in the ticket execution record.

### Explicitly Out of Scope

- Production changes unrelated to architecture test semantic hardening.
- Training-data, model-update, aggregation, or test-data poisoning.
- New FL algorithms, model architectures, datasets, deployment work, hardware work, privacy mechanisms, or broad adversarial workflows.
- Output-root renaming, historical artifact migration, or public-interface removal without a dedicated compatibility migration.
- Broad package rewrites, generic utility dumping grounds, or collapsing B1/B2/B4 semantics.

## Protected Contracts

- PKG-BOUNDARY: Package dependency direction remains coherent; generic packages do not absorb CP2 scientific behavior without explicit justification. Status: validated.
- TST-FIXTURES: Testsupport remains test-only; fixture semantics preserve CP2 scientific edge cases. Status: validated.
- SC-CP2-SCOPE: Calibration-channel-only CP2 scope; no training-data, model-update, aggregation, test-data, backdoor, privacy, deployment, hardware, or new-dataset expansion. Status: validated.

## Scientific and Protocol Preservation

- Calibration-channel-only attack scope is preserved.
- Clean training, scoring, and test behavior is preserved.
- Clean-versus-poisoned comparisons remain paired when this ticket touches identity, seed, score, metric, manifest, or run behavior.
- B1, B2, and B4 remain scientifically distinct where policy behavior is in scope.
- B3 remains excluded from the default CP2 policy matrix where policy behavior is in scope.
- B4 deterministic behavior, effective-threshold semantics, and decomposition semantics remain unchanged where B4 behavior is in scope.
- Reservoirs never use training or test scores where score or reservoir behavior is in scope.
- AUROC uses unchanged test-score inputs where AUROC behavior is in scope.

## Ownership Decision

- Current owner: source inspection required; likely surfaces are named in Confirmed Evidence.
- Competing or duplicate owner: source inspection required; candidate duplicates are named by the parent epic and discovery ledger.
- Intended canonical owner: the narrow package or module responsible for architecture test semantic hardening, selected only after verification.
- Consumers that must migrate: direct callers, serializers, validators, tests, CLI routes, and reporting/validation consumers discovered by `rg`.
- Intentional separations that must remain: generic DATP infrastructure remains separate from CP2-specific scientific behavior; boundary projections remain separate from semantic owners.
- Compatibility aliases or transitional shims, if any: allowed only when preserving an existing public import, CLI, JSON, CSV, path, marker, or YAML contract.
- Deletion conditions for stale ownership: all consumers migrate, compatibility tests pass, and the stale owner is proven not to be a public contract.

## Detailed Implementation Plan

1. Action: inspect confirmed surfaces and direct callers. Target module or boundary: named in Confirmed Evidence. Reason: avoid changing unverified behavior. Compatibility consideration: record all public imports, CLI routes, serialized fields, paths, marker names, and YAML keys before editing. Validation expectation: produce a short source-evidence note in the execution record.
2. Action: classify the current owner and any duplicate owner. Target module or boundary: architecture test semantic hardening. Reason: distinguish intentional boundary projection from accidental duplication. Compatibility consideration: do not merge generic and CP2 concepts by name similarity. Validation expectation: classification matches `TICKET_OWNERSHIP_AND_DUPLICATION_RULES.md`.
3. Action: implement the smallest authorized change or close no-code. Target module or boundary: execution-time verified owner. Reason: keep rollback independent. Compatibility consideration: preserve existing strings, enum values, paths, markers, JSON keys, CSV fields, and CLI behavior unless an additive migration is explicitly included. Validation expectation: focused tests pass.
4. Action: add or update tests. Target module or boundary: existing nearest test module unless a new focused test file is warranted. Reason: lock the repaired behavior. Compatibility consideration: tests must assert behavior, not incidental implementation layout. Validation expectation: failing pre-change or gap-confirming test exists when code changes are made.
5. Action: update only directly relevant documentation or comments. Target module or boundary: local docs or comments touched by the change. Reason: remove stale claims. Compatibility consideration: do not expand CP2 scope. Validation expectation: stale-reference scan is clean for this ticket's terms.

## Expected Files and Surfaces

- Source modules: confirmed surfaces named in Confirmed Evidence.
- Tests: confirmed or likely nearest tests for this package; execution-time verification required for exact files.
- Fixtures: execution-time verification required; preserve fixture semantics.
- Configuration: not applicable unless direct callers reveal config use.
- Manifests: not applicable unless direct callers reveal manifest use.
- Artifacts: not applicable unless artifact paths are direct consumers.
- CLI surfaces: not applicable unless command routes are direct consumers.
- Documentation: update only directly stale terminology created or exposed by this ticket.
- Public imports: execution-time verification required.

## Compatibility and Migration Plan

- Imports: preserve public imports; add aliases only with documented removal conditions.
- Aliases: not applicable unless needed for public compatibility.
- CLI behavior: not applicable.
- YAML input: not applicable.
- Enum serialization: preserve `.value` strings unchanged.
- JSON: not applicable.
- CSV: not applicable.
- Paths: not applicable.
- Marker files: not applicable.
- Lifecycle state: not applicable.
- Artifact readers: preserve current reader compatibility or add explicit additive compatibility handling.
- Artifact writers: preserve atomicity and schema semantics.
- Result loading: preserve current grouping and validation behavior.
- Reporting: not applicable.
- Resume: not applicable.
- Historical fixtures: use if present; otherwise document absence.

## Validation Plan

- unit tests: verify architecture test semantic hardening without changing unrelated behavior.
- architecture/import tests: verify architecture test semantic hardening without changing unrelated behavior.

## Required Post-Ticket Audits

Exactly three audits are required.

### Audit 1 — Implementation and Contract Correctness

- Confirm the implemented or no-code decision matches this ticket and not a sibling ticket.
- Confirm the canonical owner and compatibility aliases are documented.
- Confirm no protected contract listed above changed silently.

### Audit 2 — Cross-Package and Protocol Safety

- Confirm package boundaries, CP2 scope, and generic-versus-CP2 separation remain intact.
- Confirm no B3 leakage, B4 drift, seed drift, score-stage mixing, artifact path drift, or manifest drift was introduced where relevant.
- Confirm downstream consumers either still work unchanged or are migrated through an explicit compatibility path.

### Audit 3 — Tests, Artifacts, and Documentation Integrity

- Confirm focused tests and relevant architecture/import/CLI/artifact/manifest tests pass.
- Confirm malformed, partial, or invalid inputs are rejected where relevant.
- Confirm documentation and naming touched by this ticket are accurate and do not authorize unsupported scope.

## Acceptance Criteria

- Decision gate evidence is recorded.
- Exactly one canonical owner or one documented intentional separation exists for architecture test semantic hardening.
- All protected contracts remain satisfied.
- Focused validation behavior is covered by tests or the execution record explains why no code/test change was required.
- Rollback can be performed without reverting unrelated tickets.

## Rollback and Failure Boundaries

- Rollback trigger: focused tests or compatibility checks fail after the change.
- Protocol-drift trigger: CP2 scope, pairing, B3 exclusion, B4 semantics, seed semantics, reservoir safety, or AUROC invariance changes unexpectedly.
- Compatibility-failure trigger: public imports, CLI routes, YAML keys, JSON keys, CSV fields, artifact paths, marker names, or historical readers break.
- Artifact-migration failure trigger: existing artifacts require migration not explicitly authorized by this ticket.
- Public-interface failure trigger: external command or import behavior changes without alias or migration plan.
- Condition requiring ticket blocking: source evidence requires a design decision outside this ticket's scope.
- Condition requiring ticket-authoring revision: the concern belongs to a different parent epic or needs a new child ticket to remain atomic.

## Documentation and Naming Requirements

- Update only terminology directly tied to architecture test semantic hardening.
- Preserve CP2 terminology: calibration-channel poisoning, clean-versus-poisoned pairing, B1/B2/B4 distinct policies, B3 exclusion, effective B4 thresholds, victim-local benign calibration reservoir.
- Do not add broad cleanup wording, unsupported scope, or generic names that hide scientific meaning.

## Related Tickets

- Prerequisites: TKT-066, TKT-045, TKT-065, TKT-062.
- Successors: TKT-070.
- Sibling tickets: TKT-066, TKT-067, TKT-069, TKT-070.
- Potential overlap risks: work under TKT-012 may touch nearby surfaces; use the parent epic child map before editing.
- Ticket groups that must not be executed concurrently: any sibling or successor that touches the same source file, serializer, CLI route, artifact path, or validation boundary.


## Identifier History

- Final identifier: TKT-068
- Legacy identifier(s):
  - TKT-012-03
- Identifier migration date: 2026-06-18
- Crosswalk: [../TICKET_ID_CROSSWALK.md](../TICKET_ID_CROSSWALK.md)

## Execution Record

Reserved for the execution agent.

- Execution status:
- Actual files changed:
- Tests run:
- Audit evidence:
- Compatibility conclusion:
- Residual risks:
- Resume note:
