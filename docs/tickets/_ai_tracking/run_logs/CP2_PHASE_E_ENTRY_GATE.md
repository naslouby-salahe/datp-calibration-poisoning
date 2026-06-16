# CP2 Phase E — Entry-Gate & MVP-Bridge Run Log

**Date:** 2026-06-16
**Scope:** Phase E MVP (CP2-T042–T049) entry-gate verification and the
documented "bridge" between CP2-T044 and CP2-T046 (the bounded MVP run that has no
separate numbered ticket).

---

## 1. The CP2-T044 → CP2-T046 bridge (recorded as required)

The Phase E ticket set expects MVP **result** artifacts to exist before CP2-T046, but
there is no numbered ticket named "Run bounded MVP matrix." The intended order is:

1. CP2-T042 — load real N-BaIoT artifacts read-only.
2. CP2-T043 — smallest real-data diagnostics.
3. CP2-T044 — all-seeds/one-victim diagnostic + write the **bounded MVP run plan**;
   lock `mu_flag_threshold` from clean B1 eligible-client mean FPR.
4. **Bridge:** execute *only* the bounded MVP run authorized by the CP2-T044 plan
   (NOT the CP2-T056 final experiment; no Phase F additions; no final paper runs).
5. CP2-T045–T049 — cleanup, manifest/result audit, kill-triggers, drift, decision.

This bridge is recorded here so that any future MVP run is traceable to the CP2-T044
plan and is not mistaken for the CP2-T056 final experiment.

## 2. Entry-gate result (2026-06-16)

| # | Entry-gate requirement | Status | Evidence |
|---|---|---|---|
| 1 | CP2-T041 drift report exists | PASS | `audits/CP2-T041_smoke_validation_drift_check.md` (verdict PASS) |
| 2 | All synthetic smoke invariants pass | PASS | 15 invariants in `tests/integration/attacks/test_cp2_smoke.py` |
| 3 | No unresolved Phase-D blockers | **FAIL** | **FB1 TRIGGERED & unexecuted** (CP2-T007 → present) |
| 4 | Real-data loading still provenance-gated | PASS | `src/datp/validation/provenance_gate.py` (E=1/E=5 checks) |

**Gate verdict: NOT SATISFIED (requirement 3 fails).**

## 3. CP2-T042 dry-run result

Hard blocker. No clean N-BaIoT score artifacts exist; `config.yaml:41` is
`local_epochs: 5` (E=5). See `diagnostics/CP2-T042_nbaiot_load_dryrun.md`.

`outputs/` file inventory at gate time:
```
outputs/console_logs/2026-06-15_23-02-30__datp__help.log
outputs/logs/datp.log
```
No `.parquet`, no scoring manifest, no checkpoint, no
`outputs/conference_calibration_poisoning/`.

## 4. What did NOT run (and why)

- **No bounded MVP run** — depends on CP2-T044, which depends on real clean scores
  (absent) and a locked `mu_flag_threshold` (uncomputable without clean B1 FPR).
- **No training / scoring / FB1** — heavy retrain + a scientific-meaning config
  change require explicit authorization (FB1 §12, CLAUDE.md §9). Not granted by the
  Phase E prompt.
- **No `outputs/` writes** — read-only inspection only.

## 5. Real-data safety rules — status at gate

| Rule | Status |
|---|---|
| provenance gate confirms E=1 | **CANNOT — no artifact; config is E=5** |
| reject E=5 | enforced (config is E=5 → would be rejected) |
| clean score artifacts read-only | n/a (none exist) |
| `mu_flag_threshold` locked from clean B1 mean FPR pre-poison | **CANNOT — no clean scores** |
| clean & poisoned share seed/AE/split/test/victim plan | n/a (nothing to run) |
| poisoning is the only stochastic difference | n/a |
| output under `outputs/conference_calibration_poisoning/` | n/a (no run) |

## 6. Next action

Phase E remains blocked at CP2-T042. Unblock requires an explicit human decision on
FB1 (retrain to E=1) — see `decisions/CP2_FALLBACK_REGISTER.md` and the decision-log
entry. No further Phase E work is safe until E=1 clean artifacts exist and pass the
provenance gate.
