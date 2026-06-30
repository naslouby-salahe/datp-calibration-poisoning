# AUDIT-02 Normalized

**Source file:** Paper Audit 10.md  
**SHA-256:** a313b19b2324c086693b9b205d6e2e8d7e09b47a9d88653de1c68e60947b67ae  
**Grade:** 7.0 / 10  
**Recommendation:** Borderline / Weak Reject  
**Duplicate flag:** None  
**Content quality:** DEGRADED — AWS S3 URLs embedded in table cells. Recoverable: grade, scorecard, top weaknesses, verdict section.

---

## Reviewer Summary

Reviewer finds the paper "interesting and well-scoped" but identifies several structural problems that threaten acceptance. The most severe issue is a direct contradiction between the Contributions section (item 3) and the body: Contributions claim Local/Cluster have "no cross-client spillover" but §4.2 and §5.4 describe Cluster as capable of intra-cluster spillover. Cluster policy is under-specified. Gate constants lack justification. Spillover asserted but not tabulated.

---

## Findings Extracted (from recovered sections)

### S0 — Near-Fatal Risks

| # | Location | Finding |
|---|----------|---------|
| NF-A02-01 | §1 Contributions item 3 vs. §4.2/§5.4 | **Direct contradiction:** Contributions say Local/Cluster have "no cross-client spillover"; §4.2/§5.4 say Cluster CAN cause intra-cluster spillover to non-victim cluster members |
| NF-A02-02 | §2 / threat model | Score-level proxy — attack not shown to be traffic-realizable |
| NF-A02-03 | §4/§5 | Cluster policy under-specified: K=3, feature representation not described |

### S1 — Major Weaknesses

| # | Location | Finding |
|---|----------|---------|
| MW-A02-01 | §6 / statistics | Gate constants (0.1, 0.01 × IQR thresholds) unjustified — appear tuned on results |
| MW-A02-02 | §5 | Spillover asserted but not directly measured (no victim vs. non-victim ΔFPR table) |
| MW-A02-03 | §3 | Kloft & Laskov contrast not explicit enough |
| MW-A02-04 | §2 | "gray-box" label inconsistently applied |
| MW-A02-05 | §5.4 | N notation conflict: N=9 federation size vs. N=calibration set size (≈2622) in same section |
| MW-A02-06 | §5.2 | "30-80 undetected Mirai flows" — no derivation shown |
| MW-A02-07 | §1/abstract | Realism caveat should appear in abstract, not buried in limitations |
| MW-A02-08 | §1 | No artifact/code availability statement |
| MW-A02-09 | §2 | FedAvg hyperparameters missing |
| MW-A02-10 | §2 | AE architecture missing |

### S2 — Minor

| # | Location | Finding |
|---|----------|---------|
| MI-A02-01 | Table 1 | BAP10/P10 abbreviations undefined |
| MI-A02-02 | Figure 2 | Cluster condition missing; only seed 0 shown |
| MI-A02-03 | Table 1 | Bold convention direction not stated |

---

## Experiment-Scope Critiques (OUTSIDE_FROZEN_SCOPE)

- Single dataset — would require additional data collections
- Single-client compromise only — multi-client collusion out of scope per roadmap
- No defense baseline evaluated

---

## Reviewer Verdict

> "Borderline. The contradiction between the Contributions and §4.2/§5.4 on Cluster spillover is a structural error that must be resolved before submission. The Cluster policy needs precise specification. Fix these and the paper improves substantially."

---

*Note: This audit had severe URL embedding in table cells. The findings above are reconstructed from the recoverable sections (verdict, scorecard, top-10 weaknesses list). Any missing nuance from table rows is logged in `.work/audit02_degradation_note.txt`.*
