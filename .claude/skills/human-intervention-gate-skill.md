# human-intervention-gate-skill

## Purpose

Prevent agents from pretending they can complete tasks that require the user.

## Human Intervention Examples

Human intervention is required for:

1. Downloading unavailable datasets.
2. Placing raw datasets in the correct folder.
3. Providing missing files.
4. Providing credentials or access.
5. Confirming unavailable external decisions.
6. Approving scientific scope changes.
7. Choosing between unresolved scientific alternatives.
8. Supplying raw CICIoT2023 CSV files.
9. Supplying Edge-IIoTset files.
10. Confirming a long expensive experiment if not already authorized.

## Required Behavior

If human intervention is needed:

1. Stop the task.
2. Mark the ticket `BLOCKED_HUMAN`.
3. Add an entry to `docs/tickets/human_interventions.md`.
4. State exactly what the user must do.
5. State where to place the required file or decision.
6. State which ticket becomes unblocked afterward.
7. Do not implement around the missing human action.
8. Do not create fake data.
9. Do not create placeholder success artifacts.
10. Do not continue with assumptions.

## Human Intervention Entry Format

Each entry must include:

1. ID
2. Related ticket
3. Required user action
4. Required path or decision
5. Why it is required
6. What remains blocked
7. How to verify completion
8. Status

## Allowed Status Values

1. `OPEN`
2. `WAITING_FOR_USER`
3. `USER_PROVIDED`
4. `VERIFIED`
5. `CLOSED`
6. `CANCELLED_WITH_REASON`

## Stop Rule

If a task is human-blocked, the agent must not continue even if the user asks for implementation.

The correct response is to state the required human action and wait for it to be completed.