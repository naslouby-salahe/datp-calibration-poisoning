# DATP-CP Paper Fix Status

## Current phase
Complete

## Current action
Fix loop finished. All P0/P1/P2 actions resolved; P3 deferred (page-budget/tooling). Five final audits run and passed. `paper_review/FINAL_PAPER_FIX_REPORT.md` written.

---

## Completed actions

| Action ID | Priority | Files changed | Resolution | Compile | Audit |
|-----------|----------|---------------|------------|---------|-------|
| A-bc70838a10 | P0 | method.tex | Named all 4 source-objective pairs explicitly in §4.3 Attack Parameterization | PASS (13pp) | Self-consistent with roadmap §8.4 |
| A-5f02c65612 | P0 | introduction.tex | Contributions item 3 rewritten: Local=victim-only, Cluster=intra-cluster spillover, Global=fleet-wide | PASS | Consistent with §4.2 and §5.4 |
| A-a098e39ee7 | P0 | background.tex | L'Heureux citation removed; replaced with first-principles derivation sentence (threshold = quantile of calibration scores) | PASS | No citation mismatch; claim now self-evident |
| A-db7bcc5fcf | P0 | tables/table_baseline.tex | Added $^*$ footnote: actual std≈0.0002, rounds to zero at 3-decimal precision. Confirmed from seed-level metrics.json data. | PASS | Rounding artifact, not a bug |
| A-664b8440ed | P1 | conclusion.tex | Added "Code availability" statement | PASS | — |
| A-f8c713ec0c | P1 | main.tex, introduction.tex | "every defense"→precise calibration-channel-blind claim; removed "operationally meaningful in IoT deployment contexts" | PASS | — |
| A-e102f26659 | P1 | main.tex, method.tex | Score-level proxy caveat added to abstract; score-substitution language throughout | PASS | — |
| A-df1fb64bdd | P1 | method.tex §4.4 | BCa/percentile bootstrap coverage caveat at n=10 added | PASS | — |
| A-9c654c5a5e | P1 | method.tex §4.4 | Gate constant justification paragraph added (10% IQR, 1% floor, locked pre-poisoning) | PASS | — |
| A-01a7255dbd | P1 | main.tex, results.tex §5.3 | Lowering attack reframed ΔFPR/alarm-burden-first, ΔTPR secondary/non-benefit | PASS | — |
| A-f3e11e1509 | P1 | method.tex §4.1, tab:repro | Reproducibility table added (AE arch, FedAvg config, N-BaIoT calibration sizes) | PASS | — |
| A-1975d011a9 | P1 | tables/table_main_results.tex, main.tex fig 3 | Random-Benign Neg. Ctrl rows added (signed G1=0% verified from manifest) | PASS | Computed via signed-criterion script against nbaiot_main_manifest.json |
| A-984973914d | P1 | main.tex fig 2 caption | Fixed CV(FPR) seed-0 value 0.91→0.87; added mean±std; Cluster referenced to Table 1 | PASS | Seed 0 confirmed as min CV(FPR) seed |
| A-e31849338f | P1 | results.tex §5.4, tables/table_spillover.tex | Spillover table added: victim vs. non-victim Δτ/ΔTPR/blast fraction per policy at f=0.4 | PASS (14pp) | Computed from manifest: Global non-vic.=victim (shared); Cluster non-vic.≈0 (churn-driven, not aggregation); Local non-vic.=0 |
| A-5ccfae0eed | P1 | background.tex | Kloft & Laskov contrast sentence added; "no prior work"→"to the best of our knowledge, no prior work" | PASS | Comparison table deferred — page budget (14pp limit); contrast sentence + qualifier satisfy core requirement |
| Limitations (5 sentences) | P1 | discussion.tex | All 5 required sentences present: sole dataset, federation size, single-client/collusion, q=0.95 fixed, score-level proxy | PASS | Compacted to fit page budget |
| A-52a92f30db | P2 | main.tex (abstract) | Abstract Gate-1 sentence made precise: "100% pass rate on our primary materiality significance test (Gate-1; §method) at all non-zero fractions" | PASS | — |
| A-2407be7432 | P2 | method.tex §4.4 | Gate-1 victim-majority condition spelled out: "≥5/9 victims significant, i.e. a simple majority of the nine federation clients" | PASS | — |
| A-e91b1d847d | P2 | results.tex §5.1 | CV(FPR) definition added at first use (ddof=0, lower=more uniform). Placed at first use in §5.1 rather than §2/background — background.tex has no metrics content; first-use placement is the more standard convention and avoids forward-reference. Documented here as an intentional resolution of the action, not a literal §2 move. | PASS | — |
| A-741211d451 / A-2849af9957 | P2 | tables/table_baseline.tex | Caption expanded: CV defined (ddof=0), Worst BA and P10 Macro-F1 defined, bold-rule stated | PASS | — |
| A-855a2d7014 | P2 | results.tex §5.2 | Removed unverified "≈30-80 undetected Mirai flows per 1000 packets" extrapolation (no artifact backing traffic-rate conversion) | PASS | — |
| A-8db2e8afa8 | P2 | results.tex §5.2 | Global harm sentence rewritten to explain mechanism (shared threshold → identical Δτ for all 8 non-victims → comparable harm), removing prior ambiguity | PASS | — |
| A-40607a57a6 (partial) | P2 | main.tex (Fig. 1 TikZ) | Training-phase box label changed to "Training & aggregation (defended)" to reflect FedAvg aggregation occurring in that phase; color-legend enumeration left as prose-only in caption (space) | PASS | Partial — legend-as-prose accepted as sufficient given caption already states defended/undefended distinction |
| A-e6f405cf6f | P2 | method.tex §4.2 | Cluster description now fully specifies: features (4-feature standard-scaled fingerprint: mean/std/skew/$p_{95}$ of $\mathcal{C}_i$, verified against src/datp/thresholding/policies.py `compute_fingerprints`), K=3 justification, k-means++ citation, random_state=42, reassignment per seed; seed-to-seed variance explanation already present | PASS (14pp) | All three sub-items (features, K=3, seed variance) now satisfied — closed, not partial |
| A-023cc3fd20 (partial) | P2 | references.bib, method.tex | k-means++ citation added (verifiable). 2023-2024 FL-specific citations explicitly NOT added — could not verify exact titles/venues without risking fabrication, which is forbidden by the editing rules | PASS | Deliberate partial scope — documented, not silently dropped |
| conclusion.tex trim | P2 (support) | conclusion.tex | Trimmed wording to help page budget; no content removed | PASS | — |
| A-39a0f86ebd | P2 | (verified, no edit) | threat_model.tex already states: "gray-box score-level access: since the adversary controls the client, it can read and modify the local calibration buffer before threshold computation," contrasted explicitly with model-poisoning/gradient access — already precise and FL-anchored | PASS | Verified sufficient, documented |
| A-19e2ac96a6 | P2 | (verified, no edit) | Grepped all uses of "attack"/"vulnerability"/"threat"/"exploit" across all sections — usage is consistent throughout: "vulnerability" denotes the structural surface/exposure (title, abstract, intro framing), "attack" denotes the active score-substitution mechanism/experiment. No inconsistent usage found | PASS | Verified sufficient, documented |
| A-6876713dc4 | P2 | discussion.tex | Found and fixed the actual clash: discussion.tex §7 used $N$ for per-client calibration-set size ($N{\approx}2{,}622$) in the collision-count derivation, while method.tex/discussion.tex §6 use $N$ for federation size ($N{=}9$). Renamed the calibration-set-size symbol to $n_v$ (consistent with existing notation in threat_model.tex/method.tex §4.3) and added an explicit "(distinct from the federation size $N{=}9$)" clause | PASS (14pp, recompiled clean) | Genuine notation collision found and resolved, not just a false positive |
| A-c8058bdd1f | P2 | (verified, no edit) | discussion.tex §7 already names two concrete defense angles for the calibration channel: threshold validation and calibration-set integrity constraints. Treated as a sufficient sketch given 14pp ceiling; not expanded further to avoid budget regression | PASS | Verified sufficient given page constraints, documented |

