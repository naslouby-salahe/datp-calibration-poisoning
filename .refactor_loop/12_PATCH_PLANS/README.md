# 12_PATCH_PLANS/README.md

This directory holds patch plans for each approved backlog item.

A patch plan must exist and be reviewed before any implementation agent
begins writing code for that item.

Each patch plan corresponds to one backlog item (BL-ID):

```
12_PATCH_PLANS/BL-<ID>-<short-title>.md
```

---

## Patch Plan Format

```
# PATCH PLAN: BL-<ID> — <title>

## Status
DRAFT | REVIEWED | APPROVED | IMPLEMENTED | VERIFIED

## Agent
<agent who wrote the plan>

## Reviewer
<Hermes or Claude Code Sonnet>

## Date
<ISO timestamp>

## Backlog Item
BL-<ID>

## Scientific Risk
CRITICAL / HIGH / MEDIUM / LOW / NONE

## Affected Files
<list>

## Proposed Changes
<per-file change descriptions — no code yet>

## Contract Invariants to Preserve
<list from 09_SCIENTIFIC_CONTRACT_MAP.md>

## Test Coverage Plan
<what tests must pass or be added>

## Drift Gate Rows to Verify
<rows from 14_DRIFT_GATES.md>

## Rollback Plan
<how to undo if needed>

## Review Notes
<Hermes / reviewer comments>
```

---

## Files in This Directory

*(none yet — populated after BACKLOG-001 and REVIEW-001 complete)*
