# CP2-T055 — Full-Scope Drift Check

**Date:** 2026-06-16
**Type:** scientific-drift (read-only)
**Scope of this check:** the Phase-F **implementation** additions made under the
CP2-T049 = CONTINUE gate (CP2-T050 fraction 0.05, CP2-T051 multi-client pattern
selection + injection, CP2-T052 trimmed-calibration defense) and the CP2-T054
feasibility verdict. **No Phase-F experiment has run** — execution stays gated at
CP2-T056 — so this drift check covers code/config/contract drift, not run-output
drift (the run-output drift gate is re-applied at CP2-T056).

**Verdict:** **PASS** — no protocol lock drifted while broadening scope.

---

## 1. Checks against `docs/DATP_CP_Roadmap.md` §5–§14 and CLAUDE.md §3 locks

### 1.1 Fraction extension only (T050)
- `FULL_SWEEP_FRACTIONS = (0.0, 0.05, 0.10, 0.20, 0.40)` — exactly the bounded
  grid `(0.0, 0.10, 0.20, 0.40)` plus `0.05`. Verified
  `set(BOUNDED) | {0.05} == set(FULL)`.
- `enumerate_full_sweep_matrix` delegates to the same `_enumerate_single_victim_matrix`
  helper as the bounded enumerator; only the fraction grid differs. Full matrix
  is a strict superset of the bounded matrix; the difference set is exactly the
  `0.05` cells (unit-tested). Policies (B1/B2/B4, no B3), bounded sources, the 5
  locked seed pairs, and `SINGLE_CLIENT` scope are unchanged.
- The fraction guardrail now derives its full grid from `FULL_SWEEP_FRACTIONS`
  (single source of truth); `0.05` is accepted under FULL and rejected under
  BOUNDED. **PASS.**

### 1.2 Multi-client independent streams (T051)
- Pattern selection (`compromise_patterns.py`) uses
  `np.random.SeedSequence([COMPROMISE_PATTERN_SEED])` with
  `COMPROMISE_PATTERN_SEED = 400`; **no integer seed addition** (grep clean).
- `select_triples` returns exactly 20 distinct triples by default
  (`DEFAULT_N_TRIPLES = 20`); deterministic under seed 400.
- `inject_multi_victim` poisons each co-victim through `inject_single_victim`,
  whose RNG is keyed by the victim's own client index via `make_seed_rng`
  (`SeedSequence([training_seed, poisoning_seed, client_idx, scope_idx])`). Each
  co-victim's stream is therefore independent and identical to its solo stream
  (unit-tested), with no shared or added seeds.
- Clean arrays are not mutated in place (non-victims copied; injector copies
  internally) — unit-tested. **PASS.**

### 1.3 Trimmed-calibration defense (T052)
- Defense is the locked enum member `PoisoningDefense.TRIMMED_CALIBRATION`; no new
  defense variants added.
- Trim fraction comes from config (`CalibrationPoisoningConfig.trim_fraction`,
  default `TRIM_FRACTION_PRIMARY = 0.05`; `TRIM_FRACTION_APPENDIX = 0.10`
  appendix-only) — not hardcoded in logic; validated to `[0, 0.5)`.
- Trimming is applied **before** the threshold percentile and **before** B4
  fingerprinting: the defense produces a defended `ScoreCollection` (trimmed cal)
  and a defended poisoned-cal dict, then the **existing** `recompute_pair` runs
  unchanged, so trimming necessarily precedes both the percentile and the B4
  clustering/fingerprint.
- `trimmed_calibration` never mutates its input (sorts a copy, returns a slice
  copy) — unit-tested.
- **No robustness overclaim.** Unit tests assert the *mechanism* (trimming
  removes injected tail contamination; reduces |Δτ| when the trim covers the
  contamination), and explicitly document that the in-range-reservoir regime can
  leave |Δτ| barely changed or slightly worse — the honest cost CP2-T053 must
  report. **PASS.**

### 1.4 CICIoT2023 strictly feasibility-gated; no device fabrication (T054)
- CP2-T054 verdict is INFEASIBLE-NOW (DEFERRED); no stretch run occurred.
- Pseudo-clients remain file-level (`ClientIdentity.MERGED_FILE`); never
  presented as physical devices.
- FB4 stays NOT TRIGGERED.
- **Edge-IIoTset absent** from all new code (grep clean); raw on disk is unused.
  **PASS.**

### 1.5 No journal scope, forbidden comparators, or overclaims
- Grep over new/changed source for `Edge-IIoTset|FedProx|Ditto|FedRep|FedPer|
  Laridi|B-FedStatsBenign|journal`: the only hit is the pre-existing
  `AuditDisposition.QUARANTINE_JOURNAL` enum member (a Phase-A audit verdict for
  quarantining stale logic — not journal-extension scope). No forbidden
  comparators or journal scope introduced. **PASS.**

### 1.6 Unchanged primary locks
- B4 `K=3` and all B4 hyperparameters untouched (no edits to `b4_recompute.py`
  or B4 config).
- `mu_flag_threshold` pre-poison lock path untouched.
- E=1 lock, REPLACE_FIXED_BUDGET, victim-local reservoirs, CV(FPR) without
  epsilon, seed pools — none modified.
- The FULL execution stage (`ExperimentStage.NBAIOT_FULL`) keeps
  `allow_run=False` behind `full_scope_continue_decision`; CICIOT2023_STRETCH
  keeps `allow_run=False`. **No execution was unlocked.** **PASS.**

## 2. Static / test evidence
- `pyright` on all changed source + new tests: 0 errors.
- `ruff` (project default select) on all changed files: clean; new files also
  clean under explicit `--select E501`.
- `pytest tests/unit/attacks tests/unit/thresholding tests/unit/config`:
  **601 passed**.

## 3. Conclusion
All Full-scope **implementation** additions preserved every CP2 protocol lock.
No drift. The only remaining Full-scope gate is the run-output drift re-check at
CP2-T056, once (and if) execution is authorized.
