# Prioritized Action Checklist

This is the working checklist for revisions. Check each item off as completed.
Items are ordered: P0 first, then P1, then P2, then P3.
Within each priority, shortest effort first.

---

## P0 — Do Before Anything Else

- [ ] **A-bc70838a10** `[XS]` Fix "4 source-objective pairs" — correct to 3 or describe the 4th  
  _→ §4 / §1 Contributions_

- [ ] **A-5f02c65612** `[S]` Fix Contributions item 3 vs. §4.2/§5.4 spillover contradiction  
  _→ §1 Contributions item 3 + §4.2 + §5.4_  
  _Choose: spillover is policy-dependent (Local=none, Cluster=intra-cluster, Global=fleet-wide)_

- [ ] **A-a098e39ee7** `[S]` Verify Reference [12] (L'heureux 2017) — correct if wrong  
  _→ §3 + references.bib_  
  _CRITICAL: open the paper; verify claim support; fix or remove_

- [ ] **A-db7bcc5fcf** `[M]` Explain Cluster Macro-F1 ± 0.000 — investigate results pipeline  
  _→ Table 1 + code_

---

## P1 — Required for Submission

- [ ] **A-664b8440ed** `[XS]` Add artifact/code availability statement  
  _→ §1 or §7_

- [ ] **A-f8c713ec0c** `[XS]` Remove "every defense" and deployment language  
  _→ Abstract + §1_  
  _"every defense" → "no existing defense that monitors the calibration channel"_  
  _Remove "operationally meaningful in IoT deployment contexts"_

- [ ] **A-e102f26659** `[S]` Add score-level proxy caveat; fix attack/characterization language  
  _→ Abstract + §1 + §2 + §6_

- [ ] **A-df1fb64bdd** `[S]` Add BCa bootstrap caveat for N=10 seeds  
  _→ §6 Statistics_

- [ ] **A-9c654c5a5e** `[S]` Justify gate constants and three-gate framework  
  _→ §6 Statistics_

- [ ] **A-01a7255dbd** `[S]` Reframe lowering attack: ΔFPR alarm burden first, ΔTPR secondary  
  _→ Abstract + §5.3_

- [ ] **A-f3e11e1509** `[M]` Add reproducibility table (AE arch, FedAvg config, splits, features)  
  _→ §2 / new Table_

- [ ] **A-1975d011a9** `[M]` Add Random-Benign rows to Table 2; add RB line to Figure 3  
  _→ Table 2 + Figure 3_

- [ ] **A-984973914d** `[M]` Fix Figure 2: add Cluster; add seeds or justify seed 0  
  _→ Figure 2_

- [ ] **A-e31849338f** `[M]` Add spillover quantification table (victim vs. non-victim)  
  _→ §5.4 + new Table_

- [ ] **A-5ccfae0eed** `[M]` Expand related work: Kloft & Laskov contrast; add comparison table  
  _→ §3 Related Work_

---

## P2 — Strongly Recommended

- [ ] **A-741211d451** `[XS]` Define BAP10/P10/Worst BA in Table 1 footnote  
- [ ] **A-2849af9957** `[XS]` State bold convention direction in Table 1 + Table 2 captions  
- [ ] **A-52a92f30db** `[XS]` Define Gate-1 at first use in abstract; forward-reference  
- [ ] **A-39a0f86ebd** `[XS]` Add precise gray-box definition anchored to FL setup  
- [ ] **A-f47168b200** `[XS]` Add formal contamination equation for REPLACE-FIXED-BUDGET  
- [ ] **A-19e2ac96a6** `[XS]` Standardize attack vs. vulnerability language throughout  
- [ ] **A-40607a57a6** `[XS]` Fix Figure 1: add color legend; correct "training defended" label  
- [ ] **A-e91b1d847d** `[XS]` Move CV(FPR) definition to §2  
- [ ] **A-2407be7432** `[XS]` Justify victim-majority condition (≥5/9 clients) for Global  
- [ ] **A-01d8c9ea7a** `[XS]` Add paper roadmap to §1 Introduction  
- [ ] **A-213529531a** `[XS]` Fix Figure 3: adjust scale or add inset for Global line  
- [ ] **A-8db2e8afa8** `[XS]` Disambiguate victim vs. fleet ΔTPR in Global results  
- [ ] **A-d9bc51f540** `[XS]` Add concrete motivating harm scenario to §1  
- [ ] **A-023cc3fd20** `[XS]` Add 2023-2024 FL citations; add K-means++ citation (Arthur & Vassilvitskii 2007)  
- [ ] **A-6876713dc4** `[XS]` Disambiguate N notation in §6 (|F|=9 vs. n_cal≈2622)  
- [ ] **A-855a2d7014** `[S]` Remove or derive "30-80 undetected Mirai flows" claim  
- [ ] **A-c8058bdd1f** `[S]` Add defense requirements sketch to Discussion  
- [ ] **A-e6f405cf6f** `[S]` Specify Cluster: features, K=3 justification, seed variance  

---

## P3 — Nice to Have

- [ ] **A-a1dbe8cc63** `[XS]` Regenerate all figures at 300 DPI / vector (PDF/SVG)  
- [ ] **A-418234b961** `[XS]` Add discussion of Local vs. Global P10 Macro-F1 tradeoff  
- [ ] **A-c5f373c929** `[S]` Improve Table 2 layout density  

---

## Limitations Text Additions (No Action ID — Direct Edit)

The following items need a sentence added to the Limitations section (§7 or Discussion). No action entry needed — just add the sentences:

- [ ] N-BaIoT is the sole dataset; generalizability to other federated IoT datasets is an open question
- [ ] Federation comprises nine physical devices; behavior at larger sizes is unknown  
- [ ] Single-client compromise; multi-client collusion is a natural extension
- [ ] q=0.95 is fixed; quantile sensitivity is left to future work
- [ ] Score-level proxy: traffic-level realization of calibration-buffer access is future work

---

## Total Count

| Priority | Count | XS | S | M |
|----------|-------|----|---|---|
| P0 | 4 | 1 | 2 | 1 |
| P1 | 11 | 2 | 4 | 5 |
| P2 | 18 | 14 | 4 | 0 |
| P3 | 3 | 2 | 1 | 0 |
| **Total** | **36** | **19** | **11** | **6** |
