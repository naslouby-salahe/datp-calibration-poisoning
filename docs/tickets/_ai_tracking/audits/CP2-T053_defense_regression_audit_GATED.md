# CP2-T053 — Defense Regression & Recovery Audit — GATED

**Date:** 2026-06-17
**Status:** **GATED — cannot complete now.**

## Why gated
CP2-T053 §1 requires that **CP2-T052 ran** (real defended results) before the
recovery/regression audit can proceed. CP2-T052's *implementation* is complete
(trimmed-calibration defense + synthetic unit tests), but its **real defended
run** has not occurred and is **not authorized**: Phase-F execution is gated at
CP2-T056 (CLAUDE.md §9 hard stop; the CP2-T049 CONTINUE decision opens Phase-F
ticket *statuses* only, not runs). There are therefore no defended-vs-undefended
real result artifacts to compare.

## What this audit needs (deferred to post-CP2-T056)
Once a defended run is authorized and executed, this audit must compute, paired
on the same victims/seeds, defended vs undefended:
- residual Δτ, ASR, blast radius;
- CV(FPR) + coverage ratio, worst-client FPR;
- clean-FPR cost / utility regression per policy (B1/B2/B4);
- recovery ratio per policy; flag cases where the defense fails or over-trims.

## Honest-framing note carried forward (from CP2-T052)
The synthetic unit tests already establish that symmetric trimming at q=0.95 is
**partial/conditional** mitigation: it removes injected tail contamination when
the trim fraction covers it, but in the in-range-reservoir regime |Δτ| can be
barely changed or slightly worse. CP2-T053 must report this honestly and must
**not** overclaim robustness (T052 §10, T053 §5). Trimming also reduces
calibration cardinality (a coverage/utility cost) — must be reported.

## Resolution
Re-open CP2-T053 only after CP2-T056 authorizes and runs the defended matrix.
