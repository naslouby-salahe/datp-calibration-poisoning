# CP2-FB4 — [FALLBACK] CICIoT2023 Unsafe / B4 K Shifts

**Phase:** F — Full / optional (fallback, double-gated)
**Type:** fallback / conditional
**Priority:** conditional
**Status:** not started (activate only on trigger)
**Dependencies:** CP2-T054
**Blocks:** —
**Expected test level:** integration, static
**Graphify required:** conditional
**Paper notes required:** yes

## 1. Activation trigger
Activate **only if** CP2-T049 = CONTINUE **and** CP2-T054 returned FEASIBLE for the
CICIoT2023 stretch, **or** if B4 cluster count `K` must be revisited because the
locked `K=3` is shown unstable on the stretch data. If neither holds, leave NOT
STARTED and record "not triggered".

## 2. Purpose
Handle the conditional stretch path safely: either run a feasibility-bounded
CICIoT2023 stretch, or document a justified B4 `K` sensitivity check — without
compromising the primary N-BaIoT claims.

## 3. Pre-start audit
Inspect CP2-T054 feasibility verdict and B4 stability diagnostics.

## 4. Scope
- If CICIoT2023 FEASIBLE: run a bounded stretch (pseudo-clients, file-level) as
  **external validity only**, never confirmatory; report separately.
- If B4 `K` unstable: run a documented `K` sensitivity check **outside** the locked
  primary analysis; primary results keep `K=3`.

## 5. Non-goals
- Never upgrade stretch to confirmatory.
- Never treat pseudo-clients as physical devices.
- Never change the locked primary B4 `K=3` for N-BaIoT.
- Edge-IIoTset forbidden.

## 6. Scientific locks
Stretch external-only; primary `K=3` N-BaIoT locked; no device fabrication; no
forbidden datasets; separate reporting.

## 7. Coding locks
Typed; deterministic; isolated from primary path; no contamination of primary
artifacts.

## 8. Tests and diagnostics
```text
pytest tests/integration/data -q
pyright
```

## 9. Graphify
Optional; record deferral.

## 10. Paper-writing notes
Stretch/`K`-sensitivity belong in supplementary/external-validity sections only.

## 11. Acceptance criteria
- Stretch or `K`-sensitivity executed and reported separately, or "not triggered"
  recorded; primary claims unaffected; pyright green.

## 12. Blocking conditions
Any risk to primary-result integrity → stop and isolate; record decision.

## 13. Tracking update
Append to progress log; update fallback register.

## 14. Completion evidence
Stretch/K report or "not triggered" note, paper-notes entry, progress entry.
