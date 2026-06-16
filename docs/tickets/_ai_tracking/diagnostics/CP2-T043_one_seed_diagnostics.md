# CP2-T043 — One-Seed/One-Victim & One-Seed/All-Victims Diagnostics

**Date:** 2026-06-16
**Ticket:** CP2-T043 (Phase E — real-data diagnostic ladder, rung 1)
**Type:** integration / read-only diagnostic (no production artifacts written)
**Verdict: PASS.** Real N-BaIoT calibration-channel poisoning produces
directionally-correct, feasible, policy-differentiated effects on `training_seed=0`.
Phase E may proceed to CP2-T044.

---

## 0. Setup

- Data: real E=1 N-BaIoT clean score artifacts from FB1 execution (`outputs/`,
  `REGIME_A_NBAIOT`, `training_seed=0`).
- Loader: `datp.attacks.real_score_loader.load_real_score_collection`.
- Cell runner: `datp.attacks.mvp_runner.run_mvp_cell` /
  `lock_mu_flag_threshold` (CP2-T044-authorized primitives, built on the
  shared `datp.attacks.cell_runner` orchestration also used by the Phase D
  synthetic smoke harness).
- `mu_flag_threshold` locked once from clean B1 eligible-client mean FPR
  **before** any poisoned cell ran: `mu_flag_threshold = 0.005`.
- Eligibility: 9/9 N-BaIoT clients eligible, 0 Calibration-Pending
  (`n_min=100`; matches CP2-T042 finding).
- `poisoning_seed=100` throughout (first locked poisoning seed); no other
  seeds used at this rung (multi-seed aggregation is CP2-T044+ scope, not
  T043).
- No in-place mutation: verified via `datp.attacks.guardrails.assert_no_inplace_mutation`
  on the victim's clean calibration array before/after every cell in the
  one-victim sweep.

