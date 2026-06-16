# CP2-T037 — Phase C Core Implementation Drift Check

**Date:** 2026-06-16
**Ticket:** CP2-T037 (final Phase C gate)
**Auditor:** automated session
**Verdict: PASS — Phase C core is protocol-faithful. Gate to Phase D OPEN.**

---

## 1. Lock Checks

### 1.1 REPLACE_FIXED_BUDGET injection rule

**Check:** `m_i = max(1, round(f · n_i))` positions replaced with-replacement from
victim-local reservoir; cardinality preserved; no in-place mutation.

**Evidence:**
- `src/datp/attacks/injector.py`: `inject_fixed_budget` uses
  `max(1, round(fraction * clean_cal.size))` (line 52–53); copies clean array before
  modifying; no `clean_cal` mutation.
- `src/datp/attacks/guardrails.py`: `check_no_inplace_mutation` guardrail detects any
  clean-array mutation after injection.
- `tests/unit/attacks/test_injector.py`: cardinality preserved (23 tests pass);
  mutation detection tested.
- `grep "in.place"` → only in docstrings/guardrail prohibition contexts.

**STATUS: PASS**

---

### 1.2 Reservoir is victim-local benign calibration (no test/training scores)

**Check:** Reservoir source is victim-local benign calibration scores only.

**Evidence:**
- `src/datp/attacks/reservoir.py`: `build_reservoir` accepts `clean_cal` (calibration
  scores); no test/training array parameter exists.
- `src/datp/attacks/source_strategies.py`: diagnostic sources raise `DiagnosticSourceError`
  unless `allow_diagnostic=True`.
- `run_manifest.py`: `CP2_RESERVOIR_MODE = "victim_local_benign_cal_source_precedence_rule_2"`.

**STATUS: PASS**

---

### 1.3 B3 absent from CP2 ThresholdPolicy enum

**Check:** `ThresholdPolicy` must not include B3.

**Evidence:**
- `src/datp/attacks/poison_enums.py`: `ThresholdPolicy` = {B1_GLOBAL, B2_PERSONALIZED,
  B4_CLUSTER} — no B3.
