# 07_DUPLICATION_LEDGER.md — Duplication Ledger

**Status:** PENDING — awaiting DUP-001 (depends on INV-002)
**Owner:** OpenClaw subagent (DUP-001) / Codex CLI (fallback)
**Last updated:** 2026-06-20T21:27:24Z (scaffold only)

> WARNING: Do not edit source files during this inventory.
> This is a read-only analysis document.

---

## Purpose

Identify structural duplication across `src/`: repeated logic, copy-pasted
implementations, parallel functions that should be consolidated.

Scientific risk: HIGH — duplicated implementations can diverge during refactoring,
causing silent inconsistencies in calibration, threshold, or policy logic.

---

## Instructions for DUP-001 Agent

1. Read `02_SYMBOL_INDEX.md` to get all symbols.
2. Look for:
   - Functions with identical or near-identical bodies in different modules
   - Repeated threshold computation patterns across policy branches
   - Repeated reservoir construction patterns
   - Repeated seed construction patterns
   - Repeated config validation logic
   - Repeated manifest building patterns
3. For each duplicate pair, record both locations with file+line evidence.
4. Assess whether the duplication is structural (same logic in two places) vs.
   incidental (same name, different behavior).
5. Do not modify any source file.

---

## Evidence Rules

- Show both (or all) locations of each duplicate, with line evidence.
- Do not flag near-similar code as duplicate without reading both implementations.
- Mark cases where the logic appears identical but may have subtle differences as UNCERTAIN.

---

## Duplication Ledger Table

| ID | Type | Location A (file:line) | Location B (file:line) | Behavior identical? | Scientific risk | Notes |
|---|---|---|---|---|---|---|
| DUP-001-01 | PENDING | — | — | — | — | DUP-001 not yet run |

---

## Summary by Type

| Duplication type | Count |
|---|---|
| Threshold computation | PENDING |
| Reservoir construction | PENDING |
| Seed construction | PENDING |
| Policy dispatch | PENDING |
| Config validation | PENDING |
| Manifest building | PENDING |
| Other | PENDING |
| Total | PENDING |
