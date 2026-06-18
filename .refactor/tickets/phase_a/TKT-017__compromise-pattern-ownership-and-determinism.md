# TKT-017 — Compromise Pattern Ownership and Determinism

## Metadata

- Status: NEEDS_VERIFICATION
- Type: implementation
- Phase: Phase A
- Parent epic: EPIC-013
- Priority: P1
- Dependencies: TKT-008
- Blocks: TKT-063
- Scientific-contract sensitivity: High
- Artifact and serialization sensitivity: Low
- Public-interface sensitivity: Low
- Estimated change boundary: src/datp/attacks/compromise_patterns.py; tests/unit/attacks/test_compromise_patterns.py
- Evidence classification: CONFIRMED_SOURCE_EVIDENCE

## Why This Is a Separate Ticket

Multi-client compromise pattern selection is a distinct scientific concern with its own SeedSequence derivation. It is independently testable, independently reversible, and does not share implementation dependencies with reservoir, score, manifest, or inference modules.

## Problem Statement

`src/datp/attacks/compromise_patterns.py` implements multi-client compromise pattern selection (pairs, triples) using `_pattern_rng()` with `numpy.random.SeedSequence`. The module lacks explicit ownership documentation, deterministic-lock tests for pattern reproducibility, and validation for edge cases (requested count > available clients, empty client list, single-client degenerate pattern requests).

Realistic failure scenario: a refactor of seed derivation in `core/seed_sequence.py` changes the compromise pattern RNG sequence, multiclient results become unreproducible across runs, and the change is not detected because no regression test locks the exact pattern output for a known seed/client-list combination.

## Confirmed Evidence

- Source location: `src/datp/attacks/compromise_patterns.py` — module-level docstring, `_pattern_rng()`, `select_compromise_patterns()`, `select_pairs()`, `select_triples()`, pattern dispatch to `itertools.combinations`.
- `_pattern_rng()` uses `np.random.SeedSequence([COMPROMISE_PATTERN_SEED, ...])` — correct pattern.
- Tests: `tests/unit/attacks/test_compromise_patterns.py` — exists but coverage scope is execution-time verification required.
- No explicit test for exact output reproducibility with known seeds and client lists.
- No explicit test for degenerate edge cases (empty list, count=0, count > available).

## Unresolved Evidence Requiring Execution-Time Verification

- Exact module or surface to inspect: `compromise_patterns.py` — verify whether `select_pairs` and `select_triples` produce deterministic output for fixed inputs.
- Exact condition that authorizes a change: current tests lack output-reproducibility assertions, edge-case handling, or seed-derivation documentation.
- Exact condition that closes the ticket with no code change: tests already lock all pattern outputs deterministically and cover all edge cases.
- Exact condition that requires blocking, rejection, or ticket-authoring revision: the module uses integer seed addition instead of SeedSequence, or imports from testsupport.

## Failure Mechanism

- Protocol drift: compromise pattern seed derivation changes silently, multi-client runs become unreproducible.
- Wrong result grouping: pattern selection nondeterminism breaks clean-versus-poisoned pairing for multi-client runs.
- Silent test pass: tests pass despite nondeterministic patterns because they only check structural properties.

## Target Outcome

Compromise pattern selection has a documented seed derivation, deterministic output for fixed inputs, edge-case validation, and reproducibility tests. No integer seed addition. No testsupport imports from production code.

## Scope

### In Scope

- Inspect `compromise_patterns.py` for seed derivation correctness.
- Add deterministic reproducibility tests for each pattern type (single, pairs, triples) with known seed and client list.
- Add edge-case tests (empty list, count=0, count > available, single-client degenerate).
- Add architecture test that the module does not import from testsupport, CLI, or reporting.
- Document the seed derivation scheme in a module-level docstring if missing.

### Explicitly Out of Scope

- Changes to reservoir, injector, score, manifest, or inference modules.
- Generalization of pattern selection into a generic utility.
- Changes to `run_sweep_cell`, `cell_runner`, or orchestration.
- Output-root renaming, artifact migration, or CLI compatibility changes.

