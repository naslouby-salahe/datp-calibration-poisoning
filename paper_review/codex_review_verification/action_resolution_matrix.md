# Action Resolution Matrix

The CSV file in this directory is the full machine-readable matrix. Summary counts over the 36 registered actions:

| Verification status | Count |
|---|---:|
| VERIFIED_RESOLVED | 28 |
| DEFERRED_ACCEPTABLE | 8 |
| PARTIALLY_RESOLVED | 0 |
| NOT_RESOLVED | 0 |
| REGRESSED | 0 |
| BLOCKED_ACCEPTABLE | 0 |
| DEFERRED_UNACCEPTABLE | 0 |
| NOT_APPLICABLE | 0 |

Key verification outcomes:

| Action ID | Priority | Independent status | Decision | Evidence |
|---|---|---|---|---|
| A-bc70838a10 | P0 | VERIFIED_RESOLVED | NO_ACTION_NEEDED | §4.3 lists all four source-objective pairs and the 4320-cell total. |
| A-5f02c65612 | P0 | VERIFIED_RESOLVED | NO_ACTION_NEEDED | Introduction, method, and results consistently state Local victim-only, Cluster intra-cluster/churn-level, Global fleet-wide. |
| A-a098e39ee7 | P0 | VERIFIED_RESOLVED | NO_ACTION_NEEDED | L'Heureux citation and bib entry are absent; threshold sensitivity is stated as quantile mechanics. |
| A-db7bcc5fcf | P0 | VERIFIED_RESOLVED | NO_ACTION_NEEDED | Table 2 footnote explains Cluster Macro-F1 std rounds from approximately 0.0002 to 0.000. |
| A-5ccfae0eed | P1 | DEFERRED_ACCEPTABLE | KEEP_DEFERRED | Kloft/Laskov contrast and softened no-prior-work claim are present; comparison table remains page-budget deferred. |
| A-e6f405cf6f | P2 | VERIFIED_RESOLVED | NO_ACTION_NEEDED | Cluster fingerprint matches code; I fixed the remaining equal-size cluster wording. |
| A-213529531a | P2 | DEFERRED_ACCEPTABLE | KEEP_DEFERRED | Figure 3 Global line is visible and caption explains 1/N dilution; inset remains low-value under page budget. |
| A-a1dbe8cc63 | P3 | VERIFIED_RESOLVED | NO_ACTION_NEEDED | The submitted figures are TikZ/PDF vector assets in the paper. |
| A-c5f373c929 | P3 | DEFERRED_ACCEPTABLE | KEEP_DEFERRED | Table 3 is dense but readable and not overflowing. |

All other P0/P1/P2 actions are `VERIFIED_RESOLVED` or `DEFERRED_ACCEPTABLE` for documented page-budget/fabrication-avoidance reasons; see `action_resolution_matrix.csv` for the full row-level evidence.

