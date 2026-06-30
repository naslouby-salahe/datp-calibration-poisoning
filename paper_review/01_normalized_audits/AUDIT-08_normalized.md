# AUDIT-08 Normalized

**Source file:** Paper Audit 7.md  
**SHA-256:** 1716837f2fb7623d0cfa12a1093e77e822627b218148435aef2d070f6d375aa2  
**Grade:** 6.7 / 10  
**Recommendation:** Weak Reject ("paper not ready for strong conference")  
**Duplicate flag:** None  
**Content quality:** DEGRADED — AWS S3 URLs embedded in table cells. Recoverable: grade, scorecard, top weaknesses, final verdict, probability of acceptance (~25–35%).

---

## Reviewer Summary

This is one of the two rejection recommendations. The reviewer is most critical of: (a) realism gap is near-fatal — score-level injection has no real-world mechanism, (b) external validity is too narrow (one dataset, nine clients), (c) the novelty defense is incomplete and the paper conflates exploration with attack demonstration, (d) universal wording ("structurally outside scope of every defense") is indefensible, (e) the three-gate statistical framework appears entirely bespoke with no citation, (f) the lowering attack "success" claim is easy to misread as having achieved harm when the harm is ambiguous, (g) reproducibility is incomplete. Probability of acceptance estimated at 25–35%.

---

## Findings Extracted (from recovered sections)

### S0 — Near-Fatal Risks

| # | Location | Finding |
|---|----------|---------|
| NF-A08-01 | Global | Score-level proxy / realism gap is near-fatal for a strong conference |
| NF-A08-02 | §5 | External validity too narrow: single dataset, nine clients |
| NF-A08-03 | §3 | Novelty defense incomplete; paper conflates exploration with attack |
| NF-A08-04 | §1/abstract | "Structurally outside scope of every defense" — undefendable universal claim |

### S1 — Major Weaknesses

| # | Location | Finding |
|---|----------|---------|
| MW-A08-01 | §6 | Three-gate statistical framework is bespoke — needs citation or justification |
| MW-A08-02 | Abstract/§5 | Lowering attack "success" claim easy to misread; harm mechanism ambiguous |
| MW-A08-03 | §2 | Reproducibility incomplete (AE architecture, hyperparameters, features) |
| MW-A08-04 | §5 | Random-Benign control not visibly shown in results |
| MW-A08-05 | §3 | Kloft & Laskov not explicitly contrasted — nearest prior work |
| MW-A08-06 | §1 | No artifact/code availability statement |
| MW-A08-07 | §5.4 | Spillover evidence weak; only prose assertions |

### S2 — Minor

| # | Location | Finding |
|---|----------|---------|
| MI-A08-01 | Figure 2 | Seed 0 only; Cluster absent |
| MI-A08-02 | Figure 3 | Random-Benign not plotted |
| MI-A08-03 | Table 1 | BAP10 undefined |
| MI-A08-04 | Abstract | No realism caveat in abstract |

---

## Experiment-Scope Critiques (OUTSIDE_FROZEN_SCOPE)

- Single dataset — requires additional data
- Nine-client federation too small to generalize
- No multi-client collusion

---

## Reviewer Verdict

> "Weak reject. The paper has a good idea but the execution is not ready. The realism gap is the central flaw: the attack lives at the score level and has no traffic-level realization. This needs to be either demonstrated or prominently caveated as a theoretical exercise. At current state I estimate 25–35% acceptance probability at a strong conference."

---

*Note: This audit had severe URL embedding in table cells. Findings are reconstructed from recoverable sections. Degradation logged in `.work/audit08_degradation_note.txt`.*
