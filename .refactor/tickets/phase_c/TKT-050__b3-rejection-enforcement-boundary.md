# TKT-050 — B3 Rejection Enforcement Boundary

## Metadata

- Status: NEEDS_VERIFICATION
- Type: implementation
- Phase: Phase C
- Parent epic: EPIC-010
- Priority: P0
- Dependencies: TKT-048, TKT-003
- Blocks: TKT-063
- Scientific-contract sensitivity: High
- Artifact and serialization sensitivity: Low
- Public-interface sensitivity: High
- Estimated change boundary: execution-time verification required; see Expected Files and Surfaces.
- Evidence classification: CONFIRMED_SOURCE_EVIDENCE; INVENTORY_SUPPORTED_REQUIRES_EXECUTION_VERIFICATION

## Why This Is a Separate Ticket

Ensure B3 cannot enter CP2 default policy execution at config, matrix, CLI, or dispatch boundaries. It can be implemented, tested, audited, rolled back, deferred, or rejected without completing all sibling work under TKT-010. Its primary ownership boundary is narrower than the parent epic: b3 rejection enforcement boundary.

## Problem Statement

B3 (family-mean threshold) is excluded from the CP2 default policy matrix by scientific protocol. However, the codebase has multiple surfaces where B3 could still enter CP2 execution:

1. `src/datp/core/enums.py` — `Baseline.B3_FAMILY = "b3"` is still a member of `Baseline` and `ThresholdSource.B3_FAMILY = "b3"` maps to it. The `CONTROLLED_BASELINES` tuple includes B3 at position index 2.
2. `src/datp/thresholding/thresholds.py` line 90 — still imports `from datp.thresholding.strategies import b3_family as b3_mod` in the dispatch function.
3. `src/datp/thresholding/strategies/b3_family.py` — full implementation file still exists in the package, importable through `thresholds.py` dispatch.
4. `src/datp/validation/_client_pipeline.py` — `_emit_b3_dispersion_warnings()` and `validation/enums.py` warning code `B3_TAXONOMY_TOO_COARSE` still reference B3 as a valid thresholding path in validation.
5. `src/datp/conf/config.yaml` — `quality_gates.b3_dispersion_threshold: 0.25` and StyleConfig baseline_colors/labels include B3 `"#2ca02c"` and `"B3 (Family-Mean)"`.
6. `src/datp/checkpointing/invariants.py` — enforces B3 suppression outside Regime A but does not enforce CP2-level exclusion.
7. `src/datp/app/cli/checkpoint_protocol.py` — iterates `Baseline.B1, B2, B3, B4` for the checkpoint-protocol flow, meaning B3 is still a first-class baseline in the CLI-level experiment setup.

`ThresholdPolicy` in `poison_enums.py` correctly excludes B3. `guardrails.py` has `assert_policy_not_b3()`. The CP2 experiment runner and matrix enumeration correctly avoid B3. But the generic DATP infrastructure still treats B3 as a valid baseline, creating a contamination risk if a CLI command, configuration path, or validation flow accidentally routes B3 into a CP2 experiment.

Realistic failure scenario: a CLI command `datp poison run-bounded-sweep` is refactored. The refactor adds a B3 path from a generic matrix enumeration that includes B3 (because `Baseline.B3` is still in `CONTROLLED_BASELINES`). The matrix cell runs B3 thresholding, which succeeds (the module still exists), produces metrics, and those metrics enter CP2 comparison tables. The paper would then wrongly compare B3 against B1/B2/B4, violating the CP2 protocol.

## Confirmed Evidence

