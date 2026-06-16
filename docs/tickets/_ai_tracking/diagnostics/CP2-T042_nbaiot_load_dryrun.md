# CP2-T042 — N-BaIoT Artifact Loading Dry-Run

**Date:** 2026-06-16 (superseded; original hard-blocker report below for history)
**Ticket:** CP2-T042 (Phase E entry — real-data load dry-run)
**Type:** integration / read-only diagnostic
**Verdict (current): PASS.** FB1 has been executed (human-authorized). Real E=1
N-BaIoT clean score artifacts now exist for all 5 training seeds and pass every
provenance/integrity check. Phase E may proceed to CP2-T043.

---

## 0. What changed since the original hard-blocker finding

The original 2026-06-16 dry-run (preserved in §5 below) found clean N-BaIoT score
artifacts absent and `local_epochs: 5` (E=5) in `config.yaml`, routing to FB1. The
user explicitly authorized FB1. Execution:

1. `src/datp/conf/config.yaml:41` `local_epochs: 5 → 1` (the only change; no
   hyperparameter re-tuning, no architecture change).
2. `datp sweep --dry-run --regime a --base-dir outputs --data-root .` → 25 cells
   validated, no errors.
3. `datp sweep --regime a --base-dir outputs --data-root .` → **25/25 completed, 0
   failed, ~4174.5s (~70 min)** on GPU (NVIDIA RTX 5060 Ti). Decision log:
   `2026-06-16 | FB1 | AUTHORIZED by human — executing E=1 retrain`.

## 1. Real-artifact verification (current state)

Ran the DATP-side score-cell verifier (`datp.validation.score_manifest.verify_all_score_cells`)
against all 5 freshly generated Regime A score cells:

```
Total score cells found: 5
TrainingCellId(regime=Regime.A, seed=0): overall=PASS  n_checks=18  fails=0  missing=0  clients=9
TrainingCellId(regime=Regime.A, seed=1): overall=PASS  n_checks=18  fails=0  missing=0  clients=9
TrainingCellId(regime=Regime.A, seed=2): overall=PASS  n_checks=18  fails=0  missing=0  clients=9
TrainingCellId(regime=Regime.A, seed=3): overall=PASS  n_checks=18  fails=0  missing=0  clients=9
TrainingCellId(regime=Regime.A, seed=4): overall=PASS  n_checks=18  fails=0  missing=0  clients=9
```

All 18 checks pass for every seed: manifest present/parseable, required fields
present, completion_status="complete", scoring sentinel present, regime/seed/dataset
match, declared client IDs match the N-BaIoT partition (9 physical devices), expected
vs. actual clients/splits match, split directories (`cal`, `test_benign`,
`test_attack`) present, per-client split files present, parquet schema valid (single
`reconstruction_error` float column), parquet non-empty, checkpoint hash field
present, checkpoint file present, checkpoint hash matches. Reports written to
`outputs/scores/a/seed_{0..4}/score_cell_verification.json` and
`outputs/scores/score_cell_verification_index.json`.

**E=1 confirmation:** resolved config at
`outputs/results/a/b1/seed_0/resolved_config.yaml:40` reads `local_epochs: 1`
(checked for seed 0; the sweep composes one resolved config per cell from the same
`BASE_CONFIG`, so this applies uniformly across all 5 seeds).

## 2. Eligibility / Calibration-Pending counts

All 9 N-BaIoT physical-device clients are eligible (`n_min=100` benign calibration
samples) at every training seed — confirmed both by the sweep's own threshold-
derivation log (`eligible=9, pending=0` for every baseline/seed) and by client-count
fields in `score_cell_verification.json`. **Calibration-Pending set is empty** for
Regime A. Coverage ratio = 9/9 = 1.0.

## 3. Downstream impact on Phase E

CP2-T043 (one-seed/one-victim, one-seed/all-victims diagnostics) may now proceed: 9
eligible victims, 5 training-seed-keyed score collections, real `reconstruction_error`
calibration + test scores available read-only at
`outputs/scores/a/seed_{0..4}/{cal,test_benign,test_attack}/<ClientName>.parquet`.

## 4. Resolution path closed

FB1 is **closed/executed** (decision log `2026-06-16 | FB1 | AUTHORIZED by human —
executing E=1 retrain`). Fallback register updated accordingly.

## 5. Original hard-blocker finding (historical — superseded by §0–§3 above)

> **Verdict: HARD BLOCKER — clean N-BaIoT score artifacts are absent and the
> training config is E=5.** No clean per-client benign calibration scores, test
> scores, scoring manifest, or checkpoints existed; `config.yaml:41` was
> `local_epochs: 5`. Routed to CP2-FB1. `outputs/` contained only
> `console_logs/…help.log` and `logs/datp.log`. Two simultaneous failure modes:
> MISSING artifacts + E=5 config. `mu_flag_threshold` was uncomputable. See decision
> log `2026-06-16 | CP2-T042 | FB1 RE-CONFIRMED at Phase E gate` for full detail.

## 6. Outcome

- **CP2-T042:** PASS — real E=1 N-BaIoT clean artifacts verified for all 5 training
  seeds, 18/18 checks each.
- **CP2-T043–T049:** unblocked; proceeding.
- No fabrication; all findings backed by command output above.
