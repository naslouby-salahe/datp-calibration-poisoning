# CP2 Phase-A Gate Report

**Date:** 2026-06-16
**Ticket:** CP2-T015
**Blocks:** CP2-T016 (protocol lock)
**Status:** GATE OPEN (with one pending confirmation)

---

## 1. Phase-A Protocol Confirmations

### Confirmation #1 — E=1 clean score artifacts

**Status: PENDING (FB1 triggered)**

- Evidence: `audits/CP2-T007_artifact_audit.md`
- `outputs/` contains only `console_logs/` — no `.parquet` scoring artifacts.
- `src/datp/conf/config.yaml` has `local_epochs: 5` (E=5 forbidden for CP2).
- FB1 has been triggered but **not executed**. Phase A is read-only.
- **Phase B prerequisites before FB1 can run:**
  1. Fix `local_epochs: 5` → `1` in config (T017/T022).
  2. Add `FederationConfig` validator to reject E≠1 at load time (T022).
  3. Obtain explicit authorization before executing retraining.
- **Claim blocked:** "Clean baselines produced under E=1 conference-faithful protocol" is
  NOT writable until FB1 completes and `verify_all_score_cells` confirms provenance.
- **Non-blocking for Phase B protocol lock.** Phase B can proceed with enum design,
  config fix, and injector construction. FB1 runs after the config fix.

### Confirmation #2 — DATP bootstrap variant

**Status: PASS**

- Evidence: `src/datp/reporting/build.py:64` imports `bootstrap_ci`; `build.py:312`
  calls `bootstrap_ci(...)` for all primary CI computation.
- `src/datp/checkpointing/summary.py:206` calls `bca_ci(...)` for the
  `cv_fpr_bca95` checkpoint field — secondary/monitoring only.
- **Decision (inherited verbatim from DATP conference):**
  **Percentile bootstrap** (`bootstrap_ci`) is the primary CP2 CI method.
  BCa (`bca_ci`) is available as a secondary verification field.
- Input to `bootstrap_ci`: 5 seed-level CV(FPR) deltas (policy-level aggregates).
  NOT 9×5=45 independent samples.

### Confirmation #3 — B4 procedural reproducibility (FB3 not triggered)

**Status: PASS**

- Evidence: `audits/CP2-T011_thresholding_b4_audit.md`
- `b4_cluster.py`: K=3 (fixed via `_select_regime_a_k`), k-means++ (sklearn default),
  n_init=10 (explicit), max_iter=300 (sklearn default), random_state=42 (explicit).
- Fingerprint: [mean, std, skew, p95] ✓
- Client-indexed effective thresholds ✓; raw k-means label IDs not compared ✓.
- 123 thresholding unit tests pass.
- **FB3 is NOT triggered.** B4 is reproducible per CP2 spec.
- Hardening notes deferred to T031 (explicit `init='k-means++'`, `max_iter=300` kwargs;
  `Δτ_total = Δτ_agg + Δτ_churn` decomposition).

### Confirmation #4 — No journal contamination in CP2 paths

**Status: PASS**

- Evidence: `audits/CP2-T009_contamination_audit.md`
- Zero forbidden comparators (Edge-IIoTset, FedProx, Ditto, FedRep, FedPer, Laridi,
  FedStatsBenign) in `src/` or `tests/`.
- `conformal_threshold` isolated to substrate (`thresholding/thresholds.py`); not
  wired into `derive_threshold` dispatch for B1/B2/B4.
- `Baseline.B3` exists in DATP substrate enum but is not part of CP2 `ThresholdPolicy`
  (to be created in T016 without B3).
- `local_epochs: 5` is a config YAML flag (not hardcoded in `.py` files); Phase B fix
  is T017/T022.

---

## 2. Venue / Deadline / Submission Status

**Non-gating. Out of scope for CP2 ticket progress.**

This gate report does not gate on venue, deadline, or submission strategy. These are
tracked outside the CP2 ticket system. No protocol confirmation depends on them.

---

## 3. Bootstrap Variant Lock

**Locked: percentile bootstrap (`bootstrap_ci`).**

Inherited verbatim from the DATP conference reporting pipeline
(`src/datp/reporting/build.py`). BCa is available as secondary verification but is
NOT the primary method.

Input requirement: 5 seed-level aggregates (one per training_seed ∈ {0,1,2,3,4}).
Never 45 samples treated as independent.

```python
# CP2 primary CI — to be called in T035 analysis
result = bootstrap_ci(
    deltas,          # np.ndarray of 5 seed-level CV(FPR) deltas
    n_bootstrap=..., # from statistics config
    ci=0.95,
    seed=...,        # from analysis_seed pool
)
```

---

## 4. `mu_flag_threshold` Lock Plan

**Pre-lock plan (to be executed in MVP prep, before any poisoned run):**

```
mu_flag_threshold = round(M_clean / 8, 2 s.f.)
```

where `M_clean` = clean B1 eligible-client mean FPR across all 9 N-BaIoT devices,
averaged over the 5 training seeds (computed from FB1 artifacts once available).

**Lock rule (from CLAUDE.md §3.7):**
- `mu_flag_threshold` must be computed and locked **before** any poisoned run.
- It is a CV-instability flag, not a denominator stabilizer.
- Locking ticket: CP2-T033 (or the MVP-prep ticket that runs first poisoned analysis).
- The value is a project constant; it must not vary across experimental conditions.

