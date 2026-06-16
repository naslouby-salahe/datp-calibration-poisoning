# CP2-T041 — Smoke-Validation Drift Check (Phase D → Phase E gate)

**Date:** 2026-06-16
**Ticket:** CP2-T041 (scientific-drift gate before real data)
**Auditor:** automated session
**Verdict: PASS — all smoke invariants asserted and passing on synthetic data;
pipeline is protocol-faithful end to end; CPU-only and real-data-independent.
Gate to Phase E (real N-BaIoT) is OPEN.**

---

## 0. Invariant-source reconciliation (read first)

The Phase D tickets (CP2-T038/T039 §3) and the protocol-of-record
`docs/DATP_CP_Roadmap.md` §10 line 142 each enumerate "11 smoke invariants" but the
two lists are **not identical**. Per CLAUDE.md source-of-truth hierarchy the roadmap
outranks the ticket index, and this ticket (§2) audits against roadmap §11. The smoke
harness therefore asserts the **union** of both lists (see decision log 2026-06-16).
This report verifies every distinct invariant from both authorities.

Harness: `src/datp/testsupport/cp2_smoke_harness.py`
Tests:   `tests/integration/attacks/test_cp2_smoke.py` (19 tests, all passing)

---

## 1. Prompt/ticket invariants (CP2-T038/T039)

| # | Invariant | Test | Status |
|---|---|---|---|
| 1 | `f=0` reproduces clean exactly; zero Δτ (all 3 policies) | `test_invariant_1_f0_reproduces_clean_zero_delta` | PASS |
| 2 | Cardinality preserved (`n_i` constant); eligibility invariant | `test_invariant_2_cardinality_preserved` | PASS |
| 3 | Clean arrays never mutated in place | `test_invariant_3_no_inplace_mutation` | PASS |
| 4 | HIGH raises / LOW lowers (B2 victim direction) | `test_invariant_4_high_raises_low_lowers_b2` | PASS |
| 5 | Calibration-Pending excluded from victims/CV(FPR); gets `tau_global` (all 3 policies) | `test_invariant_5_pending_excluded_and_gets_tau_global` | PASS |
| 6 | Determinism: same seeds → identical poisoned arrays + metrics | `test_invariant_6_determinism` | PASS |
| 7 | B4 `Δτ_total = Δτ_agg + Δτ_churn`; client-indexed; finite | `test_invariant_7_b4_decomposition_identity` | PASS |
| 8 | Two-layer stats: bootstrap on **5** seed aggregates, not 45 | `test_invariant_8_two_layer_bootstrap_on_seed_aggregates` | PASS |
| 9 | Manifest round-trips (child seeds, locks, reservoir mode, `mu_flag`); emit blocked when `mu_flag` None | `test_invariant_9_manifest_round_trip`, `..._requires_locked_mu_flag` | PASS |
| 10 | AUROC invariant (test scores unchanged) | `test_invariant_10_auroc_invariant` | PASS |
| 11 | CV(FPR) reported with coverage; `nan` (no ε) when µ=0 | `test_invariant_11_cv_fpr_reported_with_coverage`, `..._no_epsilon_returns_nan_when_mean_zero` | PASS |

## 2. Roadmap §10 invariants not in the prompt list

| Roadmap invariant | Test | Status |
|---|---|---|
| RANDOM_BENIGN → near-null (negative control) | `test_roadmap_random_benign_near_null` | PASS |
| B1 victim shift < B2 victim shift (same single-client attack) | `test_roadmap_b1_shift_less_than_b2_shift` | PASS |
| B4 K stays fixed at 3 under clean **and** poisoned cal | `test_roadmap_b4_k_fixed_at_three` | PASS |
| Outputs written to temp only (no `conference_calibration_poisoning/`) | `test_roadmap_outputs_in_temp_only` | PASS |

Roadmap invariants that map onto prompt invariants (not double-counted): "clean
arrays never mutated" → prompt 3; "reproducibility" → prompt 6; "AUROC invariant" →
prompt 10; "B4 decomposition computable & finite" → prompt 7.

**Full coverage: 11 prompt invariants + 4 distinct roadmap invariants = 15 distinct
assertions, all asserted and passing.**

---

## 3. No invariant weakened during CP2-T040 consolidation

CP2-T040 added no skips/xfails and removed no assertions from the CP2 smoke suite
(`rg "@pytest.mark.skip|xfail|pytest.skip" tests/integration/attacks` → 0). All
assertions are behavior-based over the real pipeline (no mocks). See
`CP2-T040_smoke_test_consolidation.md`.

---

## 4. CPU-only / deterministic / no-real-data confirmation

- No CUDA/GPU calls in the smoke path; the only `cuda`/`gpu` hits in CP2 files are
  docstrings. Real-data DATP gates live only in DATP substrate tests (out of scope).
- All randomness flows through `SeedSequence` (`make_cp2_rng`) — no integer seed
  addition. Determinism invariant (6) passing confirms reproducibility.
- The harness reads only synthetic arrays from `testsupport/synthetic_scores.py`; it
  never touches `data/raw/` or `outputs/`. Invariant (roadmap) confirms no real
  output root is created.

---

## 5. Test + static results

| Scope | Result |
|---|---|
| `pytest tests/integration/attacks/test_cp2_smoke.py` | 19 passed |
| `pytest tests/unit/attacks tests/integration/attacks` | 301 passed |
| CP2-relevant broad suite (8 unit dirs + integration/attacks) | 1241 passed |
| `pyright` (changed CP2 files) | 0 errors, 0 warnings |
| `ruff --select E,F` (changed CP2 files) | clean |

Pre-existing DATP-substrate collection errors: 4 at drift-gate time (down from 8),
none CP2. **All 4 subsequently repaired (post-gate, user request)** — full collection
now 1878 collected, 0 errors. See `CP2-T040_smoke_test_consolidation.md` §6.

---

## 6. Locks re-verified against README §9 / CLAUDE.md §3

- REPLACE_FIXED_BUDGET, cardinality preserved, no in-place mutation — invariants 2/3.
- Reservoir victim-local benign cal only — manifest `reservoir_mode` round-trip (9).
- B3 absent — only B1/B2/B4 exercised (`_ALL_POLICIES`).
- B4 K=3, decomposition identity — roadmap K-fixed + invariant 7.
- CV(FPR) no ε + coverage — invariant 11.
- `mu_flag_threshold` locked from clean **before** poisoned metrics — harness order
  (clean baseline → lock → poisoned), enforced at emit (invariant 9b).
- Two-layer inference, bootstrap on 5 aggregates — invariant 8.
- SeedSequence, no integer addition — §4 above.
- No Edge-IIoTset; no journal scope — none imported by harness/test.

---

## 7. Gate decision

All 11 prompt invariants + 4 distinct roadmap invariants are asserted and passing;
no assertion was weakened; the pipeline is CPU-only, deterministic, and real-data
independent. **CP2-T041 PASS. Gate to Phase E (real N-BaIoT MVP) is OPEN.**

Phase E may now load real N-BaIoT artifacts — subject to the still-open FB1 gate
(clean E=1 artifacts must be produced first; see decision log CP2-T007 FB1 and the
Phase A/B/C AUDIT entry on `config.yaml local_epochs`). The smoke harness itself
imposes no real-data dependency.
