# AUDIT-09 Normalized

**Source file:** Paper Audit 8.md  
**SHA-256:** 4d3b7dc1a71da56540fd90092ff9385b49ae72957f30d875a09990a764311f5c  
**Grade:** 8.2 / 10  
**Recommendation:** Weak Accept / Borderline (most generous audit)  
**Duplicate flag:** None  
**Content quality:** Full — no URL embedding degradation

---

## Reviewer Summary

The most generous of all ten audits. Describes the paper as "close to submission-ready" with four "fatal risks" that can all be fixed without new experiments: (a) "4 source-objective pairs" language is ambiguous — the paper describes only 3 conditions (HSB-raise, LSB-lower, RB-control), (b) Random-Benign control is never numerically shown in any table, (c) reproducibility details are missing, (d) the negative control is described in prose but never presented as data. The reviewer provides a fastest-path checklist. Bootstrap issue is noted as a concern but not listed as fatal.

---

## Findings Extracted

### S0 — Fatal Risks (in reviewer's words)

| # | Location | Finding |
|---|----------|---------|
| NF-A09-01 | §4 / §1 | **"4 source-objective pairs" inconsistency**: paper says "4 pairs" but only 3 conditions described (HSB-raise, LSB-lower, RB-control). Either a counting error or an undescribed 4th pair. |
| NF-A09-02 | Table 2 / §5 | **Random-Benign not numerically shown**: control condition is present in prose/captions but has no table row showing its effect values |
| NF-A09-03 | §2 | **Reproducibility gap**: AE architecture, FedAvg hyperparameters, train/calibration/test split, feature pipeline all missing |
| NF-A09-04 | §5 | **Negative control hidden in prose**: Random-Benign results should be explicit data rows, not assertions in text |

### S1 — Major Weaknesses

| # | Location | Finding |
|---|----------|---------|
| MW-A09-01 | §5.3 | Lowering attack harm framing: positive ΔTPR sounds beneficial; should foreground increased alarm burden (ΔFPR) |
| MW-A09-02 | §5.4 | Spillover evidence thin; victim vs. non-victim table absent |
| MW-A09-03 | Figure 2 | Only seed 0 shown without justification; Cluster condition absent |
| MW-A09-04 | Figure 3 | Random-Benign not plotted |
| MW-A09-05 | §1 | No artifact/code availability statement |
| MW-A09-06 | §3 | Kloft & Laskov [11] needs explicit contrast |
| MW-A09-07 | §1 | "Every defense" language too universal |

### S2 — Minor

| # | Location | Finding |
|---|----------|---------|
| MI-A09-01 | Table 1 | BAP10/"Worst BA" undefined |
| MI-A09-02 | Table 2 | Dense layout; Random-Benign absence makes control comparison hard |
| MI-A09-03 | Figure 1 | Color legend absent |
| MI-A09-04 | Abstract | "100% Gate-1 pass rate" before Gate-1 defined |

---

## Fastest-Path Checklist (reviewer's own words, adapted)

1. Add reproducibility table (AE, FedAvg, split, features)
2. Define "4 source-objective pairs" precisely or correct count to 3
3. Expose Random-Benign as explicit data rows in Table 2
4. Reframe lowering attack: alarm burden, not detection improvement
5. Add spillover evidence table (victim vs. non-victim)

---

## Experiment-Scope Critiques (OUTSIDE_FROZEN_SCOPE)

- N=10 seeds: bootstrap CI concern (noted but not fatal per this reviewer)
- Single dataset

---

## Reviewer Verdict

> "Weak accept / borderline. Closest to submission-ready of all audits reviewed. The four fatal risks are all paper-writing fixes, not experiment changes. Fix the '4 pairs' inconsistency, show Random-Benign as data, add the reproducibility table, clarify the lowering attack harm. Then submit."
