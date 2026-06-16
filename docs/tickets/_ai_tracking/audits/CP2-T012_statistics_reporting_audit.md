# CP2-T012 — Scoring/Statistics/Reporting Reuse Audit

**Date:** 2026-06-16
**Ticket:** CP2-T012
**Auditor:** Phase-A read-only audit
**Verdict:** SUBSTANTIAL REUSE AVAILABLE; SIGN TEST + HOLM CORRECTION + CP2-SPECIFIC
METRICS MISSING → T033/T035 to build.

---

## 1. Method

```bash
find src/datp/statistics src/datp/reporting src/datp/evaluation -name "*.py"
cat src/datp/statistics/{bootstrap,cv,wilcoxon,constants}.py
cat src/datp/evaluation/metrics.py
rg -n "sign_test|Holm|holm" src/
rg -n "auroc|roc_auc" src/datp/evaluation/
pytest tests/unit/statistics tests/unit/reporting -q   # 101 passed in 9.96s
```

---

## 2. Reuse map

### 2.1 Bootstrap CI — REUSABLE

| Function | Status | CP2 use |
|---|---|---|
| `bootstrap_ci(deltas, n_bootstrap, ci, seed)` — percentile | PRESENT ✓ | Primary; "bootstrap CI on 5 seed-level aggregates (DATP variant if found, else percentile)" |
| `bca_ci(deltas, n_bootstrap, ci, seed)` — BCa | PRESENT ✓ | "DATP variant if found" — both variants present |
| `BootstrapResult` | PRESENT ✓ | Structured return type |

Both are in `src/datp/statistics/bootstrap.py`.

### 2.2 CV(FPR) — REUSABLE

`cv(arr, ddof=1) = std(arr, ddof=1) / mean(arr)`:
- Returns `nan` if `|mean| < 1e-15` (near-zero guard, not ε denominator) ✓
- CP2 spec: `σ/µ` with no ε denominator ✓
- When mean → 0, CV is `nan` → absolute metrics (IQR, max-min, WorstClientFPR) take over (consistent with `mu_flag_threshold` logic to be added in T033)

### 2.3 Wilcoxon test — REUSABLE (supporting/descriptive only)

`wilcoxon_test(x, y)` present. CP2 spec: Wilcoxon is **supporting evidence only** (not primary). Reusable as-is.

### 2.4 Dispersion metrics — LARGELY REUSABLE

`DispersionMetrics` in `src/datp/evaluation/metrics.py` already has:

| Field | CP2 use |
|---|---|
| `cv_fpr` via `cv()` | Primary CP2 dispersion metric |
| `mean_fpr` | `mu_flag_threshold` denominator (T033) |
| `std_fpr` | Component of CV(FPR) |
| `iqr_fpr` | Small-denominator guard |
| `max_min_fpr_gap` | Small-denominator guard |
| `worst_client_fpr` | `WorstClientFPR = max_i FPR_i` |

**Note:** `DispersionMetrics` uses `eligible_ids` correctly (pending clients excluded from FPR array). ✓

### 2.5 Binary metrics — REUSABLE

`BinaryMetrics`: `fpr`, `tpr`, `macro_f1`, `balanced_accuracy`. All CP2 secondary metrics are here. `recompute_binary_metrics` can be called with poisoned thresholds. ✓

### 2.6 AUROC — REUSABLE

`evaluation/ranking.py`: `BinaryRankingMetrics.auroc` via `sklearn.metrics.roc_auc_score`. CP2 uses AUROC as an invariance check (test scores unchanged → AUROC unchanged). Reusable. ✓

---

## 3. Gaps — to be built in T033/T035

| Missing function | CP2 protocol requirement | Ticket |
|---|---|---|
| `sign_test(deltas)` — exact paired sign test | "≥4/5 sign consistency; exact paired sign test supporting only" | T035 |
| `holm_correct(p_values, alpha)` | "Holm-adjusted p-values descriptive only" | T035 |
| `Δτ_i = τ^pois − τ^clean` | Primary endpoint | T033 |
| `Δτ_rel = Δτ / max(\|τ_clean\|, ε)` | Relative shift | T033 |
| `δ_{τ,i} = 0.1 · IQR(cal_scores_i)` | Materiality scale | T033 |
| `ASR_raise = mean(1[Δτ ≥ δ])` | Attack success rate | T033 |
| `BlastRadius_p = (1/K_elig) Σ 1[\|Δτ_i\| ≥ δ_i]` | Blast radius | T034 |
| `SpilloverCount_p` | Spillover diagnostic | T034 |
| `mu_flag_threshold` instability flag | CV instability guard | T033 |
| Coverage ratio | Required alongside CV(FPR) | T033 |
| Seed-level aggregate helper | Layer-2 statistical unit | T035 |
| Paired comparison function | Clean-vs-poisoned join on client_id | T035 |
| Run manifest / logging | Provenance of each run | T035 |

**Holm correction**: Only `bonferroni_correct` exists; need to add `holm_correct`
(sequential Bonferroni variant). Not hard — scipy can compute, or implement directly.

**Sign test**: No implementation. Need exact binomial p-value for `k` consistent-sign
out of `n` seeds; `scipy.stats.binomtest(k, n, 0.5)` will suffice.

---

## 4. CV(FPR) compliance note

`cv.py`: `std(ddof=1) / mean` — uses **sample standard deviation** (ddof=1).
CP2 spec says `σ/µ` without specifying ddof. DATP conference paper presumably used
ddof=1. Acceptable for n≥5 seeds. **No action needed.**

Note: the `cv` function uses an implicit `1e-15` near-zero guard. The spec says "no
ε denominator" — this guard is a numerical precision protection, NOT an ε
regularizer. Compliant.

---

## 5. Tests

```
pytest tests/unit/statistics tests/unit/reporting -q
101 passed in 9.96s
```

Existing statistics/reporting tests pass. No CP2-specific test coverage yet (to be
added in T033/T035).

---

## 6. Reuse/gap summary

| Category | Status |
|---|---|
| Percentile bootstrap CI | REUSE |
| BCa bootstrap CI | REUSE |
| CV(σ/µ, no ε) | REUSE |
| Wilcoxon test (supporting only) | REUSE |
| DispersionMetrics (cv_fpr, iqr_fpr, max_min, worst_client) | REUSE |
| BinaryMetrics (fpr, tpr, macro_f1) | REUSE |
| AUROC | REUSE |
| Sign test (exact paired) | BUILD (T035) |
| Holm correction | BUILD (T035) |
| Δτ, Δτ_rel, δ_{τ,i} | BUILD (T033) |
| ASR_raise, ASR_lower | BUILD (T033) |
| BlastRadius, SpilloverCount | BUILD (T034) |
| mu_flag_threshold instability flag | BUILD (T033) |
| Coverage ratio | BUILD (T033) |
| Seed-level aggregate + paired comparison | BUILD (T035) |

---

## 7. Evidence Paths

- `src/datp/statistics/bootstrap.py`
- `src/datp/statistics/cv.py`
- `src/datp/statistics/wilcoxon.py`
- `src/datp/evaluation/metrics.py` (DispersionMetrics, BinaryMetrics)
- `src/datp/evaluation/ranking.py` (AUROC)
