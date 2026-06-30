**Paper Audit and Review Report**

**1. Executive Verdict**

* **Overall grade**: 7.8/10  
* **Recommendation**: Weak Accept (borderline for top-tier venues like USENIX Security, NDSS, or IEEE S&P; solid for good workshops or specialized MLsec venues). Revise and resubmit after targeted fixes.  
* **One-paragraph verdict**: This is a focused, well-executed vulnerability characterization of an under-studied attack surface (post-training threshold calibration in federated IoT anomaly detection). The paper correctly isolates the calibration channel, uses a clean score-level model, demonstrates policy-dependent effects with proper controls/sanity checks, and maintains strong claim discipline. Strengths in experimental rigor and clarity are offset by modest novelty (incremental over known data-poisoning intuitions), limited scope (single dataset, autoencoders, 9 clients, score-level proxy), some visual weaknesses, and minor overstatements in impact framing. It is technically sound but not groundbreaking.  
* **Main reason to accept**: Timely isolation of a structurally undefended phase in FL-IDS pipelines; clean methodology and reproducible-style protocol; policy-differentiated analysis adds value.  
* **Main reason to reject**: Incremental novelty ("we show calibration poisoning works differently by policy") + narrow scope + score-level proxy may lead reviewers to say "obvious once stated" or "not a full attack."  
* **Fastest path to improve**: Strengthen novelty positioning, fix visuals/tables for camera-ready polish, tighten abstract/intro impact language, add explicit reproducibility statement.

**2. Scorecard**

| Category                  | Score |
|---------------------------|-------|
| Novelty                   | 6.5  |
| Technical correctness     | 9.0  |
| Methodological rigor      | 8.5  |
| Experimental support      | 8.5  |
| Claim discipline          | 8.0  |
| Related work positioning  | 7.0  |
| Reproducibility           | 7.5  |
| Visual presentation       | 6.5  |
| Writing clarity           | 8.5  |
| Reviewer-proofness        | 7.5  |
| **Final overall**         | **7.8** |

**3. Top Strengths** (ranked)
1. Excellent isolation of the calibration stage as a distinct attack surface (clear separation from training/aggregation defenses).
2. Strong statistical framework (paired seeds, Gate 1-3, bootstrap CIs, negative controls, AUROC invariance sanity check).
3. Policy-differentiated analysis with clear trade-offs (Local vs. Global vs. Cluster) — this is the real contribution.
4. Disciplined scoping throughout (explicitly score-level, single-client, N-BaIoT, etc.).
5. Clean threat model and experimental protocol that match the claims.

**4. Top Weaknesses** (ranked with severity and location)
1. **Visuals/tables** (major): Figures 2/3 are low-resolution screenshots with poor readability (blurry text, small fonts, inconsistent styling). Table 1/2 formatting is acceptable but could be tighter. (Pages 7-11)
2. **Novelty positioning** (major): Underplays how close this is to standard data poisoning applied late; over-relies on "structurally outside defenses" without a crisp comparison table to prior calibration/threshold poisoning work. (§2, Contributions)
3. **Impact framing** (moderate): Abstract/intro imply stronger practical harm than the modest TPR drops (2.4-7.9 pp) support, especially with score-level proxy. (Abstract, §5.2, §6)
4. **Reproducibility gaps** (moderate): No artifact link, missing exact model architecture/hyperparameters, code/commands. (§4)
5. **Minor overclaims on "100% Gate-1"** without clearer materiality justification for δτ across heterogeneous devices. (§4.4)

**5. Fatal or Near-Fatal Risks** (none fatal)
- None. The paper is technically solid. Biggest rejection risk is "incremental" rather than fundamental flaw.

**6. Section-by-Section Review** (summarized; all sections submission-viable after minor edits)

* **Title**: 8/10. Clear and specific. Minor: Could be punchier.
* **Abstract**: 7.5/10. Good structure but packs too much; "100% Gate-1" and pp drops need context for general readers. Fix: Trim numbers slightly.
* **Introduction**: 8.5/10. Strong motivation. Clearly states undefended phase. Good.
* **Contributions**: 8/10. Numbered list is clear. Bullet 2 slightly overstates generality.
* **Related Work**: 7/10. Adequate but misses some recent FL-IDS threshold papers; weak on centralized threshold poisoning distinctions.
* **Threat Model**: 9/10. Excellent — gray-box score-level, single client, explicit non-modification of everything else.
* **Methodology/Experimental Setup**: 9/10. Highly detailed, paired seeds, policies well-defined.
* **Results**: 8/10. Policy effects clear; visuals drag it down.
* **Discussion/Limitations**: 8.5/10. Honest on score-level proxy and detectability.
* **Conclusion**: 8/10. Concise, scoped.
* **References**: 8/10. Solid but could cite more recent FL personalization work.

