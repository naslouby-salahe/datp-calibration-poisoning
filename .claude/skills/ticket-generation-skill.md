# ticket-generation-skill

## Purpose

Generate complete implementation tickets from the four active journal plans and the actual codebase.

## Required Sources

1. `docs/journal/PRE_CODING_PLAN.md`
2. `docs/journal/CODING_PLAN.md`
3. `docs/journal/EXPERIMENT_PLAN.md`
4. `docs/journal/POST_EXPERIMENT_PLAN.md`
5. `CLAUDE.md`
6. Existing source code
7. Existing tests
8. Existing configs
9. Existing scripts
10. Existing artifacts when relevant

## Ticket Naming

Use:

- `docs/tickets/T01.md`
- `docs/tickets/T02.md`
- `docs/tickets/T03.md`

Continue sequentially.

Do not skip numbers unless a ticket is intentionally removed and recorded in `ticket_inventory.md`.

## Ticket Template

Each ticket must contain:

1. Ticket ID
2. Title
3. Status
4. Phase
5. Source plan references
6. Goal
7. Why this exists
8. Scope
9. Out of scope
10. Human intervention required
11. Dependencies
12. Previous-ticket check
13. Existing code to inspect first
14. Existing tests to inspect first
15. Files likely touched
16. Implementation requirements
17. Refactoring requirements
18. Schema, enum, constant, and config checks
19. Test requirements
20. Commands to run
21. Full-suite trigger condition
22. Acceptance criteria
23. Stop conditions
24. Implementation notes

## Mandatory Ticket Rules

1. Do not create implementation tickets without reading existing code.
2. Do not tell agents to create new code before checking existing ownership.
3. Every ticket must include refactoring requirements.
4. Every ticket must include test requirements.
5. Every ticket must include stop conditions.
6. Every ticket must include human-intervention status.
7. Every ticket must include previous-ticket check.
8. Every ticket must preserve scientific invariants.
9. Every ticket must avoid unnecessary backward compatibility.
10. Every ticket must prefer clean greenfield implementation where scientifically safe.

## Required Output Files

The ticket generation process must create:

1. `docs/tickets/ticket_inventory.md`
2. `docs/tickets/ticket_progress.md`
3. `docs/tickets/human_interventions.md`
4. One `TXX.md` file per ticket

## Completion Rule

Ticket generation is not complete until:

1. Every active plan item is mapped.
2. Every code area is inspected.
3. Every dependency is recorded.
4. Every human intervention is listed.
5. Every ticket has tests.
6. Every ticket has refactoring requirements.
7. The ticket inventory is complete.
8. The ticket progress file is initialized.
9. The audit skill passes.