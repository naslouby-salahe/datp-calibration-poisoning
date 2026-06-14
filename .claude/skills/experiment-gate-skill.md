# experiment-gate-skill

## Purpose

Prevent premature coding, premature experiments, and invalid phase transitions.

## Gate Checks

1. Is the current phase known?
2. Is the requested work allowed?
3. Are required files present?
4. Are scientific assumptions frozen?
5. Are configs valid?
6. Are datasets available?
7. Are tests ready?
8. Are artifacts clean?
9. Are logs configured?
10. Is failure handling defined?

## Decisions

Allowed decisions:

1. Proceed
2. Proceed with limited scope
3. Block until prerequisite is fixed
4. Stop and request scientific decision

## Required Output

1. Gate verdict
2. Blocking issues
3. Allowed scope
4. Next required action