**7. Reviewer Questions the Paper Must Already Answer**
- **Threat model**: Does the attacker modify test data/labels? (No — explicitly clean.)
- **Novelty**: How does this differ from poisoning the validation set in centralized settings? (Temporal isolation + FL trust model.)
- **Methodology**: Why Replace-Fixed-Budget (with replacement duplicates) instead of without-replacement or targeted removal?
- **Dataset**: Why only N-BaIoT? Generalization?
- **Metrics**: Is δτ materiality threshold justified? Why not multiple quantiles?
- **Statistical**: Are 10 seeds enough for bootstrap CIs on 9 clients?
- **Scope**: Does Global policy really propagate harm meaningfully?
- **Reproducibility**: Code/dataset version?
- **Visual**: Why blurry figure screenshots?

**8. Claim Discipline Audit** (selected key claims)
- Claim: "the score-level raising attack achieves 100% Gate-1 pass rate..." — Fully supported by Table 2. Safe.
- Claim: "degrading victim true-positive rates by 2.4 to 7.9 percentage points" — Supported. Minor risk of overstating operational impact (fix: "modest but consistent").
- Claim: "structurally outside the scope of these defenses" — Well-supported. Good.
- Lowering attack as "lower bound" — Properly caveated.

**9. Methodology and Experiment Audit**
The design supports the claims. Paired seeds, clean/poisons, negative Random-Benign control, AUROC invariance, and isolation checks are excellent. No train/calibration/test leakage. Policy definitions are precise. Main limitation: score-level only (acknowledged). Negative control works. Statistical gates are reasonable but δτ definition could use more justification. No major confounders identified.

**10. Figures and Tables Audit**
- **Fig 1**: 7/10. Conceptual diagram good but low-res in provided PDF.
- **Fig 2**: 5.5/10. Bar chart hard to read; small labels, blurry.
- **Fig 3**: 6/10. Line plots with error bars are informative but resolution/axis clarity poor.
- **Table 1**: 8/10. Good baseline comparison.
- **Table 2**: 8.5/10. Core results table — strongest visual.

**11. Visual and Formatting Review**
Screenshots in the provided PDF are poor quality (blurry, inconsistent). In a real submission, use vector/PDF-native figures with larger fonts, better color contrast, and self-contained captions. Page layout is standard but some captions wrap poorly. Professional but not camera-ready.

**12. Related Work and Novelty Review**
Novelty score 6.5/10. Closest work (centralized threshold poisoning, FL training poisoning) is cited but not crisply differentiated in a table. The "policy-differentiated blast radius" angle is the strongest novel element. Risk: Reviewers saying "late-stage data poisoning is known."

**13. Reproducibility Checklist**
- Strong: seeds, fractions, dataset (N-BaIoT public), policies, gates.
- Missing: exact autoencoder architecture, FedAvg details (epochs, lr), code repo, full hyperparams, calibration set exact preprocessing, software versions. Add a short "Reproducibility" paragraph or appendix.

**14. Action Plan to Reach 10/10**
**Must fix before submission**:
- Replace/rebuild all figures with high-quality vector versions (larger fonts, clear labels).
- Add explicit artifact availability statement + reproducibility paragraph.
- Tighten abstract/intro impact language; add one-sentence scope reminder.
- Include a small related-work comparison table.

**Should fix**:
- Justify δτ more rigorously or run sensitivity.
- Discuss multiple q values or additional detectors briefly.
- Improve Table 1/2 formatting (bold best values consistently).

**Nice to fix**:
- Minor ablation on duplicate-score detectability.
- One extra dataset mention (even if preliminary).

**Do not touch**: Core threat model, statistical gates, policy analysis.

**15. Final Reviewer Simulation**

1. **Supportive expert**: Score 8.5. "Solid characterization of an overlooked surface. Policy insights useful." Objections: visuals.
2. **Skeptical methods**: Score 7. "Score-level proxy weakens real-world claim. Only 10 seeds?" (Paper mostly answers via caveats.)
3. **Security/adversarial ML**: Score 7.5. "Interesting but is this deployable? Real traffic generation missing." (Acknowledged in limitations — sufficient.)
4. **Presentation**: Score 6.5. "Figures need work; some blurring in PDF."

**Verdict**: The paper is **almost ready** but not submission-ready in its current visual/formatting state. With the must-fix items addressed, it becomes a strong 8.5-9/10 submission. The scientific core is already quite good — focus on polish and positioning.