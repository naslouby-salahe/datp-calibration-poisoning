# ticket-audit-skill

## Purpose

Audit the generated tickets to ensure nothing is missing, duplicated, unsafe, or vague.

## Audit Passes

### Pass 1 — Plan Coverage

Check that every actionable item from:

1. `PRE_CODING_PLAN.md`
2. `CODING_PLAN.md`
3. `EXPERIMENT_PLAN.md`
4. `POST_EXPERIMENT_PLAN.md`

is represented in the ticket system.

### Pass 2 — Codebase Grounding

Check that every ticket references actual existing code, tests, configs, commands, or artifacts.

Flag any ticket that tells the implementation agent to invent structure without inspecting the current code.

### Pass 3 — Dependency Coverage

Check that:

1. Dependencies are explicit.
2. Previous-ticket ordering is clear.
3. Human-blocked work is not executable.
4. Dataset work is blocked until datasets exist.
5. Experiment work is blocked until tests and gates pass.
6. Paper work is blocked until result freeze.

### Pass 4 — Refactor and Clean-Code Coverage

Check that every implementation ticket asks:

1. Does this already exist?
2. Should this be an enum?
3. Should this be a constant?
4. Should this be a config value?
5. Should this be a schema?
6. Can this reuse existing code?
7. Can this remove duplication?
8. Can this be shorter and clearer?
9. Can tests be refactored?
10. Can obsolete tests be deleted?

### Pass 5 — Test Coverage

Check that every ticket includes:

1. Unit tests
2. Integration tests where needed
3. Failure cases
4. Missing-artifact cases
5. Invalid-config cases
6. Weird edge cases
7. Scientific-invariant tests
8. Existing-test adaptation
9. Obsolete-test deletion when needed
10. Practical command strategy

### Pass 6 — Human Intervention

Check that every required user action is listed in `human_interventions.md`.

No hidden human action is allowed.

### Pass 7 — Reviewer Attack

Attack the tickets as if trying to reject the project.

Flag:

1. Missing prerequisites
2. Hidden scientific decisions
3. Weak tests
4. Duplicate work
5. Artifact ambiguity
6. Dataset ambiguity
7. Scope drift
8. Unbounded compute
9. Vague acceptance criteria
10. Missing stop conditions

## Required Output

The audit must update:

1. `docs/tickets/ticket_inventory.md`
2. `docs/tickets/ticket_progress.md`
3. `docs/tickets/human_interventions.md`
4. Any affected `TXX.md` files

## Pass Criteria

The ticket system passes only when:

1. No active plan item is unmapped.
2. No ticket is vague.
3. No required human action is hidden.
4. No blocked work appears executable.
5. No experiment can start before tests and gates.
6. No paper update can start before result freeze.
7. No ticket bypasses refactoring.
8. No ticket bypasses tests.