# 11_MODULE_AUDITS/README.md

This directory holds per-module audit reports.

Each module that requires a detailed refactor audit gets its own file here:

```
11_MODULE_AUDITS/<module_name>.md
```

Audits are written by OpenClaw subagents or Claude Code Sonnet during
the inventory and analysis phases.

---

## Audit File Format

```
# MODULE AUDIT: <module path>

## Status
PENDING | IN_PROGRESS | COMPLETE | BLOCKED

## Agent
<agent name>

## Date
<ISO timestamp>

## Module Purpose
<one-line description>

## Symbols Found
<list of classes, functions, enums>

## Type Debt
<Any, dict, object usage — with line numbers>

## Hardcoded Values
<literal constants — with line numbers>

## Duplication
<duplicated logic — with evidence>

## Scientific Contract Coverage
<which elements of 09_SCIENTIFIC_CONTRACT_MAP.md does this module implement?>

## Violations Found
<NONE or list with severity>

## Recommended Refactor Actions
<list — link to backlog categories in 10_REFACTOR_BACKLOG.md>
```

---

## Files in This Directory

*(none yet — populated during inventory phase)*
