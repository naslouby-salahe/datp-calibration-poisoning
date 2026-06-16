# CP2 Fallback Register

Tracks the four conditional fallbacks (FB1–FB4): trigger state, blocking conditions,
authorization status, and resolution. Source tickets:
`docs/tickets/phase_a_audit/CP2-FB1.md`, `…/CP2-FB3.md`,
`docs/tickets/phase_c_core_implementation/CP2-FB2.md`,
`docs/tickets/phase_f_full_optional/CP2-FB4.md`.

Status vocabulary: `not triggered`, `TRIGGERED — awaiting authorization`,
`authorized`, `executed`, `closed`.

---

| FB | Condition | Status | Authorization | Evidence |
|---|---|---|---|---|
| **FB1** | Clean score artifacts fail provenance (absent / not E=1) | **executed** | **granted 2026-06-16** (user authorized heavy retrain + E=1 config fix) | below |
| FB2 | (Phase C conditional) | not triggered | — | `CP2-FB2.md` |
| FB3 | (Phase A conditional) | not triggered | — | `CP2-FB3.md`; CP2-T011 audit ("FB3 NOT triggered") |
| FB4 | CICIoT2023 stretch feasibility gate | not triggered | — | `CP2-FB4.md` (Phase F, conditional on T049 CONTINUE) |

---

## FB1 — detail

**Triggered:** 2026-06-16, CP2-T007; **re-confirmed** 2026-06-16 at the Phase E
entry gate (CP2-T042).

**Trigger condition met (two independent failure modes):**
1. **MISSING** — no CP2-controlled clean N-BaIoT per-client calibration/test score
   artifacts exist. `outputs/` holds only `console_logs/…help.log` and `logs/datp.log`.
2. **E=5** — `src/datp/conf/config.yaml:41` = `local_epochs: 5`. Training as-is would
   produce E=5 artifacts, which the provenance gate rejects.

**Blocks (transitively):** CP2-T042, T043, T044, the bounded MVP run, T045, T046,
T047, T048, T049 — i.e. all of Phase E — and therefore the Phase E go/no-go gate.

**Authorization required (NOT granted by the Phase E agent prompt):**
- Per FB1 §5: *"Heavy training requires explicit authorization (experiment-gate);
  GPU path may apply."*
- Per FB1 §12: *"Heavy training without authorization → stop and request
  authorization via decision record."*
- Per CLAUDE.md §9 hard-stop: a scientific-meaning config change
  (`local_epochs 5 → 1`) and an experiment run both require explicit authorization.

**Execution plan once authorized (FB1 §3, locks unchanged):**
1. Edit `src/datp/conf/config.yaml:41` `local_epochs: 5 → 1` (E=1 lock).
2. One federated retrain: E=1, `rounds_initial=40`, `rounds_max=150`, DATP
   convergence criterion, FedAvg weighted by local benign size, Flower,
   `training_seed=[0,1,2,3,4]`. No hyperparameter re-tuning, no architecture change.
3. Generate per-client benign calibration + test scores; write
   `_ai_tracking/manifests/clean_score_artifacts.json` with full provenance.
4. Re-run CP2-T007 / CP2-T042 provenance load → expect PASS (E=1).
5. Resume Phase E at CP2-T042 → T049.

**Compute note:** GPU may be required; confirm availability before authorizing. If
compute/GPU is unavailable, record a blocker per FB1 §12.

**Decision pending:** see `CP2_DECISION_LOG.md` entry
`2026-06-16 | CP2-T042 | FB1 RE-CONFIRMED at Phase E gate`.

**Executed 2026-06-16:** user authorized FB1 explicitly. `config.yaml:41`
`local_epochs: 5 → 1`; `datp sweep --regime a --base-dir outputs --data-root .` ran
25/25 cells (0 failed, ~70 min, GPU). Real E=1 N-BaIoT clean artifacts now exist for
all 5 training seeds and pass `verify_all_score_cells` (18/18 checks each, 9/9
clients eligible). See decision log `2026-06-16 | FB1 | AUTHORIZED by human —
executing E=1 retrain`. **FB1 status: closed.**
