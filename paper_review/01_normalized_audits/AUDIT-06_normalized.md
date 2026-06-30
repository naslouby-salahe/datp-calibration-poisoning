# AUDIT-06 Normalized

**Source file:** Paper Audit 5.md  
**SHA-256:** 755ec5685e879ae36e2b601b4a719855981a71cde8312cbf967d3a6f633ed0cc  
**Grade:** 7.8 / 10  
**Recommendation:** Weak Accept  
**Duplicate flag:** AUDIT-07 is identical (same SHA-256)  
**Content quality:** Full — no URL embedding degradation

---

## Reviewer Summary

Reviewer awards 7.8 / weak accept and identifies five near-fatal and major concerns. The most distinctive critiques from this audit: (a) the paper inconsistently uses "attack" (in abstract) vs. "vulnerability characterization" (in §6) — this framing inconsistency could cause reviewer rejection, (b) BAP10 is undefined in Table 1, (c) the defense requirements sketch is completely missing from Discussion, (d) "gray-box" is used without a precise definition anchored to the FL setup, (e) no formal contamination equation. The score-level proxy limitation is flagged as near-fatal, consistent with all other audits.

---

## Findings Extracted

### S0 — Near-Fatal Risks

| # | Location | Finding |
|---|----------|---------|
| NF-A06-01 | Abstract vs. §6 | **"attack" vs "vulnerability characterization" inconsistency**: abstract says "attack," §6 says "characterization of vulnerability" — reviewers may penalize for lack of epistemic clarity |
| NF-A06-02 | Global / realism | Score-level proxy: attack not shown to be traffic-realizable |

### S1 — Major Weaknesses

| # | Location | Finding |
|---|----------|---------|
| MW-A06-01 | Table 1 | BAP10 undefined — appears without definition or footnote |
| MW-A06-02 | §5/Discussion | Defense requirements sketch completely missing |
| MW-A06-03 | §2 / threat model | "gray-box" label: precise definition anchored to FL setup missing |
| MW-A06-04 | §4 / method | Formal contamination equation absent — replaces informal description |
| MW-A06-05 | §5 | Lowering attack: Global conditionality (why lowering works for Global but not Local/Cluster) under-explained |
| MW-A06-06 | §1 | No paper roadmap (§-by-§ guide) in introduction |
| MW-A06-07 | §2 | AE architecture missing |
| MW-A06-08 | §2 | FedAvg hyperparameters missing |
| MW-A06-09 | §5 | Random-Benign control not tabulated |
| MW-A06-10 | §1 | No artifact/code availability statement |
| MW-A06-11 | §5.4 | Spillover claims not directly quantified |
| MW-A06-12 | §6 | Gate constants unjustified |

### S2 — Minor

| # | Location | Finding |
|---|----------|---------|
| MI-A06-01 | Figure 2 | Seed 0 only, no justification; Cluster absent |
| MI-A06-02 | Figure 3 | Random-Benign not plotted |
| MI-A06-03 | Table 1 | Bold convention direction not stated |
| MI-A06-04 | Abstract | Realism caveat missing from abstract |

---

## Experiment-Scope Critiques (OUTSIDE_FROZEN_SCOPE)

- No multi-client collusion — outside frozen scope
- Single dataset limitation
- No other detectors (LOF, isolation forest) — out of scope

---

## Reviewer Verdict

> "Weak accept with reservations. The 'attack' vs 'vulnerability characterization' framing must be resolved consistently. Add the formal contamination equation. Add a defense sketch. Clarify gray-box threat model. These are presentation-layer fixes that don't require new experiments."
