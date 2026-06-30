# DATP-CP Paper Fix — Final Report

## Outcome
The paper is submission-ready at **14 pages**, compiling cleanly (3×`pdflatex` + `bibtex`, zero errors, zero new warnings, no undefined references, all citations resolved). All P0 (4/4) and P1 (11/11) actions from the audit checklist are resolved. All 18 P2 actions are resolved — either fixed in place or deliberately deferred with a documented, page-budget-driven reason. All 3 P3 actions are deferred (tooling unavailable and/or zero remaining page-budget slack).

Full action-by-action ledger: `paper_review/PAPER_FIX_STATUS.md`.

## What changed (by priority)

**P0 (4/4):** explicit naming of all 4 source-objective pairs; contributions item rewritten to distinguish Local/Cluster/Global spillover precisely; removed an unverifiable citation in favor of a first-principles derivation; added a footnote explaining a zero-rounding artifact in Table 1.

**P1 (11/11):** code-availability statement; precise calibration-channel-blind defense claim (removed overclaim "every defense"); score-level proxy caveat added to abstract; bootstrap-coverage-at-n=10 caveat; Gate-constant justification; lowering attack reframed around ΔFPR/alarm-burden as primary, ΔTPR as a non-benefit secondary indicator; reproducibility table added; Random-Benign negative-control rows added to the main results table; a wrong seed-0 CV(FPR) value fixed; a new spillover table (Table 3) quantifying victim vs. non-victim Δτ/ΔTPR/blast-radius per policy, with the related-work Kloft & Laskov contrast and a "to the best of our knowledge" qualifier; all 5 required limitations sentences present.

**P2 (18/18):** Gate-1 definition tightened in the abstract; victim-majority condition spelled out; CV(FPR) defined at first use; Table 1 caption fully defines CV/Worst-BA/P10-Macro-F1 and the bold convention; an unverified Mirai-flows extrapolation removed (no artifact backed the traffic-rate conversion); the Global-harm mechanism sentence rewritten for clarity; Figure 1's training-phase box relabeled to include aggregation; Cluster policy description now specifies the exact clustering features (4-feature standard-scaled fingerprint: mean/std/skew/p95 of the calibration-score distribution, verified against `src/datp/thresholding/policies.py::compute_fingerprints`), K=3 cluster-size rationale, and a real k-means++ citation (Arthur & Vassilvitskii, 2007); the gray-box adversary definition and attack-vs-vulnerability terminology were checked and found already consistent (no edit needed); a genuine N-notation collision was found and fixed (discussion.tex was reusing $N$ for per-client calibration-set size while method.tex uses $N$ for federation size — renamed to $n_v$ with an explicit disambiguating clause); the existing defense-requirements sketch in the Discussion was confirmed sufficient.

Deferred (documented in PAPER_FIX_STATUS.md, all due to the 14pp ceiling or missing tooling): a formal contamination equation (prose already covers it unambiguously), a related-work comparison table, a paper-roadmap paragraph in §1, a second motivating-harm scenario in §1 (one already exists in §5.2), and a Figure 3 regeneration (needs plotting scripts, not a text edit).

**P3 (0/3, all deferred):** 300dpi figure regeneration and Table 2 density are tooling/cosmetic items with no remaining page-budget slack; the Local-vs-Global P10 Macro-F1 tradeoff discussion would require net-new prose that the budget cannot absorb.

## Page-budget incident
Mid-way through the P2 batch, the paper regressed from 14pp to 15pp. The cause was cumulative line growth across roughly six small additions (definitions, clauses, an expanded caption), not any single edit and not the new bibliography entry (isolated and ruled out experimentally). Trimming the Cluster K=3 justification clause in method.tex §4.2 restored 14pp with no information loss. Every edit after that point was verified against a fresh 3-pass compile before being accepted.

## Final audits (all clean)
1. **Forbidden-claims audit** — grepped for "training/model/aggregation poisoning", "evasion", "privacy guarantee", "deployment readiness", "robust federated learning", "every defense", "operationally meaningful [...] deployment". The two raw hits ("model poisoning" in background.tex, "evasion" in introduction.tex) are both citations-to-prior-work or explicit negations ("we do not claim ... evasion guarantees"), not claims about this work. **Pass.**
2. **Citation-integrity audit** — every `\cite{}` key resolves against references.bib (21 used / 21 resolved); one unused bib entry (`lheureux2017machine`, dropped from the text during the P0 pass) was found and removed for cleanliness. Bibliography renders 21 numbered entries, bibtex log clean. **Pass.**
3. **Numeric-consistency audit** — the headline Δτ/ΔTPR figures (+0.100/+0.899/+0.902 Δτ; −6.1/−4.9/−7.9 pp ΔTPR at f=0.4; 2.4–7.9pp range; 10–12pp / 0.05–0.06 lowering figures) were cross-checked across abstract, introduction, results, conclusion, discussion, and both tables — identical everywhere. **Pass.**
4. **Page-budget/compile audit** — 3×pdflatex + bibtex, exit 0, 14 pages, zero errors, zero new warnings, no undefined cross-references. **Pass.**
5. **Scientific-boundary audit** — grepped for claims of aggregation poisoning, gradient/label poisoning, or privacy/robustness/deployment guarantees attributed to this work. The two raw hits ("gradient injection", "altering model weights") are both explicit negations contrasting this work's weaker score-level capability against model-poisoning adversaries. The calibration-channel-only framing is intact throughout (mentioned 47 times across all sections). **Pass.**

## Outstanding items (not blocking submission, documented for future work)
- Figure 3 (Global line scale/inset) needs regeneration from the plotting pipeline — not attempted in this text-only pass.
- Formal contamination equation, related-work comparison table, paper roadmap, second motivating scenario, and all P3 items are deferred purely for page-budget reasons; none represent a correctness or scientific-boundary gap.

## Repository state
No commits were made and no pull requests were opened during this fix loop, per instructions. All changes are unstaged edits in the working tree under `paper/`. `paper_review/PAPER_FIX_STATUS.md` contains the complete, auditable action-by-action ledger.