- `src/datp/core/poison_enums.py` line 33: `class ThresholdPolicy(enum.StrEnum):` — only B1_GLOBAL, B2_PERSONALIZED, B4_CLUSTER are members. B3 is explicitly excluded by protocol (line comment).
- `src/datp/attacks/guardrails.py` function `assert_policy_not_b3()`: raises `ValueError` if a raw string `"b3"` or `Baseline.B3` enters a CP2 policy boundary.
- `src/datp/core/enums.py` line 105: `Baseline.B3_FAMILY = "b3"` — still a member of Baseline enum. Line 118: `CONTROLLED_BASELINES = (Baseline.B0, Baseline.B1, Baseline.B2, Baseline.B3, Baseline.B4)`. Line 244: `BASELINE_THRESHOLD_SOURCE` maps `Baseline.B3 → ThresholdSource.B3_FAMILY`.
- `src/datp/thresholding/thresholds.py` line 86-91: lazy import `from datp.thresholding.strategies import b3_family as b3_mod` — B3 module is still importable through the canonical threshold dispatch.
- `src/datp/thresholding/strategies/b3_family.py`: 85 lines — full implementation of `compute_thresholds(b3_family)` returning `B3FamilyInfo`, `B3Metadata`. Module string: `_MODULE = "thresholding.b3_family"`.
- `src/datp/core/types.py` lines 50-62: `B3FamilyInfo` and `B3Metadata` dataclasses — still defined, importable, and used by `thresholding/eligibility.py`.
- `src/datp/thresholding/eligibility.py` line 63: `b3_metadata: B3Metadata | None` parameter in `build_threshold_result()` — still flows through generic threshold result.
- `src/datp/config/models.py` line 198: `b3_dispersion_threshold: float` in `QualityGateConfig` — still configurable via YAML.
- `src/datp/conf/config.yaml` line 67: `b3_dispersion_threshold: 0.25` — active YAML value.
- `src/datp/validation/_client_pipeline.py` line 176: `_emit_b3_dispersion_warnings()` — still called during full validation pipeline.
- `src/datp/app/cli/checkpoint_protocol.py`: iterates `Baseline.B1, B2, B3, B4` — B3 still first-class in CLI setup.
- `tests/unit/core/test_enums.py` lines 40, 104-106, 117-118, 124, 167-168, 203, 207, 219, 221, 229, 231, 233, 235, 261, 264: multiple tests reference B3 as valid Baseline member — these must be preserved for the DATP generic baseline infrastructure, not removed for CP2.
- `tests/unit/thresholding/strategies/test_threshold_strategies.py`: likely tests B3 family threshold path — verify whether these exist and what they test.
- `tests/unit/checkpointing/test_invariants_status.py` line 112: `test_b3_suppression_outside_regime_a_fails` — B3 suppression test exists for Regime A constraint, not CP2 constraint.

## Unresolved Evidence Requiring Execution-Time Verification

- Exact module or surface to inspect: all source and test locations named in Confirmed Evidence, plus direct callers discovered by `rg`.
- Exact condition that authorizes a change: source inspection proves two active owners, duplicate runtime behavior, missing validation, missing compatibility handling, or a confirmed test gap for this ticket's stated boundary.
- Exact condition that closes the ticket with no code change: source inspection proves the current implementation already has one owner, one validation path, and adequate tests for the protected contracts.
- Exact condition that requires blocking, rejection, or ticket-authoring revision: the source contradicts the parent epic, requires artifact migration, requires public interface removal, or would authorize work outside calibration-channel CP2 scope.
- Execution-time verification required: inspect the module responsible for b3 rejection enforcement boundary; identify the exact constructor, call site, serializer, validator, or CLI route; confirm whether the concern exists.

## Failure Mechanism

B3 leakage changes CP2 policy matrix and claims. This mechanism is limited to the evidence above. Do not infer broader cleanup or unrelated package rewrites from this ticket.

## Target Outcome

The repository has one explicit, documented, and tested owner for b3 rejection enforcement boundary. Existing scientific behavior, artifact paths, serialized values, and public interfaces are preserved unless this ticket explicitly authorizes an additive compatibility-safe migration.

## Scope

### In Scope

- Verify that every entry point where CP2 experiments can be initiated (CLI commands, sweep runners, smoke harness, bounded-sweep orchestrator) has a B3 rejection gate before B3 can reach threshold dispatch, metric computation, or manifest assembly.
- Verify that the existing `assert_policy_not_b3()` in `guardrails.py` is actually called at the correct boundary (not just defined but unused).
- If any CP2 entry point lacks B3 rejection, add a guard at the narrowest boundary (e.g., matrix enumeration, sweep cell runner, CLI parameter validation).
- Do NOT remove `b3_family.py`, `Baseline.B3`, `ThresholdSource.B3_FAMILY`, `B3FamilyInfo`, `B3Metadata`, `b3_dispersion_threshold`, or B3 references in generic DATP infrastructure — those are part of the broader DATP baseline ladder and are intentionally separate from CP2.
- Add tests proving B3 cannot reach CP2 threshold dispatch, metric computation, manifest writing, or result reporting.
- Add architecture test that CP2 policy dispatch cannot import or call the B3 threshold strategy.
- Verify `config.yaml` StyleConfig B3 references are only used by the generic DATP reporting path, not the CP2 reporting path.

