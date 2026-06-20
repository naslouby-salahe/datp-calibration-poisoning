# 03_METHOD_IO_INDEX.md — Method Input/Output Index

**Status:** PENDING — awaiting INV-003 (depends on INV-002)
**Owner:** OpenClaw subagent (INV-003) / Codex CLI (fallback)
**Last updated:** 2026-06-20T21:27:24Z (scaffold only)

> WARNING: Do not edit source files during this inventory.
> This is a read-only analysis document.

---

## Purpose

Catalogue public method and function signatures, including parameter types and
return types. Identify untyped parameters, `Any` returns, and `dict`-shaped
contracts that should become typed dataclasses.

---

## Instructions for INV-003 Agent

1. Read `02_SYMBOL_INDEX.md` to get the symbol list.
2. For each public function/method (not prefixed with `_`), extract:
   - Full qualified name (e.g. `module.ClassName.method_name`)
   - Parameter names and annotated types (or `UNTYPED` if missing)
   - Return type annotation (or `UNTYPED` if missing)
   - File and line number of the signature
3. Note any parameter or return type using `Any`, `dict`, `object`, or no annotation.
4. Note any function that returns a raw dict that should be a dataclass.
5. Do not modify any source file.

---

## Evidence Rules

- Extract from actual source annotations — do not infer from naming.
- If a function has `# type: ignore`, note it.
- If a function has no annotations at all, mark all types as UNTYPED.

---

## Method IO Index Table

| Qualified name | File | Line | Parameters (name: type) | Return type | Untyped? | Notes |
|---|---|---|---|---|---|---|
| PENDING | — | — | — | — | — | — |

---

## Untyped Summary

*(populated by INV-003)*

| Symbol | Untyped parameters | Untyped return | File | Line |
|---|---|---|---|---|
| PENDING | — | — | — | — |
