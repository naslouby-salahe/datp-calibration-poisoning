# ticket-progress-skill

## Purpose

Track what is done, what is missing, what is blocked, and what must happen next.

## Required Files

**CP2 (active):**
1. `docs/tickets/_ai_tracking/progress/CP2_PROGRESS.md`
2. `docs/tickets/TICKET_INDEX.md`
3. `docs/tickets/_ai_tracking/decisions/CP2_DECISION_LOG.md`
4. `docs/tickets/_ai_tracking/paper_notes/CP2_PAPER_NOTES_CONSOLIDATED.md`

**DATP journal (if that work resumes):**
1. `docs/tickets/ticket_progress.md`
2. `docs/tickets/ticket_inventory.md`
3. `docs/tickets/human_interventions.md`

## Before Starting a Ticket

The executing agent must:

1. Open `docs/tickets/_ai_tracking/progress/CP2_PROGRESS.md`.
2. Open `docs/tickets/TICKET_INDEX.md`.
3. Open the requested ticket from `docs/tickets/<phase>/CP2-T*.md`.
4. Check all previous tickets.
5. Confirm every previous ticket is `DONE`, `SKIPPED_WITH_REASON`, or correctly blocked.
6. If a previous ticket is incomplete, stop and return to that ticket first.
7. Record this decision in `ticket_progress.md`.

## During a Ticket

Update `CP2_PROGRESS.md` with:

1. Ticket started
2. Files inspected
3. Existing code reused
4. Refactors performed
5. Tests adapted
6. Tests added
7. Tests deleted
8. Commands run
9. Failures found
10. Current status

## After a Ticket

Update:

1. The ticket file status.
2. `docs/tickets/_ai_tracking/progress/CP2_PROGRESS.md`.
3. `docs/tickets/_ai_tracking/decisions/CP2_DECISION_LOG.md` if a decision was made.
4. `docs/tickets/_ai_tracking/paper_notes/CP2_PAPER_NOTES_CONSOLIDATED.md` if the ticket affects claims.

## Required Status Values

Use only:

1. `NOT_STARTED`
2. `IN_PROGRESS`
3. `BLOCKED_HUMAN`
4. `BLOCKED_TECHNICAL`
5. `BLOCKED_SCIENTIFIC`
6. `READY_FOR_REVIEW`
7. `DONE`
8. `SKIPPED_WITH_REASON`

## Repair Tickets

The ticket system may become less central after the main implementation is complete.

However, new tickets may still be created by:

1. `experiment-runner-agent`
2. `results-audit-agent`
3. `reviewer-agent`
4. `drift-enforcer-agent`

Repair tickets must use the next available ticket number and must be added to:

1. `ticket_inventory.md`
2. `ticket_progress.md`

## Required Output

Whenever progress changes, record:

1. Date/time if available
2. Ticket ID
3. Old status
4. New status
5. Reason
6. Next action