Script: ad hoc, read-only, run directly against real artifacts (not committed
— diagnostic only, per ticket guidance "keep cheap; do not launch the full
matrix"). Raw output captured below; row-level JSON retained at
`/tmp/cp2_t043_one_victim_rows.json` and `/tmp/cp2_t043_all_victim_rows.json`
for this session (ephemeral; not a production artifact).

---

## 1. One seed / one victim

Victim: `Danmini_Doorbell` (`n_cal=9909`). Swept all 3 policies
(`B1_GLOBAL`, `B2_PERSONALIZED`, `B4_CLUSTER`) × 3 sources (`RANDOM_BENIGN`,
`HIGH_SCORE_BENIGN`, `LOW_SCORE_BENIGN`) × 4 fractions (`0, 0.10, 0.20, 0.40`)
= 36 cells.

### 1.1 Cardinality, AUROC invariance, exact-zero at f=0

All 36 cells: `cardinality_unchanged=True` (REPLACE_FIXED_BUDGET preserves
`n_i`), `auroc_invariant=True` (`math.isclose(auroc_clean, auroc_poisoned,
abs_tol=1e-12)` — test scores untouched by calibration-channel poisoning, as
required), and every `f=0.00` cell gives `delta_tau == 0.0` exactly (no
no-op-injection drift) across all 9 (policy, source) combinations. No
violations found in any of the 36 cells.

### 1.2 Direction check (f=0.40; expect HIGH↑, LOW↓, RANDOM near-null)

| Policy | RANDOM | HIGH | LOW |
|---|---|---|---|
| B1_GLOBAL | −0.003275 | **+0.183953** | **−0.027384** |
| B2_PERSONALIZED | −0.029477 | **+1.655576** | **−0.246454** |
| B4_CLUSTER | −0.014738 | **+1.805393** | **−0.123227** |

Direction is correct for all 3 policies: HIGH_SCORE_BENIGN strictly raises
τ, LOW_SCORE_BENIGN strictly lowers τ, RANDOM_BENIGN stays an order of
magnitude smaller than either directional source and does not show a
consistent sign. This matches the THRESHOLD_RAISE / THRESHOLD_LOWER
objective semantics and the CP2 attack-mechanics lock.

Magnitude ordering (|Δτ| at f=0.40, HIGH source) is
`B1 (0.184) < B4 (1.805) ≈ B2 (1.656)` — expected, since B1_GLOBAL averages
the victim's shift across all 9 eligible clients while B2/B4 concentrate it
on the victim (B2 fully, B4 within-cluster).

### 1.3 Full one-victim grid (all 36 cells)

```
policy=b1_global          source=random_benign      f=0.00  delta_tau=+0.000000  card_ok=True  auroc_inv=True
policy=b1_global          source=random_benign      f=0.10  delta_tau=+0.002519  card_ok=True  auroc_inv=True
policy=b1_global          source=random_benign      f=0.20  delta_tau=-0.001649  card_ok=True  auroc_inv=True
policy=b1_global          source=random_benign      f=0.40  delta_tau=-0.003275  card_ok=True  auroc_inv=True
policy=b1_global          source=high_score_benign  f=0.00  delta_tau=+0.000000  card_ok=True  auroc_inv=True
policy=b1_global          source=high_score_benign  f=0.10  delta_tau=+0.035696  card_ok=True  auroc_inv=True
policy=b1_global          source=high_score_benign  f=0.20  delta_tau=+0.075674  card_ok=True  auroc_inv=True
policy=b1_global          source=high_score_benign  f=0.40  delta_tau=+0.183953  card_ok=True  auroc_inv=True
policy=b1_global          source=low_score_benign   f=0.00  delta_tau=+0.000000  card_ok=True  auroc_inv=True
policy=b1_global          source=low_score_benign   f=0.10  delta_tau=-0.007357  card_ok=True  auroc_inv=True
policy=b1_global          source=low_score_benign   f=0.20  delta_tau=-0.019574  card_ok=True  auroc_inv=True
policy=b1_global          source=low_score_benign   f=0.40  delta_tau=-0.027384  card_ok=True  auroc_inv=True
policy=b2_personalized    source=random_benign      f=0.00  delta_tau=+0.000000  card_ok=True  auroc_inv=True
policy=b2_personalized    source=random_benign      f=0.10  delta_tau=+0.022670  card_ok=True  auroc_inv=True
policy=b2_personalized    source=random_benign      f=0.20  delta_tau=-0.014844  card_ok=True  auroc_inv=True
policy=b2_personalized    source=random_benign      f=0.40  delta_tau=-0.029477  card_ok=True  auroc_inv=True
policy=b2_personalized    source=high_score_benign  f=0.00  delta_tau=+0.000000  card_ok=True  auroc_inv=True
policy=b2_personalized    source=high_score_benign  f=0.10  delta_tau=+0.321263  card_ok=True  auroc_inv=True
policy=b2_personalized    source=high_score_benign  f=0.20  delta_tau=+0.681070  card_ok=True  auroc_inv=True
policy=b2_personalized    source=high_score_benign  f=0.40  delta_tau=+1.655576  card_ok=True  auroc_inv=True
policy=b2_personalized    source=low_score_benign   f=0.00  delta_tau=+0.000000  card_ok=True  auroc_inv=True
policy=b2_personalized    source=low_score_benign   f=0.10  delta_tau=-0.066217  card_ok=True  auroc_inv=True
policy=b2_personalized    source=low_score_benign   f=0.20  delta_tau=-0.176167  card_ok=True  auroc_inv=True
policy=b2_personalized    source=low_score_benign   f=0.40  delta_tau=-0.246454  card_ok=True  auroc_inv=True
policy=b4_cluster         source=random_benign      f=0.00  delta_tau=+0.000000  card_ok=True  auroc_inv=True
policy=b4_cluster         source=random_benign      f=0.10  delta_tau=+0.011335  card_ok=True  auroc_inv=True
policy=b4_cluster         source=random_benign      f=0.20  delta_tau=-0.007422  card_ok=True  auroc_inv=True
policy=b4_cluster         source=random_benign      f=0.40  delta_tau=-0.014738  card_ok=True  auroc_inv=True
policy=b4_cluster         source=high_score_benign  f=0.00  delta_tau=+0.000000  card_ok=True  auroc_inv=True
policy=b4_cluster         source=high_score_benign  f=0.10  delta_tau=+0.471081  card_ok=True  auroc_inv=True
policy=b4_cluster         source=high_score_benign  f=0.20  delta_tau=+0.830888  card_ok=True  auroc_inv=True
policy=b4_cluster         source=high_score_benign  f=0.40  delta_tau=+1.805393  card_ok=True  auroc_inv=True
policy=b4_cluster         source=low_score_benign   f=0.00  delta_tau=+0.000000  card_ok=True  auroc_inv=True
policy=b4_cluster         source=low_score_benign   f=0.10  delta_tau=-0.033108  card_ok=True  auroc_inv=True
policy=b4_cluster         source=low_score_benign   f=0.20  delta_tau=-0.088084  card_ok=True  auroc_inv=True
policy=b4_cluster         source=low_score_benign   f=0.40  delta_tau=-0.123227  card_ok=True  auroc_inv=True
```

Monotonicity: within each (policy, directional-source) row, `|delta_tau|`
increases monotonically with fraction (0 → 0.10 → 0.20 → 0.40) in all 6
directional series. RANDOM_BENIGN does not show monotonic growth (expected —
it is not a directional attack).

---

## 2. One seed / all victims (feasibility coverage + blast radius)

Swept all 9 eligible victims × 3 policies × 3 sources at `f=0.40` = 81 cells.

**Feasibility coverage: 9/9 eligible victims tested successfully.** No
victim was infeasible (no victim has too few calibration samples to support
`m_i = max(1, round(0.40 · n_i))` replacement, consistent with all 9 being
eligible/non-pending).

### 2.1 Blast radius (HIGH_SCORE_BENIGN, f=0.40), by policy

`blast_fraction` = fraction of the 9 eligible clients whose per-client Δτ
exceeds that client's own materiality scale (`0.1 × IQR(clean cal)`) —
i.e. mechanistic propagation, not an independence violation
(`datp.attacks.diagnostics.compute_blast_radius`).

| Policy | Δτ range across 9 victims | mean blast_fraction |
|---|---|---|
| B1_GLOBAL | [+0.011339, +0.316908] | **1.0000** (9/9) |
| B2_PERSONALIZED | [+0.102050, +2.852175] | **0.1111** (1/9) |
| B4_CLUSTER | [+0.033778, +2.777851] | **0.8889** (8/9) |

This is the expected qualitative ordering for the locality hypothesis:

- **B1 = 100%.** A single global threshold is shared by all eligible
  clients, so any victim's shift propagates to the entire fleet by
  construction. Matches CP2's "global policy → maximal blast radius"
  expectation exactly.
- **B2 = 11.1% (1/9).** Personalized per-client thresholds are computed
  from each client's own calibration set; only the victim's own threshold
  moves. No spillover to any other client, for any of the 9 victims tested.
  Matches the "personalized policy → fully local" expectation exactly.
- **B4 = 88.9% (8/9).** This is qualitatively between B1 and B2 as
  hypothesized (cluster-mediated propagation is real and present), but the
  *magnitude* — 8 of 9 clients flagged significant, not just the victim's
  own ~3-member K=3 cluster — is higher than a naive "blast radius ≈
  cluster size / fleet size" intuition (~33%) would suggest. This is not
  necessarily wrong: B4's lock specifies `Δτ_total = Δτ_agg + Δτ_churn`,
  and churn from cluster-membership reassignment after a victim's shift can
  affect clients outside the victim's original cluster, and the
  per-client materiality scale (`0.1 × IQR`) is small relative to the
  N-BaIoT calibration-score distributions seen here. **Flagging for
  closer audit at CP2-T046/T047** (multi-seed B4 blast-radius statistics)
  rather than asserting a conclusion now — this single-seed result should
  not be over-interpreted, but it is not a null/incorrect result either:
  B4 is still strictly below B1 and strictly above B2, which is the
  qualitative ordering CP2 needs.

### 2.2 RANDOM_BENIGN (f=0.40), all 9 victims, for reference

```
b1_global RANDOM delta_tau range: -0.003275  +0.008464
b2_personalized RANDOM delta_tau range: -0.029477  +0.076172
b4_cluster RANDOM delta_tau range: -0.111961  +0.025391
```

RANDOM_BENIGN deltas stay roughly an order of magnitude (B1, B2) to
comparable-but-mixed-sign (B4) smaller than the HIGH_SCORE_BENIGN deltas in
§2.1, and do not show a consistent sign across victims — consistent with
RANDOM_BENIGN being a non-directional control rather than an attack.

---

## 3. Acceptance criteria check (ticket §11)

> One-seed diagnostics produce directionally-correct, feasible effects;
> reports written; pyright green.

- Directionally correct: §1.2, §1.3 (HIGH↑/LOW↓ in all 3 policies, all 4
  nonzero fractions, monotonic in fraction).
- Feasible: §2 (9/9 eligible victims feasible at f=0.40, the largest MVP
  fraction).
- Cardinality preserved, no in-place mutation, AUROC invariant: §1.1.
- Policy-differentiated blast radius observed and qualitatively correct
  (B2 < B4 < B1): §2.1.
- pyright: `python -m pyright src/datp/attacks/real_score_loader.py
  src/datp/attacks/mvp_runner.py src/datp/attacks/cell_runner.py` → 0
  errors, 0 warnings (re-verified same session as CP2-T044 build, see
  CP2-T044 evidence).

**Verdict: PASS. No blocking condition (ticket §12) triggered — effects are
neither null nor incorrect.**

---

## 4. Outcome

CP2-T043 is done. Phase E may proceed to CP2-T044 (lock the bounded MVP run
plan) using the same `real_score_loader` / `mvp_runner` primitives exercised
here.