## Protected Contracts

- SC-SEEDS: Training, poisoning, analysis, compromise-pattern, client, and scope seeds remain semantically distinct; SeedSequence entropy is preserved. Status: validated.
- SC-PAIRING: Clean-versus-poisoned paired comparison; poisoning is the only stochastic difference. Status: validated.
- PKG-BOUNDARY: Package dependency direction remains coherent. Status: preserved unchanged.

## Scientific and Protocol Preservation

- Compromise pattern seed (400) remains semantically distinct from training, poisoning, and analysis seeds.
- SeedSequence derivation remains the only entropy source for pattern selection.
- No integer seed addition introduced.

## Ownership Decision

- Current owner: `datp.attacks.compromise_patterns` (one module, one purpose).
- Competing or duplicate owner: none detected.
- Intended canonical owner: `datp.attacks.compromise_patterns`.
- Consumers that must migrate: `cell_runner.py` and `bounded_sweep_run.py` callers — verify at execution time.
- Intentional separations that must remain: pattern selection is distinct from victim identification (victim plan is a separate concern in TKT-020).

## Detailed Implementation Plan

1. Inspect `compromise_patterns.py`: confirm seed derivation uses `SeedSequence`, no integer addition, no testsupport import.
2. Record current public interface (functions, signature, return types).
3. Add deterministic output tests: `test_compromise_patterns_reproducibility(known_seed, client_list)` that asserts exact pattern for each `select_pairs`, `select_triples`, and the combined dispatcher.
4. Add edge-case tests: empty list, count=0, count > len(clients), single-client pattern.
5. Add architecture test: verify no runtime import from testsupport, CLI, or reporting packages.
6. Document seed derivation and pattern semantics in module docstring.

## Expected Files and Surfaces

- Source modules: `src/datp/attacks/compromise_patterns.py` (confirmed).
- Tests: `tests/unit/attacks/test_compromise_patterns.py` (confirmed).
- Architecture tests: likely `tests/unit/core/test_model_boundary_architecture.py` or a new focused architecture test file.

## Compatibility and Migration Plan

- Imports: preserve current public names; no aliases needed.
- CLI behavior: not applicable (no CLI surface).
- YAML input: not applicable.
- Enum serialization: not applicable.
- Paths: not applicable.
- Resume: not applicable.

## Validation Plan

- unit tests: deterministic reproducibility for known seed/client-list combinations; edge-case rejection.
- architecture/import tests: no testsupport, CLI, or reporting imports.

## Required Post-Ticket Audits

### Audit 1 — Implementation and Contract Correctness

- Confirm seed derivation uses `SeedSequence` (no integer addition).
- Confirm deterministic reproducibility tests lock exact pattern output.

### Audit 2 — Cross-Package and Protocol Safety

- Confirm no testsupport imports from production code.
- Confirm seed semantics remain distinct.

### Audit 3 — Tests, Artifacts, and Documentation Integrity

- Confirm edge-case tests pass.
- Confirm docstring documents seed derivation.

## Acceptance Criteria

- Deterministic reproducibility test locks exact pattern for known seed and client list.
- Edge-case tests pass for empty list, count=0, count > available.
- Architecture test verifies no testsupport import.
- Module docstring documents seed derivation.
- All existing tests continue to pass.

## Rollback and Failure Boundaries

- Rollback trigger: any existing test fails after changes.
- Protocol-drift trigger: seed derivation changes to integer addition or loses SeedSequence.
- Compatibility-failure trigger: public function signature changes without migration.

## Related Tickets

- Prerequisites: TKT-008 (seed pool ownership and typed propagation).
- Successors: TKT-063 (CLI to orchestration delegation — multi-client run depends on stable patterns).
- Sibling tickets: TKT-056, TKT-057, TKT-058, TKT-013.
- Potential overlap risks: TKT-020 (pair grouping and victim plan identity validation) — pattern selection is input to victim plan, not victim plan itself.


## Identifier History

- Final identifier: TKT-017
- Legacy identifier(s):
  - TKT-013-01
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
