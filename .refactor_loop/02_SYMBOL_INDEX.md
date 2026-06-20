# 02_SYMBOL_INDEX.md — Symbol Index

**Status:** PENDING — awaiting INV-002 (depends on INV-001)
**Owner:** OpenClaw subagent (INV-002)
**Last updated:** 2026-06-20T21:27:24Z (scaffold only)

> WARNING: Do not edit source files during this inventory.
> This is a read-only analysis document.

---

## Purpose

Catalogue all classes, functions, enums, dataclasses, and Pydantic models
defined in `src/`. This is the foundation for the type-debt and duplication
ledgers, and for the method IO index.

---

## Instructions for INV-002 Agent

1. Read `01_FILE_INDEX.md` to get the file list.
2. For each file, extract top-level and nested class/function/enum definitions.
3. Use `grep` or static AST scanning — do not run the code.
4. Record:
   - Symbol name
   - Symbol type (class / function / enum / dataclass / Protocol / TypeAlias)
   - File and line number
   - Parent class or module (for methods)
   - Brief role (1 line)
5. Flag any symbol whose name contains `CP2`, `MVP`, `phase_e`, or ticket IDs
   (these violate production-naming rules from `CLAUDE.md` §4.1).
6. Do not modify any source file.

---

## Evidence Rules

- Record actual line numbers from `grep` output or file reading.
- Do not speculate about symbol purpose from name alone — read the actual definition.
- Mark symbols with unclear roles as UNCERTAIN.

---

## Symbol Index Table

| Symbol name | Type | File | Line | Parent | Role | Naming violation? |
|---|---|---|---|---|---|---|
| PENDING | — | — | — | — | — | — |

---

## Naming Violation Summary

*(populated by INV-002)*

| Symbol | File | Line | Violation type |
|---|---|---|---|
| PENDING | — | — | — |