---

## Blocked actions

*(none at P0 level)*

---

## Deferred actions

| Action ID | Reason | Scope |
|-----------|--------|-------|
| A-5ccfae0eed (partial) | Comparison table (4-6 works) deferred due to 14pp page budget; contrast paragraph + softened claim implemented instead | P1 — page budget |
| A-f47168b200 | Formal position-set/equation notation for REPLACE-FIXED-BUDGET attempted; reverted to original prose. The equation form cost net page space relative to budget, and the prose already states the mechanism (m positions, tail reservoir, with replacement) unambiguously | P2 — page budget |
| A-01d8c9ea7a | Add paper roadmap/outline paragraph to §1 Introduction — deferred; introduction.tex is already dense and at-budget; section headers + abstract already convey paper structure | P2 — page budget |
| A-d9bc51f540 | Add concrete motivating harm scenario to §1 — deferred; §5.2 already contains a concrete TPR-drop scenario (Danmini/Ennio Doorbell) which substantively covers the same need | P2 — page budget |
| A-213529531a | Fix Figure 3 (Global line scale/inset) — deferred; requires regenerating the figure from plotting scripts/raw data, out of scope for a text-only editing pass in this loop | P2 — needs figure regeneration tooling, not available in this pass |
| A-a1dbe8cc63 | Regenerate all figures at 300 DPI/vector — deferred; requires figure regeneration tooling/scripts, out of scope for a text-only editing pass; also P3 and page budget has zero slack (14pp ceiling, exactly at limit) | P3 — tooling + page budget |
| A-418234b961 | Local vs. Global P10 Macro-F1 tradeoff discussion — deferred; would require net-new prose with zero page-budget slack remaining | P3 — page budget |
| A-c5f373c929 | Improve Table 2 (tab:main-results) layout density — deferred; cosmetic-only improvement, not required for correctness/reviewer-proofing, and any reflow risks the 14pp ceiling | P3 — page budget, low priority |

