# CP2-T032 — Attack & Thresholding Drift Check

**Date:** 2026-06-16
**Phase:** C — Core implementation (mid-phase gate)
**Ticket:** CP2-T032
**Verdict:** NO DRIFT — all protocol locks confirmed

---

## 1. Tests Run

```
pytest tests/unit/attacks tests/unit/thresholding -q
317 passed, 9134 warnings in 74.84s
```

pyright clean on all CP2 attack modules:
- `src/datp/attacks/injector.py` → 0 errors
- `src/datp/attacks/reservoir.py` → 0 errors
- `src/datp/attacks/source_strategies.py` → 0 errors
- `src/datp/attacks/threshold_recompute.py` → 0 errors
- `src/datp/attacks/b4_recompute.py` → 0 errors

---

## 2. Drift Scan Results

Pattern scanned: `in.?place|shift_magnitude|cluster label|B3`
in `src/datp/attacks/` and `src/datp/thresholding/`

| Pattern | Occurrences | Context |
|---------|------------|---------|
| `in.?place` | guardrails.py × 4 | `assert_no_inplace_mutation` enforcement function — **POSITIVE** |
| `shift_magnitude` | injector.py × 1 | Comment: "No shift_magnitude" — **POSITIVE** |
| `cluster label` | 0 | — |
| `B3` | guardrails.py × 3, thresholding/thresholds.py × 4, poison_enums.py × 1 | All in prohibition/exclusion context — **POSITIVE** |

**Result: CLEAN — no drift indicators.**

---

## 3. Protocol Lock Verification

### 3.1 REPLACE_FIXED_BUDGET

- `inject_fixed_budget` in `injector.py`: `m = max(1, round(fraction * n))` — ✅
- No `shift_magnitude`, no `attack_rate` — ✅
- `CalibrationInjectionRule.REPLACE_FIXED_BUDGET` is the only enum value — ✅

### 3.2 No In-Place Mutation

- `inject_fixed_budget`: `poisoned = clean_cal.copy()` then modifies `poisoned` — ✅
- `build_reservoir`: returns `pool = sorted_cal[-n_tail:].copy()` — ✅
- Test `TestNoInPlaceMutation` confirms this — ✅
- `assert_no_inplace_mutation` guardrail available for defence-in-depth — ✅

### 3.3 Cardinality Preserved

- `poisoned_cal.shape == c.cal.shape` — verified by `TestCardinalityPreserved` — ✅
- `n_total == c.n_cal` in InjectionResult — ✅

### 3.4 Victim-Local Reservoirs

- `build_reservoir` operates on `clean_cal` only (victim-local) — ✅
- `select_reservoir` dispatches to `build_reservoir` with no cross-client access — ✅
- Test scores are never passed to `build_reservoir` — ✅
- Training scores are never a reservoir — ✅

### 3.5 B3 Absent

- `ThresholdPolicy` enum has no B3 member — ✅
- `assert_policy_not_b3` guardrail blocks B3 if somehow created — ✅
- `compute_b1_pair` and `compute_b2_pair` use B1/B2 only — ✅
- `compute_b4_pair` uses B4 only — ✅

### 3.6 B4 Hyperparameters Locked

- `k=3, n_init=10, random_state=42` passed through from `CP2_B4_*` constants — ✅
- `k_candidates=[k]` prevents silhouette-based K selection in CP2 context — ✅
- `TestDeterminism` confirms reproducibility — ✅
- `TestFractionZero` confirms f=0 → Δτ=0 for B4 — ✅

### 3.7 Client-Indexed B4 Decomposition

- `Cp2B4DecompEntry` has no `cluster_label` field — ✅
- Decomposition: `Δτ_total = Δτ_agg + Δτ_churn` verified with `abs=1e-10` tolerance — ✅
- Test `TestDecompositionIdentity` covers all eligible clients — ✅

### 3.8 SeedSequence Child-Seed Scheme

- `inject_fixed_budget` receives `rng: np.random.Generator` from `make_cp2_rng` — ✅
- No integer seed addition anywhere in attack modules — ✅

### 3.9 Legacy Prototype Removed

- `calibration_poisoning.py`, `poisoning_config.py`, `poisoning_metrics.py` deleted — ✅
- `experiments/calibration_poisoning.py` deleted — ✅
- `rg shift_magnitude src/ tests/` confirms no remnants outside prohibition comments — ✅

---

## 4. Mechanism Framing (Paper-Notes Check)

- Spillover is described as **mechanistic** (via B4 cluster aggregation), not as
  a claim of victim independence violation — ✅
- No causal overclaim in module docstrings — ✅

---

## 5. Summary

All protocol locks for CP2-T026 through CP2-T031 are confirmed faithful.
No protocol drift detected.

**Gate to CP2-T033 (metric engine): OPEN.**
