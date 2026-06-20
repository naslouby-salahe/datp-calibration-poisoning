# 01_FILE_INDEX.md — Source File Index

**Status:** PENDING — awaiting INV-001
**Owner:** OpenClaw subagent (INV-001)
**Last updated:** 2026-06-20T21:27:24Z (scaffold only)

> WARNING: Do not edit source files during this inventory.
> This is a read-only analysis document.

---

## Purpose

A complete enumeration of all source files in `src/` (and relevant `tests/`,
`scripts/`, `configs/`) with module path, role, and primary exports.

---

## Instructions for INV-001 Agent

1. Run `find src/ -name "*.py" | sort` to enumerate all source files.
2. For each file, record:
   - Relative path from repo root
   - Module path (dot notation)
   - One-line role description
   - Primary exports (top-level classes, functions, enums)
3. Also enumerate `tests/`, `scripts/`, and any config files relevant to the campaign.
4. Do not read file bodies at this stage — use `head` or import scanning only.
5. Write all findings to this file under the table below.
6. Mark status COMPLETE when all `src/` files are enumerated.

---

## Evidence Rules

- Use actual file listing commands, not memory of prior sessions.
- Do not speculate about file purpose — read the top-level exports.
- If a file cannot be read, mark it UNREADABLE with the reason.

---

## File Index Table

| Relative path | Module path | Role | Primary exports | Notes |
|---|---|---|---|---|
| PENDING | — | — | — | INV-001 not yet run |

---

## File Count Summary

| Area | File count |
|---|---|
| `src/` | PENDING |
| `tests/` | PENDING |
| `scripts/` | PENDING |
| `configs/` | PENDING |
| Total | PENDING |
