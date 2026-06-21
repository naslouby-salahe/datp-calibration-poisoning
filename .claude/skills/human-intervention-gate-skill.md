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
9. Confirming a long expensive experiment if not already authorized.

## Required Behavior

If human intervention is needed:

1. Stop the task.
2. State exactly what the user must do.
3. State where to place the required file or decision.
4. State what work becomes unblocked afterward.
5. Do not implement around the missing human action.
6. Do not create fake data.
7. Do not create placeholder success artifacts.
8. Do not continue with assumptions.

## Stop Rule

If a task is human-blocked, the agent must not continue even if the user asks for implementation.

The correct response is to state the required human action and wait for it to be completed.