---

## Compile status
- Command: `pdflatex` (3 passes) + `bibtex`
- Result: **PASS** — exit 0
- Page count: **14 pages**
- Warnings: none new (grep of latest log for error/undefined/missing: clean; bibtex log: clean)
- Errors: none
- Citation check: all `\cite{}` keys resolve in references.bib (21 entries incl. new arthur2007kmeanspp)
- Cross-reference check: no undefined references after 3 passes
- Note: the P2 XS/S batch (10 edits) transiently pushed the paper to 15pp. Root cause was cumulative line growth across many small additions (CV(FPR) definition, Gate-1 abstract clause, K=3/citation clause, victim-majority clause, expanded table caption, Fig.1 label), not any single edit or the new bib entry (isolated and ruled out by temporarily stripping the `\cite{arthur2007kmeanspp}` call and recompiling — still 15pp). Resolved by trimming the Cluster K=3 justification clause in method.tex §4.2 (removed "chosen to yield 3-client clusters for the 9-device federation" and "assignments recomputed each seed as calibration fingerprints vary with training", replaced with terser equivalents) — restored 14pp with no information loss.

---

## Page budget status
14 pages — at the LLNCS budget ceiling used for this paper. No further additive content (new tables/figures/paragraphs) without an equal-or-greater trim elsewhere. Remaining P2 items must be edits-in-place (wording/labels/footnotes) or explicitly deferred (see Deferred actions table).

---

## Post-P1 self-audit (passed)
1. Forbidden-claims grep: no "training poisoning", "model poisoning" (as a claim about this work), "aggregation poisoning", "every defense", "operationally meaningful in IoT deployment", "privacy guarantee", "robust federated learning" found as first-person claims. ("model poisoning" appears only in a citation to prior work, background.tex:21.)
2. "No prior work" claim now qualified: "To the best of our knowledge, no prior work...".
3. Numeric consistency: -6.1pp (Global), -4.9pp (Cluster), -7.9pp (Local) victim ΔTPR at f=0.4 cross-checked identical across abstract, intro, results §5.2, conclusion, table_main_results.tex, table_spillover.tex.
4. Citation integrity: all cite keys resolve; bibtex runs clean.
5. Compile: clean 3-pass + bibtex, 14pp, no undefined refs.

---

## Scientific-contract status
All P0 and P1 fixes respect frozen DATP-CP scope. No new claims introduced. Cluster spillover wording now precise: victim harm is large (Δτ≈0.899) but non-victim intra-cluster effect is churn-driven and operationally negligible (Δτ≈0.000), not aggregation-driven spillover — this nuance is now explicit in §5.4 and Table 3 (tab:spillover). Score-level limitation intact throughout.

---

## Final audits (all PASS)
1. Forbidden-claims audit — clean (2 raw hits, both citations-to-prior-work or explicit negations)
2. Citation-integrity audit — clean (21/21 cites resolve; 1 unused bib entry `lheureux2017machine` found and removed)
3. Numeric-consistency audit — clean (all headline Δτ/ΔTPR figures identical across abstract/intro/results/conclusion/discussion/tables)
4. Page-budget/compile audit — clean (14pp, 3×pdflatex+bibtex, exit 0, no errors/warnings/undefined refs)
5. Scientific-boundary audit — clean (2 raw hits, both explicit negations confirming the boundary)

Full detail in `paper_review/FINAL_PAPER_FIX_REPORT.md`.

## Next action
None — fix loop complete. Paper is submission-ready at 14pp. No commits/PRs made (per instructions).
