# P3 Visual Action Plan

| Action ID | Issue | Location | Visual evidence | Safe to fix within 14 pages? | Requires figure regeneration? | Source artifact available? | Decision |
|---|---|---|---|---|---|---|---|
| A-a1dbe8cc63 | Regenerate figures at 300 DPI/vector | Figure 1, Figure 2, Figure 3 | Rendered pages 8, 10, 11 are readable; `paper/main.tex` uses TikZ and PDF figure assets. | Yes, no edit needed. | No. | Yes: `paper/figures/*.pdf`, TikZ in `main.tex`. | FIX_NOW |
| A-418234b961 | Add Local vs Global P10 Macro-F1 tradeoff discussion | Results/discussion | Policy tradeoff already discussed; Table 2 reports P10 Macro-F1. | No additive prose without risking page budget. | No. | N/A. | KEEP_DEFERRED_PAGE_BUDGET |
| A-c5f373c929 | Improve Table 2/Table 3 layout density | Table 3 on PDF p.12 | Table is dense but readable; no overflow or clipped columns. | Reflow could destabilize page budget. | No. | Yes: `paper/tables/table_main_results.tex`. | KEEP_DEFERRED_LOW_VALUE |
| A-213529531a | Figure 3 Global line scale/inset (P2 visual deferred item) | Figure 3 on PDF p.11 | Global line is visible; caption explains 1/N dilution. | Possible but not necessary; inset may increase size/complexity. | Yes, if implemented cleanly. | Partial: current PDF exists, but paper figure is already legible. | KEEP_DEFERRED_LOW_VALUE |

Note: For A-a1dbe8cc63, `FIX_NOW` means the issue is handled by verifying the current submitted assets are vector/PDF or TikZ; no source regeneration was required.

