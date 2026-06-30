# Codex Review Resolution Audit

## 1. Executive verdict

The previous fix loop mostly handled P0/P1/P2, but independent verification found one remaining precision issue in the Cluster policy description: the paper said `K=3 clusters of 3 clients each`, while k-means fixes only the number of clusters and the audit metadata shows seed-dependent cluster sizes. I corrected that wording in `paper/sections/method.tex`.

After that fix, P0/P1/P2 are reviewer-safe: no P0/P1 blocker remains, and all P2 omissions are acceptable page-budget or citation-integrity deferrals.

## 2. Verification method

Checked prior reports and registers:

| Source | Purpose |
|---|---|
| `paper_review/05_final_outputs/02_prioritized_action_checklist.md` | Full action inventory and priority. |
| `paper_review/03_action_register/action_register.md` | Detailed action intent. |
| `paper_review/PAPER_FIX_STATUS.md` | Previous claimed status and deferred items. |
| `paper_review/FINAL_PAPER_FIX_REPORT.md` | Previous final claims. |
| `paper_review/03_action_register/*ledger.md` | Wording/visual/experiment constraints. |
| `docs/DATP_CP_Roadmap.md` | Frozen protocol and boundary checks. |

Checked actual source and artifacts:

| Area | Files/artifacts |
|---|---|
| LaTeX source | `paper/main.tex`, `paper/sections/*.tex`, `paper/tables/*.tex`, `paper/references.bib` |
| Implementation | `src/datp/thresholding/policies.py`, `src/datp/core/enums.py`, `src/datp/conf/config.yaml` |
| Result metadata | `artifacts/audit/cluster_assignments.csv`, figure/table outputs |
| PDF | `paper/main.pdf`, rendered pages in `paper_review/codex_review_verification/rendered_pages/` |

Compile command used because `latexmk` is unavailable:

```bash
cd paper
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

## 3. P0 verification

| P0 item | Status | Evidence | Remaining risk |
|---|---|---|---|
| A-a098e39ee7 | VERIFIED_RESOLVED | L'Heureux removed from `references.bib`; threshold sensitivity stated in `background.tex` as quantile mechanics. | None. |
| A-bc70838a10 | VERIFIED_RESOLVED | `method.tex` lists all four source-objective pairs, including Random-Benign raise and lower controls. | None. |
| A-5f02c65612 | VERIFIED_RESOLVED | Contributions and §5.4 consistently distinguish Local, Cluster, and Global spillover. | None. |
| A-db7bcc5fcf | VERIFIED_RESOLVED | `table_baseline.tex` footnote explains actual std approximately 0.0002 rounds to 0.000. | None. |

## 4. P1 verification

| P1 item | Status | Evidence | Remaining risk |
|---|---|---|---|
| Code availability | VERIFIED_RESOLVED | Conclusion contains code/artifact availability statement. | None. |
| Forbidden defense/deployment wording | VERIFIED_RESOLVED | No "every defense" or deployment-readiness claim remains; scope section negates deployability/generalization. | None. |
| Score-level proxy caveat | VERIFIED_RESOLVED | Abstract, threat model, and discussion all state score-level/traffic-level future-work boundary. | None. |
| Bootstrap/gates/lowering framing | VERIFIED_RESOLVED | §4.4 and §5.3 contain the caveat, gate constants, and alarm-burden-first interpretation. | None. |
| Reproducibility table | VERIFIED_RESOLVED | Table 1 lists AE, FedAvg, optimizer, rounds, batch size, and calibration sizes. | None. |
| Random-Benign negative controls | VERIFIED_RESOLVED | Table 3 has Neg. Ctrl rows with G1=0%; Fig. 3 caption explicitly points to them. | None. |
| Figure 2 seed/Cluster concern | VERIFIED_RESOLVED | Caption gives seed-0 CV plus 10-seed mean±std and points Cluster to Table 2. | None. |
| Spillover table | VERIFIED_RESOLVED | Table 4 quantifies victim/non-victim threshold shift and blast. | None. |
| Related-work expansion | DEFERRED_ACCEPTABLE | Kloft/Laskov contrast and qualified no-prior-work claim are present. | Comparison table remains deferred due to 14-page ceiling; acceptable because core credibility risk is fixed. |

## 5. P2 verification

| P2 item | Status | Evidence | Remaining risk |
|---|---|---|---|
| Gate/CV/table definitions | VERIFIED_RESOLVED | Abstract, §4.4, §5.1, and table captions define Gate-1, victim-majority, CV(FPR), Worst BA, P10 Macro-F1, and bold conventions. | None. |
| Threat/boundary language | VERIFIED_RESOLVED | Threat model states no model weights, gradients, training/test data, test labels, or labels changed. | None. |
| Global victim/fleet disambiguation | VERIFIED_RESOLVED | Results and Table 4 explain victim harm and non-victim shared threshold effect. | None. |
| Cluster fingerprint/K/variance | VERIFIED_RESOLVED | Fingerprint is mean/std/skew/p95 in both paper and code; K=3/random_state=42/reassignment stated; equal-size implication removed. | None. |
| Notation collision | VERIFIED_RESOLVED | Discussion uses `n_v` for calibration-set size and distinguishes `N=9`. | None. |
| Defense sketch | VERIFIED_RESOLVED | Discussion names threshold validation and calibration-set integrity constraints. | None. |
| Formal equation, roadmap, intro scenario, Figure 3 inset, unverified recent FL citations | DEFERRED_ACCEPTABLE | Existing prose/captions cover reviewer-facing meaning; additions would consume page budget or risk fabricated citations. | Non-blocking. |

## 6. Regression checks

No previous P0/P1 fix was undone. One P2 Cluster wording regression was found and fixed: `K=3 clusters of 3 clients each` was changed to `K=3`, because the implementation and audit metadata do not guarantee balanced cluster sizes.

## 7. Scientific-boundary checks

Forbidden claims were searched and checked in context. Raw hits for Byzantine, privacy, deployment, model poisoning, gradients, and evasion are either prior-work context, contrastive threat-model exclusions, future-work statements, or explicit negations. The paper still preserves:

- post-training benign calibration-channel poisoning only;
- score-level proxy only;
- N-BaIoT physical-device clients as main evidence;
- FedAvg autoencoder;
- `GLOBAL_THRESHOLD`, `LOCAL_THRESHOLD`, `CLUSTER_THRESHOLD`;
- single-client compromise;
- paired clean-vs-poisoned comparison;
- training data, model weights, aggregation, test scores, and test labels unchanged.

## 8. Page-budget and compile checks

| Item | Result |
|---|---|
| PDF path | `paper/main.pdf` |
| Page count | 14 |
| Compile result | PASS |
| Citation/reference status | 21 used citations, 21 resolved, 0 unused bib entries |
| Warnings/boxes | Three small overfull boxes (4.89pt, 3.72pt, 0.70pt) and one bibliography underfull box; no visible damage. |

## 9. Decision

P0/P1/P2 verified; proceed to P3.

