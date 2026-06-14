# ticket-completion-audit-skill

## Purpose

Verify whether one or more tickets were implemented completely and honestly.

## Required Sources

1. Requested ticket file or files
2. `docs/tickets/ticket_inventory.md`
3. `docs/tickets/ticket_progress.md`
4. `docs/tickets/human_interventions.md`
5. Relevant source code
6. Relevant tests
7. Relevant configs
8. Relevant artifacts or logs when applicable

## Audit Checklist

For each ticket, check:

1. Status accuracy
2. Dependency completion
3. Previous-ticket rule compliance
4. Human-blocker compliance
5. Scope completion
6. Out-of-scope violations
7. Implementation completeness
8. Refactoring completeness
9. Existing-code reuse
10. Enum usage
11. Constant usage
12. Schema or typed-object usage
13. Config discipline
14. Test completeness
15. Obsolete-test cleanup
16. Command execution
17. Artifact validity
18. Scientific invariant preservation
19. Documentation updates if required
20. Acceptance criteria completion

## Refactoring Audit Questions

Ask:

1. Was existing code checked before adding new code?
2. Was duplicate logic avoided?
3. Were repeated literals centralized?
4. Were loose strings replaced with enums where appropriate?
5. Were constants used for stable values?
6. Were schemas or typed objects used instead of dictionaries where appropriate?
7. Were long argument lists avoided?
8. Was obsolete compatibility code removed?
9. Were comments minimized?
10. Is the final code cleaner than before?

## Test Audit Questions

Ask:

1. Were existing tests inspected?
2. Were existing tests adapted where possible?
3. Were new tests added only where needed?
4. Were obsolete tests deleted or rewritten?
5. Are weird cases covered?
6. Are failure cases covered?
7. Are missing-artifact cases covered?
8. Are invalid-config cases covered?
9. Are scientific-invariant violations covered?
10. Are experiment-breaking cases caught before real runs?

## Verdicts

Allowed verdicts:

1. `PASS`
2. `PASS_WITH_MINOR_NOTES`
3. `FAIL_INCOMPLETE`
4. `FAIL_TESTS_MISSING`
5. `FAIL_REFACTOR_MISSING`
6. `FAIL_HUMAN_BLOCKER_BYPASSED`
7. `FAIL_SCIENTIFIC_DRIFT`
8. `FAIL_ARTIFACT_INVALID`
9. `BLOCKED_CANNOT_AUDIT`

## Repair Output

If the ticket fails, produce a repair plan or repair ticket.

A repair ticket must state:

1. Original ticket
2. Exact failed requirements
3. Required implementation fixes
4. Required refactoring fixes
5. Required test fixes
6. Required commands
7. Human intervention if any
8. Acceptance criteria

## Pass Criteria

A ticket passes only if:

1. The implementation satisfies the ticket.
2. Refactoring was done.
3. Tests were handled properly.
4. Commands were run or correctly skipped.
5. No human blocker was bypassed.
6. No scientific invariant was violated.
7. Progress files are accurate.
8. Acceptance criteria are satisfied.