**Blocking:** Cannot compute until FB1 artifacts exist (Confirmation #1 pending).
Once FB1 completes, `M_clean` computation and locking are a mandatory prerequisite
before any poisoned experiment.

---

## 5. Phase-B Readiness Assessment

| Item | Status | Action |
|---|---|---|
| Protocol confirmations 2–4 | PASS | None |
| Confirmation #1 (artifacts) | PENDING | Phase B config fix (T017/T022) then FB1 |
| `ThresholdPolicy` enum design | Ready | T016 (first Phase B ticket) |
| Enum: `AttackerObjective`, `SourceStrategy`, `TargetScope` | Ready | T016 |
| `local_epochs: 5` fix | Phase B | T017/T022 |
| `SeedSequence` implementation | Phase B | T019 |
| `REPLACE_FIXED_BUDGET` injector | Phase B | T027 |
| Reservoir selection | Phase B | T026 |
| Artifact provenance gate | Phase B | T021 |
| B4 decomposition | Phase B | T031 |
| Metric engine | Phase B | T033 |
| Sign test + Holm | Phase B | T035 |
| Bootstrap CI (percentile) | Ready (DATP substrate) | T035 wires it |

**Phase B may start. T016 is the first Phase B ticket.**

---

## 6. Blockers Summary

| Blocker | Resolution |
|---|---|
| `local_epochs: 5` in config.yaml | T017/T022: fix to `1`; add validator |
| Clean artifacts absent (FB1 triggered) | Execute FB1 with authorization AFTER T017/T022 config fix |
| `mu_flag_threshold` not yet lockable | Compute from FB1 artifacts; lock before any poisoned run |

No Phase B design tickets are blocked by these items. Only experiment execution
(post-T056) requires FB1 artifacts.

---

## 7. Five End-of-Phase Audits Summary

### Audit 1 — Artifact provenance and E=1 gate

**Verdict: PENDING (FB1 required)**

- Artifacts absent: no `.parquet` files in `outputs/`.
- E=5 config flag: `local_epochs: 5` in `src/datp/conf/config.yaml`.
- FB1 triggered; execution requires (a) Phase B config fix and (b) explicit authorization.
- Scoring infrastructure correct: `compute_reconstruction_errors`, `score_manifest.py`
  (`verify_all_score_cells`, 17 check codes), `schema.py` (`reconstruction_error`).

### Audit 2 — Split, reservoir, and eligibility

**Verdict: PASS**

- Split: 60%/1%/20%/1%/~18% (CHRONOLOGICAL_SPLIT=True, BENIGN_ONLY_CALIBRATION=True).
- All 9 N-BaIoT devices; n_min=100; all 9 ≥ 100 calibration samples → no pending clients.
- Reservoir: source-precedence rule 2 — victim's own clean calibration pool (CAL split);
  test/training scores excluded from reservoir.
- Proxy abstraction documented; with-replacement resampling at high f produces repetition.

### Audit 3 — Forbidden-scope and journal-contamination

**Verdict: PASS (NO CONTAMINATION)**

- Zero forbidden comparators in src/tests.
- `conformal_threshold` substrate-only; B3 DATP substrate (not CP2 policy enum).
- No temporal recalibration; no Edge-IIoTset; no FedProx/Ditto/Laridi.
- Phase B isolation actions: `ThresholdPolicy` enum (T016), `conformal_threshold`
  guardrail (T022), 4 prototype files quarantined (T027 replaces).

### Audit 4 — B4, thresholding, and statistics reuse

**Verdict: PASS**

- B1/B2/B4 strategies confirmed; 123 thresholding tests pass.
- B4: K=3 fixed, fingerprint [mean,std,skew,p95], client-indexed deltas — all correct.
- Bootstrap: percentile primary, BCa secondary; `cv.py` σ/µ no ε; DispersionMetrics/
  BinaryMetrics/AUROC reusable.
- Gaps: sign test, Holm, Δτ metrics, ASR, BlastRadius, seed-level aggregation → T033–T035.

### Audit 5 — Phase B readiness and resume

**Verdict: READY TO PROCEED**

- All Phase A audit notes (T007–T014) complete and consistent.
- No drift found (T014: NO DRIFT).
- T016 is unblocked: enum design requires no artifacts.
- Resume state: this gate report is the Phase A exit document.
- Next ticket: **CP2-T016** (ThresholdPolicy and attack enum design).

---

## 8. Evidence Index

| Source | Ticket | Key Finding |
|---|---|---|
| `audits/CP2-T007_artifact_audit.md` | T007 | Artifacts absent; E=5 config; FB1 triggered |
| `manifests/clean_score_artifacts.json` | T007 | JSON evidence of FB1 |
| `audits/CP2-T008_split_semantics_audit.md` | T008 | Split confirmed; reservoir rule 2 |
| `audits/CP2-T009_contamination_audit.md` | T009 | NO contamination |
| `audits/CP2-T010_attack_prototype_audit.md` | T010 | QUARANTINE+REPLACE all 4 proto files |
| `audits/CP2-T011_thresholding_b4_audit.md` | T011 | B4 PASS; FB3 NOT triggered |
| `audits/CP2-T012_statistics_reporting_audit.md` | T012 | Reuse map; gaps → T033–T035 |
| `audits/CP2_PHASE_A_SUMMARY.md` | T013 | Full decision map |
| `audits/CP2-T014_audit_phase_drift_check.md` | T014 | NO DRIFT |
| `src/datp/reporting/build.py:64,312` | T015 | Percentile bootstrap (DATP primary) |
| `src/datp/checkpointing/summary.py:206` | T015 | BCa secondary checkpoint field |