### Explicitly Out of Scope

- Deleting or quarantining `b3_family.py` — that module supports the generic DATP Baseline ladder (B1/B2/B3/B4/B0).
- Removing `Baseline.B3` from the `Baseline` enum — B3 is a valid baseline for the DATP journal and the generic thresholding infrastructure.
- Removing `b3_dispersion_threshold` from `config/models.py` or `config.yaml` — those support the generic validation pipeline.
- Production changes unrelated to CP2 B3 boundary enforcement.
- Training-data, model-update, aggregation, or test-data poisoning.
- New FL algorithms, model architectures, datasets, deployment work, hardware work, privacy mechanisms, or broad adversarial workflows.
- Broad package rewrites, generic utility dumping grounds, or collapsing B1/B2/B4 semantics.

## Protected Contracts

- SC-POLICY: Default CP2 policies are B1_GLOBAL, B2_PERSONALIZED, B4_CLUSTER; B3 is excluded from default CP2 matrix. Status: validated.
- SC-CP2-SCOPE: Calibration-channel-only CP2 scope; no training-data, model-update, aggregation, test-data, backdoor, privacy, deployment, hardware, or new-dataset expansion. Status: validated.
- CLI-PUBLIC: CLI command names, option names, exit-code behavior, and user-facing routing remain compatible unless explicitly migrated. Status: preserved unchanged unless an explicitly additive compatibility path is required.

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
- Intended canonical owner: the narrow package or module responsible for b3 rejection enforcement boundary, selected only after verification.
- Consumers that must migrate: direct callers, serializers, validators, tests, CLI routes, and reporting/validation consumers discovered by `rg`.
- Intentional separations that must remain: generic DATP infrastructure remains separate from CP2-specific scientific behavior; boundary projections remain separate from semantic owners.
- Compatibility aliases or transitional shims, if any: allowed only when preserving an existing public import, CLI, JSON, CSV, path, marker, or YAML contract.
- Deletion conditions for stale ownership: all consumers migrate, compatibility tests pass, and the stale owner is proven not to be a public contract.

## Detailed Implementation Plan

1. Action: trace every CP2 experiment entry point — `poison.py` CLI (preview, dry-run, smoke, run-bounded-sweep), `bounded_sweep_run.py` orchestration, `cell_runner.py` cell dispatch, `bounded_sweep_matrix.py` matrix enumeration. Target: verify each has a B3 rejection gate before threshold dispatch. Reason: B3 entering at any point would contaminate results. Compatibility: no CLI, YAML, or path changes.
2. Action: verify `assert_policy_not_b3()` in `guardrails.py` is called in `cell_runner.py`, `bounded_sweep_cell.py`, and `bounded_sweep_run.py` before any threshold recomputation. Target: guardrails module. Reason: if the guard exists but is not called from CP2 paths, it provides no protection. Validation: grep for calls to `assert_policy_not_b3` in the CP2 call stack.
3. Action: if any CP2 entry point lacks a B3 guard, add one at the narrowest boundary. Target: module where the gap is found. Reason: defense-in-depth, not cosmetic. Compatibility: no public interface changes.
4. Action: verify `config.yaml` StyleConfig B3 color/label `"#2ca02c"` / `"B3 (Family-Mean)"` are consumed only by generic DATP reporting, not CP2 reporting. Target: `reporting/` module. Reason: CP2 tables and figures must never display B3. Validation: trace StyleConfig.baseline_colors consumption.
5. Action: add architecture test that `datp.attacks` policy code cannot import from `datp.thresholding.strategies.b3_family`. Target: architecture test module. Reason: prevent accidental B3 dispatch import from CP2 code paths. Validation: test imports CP2 modules and asserts b3_family is not in the import graph.
6. Action: add integration test that a B3 policy parameter in CLI/CLI preview produces an error. Target: CLI test. Reason: prevent B3 from reaching CP2 dispatch via CLI parameter. Validation: CLI test passes with B3 rejected.
7. Action: add unit test that B3 is not in `CP2_SWEEP_FRACTIONS`, `DEFAULT_POLICIES`, `BOUNDED_SWEEP_OBJECTIVES`, or any CP2 matrix tuple. Target: test_poison_enums.py. Reason: matrix tuple composition is a second line of defense. Validation: assertion passes.

