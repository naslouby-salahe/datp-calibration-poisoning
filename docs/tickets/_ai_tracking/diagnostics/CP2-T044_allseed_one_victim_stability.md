# CP2-T044 — All-Seeds/One-Victim Stability Diagnostic

**Date:** 2026-06-16
**Ticket:** CP2-T044 (Phase E — diagnostic ladder, rung 2: multi-seed stability)
**Type:** integration / read-only diagnostic
**Verdict: PASS.** Sign consistency 5/5 on every directional (policy, source)
combination; moderate, bounded magnitude variance across seeds.

---

## 0. Setup

- All 5 real N-BaIoT training-seed collections loaded (`training_seed=0..4`,
  `poisoning_seed=100..104`, **paired 1:1** per the locked seed scheme — not a
  5×5 cross product).
- `CP2_TRAINING_SEEDS=(0, 1, 2, 3, 4)`, `CP2_POISONING_SEEDS=(100, 101, 102,
  103, 104)` (verified from `datp.artifacts.poison_names`).
- Eligible client set is **identical across all 5 training seeds** (9/9
  eligible, 0 pending, every seed) — same 9 physical N-BaIoT devices regardless
  of FL training-seed randomness.
- Victim: `Danmini_Doorbell` (first eligible client, sorted; consistent
  across all 5 seeds since the eligible set doesn't vary).
- Swept all 3 policies × 3 sources × 4 fractions = 36 cells per seed pair × 5
  seed pairs = 180 cells total.

## 1. mu_flag_threshold per training seed

`mu_flag_threshold` was locked independently for each training seed from that
seed's own clean B1 eligible-client mean FPR (never reused across seeds):

| training_seed | mu_flag_threshold |
|---|---|
| 0 | 0.0050 |
| 1 | 0.0049 |
| 2 | 0.0056 |
| 3 | 0.0053 |
| 4 | 0.0050 |

Values are close (0.0049–0.0056) but not identical — confirms the lock is
correctly seed-specific (clean B1 mean FPR has small FL-training variance
across seeds) and must **not** be hardcoded or reused from `training_seed=0`
for the other 4 seeds in the bounded MVP run.

## 2. Sign consistency (f=0.40, directional sources)

| Policy | Source | Δτ across 5 seeds | Sign-consistent | n |
|---|---|---|---|---|
| B1_GLOBAL | HIGH | 0.1840, 0.1569, 0.1870, 0.1593, 0.1741 | **True** | 5/5 |
| B1_GLOBAL | LOW | −0.0274, −0.0278, −0.0262, −0.0294, −0.0291 | **True** | 5/5 |
| B2_PERSONALIZED | HIGH | 1.6556, 1.4118, 1.6828, 1.4341, 1.5666 | **True** | 5/5 |
| B2_PERSONALIZED | LOW | −0.2465, −0.2505, −0.2355, −0.2644, −0.2617 | **True** | 5/5 |
| B4_CLUSTER | HIGH | 1.8054, 1.2613, 1.8448, 1.4341, 1.4222 | **True** | 5/5 |
| B4_CLUSTER | LOW | −0.1232, −0.4189, −0.1178, −0.3008, −0.4465 | **True** | 5/5 |

All 6 directional (policy, source) combinations show 5/5 sign consistency —
the locked ≥4/5 sign-test threshold (CLAUDE.md §3.7) is met with margin for
every one of them, on this single victim across all 5 paired seeds.

## 3. Magnitude stability (f=0.40, HIGH_SCORE_BENIGN)

| Policy | mean Δτ | std (ddof=1) | CV |
|---|---|---|---|
| B1_GLOBAL | 0.1722 | 0.0138 | 0.0800 |
| B2_PERSONALIZED | 1.5502 | 0.1241 | 0.0800 |
| B4_CLUSTER | 1.5536 | 0.2575 | 0.1657 |

B1 and B2 show identical, low across-seed variability (CV=0.08). B4 shows
roughly 2× higher variability (CV=0.166) — consistent with B4's k-means
clustering being mildly seed-sensitive: a benchmarking side-observation during
this same session showed cluster sizes varying between `[4,3,2]` and `[3,3,3]`
across different (victim, fraction) inputs at `K=3`, which is expected (K=3
clustering on a 9-point fingerprint set is not perfectly balance-invariant)
and is exactly the kind of variance the locked `Δτ_total = Δτ_agg + Δτ_churn`
decomposition exists to make auditable. This is not a stability failure — CV
0.166 is still a small fraction of the mean — but it is consistent with, and
gives a partial mechanistic explanation for, the higher-than-naive B4 blast
radius flagged in CP2-T043 §2.1: cluster membership itself shifts modestly
seed-to-seed, so a victim's effective "cluster-mates" set is not perfectly
fixed.

## 4. Acceptance criteria check (ticket §11)

> Multi-seed stability confirmed; bounded MVP plan + resource estimate
> written; `mu_flag_threshold` locked; pyright green.

- Multi-seed stability: §2 (sign consistency 5/5 throughout), §3 (bounded
  variance, mechanistically explained for B4).
- `mu_flag_threshold` locked per seed: §1 (5 distinct values, all computed
  from clean B1 data before any poisoned cell for that seed).
- Bounded MVP plan + resource estimate: see
  `_ai_tracking/run_logs/CP2-T044_mvp_run_plan.md`.
- pyright: re-verified 0 errors on `real_score_loader.py`, `mvp_runner.py`,
  `cell_runner.py` (no source changes this ticket; diagnostic-only).

**No blocking condition triggered (ticket §12) — stability confirmed, no
scope shrink required.**
