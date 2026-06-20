# 08_CONFIG_FLOW_MAP.md — Config Flow Map

**Status:** PENDING — awaiting CONFIG-001 (depends on INV-003, INV-004)
**Owner:** OpenClaw subagent (CONFIG-001) / Claude Code Sonnet (fallback)
**Last updated:** 2026-06-20T21:27:24Z (scaffold only)
**Review required:** YES

> WARNING: Do not edit source files during this inventory.
> This is a read-only analysis document.

---

## Purpose

Document how configuration is constructed and propagated from the CLI entry point
through to experiment runners, sweep builders, and metric collectors.

The goal is to identify fragmentation points where scientific parameters could
be silently dropped, overridden, or defaulted incorrectly.

---

## Instructions for CONFIG-001 Agent

1. Read `03_METHOD_IO_INDEX.md` and `04_DATACLASS_ENUM_INDEX.md`.
2. Trace the config construction path from CLI argument parsing:
   - What is the entry point? (CLI command, `argparse`, `click`, `typer`)
   - Where is `CalibrationPoisoningConfig` (or equivalent) constructed?
   - How is it propagated to runners, sweep builders, and collectors?
   - Are there any places where raw parameters are re-extracted from the config dict?
   - Are there any places where config is reconstructed from partial state?
3. Document the full flow as a chain: `CLI → Builder → Config → Runner → Collector`.
4. Identify any "fragmentation points" where a dict is used instead of the typed config.
5. Do not modify any source file.

---

## Evidence Rules

- Show actual file+line for each step in the flow.
- If a step is inferred (not directly traceable), mark it INFERRED.
- If the flow has branches (e.g. different entry points for CLI vs. script), document each branch.

---

## Config Flow Diagram

*(to be filled by CONFIG-001)*

```
CLI entry (PENDING: file:line)
  │
  ├─ Argument parsing (PENDING: file:line)
  │
  ├─ CalibrationPoisoningConfig construction (PENDING: file:line)
  │
  ├─ Runner dispatch (PENDING: file:line)
  │    ├─ BoundedSweepRunner (PENDING: file:line)
  │    └─ ... (PENDING)
  │
  ├─ Sweep manifest build (PENDING: file:line)
  │
  ├─ Per-trial execution (PENDING: file:line)
  │
  └─ Metric collection (PENDING: file:line)
```

---

## Fragmentation Points

*(populated by CONFIG-001)*

| ID | File | Line | Description | Risk | Recommended fix |
|---|---|---|---|---|---|
| PENDING | — | — | — | — | — |

---

## Config Object Lifecycle

| Phase | Object type | File | Line | Notes |
|---|---|---|---|---|
| CLI construction | PENDING | — | — | — |
| Passed to runner | PENDING | — | — | — |
| Passed to sweep builder | PENDING | — | — | — |
| Passed to trial executor | PENDING | — | — | — |
| Passed to metric collector | PENDING | — | — | — |