## Expected Files and Surfaces

- Source modules (confirmed): `src/datp/core/poison_enums.py`, `src/datp/attacks/guardrails.py`, `src/datp/attacks/cell_runner.py`, `src/datp/attacks/bounded_sweep_cell.py`, `src/datp/attacks/bounded_sweep_run.py`, `src/datp/attacks/bounded_sweep_matrix.py`, `src/datp/app/cli/poison.py`.
- Source modules (CP2 guard insertion likely): `src/datp/attacks/cell_runner.py` (the policy dispatch entry point), `src/datp/attacks/bounded_sweep_matrix.py` (matrix enumeration).
- Source modules (inspect only, no change): `src/datp/thresholding/thresholds.py`, `src/datp/thresholding/strategies/b3_family.py`, `src/datp/core/enums.py`, `src/datp/core/types.py`, `src/datp/config/models.py`, `src/datp/conf/config.yaml`, `src/datp/validation/_client_pipeline.py`, `src/datp/validation/enums.py`, `src/datp/checkpointing/invariants.py`, `src/datp/app/cli/checkpoint_protocol.py`, `src/datp/reporting/engine.py`, `src/datp/reporting/constants.py`.
- Tests (confirmed): `tests/unit/attacks/test_guardrails.py`, `tests/unit/attacks/test_poison_enums.py`, `tests/unit/app/cli/test_poison_cli.py`.
- Tests (likely new or updated): architecture test for CP2→B3 import prohibition; CLI integration test for B3 policy rejection.
- Configuration: `src/datp/conf/config.yaml` (inspect StyleConfig B3 references only; no changes).
- CLI surfaces: `poison.py` preview, dry-run, smoke, run-bounded-sweep — confirm B3 rejection at parameter validation.
- Documentation: update if CP2 README or CLI help text mentions B3 as a valid CP2 option.
- Public imports: none affected — B3 types remain in the generic domain.

## Compatibility and Migration Plan

- Imports: preserve public imports; add aliases only with documented removal conditions.
- Aliases: not applicable unless needed for public compatibility.
- CLI behavior: preserve unchanged and test command compatibility.
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

- unit tests: verify b3 rejection enforcement boundary without changing unrelated behavior.
- architecture/import tests: verify b3 rejection enforcement boundary without changing unrelated behavior.
- CLI tests: verify b3 rejection enforcement boundary without changing unrelated behavior.
- policy semantic tests: verify b3 rejection enforcement boundary without changing unrelated behavior.

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
- Exactly one canonical owner or one documented intentional separation exists for b3 rejection enforcement boundary.
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

- Update only terminology directly tied to b3 rejection enforcement boundary.
- Preserve CP2 terminology: calibration-channel poisoning, clean-versus-poisoned pairing, B1/B2/B4 distinct policies, B3 exclusion, effective B4 thresholds, victim-local benign calibration reservoir.
- Do not add broad cleanup wording, unsupported scope, or generic names that hide scientific meaning.

## Related Tickets

- Prerequisites: TKT-048, TKT-003.
- Successors: TKT-063.
- Sibling tickets: TKT-048, TKT-049, TKT-051, TKT-053, TKT-055.
- Potential overlap risks: work under TKT-010 may touch nearby surfaces; use the parent epic child map before editing.
- Ticket groups that must not be executed concurrently: any sibling or successor that touches the same source file, serializer, CLI route, artifact path, or validation boundary.


## Identifier History

- Final identifier: TKT-050
- Legacy identifier(s):
  - TKT-010-02
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
