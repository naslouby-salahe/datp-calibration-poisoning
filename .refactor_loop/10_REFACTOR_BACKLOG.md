# 10_REFACTOR_BACKLOG.md — Refactor Backlog

**Status:** TEMPLATE ONLY — awaiting inventory completion
**Owner:** OpenClaw (synthesis, BACKLOG-001)
**Last updated:** 2026-06-20T21:27:24Z (scaffold only)

> Do not populate this backlog with specific items until the following are complete:
> DEBT-001, DEBT-002, DUP-001, CONFIG-001, SCI-001.
> Do not fabricate items. Every backlog entry must cite evidence from the ledgers.

---

## Purpose

A prioritized, evidence-backed list of refactoring tasks to be executed
in implementation loops by Claude Code Sonnet and/or Codex CLI.

All items must be reviewed by Hermes (REVIEW-001) before any implementation begins.

---

## Backlog Item Format

```
### BL-<ID> — <short title>

| Field | Value |
|---|---|
| Category | <see categories below> |
| Priority | CRITICAL / HIGH / MEDIUM / LOW |
| Scientific risk | CRITICAL / HIGH / MEDIUM / LOW / NONE |
| Evidence | <ledger entry ID(s)> |
| Affected files | PENDING |
| Recommended agent | — |
| Dependencies | <other BL-IDs or NONE> |
| Status | PENDING_EVIDENCE |
| Hermes verdict | NOT_YET_REVIEWED |
```

---

## Categories

### 1. Enum / Dataclass Contract Foundation

Replace raw strings, loose dicts, and untyped dispatch with typed enums and dataclasses.

Scientific risk: MEDIUM — raw strings can silently allow invalid policy/objective/source values.

Items: PENDING EVIDENCE (from DEBT-001, INV-004)

---

### 2. CalibrationPoisoningConfig Runner Wiring

Ensure `CalibrationPoisoningConfig` is the single authoritative config object
propagated through all runners, sweep builders, and metric collectors.

Scientific risk: HIGH — config fragmentation can cause silent parameter drift.

Items: PENDING EVIDENCE (from CONFIG-001, DEBT-001)

---

### 3. CLI / Parsing Boundary Isolation

Isolate CLI argument parsing from scientific domain logic.
CLI should construct typed config; domain code should never parse strings.

Scientific risk: MEDIUM — string parsing in domain code bypasses type guarantees.

Items: PENDING EVIDENCE (from CONFIG-001, INV-003)

---

### 4. Raw-String Policy / Objective / Source Dispatch Removal

Eliminate any `if policy == "B1"` or `if source == "RANDOM"` style dispatch.
Replace with enum-based dispatch throughout.

Scientific risk: HIGH — raw-string dispatch does not catch typos or enum evolution.

Items: PENDING EVIDENCE (from DEBT-001, INV-002)

---

### 5. Scientific Constants Centralization

Move all hardcoded numeric constants (K=3, n_init=10, fraction values,
n_min=100, seed values) to a single constants module.
No scientific value may appear as a literal in implementation modules.

Scientific risk: CRITICAL — scattered constants create drift risk across refactors.

Items: PENDING EVIDENCE (from DEBT-002)

---

### 6. Reservoir and Injection Contract Refactor

Ensure reservoir construction and injection are encapsulated behind a typed interface.
The interface must enforce:
- victim-local benign scores only
- no in-place mutation of clean arrays
- cardinality preservation
- with-replacement resampling

Scientific risk: CRITICAL — any looseness here can silently violate the attack boundary.

Items: PENDING EVIDENCE (from SCI-001, DEBT-001)

---

### 7. Threshold Policy Dispatch Refactor

Ensure threshold calibration for B1, B2, B4 is dispatched through a typed
policy dispatch function, not a raw `if/elif` string chain.
B4 fingerprint and K=3 must be enforced at the dispatch site, not scattered.

Scientific risk: HIGH — policy dispatch errors could silently apply wrong threshold.

Items: PENDING EVIDENCE (from SCI-001, INV-003)

---

### 8. B4 Config and Decomposition Contract Refactor

Encapsulate B4 parameters (K, n_init, max_iter, random_state, fingerprint)
in a typed config. Enforce `Δτ_total = Δτ_agg + Δτ_churn` decomposition
at a single site. Eliminate raw label-ID comparison.

Scientific risk: HIGH — B4 parameter drift is a major reproducibility risk.

Items: PENDING EVIDENCE (from SCI-001, DEBT-002)

---

### 9. Metric Name / Result Contract Refactor

Replace any `dict`-based metric result structures with typed dataclasses.
Metric names must be enum-driven, not raw strings.

Scientific risk: MEDIUM — wrong metric name returns silently wrong data.

Items: PENDING EVIDENCE (from DEBT-001, INV-003)

---

### 10. Manifest / Provenance Contract Refactor

Ensure sweep manifests and provenance records use typed dataclasses or Pydantic models.
No `dict`-shaped provenance that can silently drop fields.

Scientific risk: HIGH — incomplete provenance breaks reproducibility claims.

Items: PENDING EVIDENCE (from DEBT-001, INV-004)

---

### 11. Duplication Elimination

Identify and consolidate duplicate logic across modules.
No two places should implement the same scientific operation differently.

Scientific risk: HIGH — duplicated implementations can diverge silently.

Items: PENDING EVIDENCE (from DUP-001)

---

### 12. Final Scientific Drift Gate

After all implementation loops complete, run `14_DRIFT_GATES.md` in full.
All rows must be PASS or N/A before any results are used.

Scientific risk: CRITICAL.

Items: GATED — runs last.

---

### 13. Final Readiness Audit

Populate `15_FINAL_READINESS_REPORT.md`.
Confirm no `Any`, no raw-string dispatch, no scattered constants, no journal scope.
Hermes must sign off.

Scientific risk: CRITICAL.

Items: GATED — runs after drift gate passes.

---

## Backlog Entry Table

*(to be populated by BACKLOG-001 after all inventory ledgers are complete)*

| BL-ID | Title | Category | Priority | Scientific risk | Status | Hermes verdict |
|---|---|---|---|---|---|---|
| — | — | — | — | — | PENDING_EVIDENCE | NOT_YET_REVIEWED |
