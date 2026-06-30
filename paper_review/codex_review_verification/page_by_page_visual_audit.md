# Page-by-Page Visual Audit

Rendered pages are saved in `paper_review/codex_review_verification/rendered_pages/`.

| Page | Visual density | Figure/table placement | Font/caption readability | Overflow/cropping | Page-break issues | Submission-ready? |
|---:|---|---|---|---|---|---|
| 1 | Normal title/abstract density | No figures/tables | Readable | None | None | Yes |
| 2 | Dense intro | No figures/tables | Readable | None | None | Yes |
| 3 | Dense intro/background | No figures/tables | Readable | None | None | Yes |
| 4 | Normal threat model | No figures/tables | Readable | None | None | Yes |
| 5 | Normal method | No figures/tables | Readable | None | Good break into Table 1 next page | Yes |
| 6 | Normal with Table 1 | Table 1 fits width | Readable | None | None | Yes |
| 7 | Normal statistics/results start | No figures/tables | Readable | None | None | Yes |
| 8 | Normal with Figure 1 | Figure 1 placed cleanly above §5.2 | Labels/caption readable | None | None | Yes |
| 9 | Dense results | No figures/tables | Readable | None | None | Yes |
| 10 | Normal with Figure 2 | Figure 2 top; discussion begins below | Axis/device labels readable though small; caption clear | None | None | Yes |
| 11 | Dense with Figure 3 and Table 2 | Figure 3 and Table 2 fit | Figure 3 labels/legend and Table 2 caption readable | None | None | Yes |
| 12 | Dense with Tables 3 and 4 | Both tables fit width and page | Dense but readable; negative control rows visible | None | None | Yes |
| 13 | Normal conclusion/references | No figures/tables | Readable | None | References start cleanly | Yes |
| 14 | Normal references | No figures/tables | Readable | None | None | Yes |

## Explicit P3 Checks

| Item | Verdict |
|---|---|
| Figure 1 attack surface clarity | Pass. Calibration channel is visually distinct in red, training/aggregation in green, no text overlap, caption preserves calibration-channel-only boundary. |
| Figure 2 readability and seed-0 framing | Pass. Device labels/axes/legend are readable; caption states seed 0 and points to 10-seed Table 2 values. |
| Figure 3 readability and Random-Benign explanation | Pass. Panels, axes, error bars, and legend are readable; Global line is visible; caption explains Random-Benign omission and points to Table 3. |
| Tables | Pass. Tables 2, 3, and 4 are readable; abbreviations and bold conventions are defined; Cluster `±0.000` footnote is visible. |
| Whole PDF | Pass. No cropped figure/table, broken page, orphan heading, unreadable font, or bibliography visual defect found. |