- `grep "B3" src/datp/attacks/` → only in prohibition comment ("Replaces the retired
  legacy PoisoningObjective enum").
- B3 exists only in DATP substrate (`thresholding/strategies/b3_family.py`) — not
  imported or used by any CP2 attack module.

**STATUS: PASS**

---

### 1.4 B4 client-indexed Δτ decomposition: Δτ_total = Δτ_agg + Δτ_churn

**Check:** B4 uses frozen clean cluster assignments for Δτ_agg; full re-cluster for
Δτ_total; Δτ_churn = Δτ_total − Δτ_agg.

**Evidence:**
- `src/datp/attacks/b4_recompute.py`: `compute_b4_pair` runs (1) clean B4 → frozen
  assignments; (2) aggregates poisoned taus within frozen clusters → tau_agg; (3) full
  poisoned B4 → tau_pois; (4) Δτ_agg = tau_agg − tau_clean; Δτ_total = tau_pois −
  tau_clean; Δτ_churn = Δτ_total − Δτ_agg.
- `tests/unit/attacks/test_b4_recompute.py`: 11 tests including churn identity check.

**STATUS: PASS**

---

### 1.5 CV(FPR) = σ/µ with NO epsilon denominator

**Check:** `cv()` in `statistics/cv.py` returns `nan` when µ=0; no epsilon added.

**Evidence:**
- `src/datp/statistics/cv.py:22`: `return float(a.std(ddof=ddof) / m)` — no epsilon.
  Returns `nan` when `abs(m) < 1e-15` (literal zero guard, not stabilizer).
- `metric_engine.py`: `cv_fpr = cv(fpr_arr) if n_valid >= 2 else math.nan`.
- `test_metric_engine.py::TestFleetFpr::test_cv_fpr_no_epsilon`: verifies `math.isnan(
  fleet.cv_fpr)` when all FPRs are zero.

**STATUS: PASS**

---

### 1.6 mu_flag_threshold locked before any poisoned run

**Check:** `mu_flag_threshold` must be computed from clean artifacts and set before
any poisoned run reads results.

**Evidence:**
- `run_logger.py`: `emit_manifest` raises `ManifestEmissionError` if
  `manifest.mu_flag_threshold is None`.
- `metric_engine.py`: `compute_mu_flag_threshold(mean_clean_fpr)` computes
  `round(M_clean/8, 2 significant figures)`.
- `test_run_logger.py::TestEmitManifest::test_raises_if_mu_flag_none`: enforced.

**STATUS: PASS**

---

### 1.7 AUROC invariant (test scores never modified)

**Check:** AUROC is identical clean vs. poisoned because test scores are never touched.

**Evidence:**
- `metric_engine.py:compute_auroc_records`: reads `c.test_benign` and `c.test_attack`
  directly from the score collection — never uses poisoned thresholds.
- `test_metric_engine.py::TestAurocRecords::test_auroc_invariant_test_scores_unchanged`:
  same input → identical AUROC.
- Score collection is read-only in Phase C; no code path modifies test arrays.

**STATUS: PASS**

---

### 1.8 Two-layer inference (not 45 independent samples)

**Check:** Inference operates on 5 seed-level aggregates (not 9×5=45 independently).

**Evidence:**
- `inference.py` module docstring: "Do NOT treat 9 clients × 5 seeds = 45 data points
  as 45 independent samples."
- `compute_inference` → `compute_seed_aggregates` → `bootstrap_seed_aggregates`: all
  operate on the 5 seed-level means, not 45 individual deltas.
- `test_inference.py::TestBootstrapSeedAggregates::test_raises_with_too_few_finite`:
  < 2 finite aggregates raises ValueError.

**STATUS: PASS**

---

### 1.9 Sign test is supporting evidence only; Holm is descriptive only

**Check:** Sign test ≥4/5 → 'consistent' (not 'significant'); Holm descriptive_only=True.

**Evidence:**
- `inference.py:Cp2SignTestResult.consistent`: `n_consistent >= _SIGN_CONSISTENCY_THRESHOLD`
  (4/5 threshold).
- `inference.py:Cp2HolmResult.descriptive_only: bool = True`.
- `compute_inference`: `holm=None` by default; only set when `include_holm=True`.

**STATUS: PASS**

---

### 1.10 SeedSequence scheme (no integer seed addition)

**Check:** Seed derivation uses `numpy.random.SeedSequence([t, p, c, s])`; no integer
addition.

**Evidence:**
- `core/seed_sequence.py:_parent_sequence`: `np.random.SeedSequence(list(record.entropy))`.
- `core/seed_sequence.py:make_cp2_rng`: uses `.spawn(child_index + 1)`.
- `run_manifest.py:Cp2SeedRecordModel`: records entropy tuple for manifest round-trip.
- `grep "integer.*seed\|seed.*add"` → no violations in attack modules.

**STATUS: PASS**

---

### 1.11 Edge-IIoTset forbidden

**Check:** No reference to Edge-IIoTset in any CP2 source module.

**Evidence:**
- `grep -rni "edge.iiot" src/datp/` → 0 results.

**STATUS: PASS**

---

### 1.12 No legacy/journal contamination

**Check:** Quarantined files deleted; no stale imports; no journal-only scope.

**Evidence:**
- `calibration_poisoning.py`, `poisoning_config.py`, `poisoning_metrics.py`,
  `experiments/calibration_poisoning.py` all deleted (T028).
- `git status` shows them as `D` (deleted, staged).
- `grep "PoisoningObjective\|attack_rate\|shift_magnitude"` → only in prohibition
  docstrings in remaining code.

**STATUS: PASS**

---

### 1.13 CP2_MATERIALITY_FACTOR single ownership

**Check:** Materiality factor 0.1 has a single canonical source.

**Evidence:**
- After T036 consolidation: `metric_engine.py` imports `CP2_MATERIALITY_FACTOR` from
  `artifacts/poison_names.py`.
- No private `_MATERIALITY_FACTOR` constant in metric_engine.

**STATUS: PASS**

---

## 2. Test Results

| Test scope | Count | Status |
|---|---|---|
| `tests/unit/attacks/` | 282 | PASS |
| `tests/unit/statistics/` | 101 | PASS |
| `tests/unit/thresholding/` | 123 | PASS |
| `tests/unit/evaluation/` | 32 | PASS |
| **Total** | **538** | **PASS** |

---

## 3. Static Analysis

| Tool | Scope | Result |
|---|---|---|
| `pyright` | `src/datp/attacks/` + CP2 modules | 0 errors |
| `ruff --select E,F` | `src/datp/attacks/` | 0 errors |

---

## 4. Graphify

Graphify run in T036: 7381 nodes, 18465 edges, 458 communities. Deferred for T037
(optional per ticket; no new structural changes since T036 run).

---

## 5. Claim Discipline Refresher

**Claims CP2 Phase C enables:**
- Calibration-channel poisoning implemented as REPLACE_FIXED_BUDGET (f ∈ {0, 0.10,
  0.20, 0.40}).
- Three threshold policies (B1/B2/B4) with B4 Δτ decomposition.
- CV(FPR) + coverage ratio + mu_flag_threshold guard.
- Two-layer inference: bootstrap CI on 5 seed-level aggregates (primary).
- Reproducible manifest with SeedSequence entropy.

**Do-not-claim reminders:**
- Do not claim 45 independent replicates.
- Do not claim Holm p-values are inferential.
- Do not claim ASR/blast-radius values from synthetic smoke as paper results.
- Do not claim Phase C runs constitute "experiments" — Phase E is the first real run.
- Do not claim AUROC improvement/degradation — it is invariant by construction.

---

## 6. Gate Decision

**Phase C Core Implementation: COMPLETE.**

All 13 lock checks PASS. 538 tests pass. Pyright 0 errors. Ruff 0 errors.

**Gate to Phase D (Smoke Validation): OPEN.**

Next ticket: CP2-T038 (Phase D entry).
