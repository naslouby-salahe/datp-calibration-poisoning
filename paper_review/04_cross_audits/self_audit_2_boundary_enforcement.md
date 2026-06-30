# Self-Audit 2: Frozen Boundary Enforcement

**Question:** Does any action in the register violate the frozen DATP-CP scientific boundary?

**Boundary rules (from CLAUDE.md):**
1. Only modify benign threshold-calibration scores
2. Never alter: training data, labels, model weights, gradients, aggregation, test scores, test labels, test data
3. AUROC must remain invariant under poisoning
4. Forbidden claims: model poisoning, training poisoning, aggregation poisoning, evasion, privacy, deployment readiness, broad FL robustness
5. Reservoirs must be victim-local benign calibration scores

---

## Checking Each P0 / P1 Action Against the Boundary

### A-5f02c65612 — Fix spillover contradiction
- Does it modify experiments? **No.** Text fix only.
- Does it add new attack claims? **No.** It clarifies existing boundary.
- Boundary status: **SAFE**

### A-a098e39ee7 — Fix Reference [12]
- Does it modify experiments? **No.** Citation fix only.
- Boundary status: **SAFE**

### A-bc70838a10 — Fix "4 pairs" inconsistency
- Does it modify experiments? **No.** Corrects a counting inconsistency in text.
- Boundary status: **SAFE**

### A-db7bcc5fcf — Explain Cluster Macro-F1 ± 0.000
- Does it modify experiments? **Possibly** — requires checking results pipeline.
- Risk: If a bug is found and corrected, the correction must not change any ground-truth data, labels, or model weights. Only the *reporting* of the results should be corrected.
- Boundary status: **CONDITIONAL** — investigate reporting only; do not re-run with changed model parameters.

### A-f3e11e1509 — Add reproducibility table
- Does it modify experiments? **No.** Documents existing setup.
- Risk: None. Describing AE architecture and FedAvg hyperparameters does not alter them.
- Boundary status: **SAFE**

### A-664b8440ed — Add artifact statement
- Boundary status: **SAFE** (text only)

### A-e102f26659 — Reframe score-level proxy caveat
- Does it modify any experiment or claim scope? The reframing should *limit* claims (add a caveat), not expand them.
- Boundary status: **SAFE** (limiting, not expanding)

### A-01a7255dbd — Reframe lowering attack as ΔFPR harm
- Does it change what the attack does? **No.** It changes how the existing results are narrated.
- Risk: Must not claim new attack surface (e.g., "the attack also affects model weights").
- Boundary status: **SAFE** (reframing existing results only)

### A-1975d011a9 — Add Random-Benign rows to Table 2 / Figure 3
- Does it require new experiments? The data should already exist (Random-Benign was run as a control). This action exposes existing results.
- Boundary status: **SAFE** — if Random-Benign results do not exist, this requires a new run using only the existing allowed attack mechanism (score-level substitution with benign scores). No boundary violation.

### A-984973914d — Fix Figure 2: add Cluster, seeds
- Does it require new experiments? Adding Cluster and multiple seeds requires re-generating plots from existing data. No new attack mechanism.
- Boundary status: **SAFE**

### A-e31849338f — Add spillover quantification table
- Does it require new experiments? Spillover at victim vs. non-victim level requires running the existing attack and measuring results on non-victim clients — which is allowed (measuring effects, not modifying model).
- Boundary status: **SAFE** — measurement only, no modification of training/model

### A-5ccfae0eed — Expand related work
- Boundary status: **SAFE** (text only)

### A-f8c713ec0c — Remove "every defense" and deployment language
- Boundary status: **SAFE** (removing forbidden claims — directly required by boundary)

### A-df1fb64bdd — BCa bootstrap caveat
- Boundary status: **SAFE** (statistical methodology note)

### A-9c654c5a5e — Justify gate constants
- Boundary status: **SAFE** (justification text)

---

## Finding-Level Boundary Check

Scan for any finding that, if addressed, would require:
- Modifying training data → None found
- Altering model weights → None found
- Changing aggregation → None found
- Adding privacy claims → None found (R-06 REJECTED)
- Adding deployment claims → R-07 REJECTED
- Adding Byzantine defense claims → R-01, R-02 REJECTED

---

## Verdict

**No boundary violations found in the action register.** All P0 and P1 actions are paper-writing fixes. The one conditional flag (A-db7bcc5fcf) is restricted to reporting correction, not experiment modification.

The rejected items register (rejected_or_deferred_items.md) correctly absorbs all critiques that would require boundary violations.
