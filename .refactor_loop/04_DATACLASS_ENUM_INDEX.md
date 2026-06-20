# 04_DATACLASS_ENUM_INDEX.md — Dataclass, Enum, and Config Index

**Status:** PENDING — awaiting INV-004 (depends on INV-002)
**Owner:** OpenClaw subagent (INV-004) / Codex CLI (fallback)
**Last updated:** 2026-06-20T21:27:24Z (scaffold only)

> WARNING: Do not edit source files during this inventory.
> This is a read-only analysis document.

---

## Purpose

Catalogue all typed structures: dataclasses, enums, Pydantic models, Protocols,
and TypedDicts. Identify gaps — places where a `dict` or `tuple` is used
where a typed structure should exist.

---

## Instructions for INV-004 Agent

1. Read `02_SYMBOL_INDEX.md` to identify all dataclasses, enums, and Pydantic models.
2. For each typed structure, record:
   - Name and type (dataclass / enum / Pydantic BaseModel / TypedDict / Protocol / NamedTuple)
   - File and line
   - Fields / members with types
   - Whether `frozen=True` for dataclasses
   - Whether the enum inherits from `str` (raw-string compatibility risk)
3. Identify any place in the codebase where a `dict` is used as a typed record
   that should be a dataclass (from `03_METHOD_IO_INDEX.md` return types).
4. Identify any enum member value that is a raw string equal to the enum's
   domain name (e.g. `B1 = "B1"` is fine; `B1 = "b1_global"` may be a contract).
5. Do not modify any source file.

---

## Evidence Rules

- Report actual field definitions with types — do not infer from usage.
- If a dataclass lacks type annotations on any field, mark it PARTIALLY_TYPED.
- If an enum member has a non-string value (e.g. int), note it.

---

## Typed Structure Table

| Name | Kind | File | Line | Fields / Members | Frozen? | Notes |
|---|---|---|---|---|---|---|
| PENDING | — | — | — | — | — | — |

---

## Missing Typed Structure Gaps

*(populated by INV-004 — places where a dict/tuple should be a dataclass)*

| Location | File | Line | Current type | Recommended structure | Priority |
|---|---|---|---|---|---|
| PENDING | — | — | — | — | — |
