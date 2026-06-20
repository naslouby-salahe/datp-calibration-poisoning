# 06_HARDCODED_VALUES_LEDGER.md — Hardcoded Values Ledger

**Status:** PENDING — awaiting DEBT-002 (depends on INV-001)
**Owner:** OpenClaw subagent (DEBT-002)
**Last updated:** 2026-06-20T21:27:24Z (scaffold only)
**Review required:** YES — scientific values must be verified by Hermes

> WARNING: Do not edit source files during this inventory.
> This is a read-only analysis document.

---

## Purpose

Catalogue every hardcoded scientific constant, magic number, and raw string
in `src/` that should be moved to a centralized constants module or enum.

---

## Instructions for DEBT-002 Agent

1. Read `01_FILE_INDEX.md` to get the file list.
2. Search `src/` for:
   - Integer and float literals used as scientific values (K=3, n_min=100, fractions, seeds)
   - Raw policy strings (e.g. `"B1"`, `"B2"`, `"B4"`, `"GLOBAL"`, `"PERSONALIZED"`)
   - Raw objective strings (e.g. `"THRESHOLD_RAISE"`, `"raise"`)
   - Raw source strings (e.g. `"RANDOM_BENIGN"`, `"HIGH_SCORE_BENIGN"`)
   - Hardcoded file paths or directory patterns
   - Hardcoded dataset names or regime identifiers
3. For each finding, record file, line, value, and whether it matches a known CP2 scientific lock.
4. Flag any value that differs from the locked value in `CLAUDE.md` §3 as VIOLATION.
5. Do not modify any source file.

---

## Evidence Rules

- Include the actual literal value found.
- If the same value appears in multiple files, list each occurrence separately.
- If a value is in a constants module and imported correctly, mark it CENTRALIZED (low priority).
- If a value is duplicated between a constants module and implementation code, mark DUPLICATE.

---

## Hardcoded Values Ledger Table

| ID | File | Line | Value | Domain | Matches locked value? | Status | Notes |
|---|---|---|---|---|---|---|---|
| HV-001 | PENDING | — | — | — | — | — | DEBT-002 not yet run |

---

## Scientific Lock Cross-Reference

| Locked value (from CLAUDE.md §3) | Expected location | Found in implementation? | Status |
|---|---|---|---|
| K=3 (B4, Regime A) | constants module | PENDING | — |
| n_init=10 (B4) | constants module | PENDING | — |
| max_iter=300 (B4) | constants module | PENDING | — |
| random_state=42 (B4) | constants module | PENDING | — |
| n_min=100 (Calibration-Pending) | constants module | PENDING | — |
| fractions {0, 0.10, 0.20, 0.40} | constants module | PENDING | — |
| training_seed [0,1,2,3,4] | constants module | PENDING | — |
| poisoning_seed [100..104] | constants module | PENDING | — |
| analysis_seed [300..304] | constants module | PENDING | — |
| compromise_pattern_seed=400 | constants module | PENDING | — |

---

## Violations Found

| ID | File | Line | Found value | Locked value | Severity |
|---|---|---|---|---|---|
| PENDING | — | — | — | — | — |
