# 05_TYPE_DEBT_LEDGER.md — Type Debt Ledger

**Status:** PENDING — awaiting DEBT-001 (depends on INV-002)
**Owner:** OpenClaw subagent (DEBT-001) / Codex CLI (fallback)
**Last updated:** 2026-06-20T21:27:24Z (scaffold only)
**Review required:** YES — Hermes recommended after population

> WARNING: Do not edit source files during this inventory.
> This is a read-only analysis document.

---

## Purpose

Catalogue every instance of type debt in `src/`:
- `Any` annotations
- `dict` used as a typed record (not a mapping)
- `object` annotations
- Untyped function parameters
- Untyped return types
- `# type: ignore` suppressions
- Loose `tuple` unpacking contracts

---

## Instructions for DEBT-001 Agent

1. Read `02_SYMBOL_INDEX.md` and `03_METHOD_IO_INDEX.md`.
2. Search `src/` for:
   - `from typing import Any` / usage of `Any`
   - `-> dict` / `: dict` without subscript
   - `-> object` / `: object`
   - Functions with no type annotations
   - `# type: ignore`
3. For each finding, record file, line, context, and risk assessment.
4. Assign a scientific risk level (CRITICAL/HIGH/MEDIUM/LOW) based on whether the
   loose type touches poisoning, calibration, threshold, reservoir, or policy logic.
5. Do not modify any source file.

---

## Evidence Rules

- Include the actual line text for each entry.
- Do not mark a line as debt based on name alone — read the actual annotation.
- If `Any` is justified and documented (e.g. plugin interface), mark LOW risk with reason.

---

## Type Debt Ledger Table

| ID | File | Line | Debt type | Context (brief) | Scientific risk | Notes |
|---|---|---|---|---|---|---|
| TD-001 | PENDING | — | — | — | — | INV-002 not yet run |

---

## Summary by Risk Level

| Risk level | Count |
|---|---|
| CRITICAL | PENDING |
| HIGH | PENDING |
| MEDIUM | PENDING |
| LOW | PENDING |
| Total | PENDING |

---

## High-Risk Items

*(populated by DEBT-001 — items touching scientific logic)*

| ID | File | Line | Debt type | Why high risk |
|---|---|---|---|---|
| PENDING | — | — | — | — |
