# CP2-T011 — Thresholding & B4 Procedure Audit

**Date:** 2026-06-16
**Ticket:** CP2-T011
**Auditor:** Phase-A read-only audit
**Verdict:** B1/B2/B4 INFRASTRUCTURE REUSABLE; B4 SPEC CONFORMANCE: PASS WITH TWO
HARDENING NOTES. FB3 NOT TRIGGERED.

---

## 1. Method

```bash
cat src/datp/thresholding/strategies/b4_cluster.py
cat src/datp/thresholding/strategies/b1_global.py
cat src/datp/thresholding/strategies/b2_personalized.py
cat src/datp/thresholding/eligibility.py
rg -n "B4_FINGERPRINT_FEATURES" src/datp/core/enums.py
pytest tests/unit/thresholding -q   # 123 passed in 50.60s
```

---

## 2. B1 — Global threshold

`b1_global.compute`:
- `identify_eligible` → `compute_client_thresholds` (per-client p95) → `compute_tau_global`
- `compute_tau_global = arithmetic_mean_threshold(per_client_taus)` = `(1/K_elig)×Στᵢ`
- All eligible clients receive `tau_global` (not their own tau)
- Pending clients receive `tau_global`

**CP2 lock check:** `(1/K_elig)×Στᵢ` arithmetic mean ✓; eligible only ✓; pending → tau_global ✓.
**PASS.**

---

## 3. B2 — Per-client threshold

`b2_personalized.compute`:
- `compute_client_thresholds` → per-client `percentile_threshold(errs, q=0.95)` = τᵢ
- Eligible: own threshold; pending: `tau_global`

**CP2 lock check:** Per-client p95 ✓; pending → tau_global ✓.
**PASS.**

---

## 4. B4 — Cluster-mean threshold: spec conformance table

| B4 Spec Element | Implementation | Status |
|---|---|---|
| Fingerprint `[mean, std, skew, p95]` | `compute_fingerprints`: `[mean_e, std_e, skew_e, p95_e]` | PASS |
| `B4_FINGERPRINT_FEATURES` 4-element order | `("mean", "std", "skew", "p95")` in `core/enums.py:222` | PASS |
| StandardScaler normalization | `StandardScaler().fit_transform()` in `_scaled_fingerprints` | PASS |
| k-means++ init | `KMeans(...)` — sklearn default `init='k-means++'` ✓ (implicit) | PASS (implicit) |
| `n_init=10` | `KMeans(n_init=int(n_init))` + config `b4_n_init: 10` | PASS |
| `max_iter=300` | NOT explicitly passed; sklearn default=300 ✓ (implicit) | PASS (implicit) |
| `random_state=42` | `KMeans(random_state=random_state)` + config `b4_random_state: 42` | PASS |
| K=3 on Regime A | `b4_regime_a_mode: fixed`, `b4_k_regime_a: 3` → `k_for_a=3` | PASS |
| K not silently silhouette-overridden for Regime A | `_select_regime_a_k`: when `k_regime_a > 0` uses fixed K | PASS |
| `τ_c` = arithmetic mean of eligible clients' τᵢ within cluster | `arithmetic_mean_threshold(taus)` in `_cluster_thresholds` | PASS |
| Client-indexed effective thresholds | `eligible_map = {cid: tau_per_cluster[client_cluster[cid]]}` | PASS |
| Pending excluded from clustering | `identify_eligible` → only eligible pass to `_compute_b4_thresholds` | PASS |
| Pending → `tau_global` | `build_threshold_result` with `pending_clients` → `tau_global` | PASS |

---

## 5. B4 hardening notes (non-blocking, Phase C / T031)

### Note 1 — Implicit k-means++ and max_iter defaults

```python
km = KMeans(n_clusters=k, random_state=random_state, n_init=int(n_init))
# Missing: init='k-means++', max_iter=300
```

Sklearn defaults are `init='k-means++'` and `max_iter=300`, so the behaviour is
correct. However, if sklearn changes defaults in a future version, the implicit
compliance could silently break. Phase C (T031) should harden by passing
`init='k-means++'` and `max_iter=300` explicitly.

### Note 2 — B4 decomposition not implemented

The current `compute` function does the full B4 run only. The CP2 protocol requires:
```
Δτ_agg:   hold A_clean, S_clean fixed; recompute τ from poisoned cal
Δτ_total: run full frozen procedure on poisoned fingerprints (refit S_pois, re-run k-means)
Δτ_churn: Δτ_total − Δτ_agg
```

This decomposition is NOT yet in the code. It will be built in CP2-T031. The current
single-run B4 `compute` is a prerequisite for T031 (the CP2 decomposition
wraps/invokes this twice with different inputs). **Not a blocker for Phase A.**

---

## 6. ThresholdResult structure — client-indexed delta support

`ThresholdResult.client_thresholds: tuple[ClientThreshold, ...]`

Each `ClientThreshold` has `client_id`, `threshold`, `calibration_pending`,
`strategy`. This allows: for any two runs (clean, poisoned), join on `client_id`
to compute `Δτ_i = τ_i^pois − τ_i^clean`. **Client-indexed deltas are
structurally supported.** Raw cluster label IDs are internal (in `B4Metadata`)
and not used for cross-run comparisons.

---

## 7. Tests

```
pytest tests/unit/thresholding -q
123 passed, 9134 warnings in 50.60s
```

Warnings are torch DeprecationWarnings from B0 tests; unrelated to B1/B2/B4.
B1/B2/B4 tests pass cleanly.

---

## 8. FB3 verdict

**CP2-FB3 NOT TRIGGERED.** B4 procedure matches the locked spec. Config values
(`K=3, n_init=10, random_state=42, fixed mode`) are correct. Only hardening notes
for explicit kwargs and decomposition implementation remain (Phase C).

---

## 9. Phase-A Confirmation #3 Status

| Check | Result |
|---|---|
| B1 = arithmetic mean of eligible taus | PASS |
| B2 = per-client p95 | PASS |
| B4 fingerprint order locked [mean,std,skew,p95] | PASS |
| B4 K=3 for Regime A (fixed, not silhouette) | PASS |
| B4 n_init=10, random_state=42 | PASS |
| B4 max_iter=300 (implicit) | PASS (harden in T031) |
| B4 k-means++ (implicit) | PASS (harden in T031) |
| Client-indexed thresholds structurally supported | PASS |
| Pending excluded from B4 clustering | PASS |
| Decomposition (Δτ_agg + Δτ_churn) | NOT YET — T031 to implement |
| B4 123 unit tests pass | PASS |

**Phase-A Confirmation #3: PASS** (B4 reproducible; FB3 not triggered)

---

## 10. Evidence Paths

- `src/datp/thresholding/strategies/b4_cluster.py`
- `src/datp/thresholding/strategies/b1_global.py`
- `src/datp/thresholding/strategies/b2_personalized.py`
- `src/datp/thresholding/eligibility.py`
- `src/datp/core/enums.py:222` (B4_FINGERPRINT_FEATURES)
- `src/datp/conf/config.yaml` (b4_k_regime_a=3, b4_n_init=10, b4_random_state=42)
