# AUDIT-01 Normalized

**Source file:** Paper Audit 1.md  
**SHA-256:** 72116f2ac091cd3509b793519fd224f2ddb7abe67bfc516c4238347c7701072b  
**Grade:** 8.0 / 10  
**Recommendation:** Borderline / Weak Accept  
**Duplicate flag:** AUDIT-03 is identical (same SHA-256)  
**Content quality:** Full — no URL embedding degradation

---

## Reviewer Summary

The reviewer finds DATP-CP "technically sound with a well-defined and narrow attack surface." The contribution is credited as original: policy-differentiated analysis across GLOBAL/LOCAL/CLUSTER thresholds in federated IoT anomaly detection. The three-gate statistical framework is praised. Principal concerns are: (a) attack surface is theoretical without traffic-level proof, (b) single dataset limits external validity, (c) Random-Benign control not tabulated, (d) statistical setup (N=10 seeds) is thin, (e) related work gaps, (f) lowering attack harm framing confusing.

---

## Findings Extracted

### S0 — Near-Fatal Risks (would prevent acceptance alone)

| # | Location | Finding | Verbatim / Paraphrase |
|---|----------|---------|----------------------|
| NF-A01-01 | Global / realism | Score-level proxy is a toy attack | "The attack operates at the score level…never demonstrates that a real adversary can produce duplicate calibration scores via traffic manipulation" |
| NF-A01-02 | §5 / dataset | Single dataset (N-BaIoT only) | "All experiments on a single dataset…limits generalizability" |
| NF-A01-03 | Related work | Novelty under-positioned vs. prior work | "No direct comparison to closest prior work…makes novelty claim fragile" |
| NF-A01-04 | §4/§5 | Controls asserted not shown in table | "Random-Benign asserted as control in prose…not tabulated" |

### S1 — Major Weaknesses (would require revision)

| # | Location | Finding |
|---|----------|---------|
| MW-A01-01 | §6 / statistics | N=10 seeds → bootstrap CIs unreliable at 95% level |
| MW-A01-02 | §3 / related work | Related work too thin; no 2023-2024 citations visible |
| MW-A01-03 | Table 2 | Random-Benign not shown as explicit rows in Table 2 |
| MW-A01-04 | §5.4 | Spillover not quantified; Global/Cluster claims lack victim vs. non-victim table |
| MW-A01-05 | Abstract | "lowering attack succeeds" phrasing: positive ΔTPR sounds beneficial not harmful |
| MW-A01-06 | §1/§2 | Reproducibility incomplete: AE architecture, train/calibration/test split, features missing |
| MW-A01-07 | §1 | No artifact/code availability statement |
| MW-A01-08 | Figure 1 | No color legend; attack operation unclear in diagram |
| MW-A01-09 | Figure 2 | Only seed 0 shown; no justification that seed 0 is representative |
| MW-A01-10 | §5 | "operationally meaningful in IoT deployment contexts" — deployment language out of scope per frozen boundary |
| MW-A01-11 | §1 | "every defense" claim too universal |
| MW-A01-12 | Table 1 | CV(FPR) defined inconsistently / introduced late |
| MW-A01-13 | §5 | Local vs. Global P10 Macro-F1 tradeoff not discussed |

### S2 — Minor Issues

| # | Location | Finding |
|---|----------|---------|
| MI-A01-01 | Figure 1 | Diagram shows "Training phase defended" but calibration is the attack stage |
| MI-A01-02 | Table 2 | Dense layout hard to parse |
| MI-A01-03 | §3 | No related-work comparison table |

---

## Experiment-Scope Critiques (OUTSIDE_FROZEN_SCOPE)

- Single dataset (N-BaIoT only) — would require new data
- Nine clients only — would require larger federation
- No multi-client collusion — deliberate scope boundary per roadmap
- No defense baseline — deliberate boundary

---

## Reviewer Verdict

> "Technically sound and well-scoped. The authors need to address the score-level proxy limitation explicitly, show the Random-Benign control numerically, tighten statistical claims, and expand related work. The paper is publishable with moderate revisions."
