# Rejected or Deferred Items

This register documents every critique from the 10 audits that is either:
- **REJECTED**: Out of scope per frozen DATP-CP boundary; the paper should not be modified to address it
- **DEFERRED**: In scope for future work but not addressable in the current paper
- **ACKNOWLEDGED_ONLY**: Warrants a sentence in limitations but no substantive paper change

The frozen boundary (from CLAUDE.md):
> DATP-CP is calibration-channel poisoning only. The poisoning mechanism may modify only benign threshold-calibration scores for eligible clients. Never alter: training data, labels, model weights, gradients, aggregation, test scores, test labels, or test data. Forbidden claims: model poisoning, training poisoning, aggregation poisoning, evasion, privacy guarantees, deployment readiness, broad FL robustness.

---

## REJECTED — Violate Frozen Boundary

### R-01 — Adding Byzantine-robust aggregation comparison
- **Requested by:** AUDIT-07, AUDIT-08
- **Rationale:** Byzantine aggregation defense addresses model poisoning / gradient poisoning. DATP-CP operates at the calibration stage, not the aggregation stage. This comparison would imply DATP-CP is a form of aggregation attack, which it is not.
- **Disposition:** REJECT. Do not add Byzantine aggregation baselines.

### R-02 — Demonstrating resistance to Flame, Krum, or similar defenses
- **Requested by:** AUDIT-07, AUDIT-08
- **Rationale:** These defenses target model-weight aggregation, not calibration-buffer poisoning. Testing DATP-CP against them would incorrectly position the attack in the wrong threat category.
- **Disposition:** REJECT. Do not claim or test evasion of these defenses.

### R-03 — Adding conformal prediction / conformal thresholding comparison
- **Requested by:** AUDIT-07 (implicitly)
- **Rationale:** Out of scope. DATP-CP studies quantile-based threshold calibration. Conformal prediction is a separate research direction.
- **Disposition:** DEFER to future work. Add to Future Work: "Extension to conformal threshold calibration is an interesting direction."

### R-04 — Multi-dataset evaluation (UNSW-NB15, CIC-IDS)
- **Requested by:** AUDIT-04, AUDIT-07, AUDIT-08
- **Rationale:** N-BaIoT is the contribution dataset. Adding other datasets is a scope expansion beyond the current paper.
- **Disposition:** DEFER. Mention in Limitations: "Evaluating on other IoT network datasets (e.g., UNSW-NB15) remains future work."

### R-05 — Multi-client collusion experiment
- **Requested by:** AUDIT-04, AUDIT-05, AUDIT-06, AUDIT-09
- **Rationale:** The roadmap explicitly scopes this to single-client compromise. Multi-client collusion is a separate attack model.
- **Disposition:** DEFER. Mention in Future Work. Do not run new experiments.

### R-06 — Privacy guarantee analysis
- **Requested by:** AUDIT-08 (implied)
- **Rationale:** Explicitly forbidden by frozen boundary. DATP-CP makes no privacy claims.
- **Disposition:** REJECT FIRMLY. Do not add any privacy analysis.

### R-07 — Deployment readiness / practical deployment recommendation
- **Requested by:** AUDIT-01, AUDIT-03 (implicitly via "deployment language")
- **Rationale:** Forbidden by frozen boundary.
- **Disposition:** REJECT. Remove existing deployment language (covered by A-f8c713ec0c, P1).

### R-08 — FedProx / SCAFFOLD / FedRep vulnerability analysis
- **Requested by:** AUDIT-07, AUDIT-08
- **Rationale:** Out of scope. Contribution is FedAvg + autoencoders.
- **Disposition:** DEFER. Add to Future Work: "Extending to personalized FL protocols (FedProx, FedRep) is a natural direction."

### R-09 — Isolation forest, LOF, one-class SVM comparison
- **Requested by:** AUDIT-07, AUDIT-08
- **Rationale:** DATP-CP contribution is autoencoder-based federated detection.
- **Disposition:** REJECT / DEFER. Not addressable in this paper.

---

## DEFERRED — In Scope Eventually, Not Now

### D-01 — q=0.95 sensitivity analysis
- **Requested by:** AUDIT-04, AUDIT-09, AUDIT-10
- **Action:** Acknowledge in §4 or §7: "q=0.95 is fixed; sensitivity to quantile choice is left to future work."

### D-02 — Temporal / online attack dynamics
- **Requested by:** AUDIT-08
- **Action:** Note in Future Work if desired.

### D-03 — Larger federation (>9 clients)
- **Requested by:** AUDIT-07, AUDIT-08
- **Action:** Acknowledge in Limitations.

### D-04 — Traffic-level adversary realization
- **Requested by:** AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04, AUDIT-07, AUDIT-08 (6/10)
- **Action:** This is covered by A-e102f26659 (P1) — add score-level proxy caveat. The actual traffic-level demonstration is deferred to future work.

---

## ACKNOWLEDGED_ONLY — Disclose in Limitations, No Paper Change

| ID | Critique | Disposition |
|----|----------|-------------|
| ACK-01 | Single dataset | Add sentence to §7 Limitations |
| ACK-02 | Nine clients | Add sentence to §7 Limitations |
| ACK-03 | Single-client attack only | Add sentence to §7 Limitations |
| ACK-04 | q=0.95 fixed | Add sentence to §4 or §7 |
| ACK-05 | No temporal analysis | Optional Future Work mention |

---

## Notes on Scope Enforcement

The 10 audits collectively include ~15 critiques that ask for experiments or claims beyond the frozen boundary. These are classified REJECTED or DEFERRED uniformly, regardless of how strongly any individual audit stated the critique. The frozen boundary is a design constraint, not a gap to fill.

The three most common rejected categories:
1. **Multi-dataset** (4 audits) — DEFER, mention in Limitations
2. **Other FL algorithms** (2 audits) — DEFER, Future Work
3. **Byzantine defense comparison** (2 audits) — REJECT (wrong threat model)
