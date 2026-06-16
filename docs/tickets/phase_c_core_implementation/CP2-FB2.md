# CP2-FB2 — [FALLBACK] Degenerate Tail Reservoir Handling

**Phase:** C — Core implementation (fallback)
**Type:** fallback / conditional
**Priority:** conditional
**Status:** not started (CONDITIONAL — NOT triggered; degenerate-tail handling preventively implemented as `INFEASIBLE_DEGENERATE_TAIL` in `src/datp/attacks/reservoir.py`)
**Dependencies:** CP2-T026
**Blocks:** —
**Expected test level:** unit, static
**Graphify required:** conditional
**Paper notes required:** yes

## 1. Activation trigger
Activate **only if** CP2-T026/T029 find victims whose 10% tail reservoir is
degenerate (fewer than 2 distinct values, or otherwise infeasible for HIGH/LOW
sources). If never triggered, leave NOT STARTED and record "not triggered" at close.

## 2. Purpose
Define protocol-safe handling for degenerate tail reservoirs so such victims are
treated consistently and reported, without ad-hoc fixes.

## 3. Pre-start audit
Inspect the CP2-T026 INFEASIBLE detection path and the affected victims/cells.

## 4. Scope
- Mark affected victim/source cells **INFEASIBLE**; exclude from feasible-victim
  counts and from sign-consistency denominators.
- Report feasibility coverage; never silently substitute another client's reservoir
  or fabricate values.

## 5. Non-goals
- No cross-client reservoir substitution.
- No silent inclusion of infeasible cells in statistics.

## 6. Scientific locks
Victim-local only; feasibility reported; infeasible cells excluded from feasible
denominators; no fabrication.

## 7. Coding locks
Typed feasibility status; explicit, not silent; no hardcoded thresholds.

## 8. Tests and diagnostics
```text
pytest tests/unit/attacks -q
pyright
```

## 9. Graphify
Optional; record deferral.

## 10. Paper-writing notes
Record feasibility coverage as a limitation; HIGH/LOW may be infeasible for some
clients.

## 11. Acceptance criteria
- Degenerate tails handled explicitly and reported; excluded correctly from feasible
  denominators; tests + pyright green. (Or documented "not triggered".)

## 12. Blocking conditions
If many victims are infeasible, escalate to the MVP decision (CP2-T049) via a
decision record.

## 13. Tracking update
Append to progress log; update the fallback register.

## 14. Completion evidence
Feasibility-handling diff or "not triggered" note, tests, paper-notes entry, progress.
