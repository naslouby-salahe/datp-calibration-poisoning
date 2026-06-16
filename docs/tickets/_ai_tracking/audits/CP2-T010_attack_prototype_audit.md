# CP2-T010 — Existing CP2 Attack-Code Audit (Prototype Assessment)

**Date:** 2026-06-16
**Ticket:** CP2-T010
**Auditor:** Phase-A read-only audit
**Verdict:** PROTOTYPE DOES NOT MATCH CP2 PROTOCOL — QUARANTINE + REPLACE in Phase B/C.
All 22 unit/integration attack tests pass but test the wrong model.

---

## 1. Method

```bash
cat src/datp/attacks/calibration_poisoning.py
cat src/datp/attacks/poisoning_config.py
cat src/datp/attacks/poisoning_metrics.py
cat src/datp/experiments/calibration_poisoning.py
find tests -name "*.py" | grep attack/poison
pytest tests/unit/attacks -q     # 22 passed in 2.52s
```

---

## 2. Protocol gap table

| Prototype feature | CP2 protocol requirement | Gap |
|---|---|---|
| `attack_rate` (fraction, any float in (0,1]) | `fraction f ∈ {0, 0.10, 0.20, 0.40}` | Wrong: no fraction enum; no discrete grid |
| `shift_magnitude` (adds/subtracts value) | `REPLACE_FIXED_BUDGET`: replace `m_i = max(1, round(f·n_i))` positions with values resampled **from victim-local reservoir** | Wrong injection model: shift, not replace-resample |
| `rng.choice(n, size=n_poison, replace=False)` → select positions | Must select `m_i` positions, then **replace values** with reservoir draws (replace=True from reservoir) | Wrong: replaces with shifted values, not resampled values |
| `PoisoningObjective.{RAISE,LOWER}_THRESHOLD` | `AttackerObjective.{THRESHOLD_RAISE,THRESHOLD_LOWER}` (naming mismatch) | Naming gap (not hard-stop, but must be renamed in T016) |
| No source enum | `{RANDOM_BENIGN, HIGH_SCORE_BENIGN, LOW_SCORE_BENIGN}` required | Missing entirely |
| No scope enum | `SINGLE_CLIENT` (MVP), `MULTI_CLIENT` (Full) required | Missing entirely |
| No knowledge enum | `GRAY_BOX` (gray-box, main); others diagnostic | Missing entirely |
| `CalibrationPoisoningConfig`: untyped `seed: int` | `SeedSequence([training_seed, poisoning_seed, client_id, scope_id])` child seeds | Wrong seed scheme (integer seed, not SeedSequence) |
| `run_poisoning_experiment` poisons ALL clients simultaneously | MVP: single-victim sweep; only one victim poisoned per run | Wrong: all-clients attack, no single-victim |
| No manifest / provenance gate | Manifest must record reservoir mode, E=1 gate, `mu_flag_threshold` | Missing entirely |
| `PoisoningEffect.relative_shift`: `0.0` denominator → `float("inf")` | `Δτ_rel = Δτ / max(\|τ_clean\|, ε)` (ε numerical only) | Bug: wrong denominator logic |
| No CV(FPR), AUROC, ASR metrics | Full metric engine required (T033) | Missing entirely |
| No bootstrap/sign-test | Required statistical layer (T035) | Missing entirely |
| No B4 decomposition (`Δτ_agg + Δτ_churn`) | Required B4 client-indexed delta decomposition (T031) | Missing entirely |

---

## 3. What the prototype gets right (retain as concept, not code)

| Correct element | Location |
|---|---|
| `_POISONING_BASELINES = (B1, B2, B4)` — no B3 | experiments/calibration_poisoning.py:12 |
| `errors.copy()` — no in-place mutation | calibration_poisoning.py:34 |
| `max(1, round(n * attack_rate))` injection count formula (wrong name, right formula) | calibration_poisoning.py:36 |
| Clean vs poisoned threshold comparison structure | experiments/calibration_poisoning.py |
| Absolute shift `poisoned_threshold - clean_threshold` | poisoning_metrics.py:21 |

---

## 4. File disposition table

| File | Disposition | Reason |
|---|---|---|
| `src/datp/attacks/calibration_poisoning.py` | **QUARANTINE → REPLACE** (T027) | Wrong injection model (shift_magnitude); must be replaced with REPLACE_FIXED_BUDGET + reservoir resampling |
| `src/datp/attacks/poisoning_config.py` | **QUARANTINE → REPLACE** (T017/T027) | Wrong config schema (attack_rate, shift_magnitude, integer seed); must be replaced with CP2 typed config |
| `src/datp/attacks/poisoning_metrics.py` | **QUARANTINE → REPLACE** (T033) | Wrong metrics schema (no CV(FPR), no ASR, wrong relative_shift); replace with full CP2 metric engine |
| `src/datp/experiments/calibration_poisoning.py` | **QUARANTINE → REPLACE** (T027/T029) | Wrong injection model; no single-victim sweep; replace with CP2 injector + strategy |
| `tests/unit/attacks/test_calibration_poisoning.py` | **REWRITE** (after T027) | Tests the wrong model; all must be replaced |
| `tests/unit/attacks/test_poisoning_config.py` | **REWRITE** (after T017) | Tests wrong config schema |
| `tests/unit/attacks/test_poisoning_metrics.py` | **REWRITE** (after T033) | Tests wrong metrics |
| `tests/integration/attacks/test_poisoning_experiment.py` | **REWRITE** (after T027/T029) | Tests wrong experiment runner |

---

## 5. Entanglement check

The prototype files are **not imported** by any core DATP substrate package. They are
self-contained under `src/datp/attacks/` and `src/datp/experiments/`. Quarantine is
safe — no DATP core depends on them.

The one cross-dependency: `poisoning_metrics.py` imports `Baseline` from
`datp.core.enums`, which is fine (DATP enum). The replacement will import the new
`ThresholdPolicy` CP2 enum instead.

---

## 6. Phase B/C replacement plan

| Phase B/C ticket | Creates |
|---|---|
| T016 | `AttackerObjective`, `SourceStrategy`, `TargetScope`, `ThresholdPolicy` enums |
| T017 | Typed CP2 config (`fraction`, no `shift_magnitude`) |
| T026 | Reservoir selection (victim-local, tail strategies) |
| T027 | `REPLACE_FIXED_BUDGET` injector; quarantines `calibration_poisoning.py` |
| T029 | Source strategies (RANDOM/HIGH/LOW); replaces `experiments/calibration_poisoning.py` |
| T033 | CP2 metric engine (`Δτ`, CV(FPR), ASR, coverage) |

---

## 7. Current test run

```
pytest tests/unit/attacks -q
22 passed in 2.52s
```

22 tests pass the prototype but test the **wrong protocol**. All must be rewritten.

---

## 8. Evidence Paths

- `src/datp/attacks/calibration_poisoning.py`
- `src/datp/attacks/poisoning_config.py`
- `src/datp/attacks/poisoning_metrics.py`
- `src/datp/experiments/calibration_poisoning.py`
- `tests/unit/attacks/` (22 tests)
